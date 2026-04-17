import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from processor import AladdinProcessor

# --- КОНФИГУРАЦИЯ (Ключи вписаны) ---
BOT_TOKEN = "8694698903:AAHK51pTIQo4TFcBBF1RbL4Kh5OZRiLGTiM"
ODDS_API_KEY = "2be3c040e725dabfe695ae282049a8b0"
# Дополнительные ключи (используются в соответствующих модулях)
FOOTBALL_KEY = "f286e713f060483e83f6d722f1d58ddf"
ISPORTS_API_KEY = "csHMISYm949upbV6"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Клавиатура
menu_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="⚽ Футбол"), KeyboardButton(text="🏒 Хоккей")],
        [KeyboardButton(text="🔥 Экспресс (4 матча)")]
    ],
    resize_keyboard=True
)

def format_status_icons(results: list) -> str:
    """Превращает список результатов в строку иконок (макс 5)"""
    mapping = {"win": "✅", "draw": "♻️", "loss": "❌", "none": "➖"}
    # Берем последние 5 или заполняем прочерками
    icons = [mapping.get(res, "➖") for res in results[:5]]
    while len(icons) < 5:
        icons.append("➖")
    return " ".join(icons)

@dp.message(F.text == "/start")
async def cmd_start(message: Message):
    await message.answer("🚀 Система 'АЛАДДИН' готова. Выберите вид спорта:", reply_markup=menu_kb)

@dp.message(F.text.in_({"⚽ Футбол", "🏒 Хоккей"}))
async def handle_single_sport(message: Message):
    sport_type = "football" if "Футбол" in message.text else "hockey"
    await message.answer(f"⏳ Анализирую лучшие матчи ({message.text})...")
    
    processor = AladdinProcessor(sport_type)
    # Получаем проанализированные матчи
    # Предполагаем, что processor возвращает расширенные данные MatchAnalysis
    raw_results = await processor.get_raw_analysis() 
    
    if not raw_results:
        await message.answer("❌ На данный момент подходящих матчей не найдено.")
        return

    # 1. СОРТИРОВКА по убыванию Score
    raw_results.sort(key=lambda x: x.total_score, reverse=True)
    
    # 2. ОГРАНИЧЕНИЕ: не более 21 матча
    top_matches = raw_results[:21]
    
    for m in top_matches:
        # Формируем шаблон по твоему ТЗ
        report = (
            f"📆 {datetime.now().strftime('%d.%m.%Y')}\n"
            f"🇷🇺 {m.league_name}\n"
            f"🕰️ {m.match_time} МСК\n"
            f"🏟️ {m.home_team} ({m.home_odd:.2f}) — {m.away_team} ({m.away_odd:.2f})\n"
            f"⛳ Рекомендуемая фора: +{m.safe_handicap}\n"
            f"⏳ Очные (дома): {format_status_icons(m.h2h_results)}\n"
            f"🏟️ Дома (посл. 5): {format_status_icons(m.home_form_results)}\n"
            f"🤼‍♂️ Общая форма (5): {format_status_icons(m.total_form_results)}\n"
            f"------------------------"
        )
        await message.answer(report)

@dp.message(F.text == "🔥 Экспресс (4 матча)")
async def handle_express(message: Message):
    await message.answer("🔥 Формирую экспресс '333' из ТОП-4 матчей по Score...")
    
    processor = AladdinProcessor("hockey") # Или микс
    matches, total_odd = await processor.get_express_333()
    
    if len(matches) < 4:
        await message.answer("❌ Недостаточно матчей с высоким Score для экспресса.")
        return

    res_text = f"🔥 ЭКСПРЕСС СФОРМИРОВАН!\nОбщий коэффициент: {total_odd}\n\n"
    for i, m in enumerate(matches, 1):
        res_text += f"{i}. {m['match']} — {m['bet']} ({m['koef']})\n"
    
    await message.answer(res_text)

if __name__ == "__main__":
    logging.info("Бот запущен...")
    asyncio.run(dp.start_polling(bot))
