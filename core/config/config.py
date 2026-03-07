
import os
import logging
from dotenv import load_dotenv

def validate_config():
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "ni.env")
    load_dotenv(dotenv_path=env_path)
    if not os.getenv("OPENWEATHER_KEY"):
        logging.warning("OPENWEATHER_KEY missing. Weather queries will use fallback messaging.")

OPENWEATHER_KEY = os.getenv("OPENWEATHER_KEY")
ALPHAVANTAGE_KEY = os.getenv("ALPHAVANTAGE_KEY")
