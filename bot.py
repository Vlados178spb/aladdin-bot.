import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict

import aiohttp
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command
from aiogram.types import Message, BotCommand, ReplyKeyboardMarkup, KeyboardButton
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

BOT_TOKEN = "8694698903:AAHK51pTIQo4TFcBBF1RbL4Kh5OZRiLGTiM"
ODDS_API_KEY = "2be3c040e725dabfe695ae282049a8b0"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router()
dp.include_router(router)

FOOTBALL_CACHE = []
HOCKEY_CACHE = []

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="⚽ Футбол")], [KeyboardButton(text="🏒 Хоккей")]],
    resize_keyboard=True
)

async def fetch_json(session: aiohttp.ClientSession, url: str) -> Dict:
    try:
        async with session.get(url) as response:
            if response.status == 429:
                logger.warning("⚠️ Лимит API. Жду 5 сек...")
                await asyncio.sleep(5)
                async with session.get(url) as retry:
                    retry.raise_for_status()
                    return await retry.json()
            response.raise_for_status()
            return await response.json()
    except Exception as e:
        logger.error(f"Ошибка запроса: {e}")
        return {}

async def get_events(session: aiohttp.ClientSession, sport_key: str) -> List[Dict]:
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/events?apiKey={ODDS_API_KEY}"
    data = await fetch_json(session, url)
    return data if isinstance(data, list) else []

async def get_event_odds(session: aiohttp.ClientSession, sport_key: str, event_id: str) -> Dict:
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/events/{event_id}/odds?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h&bookmakers=pinnacle"
    return await fetch_json(session, url)

async def get_event_history(session: aiohttp.ClientSession, sport_key: str, event_id: str) -> List[Dict]:
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/events/{event_id}/odds-history?apiKey={ODDS_API_KEY}&markets=h2h&date={datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')}"
    data = await fetch_json(session, url)
    return data.get('data', []) if data else []

def check_h2h_condition(history_data: List[Dict]) -> bool:
    three_years_ago = datetime.now() - timedelta(days=3*365)
    for record in history_data:
        try:
            match_time = datetime.fromisoformat(record.get('commence_time', '').replace('Z', '+00:00'))
            if match_time < three_years_ago:
                continue
            if record.get('home_winner') is True or record.get('draw') is True:
                return True
            scores = record.get('scores')
            if scores:
                home = scores.get('home')
                away = scores.get('away')
                if home is not None and away is not None and home >= away:
                    return True
        except:
            continue
    return False

async def fetch_and_filter_sport(sport_key: str, cache_list: list):
    logger.info(f"🔄 Обновление {sport_key}...")
    filtered = []
    async with aiohttp.ClientSession() as session:
        events = await get_events(session, sport_key)
        if not events:
            logger.warning(f"Нет событий для {sport_key}")
            cache_list.clear()
            return
        events.sort(key=lambda x: x.get('commence_time', '9999'))
        for event in events:
            event_id = event.get('id')
            if not event_id:
                continue
            home = event.get('home_team', 'Неизвестно')
            away = event.get('away_team', 'Неизвестно')
            commence = event.get('commence_time', '')
            odds = await get_event_odds(session, sport_key, event_id)
            if not odds or 'bookmakers' not in odds or not odds['bookmakers']:
                continue
            bookmaker = odds['bookmakers'][0]
            markets = [m for m in bookmaker.get('markets', []) if m.get('key') == 'h2h']
            if not markets:
                continue
            outcomes = markets[0].get('outcomes', [])
            home_odds = next((o['price'] for o in outcomes if o.get('name') == home), None)
            away_odds = next((o['price'] for o in outcomes if o.get('name') == away), None)
            if home_odds is None or away_odds is None:
                continue
            if home_odds >= 4.5 and away_odds <= 2.0:
                history = await get_event_history(session, sport_key, event_id)
                h2h_ok = check_h2h_condition(history)
                match_time = datetime.fromisoformat(commence.replace('Z', '+00:00'))
                date_str = match_time.strftime('%d.%m.%Y')
                time_str = match_time.astimezone().strftime('%H:%M МСК')
                filtered.append({
                    'date': date_str,
                    'time': time_str,
                    'home_team': home,
                    'away_team': away,
                    'home_odds': f"{home_odds:.2f}",
                    'away_odds': f"{away_odds:.2f}",
                    'h2h_ok': h2h_ok,
                    'commence_time': commence,
                })
            await asyncio.sleep(0.2)
    filtered.sort(key=lambda x: (x['commence_time'], not x['h2h_ok']))
    cache_list.clear()
    cache_list.extend(filtered)
    logger.info(f"✅ {sport_key}: найдено {len(filtered)}")

async def update_all_sports():
    await asyncio.gather(
        fetch_and_filter_sport('soccer', FOOTBALL_CACHE),
        fetch_and_filter_sport('icehockey_nhl', HOCKEY_CACHE)
    )

async def daily_updater():
    while True:
        now = datetime.now()
        target = now.replace(hour=3, minute=0, second=0, microsecond=0)
        if now > target:
            target += timedelta(days=1)
        wait = (target - now).total_seconds()
        logger.info(f"⏳ Следующее обновление через {wait/3600:.1f} ч.")
        await asyncio.sleep(wait)
        await update_all_sports()

@router.message(Command("start"))
async def start_cmd(message: Message):
    await message.answer(
        "🪔 Привет! Я Аладдин.\n"
        "Каждый день в 03:00 МСК обновляю списки:\n"
        "• П1 ≥ 4.5\n"
        "• П2 ≤ 2.0\n"
        "• ✅ — хозяева не проигрывали дома за 3 года\n\n"
        "Выбери спорт:",
        reply_markup=MAIN_KEYBOARD
    )

def format_matches(matches: list, sport_name: str) -> str:
    if not matches:
        return f"🧞‍♂️ Для {sport_name} сегодня лампа пуста..."
    limited = matches[:21]
    lines = [f"🏆 {sport_name}"]
    grouped = {}
    for m in limited:
        grouped.setdefault(m['date'], []).append(m)
    for date, items in grouped.items():
        lines.append(f"📆 {date}")
        for m in items:
            mark = "✅" if m['h2h_ok'] else ""
            lines.append(f"🕰️ {m['time']}\n🏟️ {m['home_team']} {m['home_odds']} — {m['away_team']} {m['away_odds']} {mark}\n")
    return "\n".join(lines)

@router.message(F.text == "⚽ Футбол")
async def show_football(message: Message):
    await message.answer(format_matches(FOOTBALL_CACHE, "Футбол"), disable_web_page_preview=True)

@router.message(F.text == "🏒 Хоккей")
async def show_hockey(message: Message):
    await message.answer(format_matches(HOCKEY_CACHE, "Хоккей"), disable_web_page_preview=True)

async def main():
    await bot.set_my_commands([BotCommand(command="start", description="Запуск")])
    asyncio.create_task(update_all_sports())
    asyncio.create_task(daily_updater())
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
