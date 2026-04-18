import os
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

class Config:
    # --- Telegram ---
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    
    # --- Odds API ---
    ODDS_API_KEY = os.getenv("ODDS_API_KEY")
    ODDS_API_IO_KEY = os.getenv("ODDS_API_IO_KEY")
    
    # --- Дополнительные API (на будущее) ---
    FOOTBALL_KEY = os.getenv("FOOTBALL_KEY")
    ISPORTS_API_KEY = os.getenv("ISPORTS_API_KEY")
    
    # --- Настройки времени ---
    TIMEZONE = os.getenv("TIMEZONE", "Europe/Moscow")
    
    # --- Настройки анализа ---
    MIN_HOME_ODD = 3.6  # Основной фильтр: дома от 3.6
    MAX_AWAY_ODD = 1.8  # Гости до 1.8
    
    # --- Спортивные лиги (ключи для The Odds API) ---
    FOOTBALL_LEAGUES = [
        "soccer_epl", "soccer_spain_la_liga", "soccer_italy_serie_a",
        "soccer_germany_bundesliga", "soccer_france_ligue_one",
        "soccer_netherlands_eredivisie", "soccer_portugal_primeira_liga",
        "soccer_brazil_campeonato", "soccer_argentina_primera_division",
        "soccer_uefa_champs_league", "soccer_uefa_europa_league",
        "soccer_russia_premier_league", "soccer_turkey_super_league"
    ]
    
    HOCKEY_LEAGUES = [
        "icehockey_nhl", "icehockey_sweden_hockey_league", "icehockey_finland_liiga",
        "icehockey_czech_republic_extraliga", "icehockey_swiss_nla", "icehockey_khl",
        "icehockey_germany_del"
    ]
