import smtplib
from core.audio.voice_utils import speak

def send_email(to_address, subject, message):
    try:
        # Replace with your credentials and server
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login("your_email@gmail.com", "your_password")
        email_message = f"Subject: {subject}\n\n{message}"
        server.sendmail("your_email@gmail.com", to_address, email_message)
        server.close()
        speak("Email sent successfully.")
    except Exception:
        speak("Failed to send email.")
