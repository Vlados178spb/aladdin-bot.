import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    ODDS_API_IO_KEY = os.getenv("ODDS_API_IO_KEY")
    TIMEZONE = os.getenv("TIMEZONE", "Europe/Moscow")

    # Жёсткие фильтры
    MIN_HOME_ODD = 3.4
    MAX_AWAY_ODD = 2.0
