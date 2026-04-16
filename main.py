import asyncio
import logging
from bot import dp, bot  # Твой основной файл бота
from services.services.processor import AladdinProcessor

# Логирование для отслеживания работы в Railway или Termux
logging.basicConfig(level=logging.INFO)

async def start_aladdin_system():
    print("🚀 СИСТЕМА 'АЛАДДИН' ЗАПУЩЕНА НА МАКСИМАЛКАХ")
    print("✅ Реальные данные: The Odds API + OpenLigaDB")
    print("✅ Логика: Формат 333 + Самообучение")
    
    try:
        # Запуск процесса приема сообщений
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Ошибка при работе бота: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(start_aladdin_system())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот выключен.")
