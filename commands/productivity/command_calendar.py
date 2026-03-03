import os
from core.audio.voice_utils import speak

def get_calendar_events():
    try:
        from googleapiclient.discovery import build
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        import pickle
        import datetime
        SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
        creds = None
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        service = build('calendar', 'v3', credentials=creds)
        now = datetime.datetime.utcnow().isoformat() + 'Z' 
        events_result = service.events().list(calendarId='primary', timeMin=now,
                                              maxResults=5, singleEvents=True,
                                              orderBy='startTime').execute()
        events = events_result.get('items', [])
        if not events:
            speak("No upcoming events found.")
        else:
            speak("Your upcoming events are:")
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                speak(f"{event['summary']} at {start}")
    except Exception as e:
        speak("Failed to read calendar events.")
