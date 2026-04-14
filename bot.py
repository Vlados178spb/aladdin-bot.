import asyncio
import aiohttp
import sqlite3
import numpy as np

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# =====================
# 🔑 KEYS (ВСТАВЛЕНЫ РЕАЛЬНЫЕ КЛЮЧИ)
# =====================
BOT_TOKEN = "8694698903:AAHK51pTIQo4TFcBBF1RbL4Kh5OZRiLGTiM"
ODDS_API_KEY = "2be3c040e725dabfe695ae282049a8b0"
FOOTBALL_DATA_KEY = "f286e713f060483e83f6d722f1d58ddf"

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# =====================
# 📦 DB
# =====================
conn = sqlite3.connect("jin_v28.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS bets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match TEXT,
    sport TEXT,
    odds REAL,
    prob REAL,
    edge REAL
)
""")
conn.commit()

# =====================
# 📱 UI
# =====================
keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="⚽ Футбол 24H")],
        [KeyboardButton(text="🏒 Хоккей 24H")],
        [KeyboardButton(text="🏀 NBA 24H")],
        [KeyboardButton(text="🎾 Теннис 24H")],
        [KeyboardButton(text="🔥 Экспресс")],
    ],
    resize_keyboard=True
)

# =====================
# 🌐 ODDS API
# =====================
async def fetch(session, url):
    async with session.get(url) as r:
        return await r.json()

async def get_odds(session, sport):
    url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h"
    return await fetch(session, url)

# =====================
# ⚽ FOOTBALL DATA FORM ENGINE
# =====================
async def get_form(session, team_id):
    url = f"https://api.football-data.org/v4/teams/{team_id}/matches?limit=5"
    headers = {"X-Auth-Token": FOOTBALL_DATA_KEY}
    async with session.get(url, headers=headers) as r:
        data = await r.json()

    matches = data.get("matches", [])
    wins = 0
    goals_for = 0
    goals_against = 0

    for m in matches:
        score = m.get("score", {}).get("fullTime", {})
        if not score:
            continue
        gf = score.get("home") or 0
        ga = score.get("away") or 0
        goals_for += gf
        goals_against += ga
        if gf > ga:
            wins += 1

    form_score = 0.5 + (wins * 0.08) + ((goals_for - goals_against) * 0.02)
    return max(0.3, min(form_score, 0.75))

# =====================
# 🧠 MARKET PROB
# =====================
def market_prob(odds):
    return 1 / odds

# =====================
# ⚖️ EDGE
# =====================
def edge(p, m):
    return (p - m) + (p - 0.5) * 0.25

# =====================
# 💰 KELLY
# =====================
def kelly(p, odds):
    b = odds - 1
    q = 1 - p
    return max(0, ((b * p - q) / b) * 0.30)

# =====================
# ⚖️ FILTER (STABLE)
# =====================
def valid(odds, p, e):
    return (
        1.45 <= odds <= 2.85 and
        p >= 0.57 and
        e >= 0.025
    )

# =====================
# 🧠 PROCESS
# =====================
def process(data):
    results = []
    for m in data:
        try:
            home = m["home_team"]
            away = m["away_team"]
            bookmakers = m["bookmakers"][0]["markets"][0]["outcomes"]
            home_odds = next(x["price"] for x in bookmakers if x["name"] == home)
            away_odds = next(x["price"] for x in bookmakers if x["name"] == away)
            odds = home_odds

            # 🧠 FORM PROXY (simplified stable version)
            home_form = 0.62 if "Man" in home or "Real" in home else 0.52
            away_form = 0.50

            p = home_form / (home_form + away_form)
            mkt = market_prob(odds)
            e = edge(p, mkt)

            if not valid(odds, p, e):
                continue

            stake = kelly(p, odds) * 1000
            results.append({
                "match": f"{home} vs {away}",
                "odds": round(odds, 2),
                "prob": round(p, 2),
                "edge": round(e, 3),
                "stake": round(stake, 2)
            })
        except:
            continue

    return sorted(results, key=lambda x: x["edge"], reverse=True)

# =====================
# 📦 CACHE
# =====================
CACHE = {}

async def build_cache():
    async with aiohttp.ClientSession() as session:
        sports = ["soccer", "icehockey_nhl", "basketball_nba", "tennis_atp"]
        all_results = []
        for s in sports:
            data = await get_odds(session, s)
            processed = process(data)
            CACHE[s] = processed
            all_results += processed

        # 🔥 EXPRES 4 DIVERSE PICKS
        express = []
        used = set()
        for m in sorted(all_results, key=lambda x: x["edge"], reverse=True):
            team = m["match"].split(" vs ")[0]
            if team in used:
                continue
            express.append(m)
            used.add(team)
            if len(express) == 4:
                break
        CACHE["express"] = express

# =====================
# 📨 FORMAT
# =====================
def format(data, title):
    if not data:
        return "❌ Нет сигналов"
    msg = f"🧠 <b>JIN v28 STABLE PRO - {title}</b>\n\n"
    for i, m in enumerate(data[:12], 1):
        msg += f"{i}. {m['match']}\n"
        msg += f"📊 Odds: {m['odds']}\n"
        msg += f"🧠 Prob: {m['prob']}\n"
        msg += f"🔥 Edge: {m['edge']}\n"
        msg += f"💰 Stake: {m['stake']}\n\n"
    return msg

# =====================
# 🤖 HANDLERS
# =====================
@dp.message(Command("start"))
async def start(m: Message):
    await m.answer("🧠 JIN v28 STABLE PRO ACTIVE", reply_markup=keyboard)

@dp.message(F.text == "⚽ Футбол 24H")
async def soccer(m: Message):
    await m.answer(format(CACHE.get("soccer", []), "FOOTBALL"))

@dp.message(F.text == "🏒 Хоккей 24H")
async def nhl(m: Message):
    await m.answer(format(CACHE.get("icehockey_nhl", []), "NHL"))

@dp.message(F.text == "🏀 NBA 24H")
async def nba(m: Message):
    await m.answer(format(CACHE.get("basketball_nba", []), "NBA"))

@dp.message(F.text == "🎾 Теннис 24H")
async def tennis(m: Message):
    await m.answer(format(CACHE.get("tennis_atp", []), "TENNIS"))

@dp.message(F.text == "🔥 Экспресс")
async def exp(m: Message):
    await m.answer(format(CACHE.get("express", []), "EXPRESS (4 PICKS)"))

# =====================
# 🔁 LOOP
# =====================
async def loop():
    while True:
        try:
            await build_cache()
        except:
            pass
        await asyncio.sleep(1800)

# =====================
# 🚀 MAIN
# =====================
async def main():
    await build_cache()
    asyncio.create_task(loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
