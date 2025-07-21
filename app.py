from flask import Flask, request, jsonify, render_template_string
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import os
import base64

app = Flask(__name__)

# Cargar archivos desde entorno (Render)
credentials_b64 = os.getenv("CREDENTIALS_JSON_B64")
if credentials_b64:
    with open("credentials.json", "wb") as f:
        f.write(base64.b64decode(credentials_b64))

token_b64 = os.getenv("TOKEN_JSON_B64")
if token_b64:
    with open("token.json", "wb") as f:
        f.write(base64.b64decode(token_b64))

# Autenticación
SCOPES = ['https://www.googleapis.com/auth/calendar']
creds = Credentials.from_authorized_user_file('token.json', SCOPES)
service = build('calendar', 'v3', credentials=creds)

@app.route('/')
def home():
    return '🗓️ API Agenda activa.'

# 1. Crear evento
@app.route('/crear_evento', methods=['POST'])
def crear_evento():
    data = request.json
    summary = data['summary']
    start = datetime.strptime(data['start'], "%Y-%m-%d %H:%M")
    end = datetime.strptime(data['end'], "%Y-%m-%d %H:%M")

    event = {
        'summary': summary,
        'start': {'dateTime': start.isoformat(), 'timeZone': 'America/Panama'},
        'end': {'dateTime': end.isoformat(), 'timeZone': 'America/Panama'}
    }

    created = service.events().insert(calendarId='primary', body=event).execute()
    return jsonify({
        "message": "Evento creado",
        "link": created.get('htmlLink')
    })

# 2. Leer agenda
@app.route('/leer_agenda', methods=['GET'])
def leer_agenda():
    rango = request.args.get('rango')  # diario, semanal, mensual
    ahora = datetime.utcnow()
    
    if rango == "diario":
        inicio = ahora
        fin = ahora + timedelta(days=1)
    elif rango == "semanal":
        inicio = ahora
        fin = ahora + timedelta(days=7)
    elif rango == "mensual":
        inicio = ahora
        fin = ahora + timedelta(days=30)
    else:
        return jsonify({"error": "Rango inválido"}), 400

    eventos = service.events().list(
        calendarId='primary',
        timeMin=inicio.isoformat() + 'Z',
        timeMax=fin.isoformat() + 'Z',
        singleEvents=True,
        orderBy='startTime'
    ).execute().get('items', [])

    resultado = []
    for evento in eventos:
        resultado.append({
            "id": evento['id'],
            "titulo": evento.get('summary', 'Sin título'),
            "inicio": evento['start'].get('dateTime'),
            "fin": evento['end'].get('dateTime'),
        })

    return jsonify(resultado)

# 3. Eliminar evento
@app.route('/eliminar_evento/<id_evento>', methods=['DELETE'])
def eliminar_evento(id_evento):
    service.events().delete(calendarId='primary', eventId=id_evento).execute()
    return jsonify({"message": "Evento eliminado"})

# 4. Modificar evento
@app.route('/modificar_evento/<id_evento>', methods=['PATCH'])
def modificar_evento(id_evento):
    data = request.json
    event = service.events().get(calendarId='primary', eventId=id_evento).execute()

    if 'summary' in data:
        event['summary'] = data['summary']
    if 'start' in data:
        event['start']['dateTime'] = datetime.strptime(data['start'], "%Y-%m-%d %H:%M").isoformat()
    if 'end' in data:
        event['end']['dateTime'] = datetime.strptime(data['end'], "%Y-%m-%d %H:%M").isoformat()

    updated_event = service.events().update(calendarId='primary', eventId=id_evento, body=event).execute()
    return jsonify({"message": "Evento modificado", "link": updated_event.get('htmlLink')})

# 5. Sugerir horario disponible
@app.route('/sugerir_horario', methods=['GET'])
def sugerir_horario():
    duracion = int(request.args.get('duracion', 30))  # en minutos
    ahora = datetime.utcnow()
    fin = ahora + timedelta(days=1)

    eventos = service.events().list(
        calendarId='primary',
        timeMin=ahora.isoformat() + 'Z',
        timeMax=fin.isoformat() + 'Z',
        singleEvents=True,
        orderBy='startTime'
    ).execute().get('items', [])

    bloque_inicio = ahora
    for evento in eventos:
        inicio_evento = datetime.fromisoformat(evento['start']['dateTime'])
        if (inicio_evento - bloque_inicio).total_seconds() >= duracion * 60:
            sugerencia = bloque_inicio.strftime("%Y-%m-%d %H:%M")
            return jsonify({"sugerido": sugerencia})
        bloque_inicio = datetime.fromisoformat(evento['end']['dateTime'])

    return jsonify({"mensaje": "No hay bloques disponibles en las próximas 24h"})

# 6. Servir el archivo openapi.yaml
@app.route('/openapi.yaml')
def openapi():
    with open('openapi.yaml', 'r') as f:
        content = f.read()
    return render_template_string(content), 200, {'Content-Type': 'text/yaml'}

# Ejecutar local
if __name__ == '__main__':
    app.run(port=5001, debug=True)