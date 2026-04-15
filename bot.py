import asyncio
import aiohttp
import sqlite3
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# =====================
# KEYS (iSports API + Telegram)
# =====================
BOT_TOKEN = "8694698903:AAHK51pTIQo4TFcBBF1RbL4Kh5OZRiLGTiM"
ISPORTS_API_KEY = "csHMISYm949upbV6"

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
async def fetch(session, url):
    try:
        async with session.get(url) as r:
            if r.status == 429:
                await asyncio.sleep(5)
                return await fetch(session, url)
            return await r.json()
    except Exception as e:
        logger.error(f"Fetch error: {e}")
        return {}

# =====================
# iSports API
# =====================
BASE_URL = "http://api2.isportsapi.com"

async def get_live_scores(session):
    """Получает live-матчи футбола (ближайшие)."""
    url = f"{BASE_URL}/sport/football/livescores?api_key={ISPORTS_API_KEY}"
    return await fetch(session, url)

async def get_fixtures(session, date=None):
    """Получает расписание матчей на дату (по умолчанию сегодня)."""
    if date is None:
        date = datetime.now().strftime("%Y%m%d")
    url = f"{BASE_URL}/sport/football/schedule?api_key={ISPORTS_API_KEY}&date={date}"
    return await fetch(session, url)

async def get_odds(session, match_id):
    """Получает коэффициенты для конкретного матча."""
    url = f"{BASE_URL}/sport/football/odds?api_key={ISPORTS_API_KEY}&match_id={match_id}"
    return await fetch(session, url)

async def get_h2h(session, team1, team2):
    """История очных встреч."""
    url = f"{BASE_URL}/sport/football/h2h?api_key={ISPORTS_API_KEY}&team1={team1}&team2={team2}"
    return await fetch(session, url)

async def get_team_stats(session, team_id):
    """Статистика команды (форма, голы)."""
    url = f"{BASE_URL}/sport/football/teamstats?api_key={ISPORTS_API_KEY}&team_id={team_id}"
    return await fetch(session, url)

# =====================
# ОБРАБОТКА ДАННЫХ
# =====================
def result_icon(gf, ga):
    if gf is None or ga is None:
        return "➖"
    if gf > ga:
        return "✅"
    elif gf == ga:
        return "♻️"
    else:
        return "❌"

def calc_form_from_results(results):
    """Вычисляет форму по последним 5 матчам (победа=1, ничья=0.5)."""
    if not results:
        return 0.5
    score = 0
    count = 0
    for r in results[:5]:
        if r == "W":
            score += 1
        elif r == "D":
            score += 0.5
        count += 1
    return score / count if count else 0.5

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

def compute_score(h2h_score, home_form, away_form, table_diff, goal_diff, odds):
    norm_odds = 1 / odds if odds else 0
    score = (
        h2h_score * 0.25 +
        (home_form - away_form) * 0.20 +
        home_form * 0.15 +
        table_diff * 0.15 +
        goal_diff * 0.15 +
        norm_odds * 0.10
    )
    return score

# =====================
# ПОСТРОЕНИЕ КЭША
# =====================
async def build_football():
    global FOOTBALL_CACHE, EXPRESS_CACHE
    results = []
    async with aiohttp.ClientSession() as session:
        data = await get_live_scores(session)
        matches = data.get("data", []) if isinstance(data, dict) else []

        for m in matches:
            try:
                home = m.get("home_name", "")
                away = m.get("away_name", "")
                match_time = m.get("match_time", "")
                match_id = m.get("match_id")

                if not home or not away or not match_time or not match_id:
                    continue

                # Время
                mt = datetime.strptime(match_time, "%Y-%m-%d %H:%M:%S")
                now = datetime.now(ZoneInfo("Europe/Moscow"))
                hours_left = (mt - now).total_seconds() / 3600
                if hours_left < 1 or hours_left > 24:
                    continue

                # Коэффициенты
                odds_data = await get_odds(session, match_id)
                odds_info = odds_data.get("data", {}) if isinstance(odds_data, dict) else {}
                home_odds = odds_info.get("home_odds")
                away_odds = odds_info.get("away_odds")
                if not home_odds or not away_odds:
                    continue
                home_odds = float(home_odds)
                away_odds = float(away_odds)

                if home_odds < 3.5 or away_odds > 2.2:
                    continue

                # H2H
                h2h_data = await get_h2h(session, home, away)
                h2h_matches = h2h_data.get("data", []) if isinstance(h2h_data, dict) else []
                h2h_score = 0.0
                h2h_icons = ["➖"] * 5
                for i, h in enumerate(h2h_matches[:5]):
                    if i >= 5:
                        break
                    home_goals = h.get("home_score", 0)
                    away_goals = h.get("away_score", 0)
                    if home_goals > away_goals:
                        h2h_score += 1
                        h2h_icons[i] = "✅"
                    elif home_goals == away_goals:
                        h2h_score += 0.5
                        h2h_icons[i] = "♻️"
                    else:
                        h2h_score -= 0.5
                        h2h_icons[i] = "❌"
                if h2h_matches:
                    h2h_score /= len(h2h_matches[:5])

                # Форма команд
                home_stats = await get_team_stats(session, home)
                away_stats = await get_team_stats(session, away)

                home_form = 0.5
                away_form = 0.5
                home_icons = ["➖"] * 5
                form_icons = ["➖"] * 5

                if home_stats and "data" in home_stats:
                    last5 = home_stats["data"].get("last_5_matches", [])
                    home_form = calc_form_from_results(last5)
                    for i, r in enumerate(last5[:5]):
                        home_icons[i] = "✅" if r == "W" else ("♻️" if r == "D" else "❌")
                        form_icons[i] = home_icons[i]
                if away_stats and "data" in away_stats:
                    last5_away = away_stats["data"].get("last_5_matches", [])
                    away_form = calc_form_from_results(last5_away)

                # Разница мячей и позиция в таблице (заглушки, т.к. iSports может не давать)
                goal_diff = 0.0
                table_diff = 0

                # Итоговый Score
                score = compute_score(h2h_score, home_form, away_form, table_diff, goal_diff, home_odds)

                # Сохранение
                cur.execute(
                    "INSERT INTO predictions (home, away, score, handicap, odds, time) VALUES (?, ?, ?, ?, ?, ?)",
                    (home, away, score, get_handicap(score), home_odds, mt.isoformat())
                )
                conn.commit()

                results.append({
                    "date": mt.strftime("%d.%m.%Y"),
                    "country": "🌍 Футбол",
                    "time": mt.strftime("%H:%M"),
                    "home": home,
                    "away": away,
                    "home_odds": round(home_odds, 2),
                    "away_odds": round(away_odds, 2),
                    "handicap": get_handicap(score),
                    "h2h_icons": h2h_icons,
                    "home_icons": home_icons,
                    "form_icons": form_icons,
                    "score": round(score, 3),
                    "confidence": round(score * (home_odds / 3.5), 3)
                })

                await asyncio.sleep(0.3)

            except Exception as e:
                logger.error(f"Error processing match: {e}")
                continue

    results.sort(key=lambda x: x["confidence"], reverse=True)
    FOOTBALL_CACHE = results[:21]
    EXPRESS_CACHE = [m for m in results if m["score"] >= 0.3][:4]

async def build_hockey():
    global HOCKEY_CACHE
    # Хоккей через iSports API пока не реализован, оставляем заглушку
    HOCKEY_CACHE = []

async def build_all():
    await build_football()
    await build_hockey()
    logger.info("Cache updated")

# =====================
# ФОРМАТИРОВАНИЕ
# =====================
def format_matches(data, title):
    if not data:
        return f"🧞‍♂️ {title}: сегодня лампа пуста"

    msg = f"📊 <b>{title}</b>\n\n"
    for i, m in enumerate(data, 1):
        msg += f"{i}. 📆 {m['date']}\n"
        msg += f"🇷🇺 {m['country']}\n"
        msg += f"🕰️ {m['time']} МСК\n"
        msg += f"🏟️ {m['home']} ({m['home_odds']}) — {m['away']} ({m['away_odds']})\n"
        msg += f"⛳ Рекомендуемая фора: {m['handicap']}\n"
        msg += f"⏳ Очные (дома): {' '.join(m['h2h_icons'])}\n"
        msg += f"🏟️ Дома (посл. 5): {' '.join(m['home_icons'])}\n"
        msg += f"🤼‍♂️ Общая форма (5): {' '.join(m['form_icons'])}\n\n"
    return msg

# =====================
# HANDLERS
# =====================
@router.message(Command("start"))
async def start(m: Message):
    await m.answer("🧞 JIN v7 (iSports API) ACTIVE\nРеальные данные с российских БК\nФутбол / Хоккей / Экспресс", reply_markup=keyboard)

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
# LOOP
# =====================
async def loop():
    while True:
        try:
            await build_all()
        except Exception as e:
            logger.error(f"Loop error: {e}")
        await asyncio.sleep(3600)

async def main():
    asyncio.create_task(loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
