import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from processor import AladdinProcessor

# --- КОНФИГУРАЦИЯ (Ключи вписаны) ---
BOT_TOKEN = "8694698903:AAHK51pTIQo4TFcBBF1RbL4Kh5OZRiLGTiM"

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
    # Если в списке уже лежат эмодзи (✅, ❌), просто склеиваем их
    if results and isinstance(results[0], str) and len(results[0]) == 1:
        return " ".join(results[:5])
        
    mapping = {"win": "✅", "draw": "♻️", "loss": "❌", "none": "➖"}
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
    
    # Создаем экземпляр процессора
    processor_inst = AladdinProcessor(sport_type)
    
    # ВАЖНО: вызываем get_analysis(), так как в твоем processor.py метод называется именно так
    raw_results = await processor_inst.get_analysis() 
    
    if not raw_results:
        await message.answer("❌ На данный момент подходящих матчей не найдено.")
        return

    # 1. СОРТИРОВКА по убыванию Score (в processor.py это total_score)
    # Так как данные приходят словарем, используем .get()
    raw_results.sort(key=lambda x: x.get('total_score', 0), reverse=True)
    
    # 2. ОГРАНИЧЕНИЕ: не более 21 матча
    top_matches = raw_results[:21]
    
    for m in top_matches:
        # Формируем отчет, извлекая данные из словаря m
        report = (
            f"📆 {datetime.now().strftime('%d.%m.%Y')}\n"
            f"🇷🇺 {m.get('league_name')}\n"
            f"🕰️ {m.get('match_time')} МСК\n"
            f"🏟️ {m.get('home_team')} ({m.get('home_odd'):.2f}) — {m.get('away_team')} ({m.get('away_odd'):.2f})\n"
            f"⛳ Рекомендуемая фора: {m.get('recommended_handicap')}\n"
            f"⏳ Очные (дома): {format_status_icons(m.get('h2h_results', []))}\n"
            f"🏟️ Дома (посл. 5): {format_status_icons(m.get('home_form_results', []))}\n"
            f"🤼‍♂️ Общая форма (5): {format_status_icons(m.get('total_form_results', []))}\n"
            f"------------------------"
        )
        await message.answer(report)

@dp.message(F.text == "🔥 Экспресс (4 матча)")
async def handle_express(message: Message):
    await message.answer("🔥 Формирую экспресс '333' из ТОП-4 матчей...")
    
    processor_inst = AladdinProcessor("hockey") 
    matches, total_odd = await processor_inst.get_express_333()
    
    if len(matches) < 4:
        await message.answer("❌ Недостаточно матчей для экспресса.")
        return

    res_text = f"🔥 ЭКСПРЕСС СФОРМИРОВАН!\nОбщий коэффициент: {total_odd}\n\n"
    for i, m in enumerate(matches, 1):
        res_text += f"{i}. {m['match']} — {m['bet']} ({m['koef']})\n"
    
    await message.answer(res_text)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(dp.start_polling(bot))
