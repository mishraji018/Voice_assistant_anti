import os

# Root of the project (Voice_Assistant/)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Standard directories
CONFIG_DIR = os.path.join(ROOT_DIR, "config")
LOG_DIR = os.path.join(ROOT_DIR, "logs")
BRAIN_DIR = os.path.join(ROOT_DIR, "brain")
CORE_DIR = os.path.join(ROOT_DIR, "core")

# Standard files
JARVIS_LOG = os.path.join(LOG_DIR, "jarvis.log")
JARVIS_CONFIG = os.path.join(CONFIG_DIR, "jarvis_config.json")
JARVIS_MEMORY = os.path.join(CONFIG_DIR, "jarvis_memory.json")
JARVIS_LEARNING = os.path.join(CONFIG_DIR, "jarvis_learning.json")
USER_KEYWORDS = os.path.join(CONFIG_DIR, "user_keywords.json")

def get_config_path(filename):
    return os.path.join(CONFIG_DIR, filename)

def get_log_path(filename):
    return os.path.join(LOG_DIR, filename)
