import imaplib
import email
from voice_utils import speak

def read_emails(username, password):
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(username, password)
        mail.select("inbox")
        _, search_data = mail.search(None, "UNSEEN")
        email_ids = search_data[0].split()
        if not email_ids:
            speak("You have no new emails.")
            return
        for e_id in email_ids[:3]:  # Read latest 3
            _, msg_data = mail.fetch(e_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject = msg["subject"]
                    from_ = msg["from"]
                    speak(f"New email from {from_}, subject: {subject}")
        mail.logout()
    except Exception:
        speak("Failed to fetch emails.")
