import threading
from core.core import run_core_loop
from ui.visual_ui import JarvisUI

if __name__ == "__main__":
    # 1. Create the UI instance (but don't start the mainloop yet)
    ui = JarvisUI(frameless=False)
    
    # 2. Start the Jarvis core loop in a side thread
    # This thread will call ui.set_state() and ui.set_subtitle()
    core_thread = threading.Thread(target=run_core_loop, args=(ui,), daemon=True)
    core_thread.start()
    
    # 3. Run the UI mainloop on the main thread
    # This blocks until the window is closed
    ui.run()
