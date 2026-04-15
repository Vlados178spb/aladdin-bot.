‎import asyncio
‎import aiohttp
‎import sqlite3
‎import logging
‎from datetime import datetime, timedelta
‎from zoneinfo import ZoneInfo
‎from deep_translator import GoogleTranslator
‎from functools import lru_cache
‎
‎from aiogram import Bot, Dispatcher, Router, F
‎from aiogram.filters import Command
‎from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
‎from aiogram.enums import ParseMode
‎from aiogram.client.default import DefaultBotProperties
‎
‎# =====================
‎# KEYS
‎# =====================
‎BOT_TOKEN = "8694698903:AAHK51pTIQo4TFcBBF1RbL4Kh5OZRiLGTiM"
‎ODDS_API_KEY = "2be3c040e725dabfe695ae282049a8b0"
‎FOOTBALL_KEY = "f286e713f060483e83f6d722f1d58ddf"
‎
‎# =====================
‎# BOT SETUP
‎# =====================
‎bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
‎dp = Dispatcher()
‎router = Router()
‎dp.include_router(router)
‎
‎# =====================
‎# DATABASE
‎# =====================
‎conn = sqlite3.connect("jin_stats.db")
‎cur = conn.cursor()
‎cur.execute("""
‎CREATE TABLE IF NOT EXISTS predictions (
‎    id INTEGER PRIMARY KEY AUTOINCREMENT,
‎    home TEXT,
‎    away TEXT,
‎    score REAL,
‎    handicap TEXT,
‎    odds REAL,
‎    result TEXT,
‎    time TEXT
‎)
‎""")
‎conn.commit()
‎
‎# =====================
‎# CACHE
‎# =====================
‎FOOTBALL_CACHE = []
‎HOCKEY_CACHE = []
‎EXPRESS_CACHE = []
‎
‎keyboard = ReplyKeyboardMarkup(
‎    keyboard=[
‎        [KeyboardButton(text="⚽ Футбол")],
‎        [KeyboardButton(text="🏒 Хоккей")],
‎        [KeyboardButton(text="🍺 Экспресс")]
‎    ],
‎    resize_keyboard=True
‎)
‎
‎# =====================
‎# LOGGING
‎# =====================
‎logging.basicConfig(level=logging.INFO)
‎logger = logging.getLogger("JIN")
‎
‎# =====================
‎# HTTP HELPERS
‎# =====================
‎async def fetch(session, url, headers=None):
‎    try:
‎        async with session.get(url, headers=headers) as r:
‎            if r.status == 429:
‎                await asyncio.sleep(5)
‎                return await fetch(session, url, headers)
‎            return await r.json()
‎    except Exception as e:
‎        logger.error(f"Fetch error: {e}")
‎        return {}
‎
‎# =====================
‎# TRANSLATION CACHE
‎# =====================
‎@lru_cache(maxsize=500)
‎def translate_to_russian(text):
‎    """Переводит текст на русский язык, игнорируя уже переведенные названия."""
‎    if not text:
‎        return text
‎    # Если текст уже содержит кириллицу, вероятно, он уже переведен
‎    if any('а' <= char <= 'я' or 'А' <= char <= 'Я' for char in text):
‎        return text
‎    try:
‎        translator = GoogleTranslator(source='auto', target='ru')
‎        return translator.translate(text)
‎    except Exception as e:
‎        logger.warning(f"Translation failed for '{text}': {e}")
‎        return text
‎
‎# =====================
‎# FOOTBALL-DATA API
‎# =====================
‎HEADERS_FD = {"X-Auth-Token": FOOTBALL_KEY}
‎
‎async def get_scheduled_matches(session):
‎    url = "https://api.football-data.org/v4/matches?status=SCHEDULED&limit=100"
‎    return await fetch(session, url, HEADERS_FD)
‎
‎async def get_team_last_matches(session, team_id, limit=5):
‎    url = f"https://api.football-data.org/v4/teams/{team_id}/matches?limit={limit}&status=FINISHED"
‎    return await fetch(session, url, HEADERS_FD)
‎
‎async def get_h2h(session, home_id, away_id, limit=5):
‎    url = f"https://api.football-data.org/v4/matches?homeTeam={home_id}&awayTeam={away_id}&limit={limit}&status=FINISHED"
‎    return await fetch(session, url, HEADERS_FD)
‎
‎async def get_standings(session, competition_code):
‎    url = f"https://api.football-data.org/v4/competitions/{competition_code}/standings"
‎    return await fetch(session, url, HEADERS_FD)
‎
‎# =====================
‎# THE ODDS API
‎# =====================
‎async def get_all_odds(session, sport_key):
‎    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h&bookmakers=pinnacle"
‎    return await fetch(session, url)
‎
‎def extract_odds(odds_data, home_team, away_team):
‎    if not isinstance(odds_data, list):
‎        return None, None
‎    for game in odds_data:
‎        if game.get("home_team", "").lower() == home_team.lower() and game.get("away_team", "").lower() == away_team.lower():
‎            bookmakers = game.get("bookmakers", [])
‎            if not bookmakers:
‎                continue
‎            h2h = next((m for m in bookmakers[0].get("markets", []) if m["key"] == "h2h"), None)
‎            if not h2h:
‎                continue
‎            outcomes = h2h["outcomes"]
‎            home_odds = next((o["price"] for o in outcomes if o["name"] == home_team), None)
‎            away_odds = next((o["price"] for o in outcomes if o["name"] == away_team), None)
‎            return home_odds, away_odds
‎    return None, None
‎
‎# =====================
‎# NHL API (для хоккея)
‎# =====================
‎async def get_nhl_team_sta
