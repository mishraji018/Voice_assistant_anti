import platform
import psutil
from core.audio.voice_utils import speak

def run(command_text: str) -> str:
    """Standardized entry point for system command."""
    return get_system_report()

def get_system_report():
    try:
        uname = platform.uname()
        cpu_usage = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        report = (
            f"System: {uname.system}, Node: {uname.node}. "
            f"Release: {uname.release}, Version: {uname.version}. "
            f"Machine: {uname.machine}, Processor: {uname.processor}. "
            f"CPU Usage is {cpu_usage}%. "
            f"Available RAM: {ram.available // (1024 ** 2)} MB."
        )
        return report
    except Exception:
        return "Failed to get system information."
