import asyncio
import aiohttp
import sqlite3
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# =====================
# KEYS
# =====================
BOT_TOKEN = "8694698903:AAHK51pTIQo4TFcBBF1RbL4Kh5OZRiLGTiM"
ODDS_API_KEY = "2be3c040e725dabfe695ae282049a8b0"
FOOTBALL_KEY = "f286e713f060483e83f6d722f1d58ddf"

# =====================
# BOT SETUP
# =====================
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router()
dp.include_router(router)

# =====================
# DATABASE
# =====================
conn = sqlite3.connect("jin_stats.db")
cur = conn.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    home TEXT,
    away TEXT,
    score REAL,
    handicap TEXT,
    odds REAL,
    result TEXT,
    time TEXT
)
""")
conn.commit()

# =====================
# CACHE
# =====================
FOOTBALL_CACHE = []
HOCKEY_CACHE = []
EXPRESS_CACHE = []

keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="⚽ Футбол")],
        [KeyboardButton(text="🏒 Хоккей")],
        [KeyboardButton(text="🍺 Экспресс")]
    ],
    resize_keyboard=True
)

# =====================
# LOGGING
# =====================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("JIN")

# =====================
# HTTP HELPERS
# =====================
async def fetch(session, url, headers=None):
    try:
        async with session.get(url, headers=headers) as r:
            if r.status == 429:
                await asyncio.sleep(5)
                return await fetch(session, url, headers)
            return await r.json()
    except Exception as e:
        logger.error(f"Fetch error: {e}")
        return {}

# =====================
# FOOTBALL-DATA API
# =====================
HEADERS_FD = {"X-Auth-Token": FOOTBALL_KEY}

async def get_scheduled_matches(session):
    """Получает ближайшие матчи (до 100) из Football-Data."""
    url = "https://api.football-data.org/v4/matches?status=SCHEDULED&limit=100"
    return await fetch(session, url, HEADERS_FD)

async def get_team_last_matches(session, team_id, limit=5):
    """Последние завершённые матчи команды."""
    url = f"https://api.football-data.org/v4/teams/{team_id}/matches?limit={limit}&status=FINISHED"
    return await fetch(session, url, HEADERS_FD)

async def get_h2h(session, home_id, away_id, limit=5):
    """Очные встречи (последние 5 матчей между командами)."""
    # Получаем матчи, где home_id играет дома против away_id
    url = f"https://api.football-data.org/v4/matches?homeTeam={home_id}&awayTeam={away_id}&limit={limit}&status=FINISHED"
    return await fetch(session, url, HEADERS_FD)

async def get_standings(session, competition_code):
    """Турнирная таблица."""
    url = f"https://api.football-data.org/v4/competitions/{competition_code}/standings"
    return await fetch(session, url, HEADERS_FD)

# =====================
# THE ODDS API
# =====================
async def get_all_odds(session, sport_key):
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h&bookmakers=pinnacle"
    return await fetch(session, url)

def extract_odds(odds_data, home_team, away_team):
    """Извлекает коэффициенты для конкретного матча."""
    if not isinstance(odds_data, list):
        return None, None
    for game in odds_data:
        if game.get("home_team", "").lower() == home_team.lower() and game.get("away_team", "").lower() == away_team.lower():
            bookmakers = game.get("bookmakers", [])
            if not bookmakers:
                continue
            h2h = next((m for m in bookmakers[0].get("markets", []) if m["key"] == "h2h"), None)
            if not h2h:
                continue
            outcomes = h2h["outcomes"]
            home_odds = next((o["price"] for o in outcomes if o["name"] == home_team), None)
            away_odds = next((o["price"] for o in outcomes if o["name"] == away_team), None)
            return home_odds, away_odds
    return None, None

# =====================
# STATS PROCESSING
# =====================
def calc_form(matches, team_id):
    """Возвращает средний балл формы (победа=1, ничья=0.5)."""
    if not matches:
        return 0.5
    total = 0
    count = 0
    for m in matches:
        if m["homeTeam"]["id"] == team_id:
            gf = m["score"]["fullTime"]["home"]
            ga = m["score"]["fullTime"]["away"]
        else:
            gf = m["score"]["fullTime"]["away"]
            ga = m["score"]["fullTime"]["home"]
        if gf is None or ga is None:
            continue
        if gf > ga:
            total += 1.0
        elif gf == ga:
            total += 0.5
        count += 1
    return total / count if count > 0 else 0.5

def calc_h2h_score(matches):
    """Средний балл H2H на поле хозяев."""
    if not matches:
        return 0.0
    total = 0
    for m in matches:
        gf = m["score"]["fullTime"]["home"]
        ga = m["score"]["fullTime"]["away"]
        if gf is None or ga is None:
            continue
        if gf > ga:
            total += 1.0
        elif gf == ga:
            total += 0.5
        else:
            total -= 0.5  # поражение дома – минус
    return total / len(matches) if matches else 0.0

def get_goal_diff(matches, team_id):
    """Средняя разница голов за последние 5 матчей."""
    if not matches:
        return 0.0
    total = 0
    count = 0
    for m in matches:
        if m["homeTeam"]["id"] == team_id:
            gf = m["score"]["fullTime"]["home"]
            ga = m["score"]["fullTime"]["away"]
        else:
            gf = m["score"]["fullTime"]["away"]
            ga = m["score"]["fullTime"]["home"]
        if gf is None or ga is None:
            continue
        total += (gf - ga)
        count += 1
    return total / count if count > 0 else 0.0

async def get_table_position(session, team_id, competition_code):
    """Возвращает позицию команды в таблице (чем меньше, тем лучше)."""
    data = await get_standings(session, competition_code)
    if not data.get("standings"):
        return None
    for standing in data["standings"]:
        for team in standing["table"]:
            if team["team"]["id"] == team_id:
                return team["position"]
    return None

# =====================
# SCORE CALCULATION
# =====================
def compute_score(h2h_score, home_form, away_form, table_diff, goal_diff, odds):
    """
    h2h_score: нормализованный (-1..1)
    home_form: 0..1
    away_form: 0..1
    table_diff: +1 если хозяева выше, -1 если ниже, 0 иначе
    goal_diff: средняя разница мячей за 5 матчей
    odds: коэффициент П1
    """
    norm_odds = 1 / odds  # вероятность по коэффициенту
    score = (
        h2h_score * 0.25 +
        (home_form - away_form) * 0.20 +  # относительная форма
        home_form * 0.15 +                # общая форма хозяев
        table_diff * 0.15 +
        goal_diff * 0.15 +
        norm_odds * 0.10
    )
    return score

def get_handicap(score):
    if score >= 0.8:
        return "0"
    elif score >= 0.5:
        return "+0.5"
    elif score >= 0.2:
        return "+1.5"
    elif score >= 0.0:
        return "+2.5"
    elif score >= -0.2:
        return "+3.0"
    else:
        return "+3.5 / +4.0"

# =====================
# MAIN ENGINE
# =====================
async def build_football():
    global FOOTBALL_CACHE, EXPRESS_CACHE
    results = []
    async with aiohttp.ClientSession() as session:
        # 1. Получаем матчи Football-Data
        fd_data = await get_scheduled_matches(session)
        matches = fd_data.get("matches", [])
        if not matches:
            logger.warning("No scheduled matches from Football-Data")
            return

        # 2. Получаем все коэффициенты The Odds API
        odds_list = await get_all_odds(session, "soccer")
        if not odds_list:
            logger.warning("No odds data")
            return

        # 3. Обрабатываем каждый матч
        for m in matches:
            try:
                home = m["homeTeam"]["name"]
                away = m["awayTeam"]["name"]
                home_id = m["homeTeam"]["id"]
                away_id = m["awayTeam"]["id"]
                competition_code = m["competition"]["code"]
                utc_time = m["utcDate"]

                # Временной фильтр
                mt = datetime.fromisoformat(utc_time.replace("Z", "+00:00"))
                now = datetime.now(ZoneInfo("Europe/Moscow"))
                hours_left = (mt - now).total_seconds() / 3600
                if hours_left < 1 or hours_left > 24:
                    continue

                # Коэффициенты
                home_odds, away_odds = extract_odds(odds_list, home, away)
                if not home_odds or not away_odds:
                    continue
                if home_odds < 3.5 or away_odds > 2.2:
                    continue

                # Статистика
                # Последние матчи команд
                home_matches = await get_team_last_matches(session, home_id)
                away_matches = await get_team_last_matches(session, away_id)
                await asyncio.sleep(0.5)  # задержка

                # H2H
                h2h_data = await get_h2h(session, home_id, away_id)
                h2h_matches = h2h_data.get("matches", [])
                h2h_score = calc_h2h_score(h2h_matches[:5])
                await asyncio.sleep(0.5)

                # Форма
                home_form = calc_form(home_matches, home_id)
                away_form = calc_form(away_matches, away_id)

                # Разница голов
                goal_diff = get_goal_diff(home_matches, home_id)

                # Турнирная позиция
                home_pos = await get_table_position(session, home_id, competition_code)
                away_pos = await get_table_position(session, away_id, competition_code)
                await asyncio.sleep(0.5)

                table_diff = 0
                if home_pos is not None and away_pos is not None:
                    if home_pos < away_pos:
                        table_diff = 1
                    elif home_pos > away_pos:
                        table_diff = -1

                # Итоговый Score
                score = compute_score(h2h_score, home_form, away_form, table_diff, goal_diff, home_odds)

                # Сохраняем в БД
                cur.execute(
                    "INSERT INTO predictions (home, away, score, handicap, odds, time) VALUES (?, ?, ?, ?, ?, ?)",
                    (home, away, score, get_handicap(score), home_odds, mt.isoformat())
                )
                conn.commit()

                results.append({
                    "home": home,
                    "away": away,
                    "time": mt.strftime("%H:%M"),
                    "odds": round(home_odds, 2),
                    "score": round(score, 3),
                    "handicap": get_handicap(score),
                    "confidence": round(score * (home_odds / 3.5), 3)
                })

            except Exception as e:
                logger.error(f"Error processing match {home} vs {away}: {e}")
                continue

    # Сортировка по confidence (уверенность + кэф)
    results.sort(key=lambda x: x["confidence"], reverse=True)
    FOOTBALL_CACHE = results[:21]
    EXPRESS_CACHE = [m for m in results if m["score"] >= 0.3][:4]

async def build_hockey():
    global HOCKEY_CACHE
    results = []
    async with aiohttp.ClientSession() as session:
        odds_list = await get_all_odds(session, "icehockey_nhl")
        if not isinstance(odds_list, list):
            return

        for game in odds_list:
            try:
                home = game["home_team"]
                away = game["away_team"]
                commence = game["commence_time"]

                home_odds, away_odds = extract_odds(odds_list, home, away)
                if not home_odds or not away_odds:
                    continue
                if home_odds < 3.5 or away_odds > 2.2:
                    continue

                mt = datetime.fromisoformat(commence.replace("Z", "+00:00"))
                now = datetime.now(ZoneInfo("Europe/Moscow"))
                hours_left = (mt - now).total_seconds() / 3600
                if hours_left < 1 or hours_left > 24:
                    continue

                # Для хоккея пока упрощённо
                score = 0.5  # заглушка
                results.append({
                    "home": home,
                    "away": away,
                    "time": mt.strftime("%H:%M"),
                    "odds": round(home_odds, 2),
                    "score": score,
                    "handicap": get_handicap(score),
                    "confidence": score * (home_odds / 3.5)
                })
            except:
                continue

    results.sort(key=lambda x: x["confidence"], reverse=True)
    HOCKEY_CACHE = results[:21]

async def build_all():
    await build_football()
    await build_hockey()
    logger.info("Cache updated")

# =====================
# FORMATTING
# =====================
def format_matches(data, title):
    if not data:
        return f"🧞‍♂️ {title}: сегодня лампа пуста"

    msg = f"📊 <b>{title}</b>\n\n"
    for i, m in enumerate(data, 1):
        msg += f"{i}. {m['home']} vs {m['away']}\n"
        msg += f"🕒 {m['time']}\n"
        msg += f"💰 Кэф: {m['odds']}\n"
        msg += f"🎯 Фора: {m['handicap']}\n"
        msg += f"📈 Score: {m['score']} | Уверенность: {m['confidence']}\n\n"
    return msg

# =====================
# HANDLERS
# =====================
@router.message(Command("start"))
async def start(m: Message):
    await m.answer("🧞 JIN v5 ACTIVE\nРеальная статистика\nФутбол / Хоккей / Экспресс", reply_markup=keyboard)

@router.message(F.text == "⚽ Футбол")
async def football_cmd(m: Message):
    await m.answer(format_matches(FOOTBALL_CACHE, "⚽ ФУТБОЛ"))

@router.message(F.text == "🏒 Хоккей")
async def hockey_cmd(m: Message):
    await m.answer(format_matches(HOCKEY_CACHE, "🏒 ХОККЕЙ"))

@router.message(F.text == "🍺 Экспресс")
async def express_cmd(m: Message):
    await m.answer(format_matches(EXPRESS_CACHE, "🍺 ЭКСПРЕСС (ТОП-4)"))

# =====================
# BACKGROUND LOOP
# =====================
async def loop():
    while True:
        try:
            await build_all()
        except Exception as e:
            logger.error(f"Loop error: {e}")
        await asyncio.sleep(3600)  # каждый час

async def main():
    asyncio.create_task(loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
