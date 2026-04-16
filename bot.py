import asyncio
import logging
from datetime import datetime
import pytz
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from deep_translator import GoogleTranslator

# ИСПРАВЛЕННЫЙ ПУТЬ (под твою структуру папок)
from services.processor import AladdinProcessor

# --- КОНФИГУРАЦИЯ ---
BOT_TOKEN = "8694698903:AAHK51pTIQo4TFcBBF1RbL4Kh5OZRiLGTiM"
ODDS_API_KEY = "2be3c040e725dabfe695ae282049a8b0"
FOOTBALL_KEY = "f286e713f060483e83f6d722f1d58ddf"
ISPORTS_API_KEY = "csHMISYm949upbV6"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
translator = GoogleTranslator(source='en', target='ru')
moscow_tz = pytz.timezone('Europe/Moscow')

# Клавиатура
menu_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="⚽ Футбол"), KeyboardButton(text="🏒 Хоккей")],
        [KeyboardButton(text="🔥 Экспресс (4 матча)")]
    ],
    resize_keyboard=True
)

def format_status_icons(results: list) -> str:
    """Превращает список результатов в строку иконок"""
    mapping = {"win": "✅", "draw": "♻️", "loss": "❌", "none": "➖"}
    if not results:
        return "➖ ➖ ➖ ➖ ➖"
    icons = [mapping.get(res, "➖") for res in results[:5]]
    while len(icons) < 5:
        icons.append("➖")
    return " ".join(icons)

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("🚀 Система 'АЛАДДИН' готова. Выберите вид спорта:", reply_markup=menu_kb)

@dp.message(F.text.in_({"⚽ Футбол", "🏒 Хоккей"}))
async def handle_single_sport(message: Message):
    sport_type = "football" if "Футбол" in message.text else "hockey"
    status_msg = await message.answer(f"⏳ Анализирую лучшие матчи ({message.text})...")
    
    try:
        processor = AladdinProcessor(sport_type)
        # Получаем данные (используем универсальный метод)
        raw_results = await processor.get_analysis() 
        
        if not raw_results:
            await status_msg.edit_text("❌ На данный момент подходящих матчей не найдено.")
            return

        # Сортировка по Score (если он есть в данных)
        raw_results.sort(key=lambda x: x.get('total_score', 0) if isinstance(x, dict) else getattr(x, 'total_score', 0), reverse=True)
        
        await status_msg.delete()

        for m in raw_results[:10]: # Ограничим до 10 для скорости
            # Перевод названий (если данные на английском)
            try:
                home_name = translator.translate(m.get('home_team', 'Team A'))
                away_name = translator.translate(m.get('away_team', 'Team B'))
                league = translator.translate(m.get('league_name', 'League'))
            except:
                home_name = m.get('home_team', 'Team A')
                away_name = m.get('away_team', 'Team B')
                league = m.get('league_name', 'League')

            report = (
                f"📆 {datetime.now(moscow_tz).strftime('%d.%m.%Y')}\n"
                f"🇷🇺 {league}\n"
                f"🕰️ {m.get('match_time', '--:--')} МСК\n"
                f"🏟️ {home_name} ({m.get('home_odd', 0)}) — {away_name} ({m.get('away_odd', 0)})\n"
                f"⛳ Рекомендация: {m.get('recommendation', 'Анализ...')}\n"
                f"⏳ Очные (дома): {format_status_icons(m.get('h2h_results', []))}\n"
                f"🏟️ Дома (посл. 5): {format_status_icons(m.get('home_form_results', []))}\n"
                f"🤼‍♂️ Общая форма (5): {format_status_icons(m.get('total_form_results', []))}\n"
                f"------------------------"
            )
            await message.answer(report)
            
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await message.answer("⚠️ Ошибка при чтении данных из процессора. Проверьте структуру папок.")

@dp.message(F.text == "🔥 Экспресс (4 матча)")
async def handle_express(message: Message):
    await message.answer("🔥 Формирую экспресс '333' из ТОП-4 матчей...")
    # Здесь логика экспресса подтянется из твоего файла processor.py
    await message.answer("⏳ Функция формирования изображения экспресса в процессе подключения...")

async def main():
    logging.info("🚀 БОТ ЗАПУСКАЕТСЯ...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
