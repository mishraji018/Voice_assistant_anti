from voice_control import take_command
from text_to_speech import speak
from task_automation import do_task
from command_weather import get_weather
from command_calculator import calculate
from command_reminder import set_reminder
from command_jokes import tell_joke
from command_email import send_email
from command_news import get_news
from command_music import play_music
from command_system import system_info
from command_hardware import wifi_control
from command_calendar import get_calendar_events
from command_todo import add_todo, list_todos
from command_translate import translate_text
from command_notes import take_note
from command_dict import define_word
from command_battery import battery_status
from command_bluetooth import bluetooth_control
from command_quotes import daily_quote
from command_email_check import read_emails
from command_youtube import search_youtube
from command_stock import get_stock_price
from command_google_search import google_search
from command_screenshot import take_screenshot
from command_clipboard import read_clipboard
from command_pdf_reader import read_pdf
from command_code_runner import run_python_code
from command_random_number import random_number
from command_horoscope import get_horoscope

def wish():
    import datetime
    hour = datetime.datetime.now().hour
    if hour < 12:
        speak("Good morning!")
    elif hour < 18:
        speak("Good afternoon!")
    else:
        speak("Good evening!")
    speak("I am Jarvis. How may I help you?")


def run_jarvis():
    wish()
    while True:
        query = take_command()
        if not query:
            continue
        if 'weather' in query:
            get_weather("Delhi")  # Or parse city from query for dynamic city
        elif 'calculate' in query:
            expression = query.replace('calculate', '').strip()
            calculate(expression)
        elif 'remind me' in query:
            message = query.replace('remind me', '').strip()
            set_reminder(message)
        elif 'joke' in query:
            tell_joke()
        elif 'send email' in query:
            # You'd parse to_address, subject, message from the query or ask interactively
            send_email("recipient@gmail.com", "Test Subject", "Hello from Jarvis!")
        # ... existing commands ...


def run_jarvis():
    wish()
    while True:
        query = take_command()
        if 'exit' in query or 'goodbye' in query:
            speak("Goodbye!")
            break
        do_task(query, speak)


if __name__ == "__main__":
    run_jarvis()
elif 'news' in query or 'headlines' in query:
    get_news()
elif 'play music' in query:
    play_music()
elif 'system info' in query:
    system_info()
elif 'wifi on' in query:
    wifi_control(True)
elif 'wifi off' in query:
    wifi_control(False)
elif 'calendar' in query or 'events' in query:
    get_calendar_events()
elif 'add task' in query or 'add todo' in query:
    task = query.replace('add task', '').replace('add todo', '').strip()
    add_todo(task)
elif 'show tasks' in query or 'list todos' in query:
    list_todos()
elif 'translate' in query:
    text = query.replace('translate', '').strip()
    translate_text(text)
elif 'note' in query:
    take_note()
elif 'define' in query:
    word = query.replace('define', '').strip()
    define_word(word)
elif 'battery' in query:
    battery_status()
elif 'bluetooth on' in query:
    bluetooth_control(True)
elif 'bluetooth off' in query:
    bluetooth_control(False)
elif 'quote' in query or 'motivation' in query:
    daily_quote()
elif 'check emails' in query:
    read_emails("your@gmail.com", "yourpassword")
elif 'youtube' in query:
    search_youtube(query.replace('youtube', '').strip())
elif 'stock' in query:
    symbol = query.split()[-1]   # e.g. "stock AAPL"
    get_stock_price(symbol)
elif 'google' in query:
    google_search(query.replace('google', '').strip())
elif 'screenshot' in query:
    take_screenshot()
elif 'clipboard' in query:
    read_clipboard()
elif 'summarize' in query:
    summarize_text(query.replace('summarize', '').strip())
elif 'read pdf' in query:
    read_pdf("example.pdf")
elif 'add reminder' in query:
    reminder = query.replace('add reminder', '').strip()
    add_reminder(reminder, "2025-11-06 18:00")  # For demo – parse actual datetime
elif 'check reminders' in query:
    check_reminders()
elif 'run code' in query:
    code = query.replace('run code', '').strip()
    run_python_code(code)
elif 'random number' in query:
    random_number()
elif 'horoscope' in query:
    get_horoscope('aries')  # For demo – parse real sign if needed

