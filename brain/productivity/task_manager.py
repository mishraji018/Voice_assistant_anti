
import sqlite3
import re
import threading
import time
from datetime import datetime
import logging
from brain.infra.database import connect_db

logger = logging.getLogger(__name__)

class TaskManager:
    """
    Manages daily tasks, to-do lists, and time-based reminders.
    """
    def __init__(self, response_manager=None):
        self.rm = response_manager
        self._stop_checker = threading.Event()
        self.checker_thread = None
        self._ensure_schema()

    def _ensure_schema(self):
        """Create task table when TaskManager is initialized standalone."""
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks_table (
                task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                task TEXT NOT NULL,
                time TEXT,
                status TEXT DEFAULT 'pending',
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
        conn.close()

    def start_reminder_checker(self):
        """Starts a background thread to check for due reminders."""
        if self.checker_thread and self.checker_thread.is_alive(): return
        self._stop_checker.clear()
        self.checker_thread = threading.Thread(target=self._reminder_loop, daemon=True)
        self.checker_thread.start()
        print("[Productivity] Reminder checker started.")

    def stop_reminder_checker(self):
        self._stop_checker.set()

    def _reminder_loop(self):
        while not self._stop_checker.is_set():
            now = datetime.now().strftime("%I:%M %p") # e.g. "05:00 PM"
            self._check_and_alert(now)
            time.sleep(30) # Check every 30 seconds

    def _check_and_alert(self, current_time: str):
        conn = connect_db()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT task_id, task FROM tasks_table WHERE time = ? AND status = 'pending'", (current_time,))
            rows = cursor.fetchall()
            for row_id, task_text in rows:
                msg = f"Sir, reminder: {task_text}."
                if self.rm:
                    self.rm.speak(msg, use_female=True)
                # Mark as completed to avoid double alert
                cursor.execute("UPDATE tasks_table SET status = 'completed' WHERE task_id = ?", (row_id,))
            conn.commit()
        except Exception as e:
            logger.error(f"[Productivity] Reminder error: {e}")
        finally:
            conn.close()

    def handle_query(self, text: str) -> str:
        """Process natural language for task management."""
        text_lower = text.lower().strip()

        # 1. Add Task/Reminder
        # "Remind me to [Task] at [Time]" or "Add task [Task]"
        add_match = re.search(r"(?:remind me to|add task|task add)\s+(?P<task>.*?)(?:\s+at\s+(?P<time>\d{1,2}:\d{2}\s*(?:am|pm|a.m.|p.m.)))?$", text_lower)
        if add_match:
            task = add_match.group("task").strip()
            time_val = add_match.group("time")
            if time_val:
                time_val = time_val.upper().replace(".", "") # Standardize to AM/PM
            self.add_task(task, time_val)
            if time_val:
                return f"Sir, I've added your task '{task}' and set a reminder for {time_val}."
            return f"Sir, I've added '{task}' to your task list."

        # 2. List Tasks
        if any(w in text_lower for w in ["what are my tasks", "show tasks", "list tasks", "my schedule"]):
            tasks = self.get_all_tasks()
            if not tasks: return "Sir, aapki task list abhi khali hai."
            
            resp = "Sir, here are your pending tasks: "
            task_strings = []
            for t in tasks:
                t_str = f"{t['task']}"
                if t['time']: t_str += f" at {t['time']}"
                task_strings.append(t_str)
            return resp + ", ".join(task_strings)

        # 3. Clear Tasks
        if any(w in text_lower for w in ["clear tasks", "remove all tasks", "delete tasks"]):
            self.clear_all_tasks()
            return "Sir, maine saari tasks clear kar di hain."

        return None

    def add_task(self, task: str, time_val: str = None):
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO tasks_table (task, time) VALUES (?, ?)", (task, time_val))
        conn.commit()
        conn.close()

    def get_all_tasks(self):
        conn = connect_db()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT task, time FROM tasks_table WHERE status = 'pending'")
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

    def clear_all_tasks(self):
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks_table")
        conn.commit()
        conn.close()

# Singleton logic handled in Orchestrator for RM dependency
