import asyncio
import aiohttp
import sqlite3
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from deep_translator import GoogleTranslator
from functools import lru_cache

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# =====================
# KEYS (теперь все четыре)
# =====================
BOT_TOKEN = "8694698903:AAHK51pTIQo4TFcBBF1RbL4Kh5OZRiLGTiM"
ODDS_API_KEY = "2be3c040e725dabfe695ae282049a8b0"
FOOTBALL_KEY = "f286e713f060483e83f6d722f1d58ddf"
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
# TRANSLATION CACHE
# =====================
@lru_cache(maxsize=500)
def translate_to_russian(text):
    """Переводит текст на русский язык, игнорируя уже переведенные названия."""
    if not text:
        return text
    # Если текст уже содержит кириллицу, вероятно, он уже переведен
    if any('а' <= char <= 'я' or 'А' <= char <= 'Я' for char in text):
        return text
    try:
        translator = GoogleTranslator(source='auto', target='ru')
        return translator.translate(text)
    except Exception as e:
        logger.warning(f"Translation failed for '{text}': {e}")
        return text

# =====================
# FOOTBALL-DATA API
# =====================
HEADERS_FD = {"X-Auth-Token": FOOTBALL_KEY}

async def get_scheduled_matches(session):
    url = "https://api.football-data.org/v4/matches?status=SCHEDULED&limit=100"
    return await fetch(session, url, HEADERS_FD)

async def get_team_last_matches(session, team_id, limit=5):
    url = f"https://api.football-data.org/v4/teams/{team_id}/matches?limit={limit}&status=FINISHED"
    return await fetch(session, url, HEADERS_FD)

async def get_h2h(session, home_id, away_id, limit=5):
    url = f"https://api.football-data.org/v4/matches?homeTeam={home_id}&awayTeam={away_id}&limit={limit}&status=FINISHED"
    return await fetch(session, url, HEADERS_FD)

async def get_standings(session, competition_code):
    url = f"https://api.football-data.org/v4/competitions/{competition_code}/standings"
    return await fetch(session, url, HEADERS_FD)

# =====================
# THE ODDS API
# =====================
async def get_all_odds(session, sport_key):
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h&bookmakers=pinnacle"
    return await fetch(session, url)

def extract_odds(odds_data, home_team, away_team):
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
# NHL API (для хоккея)
# =====================
async def get_nhl_team_stats(session, team_id):
    """Получает статистику команды NHL через неофициальное API."""
    url = f"https://statsapi.web.nhl.com/api/v1/teams/{team_id}/stats"
    return await fetch(session, url)

async def get_nhl_schedule(session, date=None):
    """Получает расписание матчей NHL на указанную дату."""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    url = f"https://statsapi.web.nhl.com/api/v1/schedule?date={date}"
    return await fetch(session, url)

def extract_nhl_team_stats(stats_data):
    """Извлекает полезную статистику из ответа NHL API."""
    if not stats_data or "stats" not in stats_data:
        return {"form": 0.5, "goal_diff": 0.0, "home_form": 0.5}
    
    try:
        splits = stats_data["stats"][0]["splits"]
        # Статистика за сезон
        season_stats = next((s for s in splits if s["stat"]["gamesPlayed"] > 0), None)
        if season_stats:
            stat = season_stats["stat"]
            games = stat.get("gamesPlayed", 1)
            wins = stat.get("wins", 0)
            ot = stat.get("ot", 0)
            goals_per_game = stat.get("goalsPerGame", 2.5)
            goals_against_per_game = stat.get("goalsAgainstPerGame", 2.5)
            
            form = (wins + ot * 0.5) / games
            goal_diff = goals_per_game - goals_against_per_game
            
            # Упрощенно, т.к. NHL API не дает отдельно домашнюю статистику без доп. запросов
            return {"form": round(form, 3), "goal_diff": round(goal_diff, 3), "home_form": round(form, 3)}
    except:
        pass
    
    return {"form": 0.5, "goal_diff": 0.0, "home_form": 0.5}

# =====================
# STATS PROCESSING
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

def get_form_icons(matches, team_id, is_home_matches=False):
    icons = []
    for m in matches[:5]:
        if is_home_matches:
            if m["homeTeam"]["id"] != team_id:
                continue
            gf = m["score"]["fullTime"]["home"]
            ga = m["score"]["fullTime"]["away"]
        else:
            if m["homeTeam"]["id"] == team_id:
                gf = m["score"]["fullTime"]["home"]
                ga = m["score"]["fullTime"]["away"]
            else:
                gf = m["score"]["fullTime"]["away"]
                ga = m["score"]["fullTime"]["home"]
        icons.append(result_icon(gf, ga))
    while len(icons) < 5:
        icons.append("➖")
    return icons[:5]

def get_h2h_icons(h2h_matches):
    icons = []
    for m in h2h_matches[:5]:
        gf = m["score"]["fullTime"]["home"]
        ga = m["score"]["fullTime"]["away"]
        icons.append(result_icon(gf, ga))
    while len(icons) < 5:
        icons.append("➖")
    return icons[:5]

def calc_form(matches, team_id):
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
            total -= 0.5
    return total / len(matches) if matches else 0.0

def get_goal_diff(matches, team_id):
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
    norm_odds = 1 / odds
    score = (
        h2h_score * 0.25 +
        (home_form - away_form) * 0.20 +
        home_form * 0.15 +
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
        odds_list = await get_all_odds(session, "soccer")
        if not isinstance(odds_list, list):
            logger.warning("No odds data")
            return

        fd_data = await get_scheduled_matches(session)
        fd_matches = fd_data.get("matches", [])

        for game in odds_list:
            try:
                home = game["home_team"]
                away = game["away_team"]
                commence = game["commence_time"]

                home_odds, away_odds = extract_odds([game], home, away)
                if not home_odds or not away_odds:
                    continue
                if home_odds < 3.5 or away_odds > 2.2:
                    continue

                mt = datetime.fromisoformat(commence.replace("Z", "+00:00"))
                now = datetime.now(ZoneInfo("Europe/Moscow"))
                hours_left = (mt - now).total_seconds() / 3600
                if hours_left < 1 or hours_left > 24:
                    continue

                fd_match = None
                for m in fd_matches:
                    if (m["homeTeam"]["name"].lower() in home.lower() or home.lower() in m["homeTeam"]["name"].lower()) and \
                       (m["awayTeam"]["name"].lower() in away.lower() or away.lower() in m["awayTeam"]["name"].lower()):
                        fd_match = m
                        break

                country = "🌍 Неизвестно"
                h2h_icons = ["➖"] * 5
                home_icons = ["➖"] * 5
                form_icons = ["➖"] * 5
                h2h_score = 0.0
                home_form = away_form = 0.5
                table_diff = 0
                goal_diff = 0.0

                if fd_match:
                    home_id = fd_match["homeTeam"]["id"]
                    away_id = fd_match["awayTeam"]["id"]
                    competition_code = fd_match["competition"]["code"]
                    country = fd_match.get("competition", {}).get("name", "🌍 Неизвестно")

                    home_matches = await get_team_last_matches(session, home_id)
                    away_matches = await get_team_last_matches(session, away_id)
                    await asyncio.sleep(0.5)

                    h2h_data = await get_h2h(session, home_id, away_id)
                    h2h_matches = h2h_data.get("matches", [])
                    h2h_icons = get_h2h_icons(h2h_matches)
                    h2h_score = calc_h2h_score(h2h_matches[:5])
                    await asyncio.sleep(0.5)

                    home_form = calc_form(home_matches, home_id)
                    away_form = calc_form(away_matches, away_id)
                    goal_diff = get_goal_diff(home_matches, home_id)

                    home_icons = get_form_icons(home_matches, home_id, is_home_matches=True)
                    form_icons = get_form_icons(home_matches, home_id, is_home_matches=False)

                    home_pos = await get_table_position(session, home_id, competition_code)
                    away_pos = await get_table_position(session, away_id, competition_code)
                    await asyncio.sleep(0.5)

                    if home_pos is not None and away_pos is not None:
                        if home_pos < away_pos:
                            table_diff = 1
                        elif home_pos > away_pos:
                            table_diff = -1

                score = compute_score(h2h_score, home_form, away_form, table_diff, goal_diff, home_odds)

                cur.execute(
                    "INSERT INTO predictions (home, away, score, handicap, odds, time) VALUES (?, ?, ?, ?, ?, ?)",
                    (home, away, score, get_handicap(score), home_odds, mt.isoformat())
                )
                conn.commit()

                # Переводим названия команд на русский язык
                home_ru = translate_to_russian(home)
                away_ru = translate_to_russian(away)

                results.append({
                    "date": mt.strftime("%d.%m.%Y"),
                    "country": country,
                    "time": mt.strftime("%H:%M"),
                    "home": home_ru,
                    "away": away_ru,
                    "home_odds": round(home_odds, 2),
                    "away_odds": round(away_odds, 2),
                    "handicap": get_handicap(score),
                    "h2h_icons": h2h_icons,
                    "home_icons": home_icons,
                    "form_icons": form_icons,
                    "score": round(score, 3),
                    "confidence": round(score * (home_odds / 3.5), 3)
                })

            except Exception as e:
                logger.error(f"Error processing {home} vs {away}: {e}")
                continue

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

        # Получаем расписание NHL для сопоставления команд
        schedule_data = await get_nhl_schedule(session)
        games = schedule_data.get("dates", [])
        nhl_games = []
        if games:
            nhl_games = games[0].get("games", [])

        for game in odds_list:
            try:
                home = game["home_team"]
                away = game["away_team"]
                commence = game["commence_time"]

                home_odds, away_odds = extract_odds([game], home, away)
                if not home_odds or not away_odds:
                    continue
                if home_odds < 3.5 or away_odds > 2.2:
                    continue

                mt = datetime.fromisoformat(commence.replace("Z", "+00:00"))
                now = datetime.now(ZoneInfo("Europe/Moscow"))
                hours_left = (mt - now).total_seconds() / 3600
                if hours_left < 1 or hours_left > 24:
                    continue

                # Ищем матч в расписании NHL для получения ID команд
                nhl_game = None
                for ng in nhl_games:
                    if (ng["teams"]["home"]["team"]["name"].lower() in home.lower() or home.lower() in ng["teams"]["home"]["team"]["name"].lower()) and \
                       (ng["teams"]["away"]["team"]["name"].lower() in away.lower() or away.lower() in ng["teams"]["away"]["team"]["name"].lower()):
                        nhl_game = ng
                        break

                home_form = away_form = 0.5
                goal_diff = 0.0
                h2h_icons = ["➖"] * 5
                home_icons = ["➖"] * 5
                form_icons = ["➖"] * 5
                h2h_score = 0.0
                table_diff = 0

                if nhl_game:
                    home_id = nhl_game["teams"]["home"]["team"]["id"]
                    away_id = nhl_game["teams"]["away"]["team"]["id"]

                    # Получаем статистику команд
                    home_stats = await get_nhl_team_stats(session, home_id)
                    away_stats = await get_nhl_team_stats(session, away_id)
                    await asyncio.sleep(0.5)

                    home_stat = extract_nhl_team_stats(home_stats)
                    away_stat = extract_nhl_team_stats(away_stats)

                    home_form = home_stat["form"]
                    away_form = away_stat["form"]
                    goal_diff = home_stat["goal_diff"]

                    # Получаем позиции в дивизионе
                    home_rank = nhl_game["teams"]["home"]["leagueRecord"].get("divisionRank", 0)
                    away_rank = nhl_game["teams"]["away"]["leagueRecord"].get("divisionRank", 0)
                    if home_rank and away_rank:
                        if home_rank < away_rank:
                            table_diff = 1
                        elif home_rank > away_rank:
                            table_diff = -1

                score = compute_score(h2h_score, home_form, away_form, table_diff, goal_diff, home_odds)

                # Переводим названия команд на русский язык
                home_ru = translate_to_russian(home)
                away_ru = translate_to_russian(away)

                results.append({
                    "date": mt.strftime("%d.%m.%Y"),
                    "country": "🏒 NHL",
                    "time": mt.strftime("%H:%M"),
                    "home": home_ru,
                    "away": away_ru,
                    "home_odds": round(home_odds, 2),
                    "away_odds": round(away_odds, 2),
                    "handicap": get_handicap(score),
                    "h2h_icons": h2h_icons,
                    "home_icons": home_icons,
                    "form_icons": form_icons,
                    "score": round(score, 3),
                    "confidence": round(score * (home_odds / 3.5), 3)
                })
            except Exception as e:
                logger.error(f"Error processing hockey {home} vs {away}: {e}")
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
    await m.answer("🧞 JIN v6 ACTIVE\nПолная статистика по шаблону\nФутбол / Хоккей / Экспресс", reply_markup=keyboard)

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
        await asyncio.sleep(3600)

async def main():
    asyncio.create_task(loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
