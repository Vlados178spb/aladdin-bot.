import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import Config
from odds_api import OddsAPI
from formatter import format_matches

bot = Bot(token=Config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Клавиатура с иконками
kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="⚽️ Футбол"), KeyboardButton(text="🏒 Хоккей")]
    ],
    resize_keyboard=True
)

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "🧞 <b>Я твой ДЖИН АЛЛАДИН!</b>\n\n"
        "🎯 Моя задача — находить матчи с выгодной форой.\n\n"
        "📌 <u>Условия поиска:</u>\n"
        "• 🏠 Домашний коэффициент ≥ 3.4\n"
        "• 🚌 Гостевой коэффициент ≤ 2.0\n\n"
        "👇 Выбери спорт, и я покажу подходящие игры на сегодня.",
        reply_markup=kb
    )

@dp.message(lambda m: m.text == "⚽️ Футбол")
async def football(message: types.Message):
    await message.answer("🔍 Ищу футбольные матчи...")
    api = OddsAPI("football")
    matches = await api.fetch_matches()
    await api.close()
    await message.answer(format_matches(matches))

@dp.message(lambda m: m.text == "🏒 Хоккей")
async def hockey(message: types.Message):
    await message.answer("🔍 Ищу хоккейные матчи...")
    api = OddsAPI("hockey")
    matches = await api.fetch_matches()
    await api.close()
    await message.answer(format_matches(matches))

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
