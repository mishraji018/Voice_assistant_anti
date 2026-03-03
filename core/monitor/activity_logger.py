
import psutil
import threading
import time
import os
from datetime import datetime
from brain.infra.database import log_activity, cleanup_old_activity

class ActivityLogger(threading.Thread):
    """
    Background thread tracking system activity.
    Records opened applications and files to SQLite and jarvis.txt.
    """
    def __init__(self):
        super().__init__(daemon=True)
        self.running = True
        self.known_pids = set()

    def run(self):
        # Initial cleanup on startup
        cleanup_old_activity()
        
        # Populate initial PIDs to only track NEW ones
        self.known_pids = {p.pid for p in psutil.process_iter()}
        
        while self.running:
            try:
                for proc in psutil.process_iter(['pid', 'name', 'exe']):
                    if proc.info['pid'] not in self.known_pids:
                        name = proc.info['name']
                        exe = proc.info['exe'] or "Unknown Path"
                        
                        # Log the new activity
                        log_activity("OPEN_APP", name, exe)
                        self.known_pids.add(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            
            # Maintenance: Remove dead PIDs from known set every 10 mins
            # (Simplified for performance)
            
            time.sleep(5) # Poll every 5 seconds for new apps

def start_logger():
    logger = ActivityLogger()
    logger.start()
    return logger # Return instance if needed for control
