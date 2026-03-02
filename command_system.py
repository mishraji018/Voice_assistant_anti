import platform
import psutil
from voice_utils import speak

def system_info():
    try:
        uname = platform.uname()
        cpu_usage = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        speak(f"System: {uname.system}, Node: {uname.node}")
        speak(f"Release: {uname.release}, Version: {uname.version}")
        speak(f"Machine: {uname.machine}, Processor: {uname.processor}")
        speak(f"CPU Usage is {cpu_usage}%")
        speak(f"Available RAM: {ram.available // (1024 ** 2)} MB")
    except Exception:
        speak("Failed to get system information.")
