import os
import json
import shutil
import logging
import threading
import requests
from dotenv import load_dotenv

try:
    import keyring
except ImportError:
    logging.warning("keyring not installed, secrets will fallback to config.json")
    keyring = None

CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.json")
CONFIG_BACKUP_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.backup.json")
ENV_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
KEYRING_SERVICE = "JARVIS_Voice_Assistant"

DEFAULT_CONFIG = {
    "version": 2,
    "ai_models": {
        "default_llm": "groq_llama3"
    },
    "services": {
    },
    "general": {
        "wake_word": "jarvis",
        "language": "en"
    }
}

# The keys we want to store in Keyring instead of plain text
SECRET_KEYS = ["groq_api_key", "elevenlabs_api_key", "openweather_api_key", "alphavantage_api_key", "deepgram_api_key"]

class ConfigManager:
    def __init__(self):
        self._config = DEFAULT_CONFIG.copy()
        self._load()

    def _load(self):
        """Loads configuration from config.json, with backup fallback."""
        if not os.path.exists(CONFIG_FILE) and os.path.exists(ENV_FILE):
            self._migrate_from_env()
        
        file_config = None
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    file_config = json.load(f)
            except Exception as e:
                logging.error(f"Failed to load config.json: {e}")
                
        # Fallback to backup if corrupted
        if not file_config and os.path.exists(CONFIG_BACKUP_FILE):
            logging.info("Restoring config from backup...")
            try:
                with open(CONFIG_BACKUP_FILE, "r") as f:
                    file_config = json.load(f)
                shutil.copy(CONFIG_BACKUP_FILE, CONFIG_FILE)
            except Exception as e:
                logging.error(f"Failed to restore backup: {e}")

        if file_config:
            # Deep merge to ensure new keys exist
            for section, values in DEFAULT_CONFIG.items():
                if section not in file_config:
                    file_config[section] = values
                elif isinstance(values, dict):
                    for key, val in values.items():
                        if key not in file_config[section]:
                            file_config[section][key] = val
            self._config = file_config
            self._config["version"] = 2 # Force version to current
        else:
            self._save()

    def _migrate_from_env(self):
        """Migrates legacy .env variables to keyring."""
        logging.info("Migrating legacy .env file to keyring...")
        load_dotenv(dotenv_path=ENV_FILE)
        
        for key, env_name in [("groq_api_key", "GROQ_API_KEY"), 
                              ("elevenlabs_api_key", "ELEVENLABS_API_KEY"),
                              ("openweather_api_key", "OPENWEATHER_KEY"),
                              ("alphavantage_api_key", "ALPHAVANTAGE_KEY"),
                              ("deepgram_api_key", "DEEPGRAM_API_KEY")]:
            val = os.getenv(env_name)
            if val:
                self.set_secret(key, val)
                
        self._save()

    def _save(self):
        """Saves current config to config.json and creates a backup."""
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self._config, f, indent=4)
            # Create backup
            shutil.copy(CONFIG_FILE, CONFIG_BACKUP_FILE)
        except Exception as e:
            logging.error(f"Failed to save config.json: {e}")

    def get(self, section: str, key: str, default=None):
        """Safely retrieve a config value."""
        return self._config.get(section, {}).get(key, default)

    def set(self, section: str, key: str, value: str):
        """Set a config value and save to disk."""
        if section not in self._config:
            self._config[section] = {}
        self._config[section][key] = value
        self._save()
        
    def get_secret(self, key: str, default="") -> str:
        """Retrieve a secret from Windows Credential Manager or fallback dict."""
        if keyring:
            try:
                val = keyring.get_password(KEYRING_SERVICE, key)
                return val if val is not None else default
            except Exception as e:
                logging.warning(f"Keyring read failed for {key}: {e}")
                return default
        # If keyring fails, we might check an in-memory cache or environment, 
        # but for security we avoid storing it plain text in JSON.
        return default
        
    def set_secret(self, key: str, value: str):
        """Store a secret securely."""
        if keyring and value:
            try:
                keyring.set_password(KEYRING_SERVICE, key, value)
            except Exception as e:
                logging.warning(f"Keyring write failed for {key}: {e}")

    def is_valid(self) -> bool:
        """Check if essential configuration is present to start the app."""
        groq_key = self.get_secret("groq_api_key")
        return bool(groq_key and groq_key.strip())
        
    def validate_groq_async(self, key: str, callback):
        """Asynchronously validate Groq API Key by sending a tiny request."""
        def check():
            if not key or not key.strip():
                callback(False, "Key is empty")
                return
            try:
                headers = {"Authorization": f"Bearer {key}"}
                # Lightweight endpoint check
                resp = requests.get("https://api.groq.com/openai/v1/models", headers=headers, timeout=5)
                if resp.status_code == 200:
                    callback(True, "Connected")
                elif resp.status_code == 401:
                    callback(False, "Invalid API Key")
                else:
                    callback(False, f"API Error: {resp.status_code}")
            except requests.RequestException as e:
                callback(False, "Network Error")
        
        threading.Thread(target=check, daemon=True).start()

# Global singleton
config = ConfigManager()

# Legacy aliases for backward compatibility with existing code
OPENWEATHER_KEY = config.get_secret("openweather_api_key")
ALPHAVANTAGE_KEY = config.get_secret("alphavantage_api_key")
GROQ_API_KEY = config.get_secret("groq_api_key")

def validate_config():
    """Legacy validation function - now handled by is_valid() gracefully in main.py"""
    pass
