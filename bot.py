
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict

import aiohttp
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from zoneinfo import ZoneInfo

# =====================
# 🔑 KEYS (ВСЕ ТРИ КЛЮЧА)
# =====================
BOT_TOKEN = "8694698903:AAHK51pTIQo4TFcBBF1RbL4Kh5OZRiLGTiM"
ODDS_API_KEY = "2be3c040e725dabfe695ae282049a8b0"
FOOTBALL_DATA_KEY = "f286e713f060483e83f6d722f1d58ddf"

# =====================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aladdin")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router()
dp.include_router(router)

FOOTBALL_CACHE = []
EXPRESS_CACHE = []

# =====================
# KEYBOARD
# =====================
keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="⚽ Футбол")],
        [KeyboardButton(text="🍺 Экспрэс 🍺")]
    ],
    resize_keyboard=True
)

# =====================
# HTTP
# =====================
async def fetch(session, url):
    try:
        async with session.get(url) as r:
            if r.status == 429:
                await asyncio.sleep(3)
                return await fetch(session, url)
            return await r.json()
    except:
        return {}

# =====================
# DATA
# =====================
async def get_events(session):
    url = f"https://api.the-odds-api.com/v4/sports/soccer/events?apiKey={ODDS_API_KEY}"
    data = await fetch(session, url)
    return data if isinstance(data, list) else []

async def get_odds(session, event_id):
    url = f"https://api.the-odds-api.com/v4/sports/soccer/events/{event_id}/odds?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h"
    return await fetch(session, url)

# =====================
# MODEL (REALITY)
# =====================
def true_prob(home_odds, away_odds):
    hp = 1 / home_odds
    ap = 1 / away_odds
    return hp / (hp + ap)

def value(prob, odds):
    return (prob * odds) - 1

# =====================
# PROCESS
# =====================
async def build():
    global FOOTBALL_CACHE, EXPRESS_CACHE

    async with aiohttp.ClientSession() as session:
        events = await get_events(session)

        results = []

        for e in events:
            try:
                event_id = e["id"]
                home = e["home_team"]
                away = e["away_team"]
                time = e["commence_time"]

                odds_data = await get_odds(session, event_id)
                if not odds_data.get("bookmakers"):
                    continue

                bk = odds_data["bookmakers"][0]
                markets = bk.get("markets", [])
                h2h = next((m for m in markets if m["key"] == "h2h"), None)
                if not h2h:
                    continue

                outs = h2h["outcomes"]
                home_odds = next(o["price"] for o in outs if o["name"] == home)
                away_odds = next(o["price"] for o in outs if o["name"] == away)

                # FILTER odds
                if not (1.5 <= home_odds <= 3.2):
                    continue

                # TIME FILTER
                mt = datetime.fromisoformat(time.replace("Z", "+00:00"))
                now = datetime.now(ZoneInfo("Europe/Moscow"))
                hours_left = (mt - now).total_seconds() / 3600

                if hours_left < 1 or hours_left > 24:
                    continue

                # MODEL
                p = true_prob(home_odds, away_odds)
                v = value(p, home_odds)

                # HARD FILTER
                if v < 0.10:
                    continue

                results.append({
                    "home": home,
                    "away": away,
                    "time": mt.strftime("%H:%M"),
                    "odds": home_odds,
                    "value": round(v, 2),
                    "prob": round(p, 2),
                })

                await asyncio.sleep(0.2)

            except:
                continue

        results = sorted(results, key=lambda x: x["value"], reverse=True)

        FOOTBALL_CACHE = results[:9]

        # EXPRESS (1 per day logic handled later)
        EXPRESS_CACHE = [
            x for x in results
            if x["value"] >= 0.15
        ][:4]

# =====================
# FORMAT
# =====================
def format_signals(data):
    if not data:
        return "🧞 Сегодня лампа молчит..."

    msg = "🧞‍♂️ ALADDIN SIGNALS\n\n"

    for i, m in enumerate(data, 1):
        msg += f"{i}. {m['home']} vs {m['away']}\n"
        msg += f"🕒 {m['time']}\n"
        msg += f"📊 Odds: {m['odds']}\n"
        msg += f"🔥 Value: {m['value']}\n\n"

    return msg

# =====================
# HANDLERS
# =====================
@router.message(Command("start"))
async def start(m: Message):
    await m.answer("🧞‍♂️ Джин активирован", reply_markup=keyboard)

@router.message(F.text == "⚽ Футбол")
async def show(m: Message):
    await m.answer(format_signals(FOOTBALL_CACHE))

@router.message(F.text == "🍺 Экспрэс 🍺")
async def express(m: Message):
    if not EXPRESS_CACHE:
        await m.answer("🧞 Экспресса сегодня нет")
        return
    await m.answer(format_signals(EXPRESS_CACHE))

# =====================
# LOOP
# =====================
async def loop():
    while True:
        await build()
        await asyncio.sleep(3600)

async def main():
    asyncio.create_task(loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
