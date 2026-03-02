from io import StringIO
import sys
from voice_utils import speak

def run_python_code(code):
    old_stdout = sys.stdout
    redirected_output = sys.stdout = StringIO()
    try:
        exec(code)
        output = redirected_output.getvalue()
        speak(f"Code output: {output.strip()}")
    except Exception as e:
        speak(f"Error: {str(e)}")
    finally:
        sys.stdout = old_stdout
