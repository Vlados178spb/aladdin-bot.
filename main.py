from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

from config import BOT_TOKEN
from data import DataService
from analyzer import analyze
from formatter import format_match

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

data_service = DataService()


@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    await msg.answer("🔥 JIN запущен\n\nЖми /find")


@dp.message_handler(commands=["find"])
async def find(msg: types.Message):
    await msg.answer("⏳ Сканирую все матчи...")

    matches = await data_service.get_matches()

    if not matches:
        await msg.answer("❌ Нет матчей по фильтру")
        return

    analyzed = [analyze(m) for m in matches]

    analyzed.sort(key=lambda x: -x["score"])

    text = "🔥 ТОП VALUE МАТЧИ (сегодня)\n\n"

    for m in analyzed[:10]:
        text += format_match(m)

    await msg.answer(text)


if __name__ == "__main__":
    executor.start_polling(dp)
