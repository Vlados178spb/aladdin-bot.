import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

ODDS_API_KEY = os.getenv("ODDS_API_KEY")
ODDS_API_IO_KEY = os.getenv("ODDS_API_IO_KEY")
