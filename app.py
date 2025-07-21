from flask import Flask, request, redirect, render_template_string
from datetime import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import os
import base64

app = Flask(__name__)

# 🔐 Crear archivos desde variables de entorno (Render)
credentials_b64 = os.getenv("CREDENTIALS_JSON_B64")
if credentials_b64:
    with open("credentials.json", "wb") as f:
        f.write(base64.b64decode(credentials_b64))

token_b64 = os.getenv("TOKEN_JSON_B64")
if token_b64:
    with open("token.json", "wb") as f:
        f.write(base64.b64decode(token_b64))

# SCOPES
SCOPES = ['https://www.googleapis.com/auth/calendar']

# Token y credenciales
creds = None
if os.path.exists('token.json'):
    creds = Credentials.from_authorized_user_file('token.json', SCOPES)
else:
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    creds = flow.run_local_server(port=5001)
    with open('token.json', 'w') as token:
        token.write(creds.to_json())

# Servicio de Google Calendar
service = build('calendar', 'v3', credentials=creds)

# HTML del formulario
formulario_html = '''
<!doctype html>
<title>Crear Evento</title>
<h1>Crear Evento en Google Calendar</h1>
<form method="POST">
  Título: <input type="text" name="summary"><br>
  Fecha inicio (YYYY-MM-DD HH:MM): <input type="text" name="start"><br>
  Fecha fin (YYYY-MM-DD HH:MM): <input type="text" name="end"><br>
  <input type="submit" value="Crear">
</form>
'''

@app.route('/crear_evento', methods=['GET', 'POST'])
def crear_evento():
    if request.method == 'POST':
        summary = request.form['summary']
        start = request.form['start']
        end = request.form['end']

        event = {
            'summary': summary,
            'start': {
                'dateTime': datetime.strptime(start, "%Y-%m-%d %H:%M").isoformat(),
                'timeZone': 'America/Panama',
            },
            'end': {
                'dateTime': datetime.strptime(end, "%Y-%m-%d %H:%M").isoformat(),
                'timeZone': 'America/Panama',
            },
        }

        event = service.events().insert(calendarId='primary', body=event).execute()
        return f"✅ Evento creado: <a href='{event.get('htmlLink')}' target='_blank'>Ver en Google Calendar</a>"

    return render_template_string(formulario_html)

# Ejecutar servidor Flask (modo local solo si es necesario)
if __name__ == '__main__':
    app.run(port=5001, debug=True)