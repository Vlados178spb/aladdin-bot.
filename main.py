import asyncio
import logging
import sys

# Импортируем объекты напрямую из корня
from bot import dp, bot
from processor import processor

# Настройка логирования для Railway
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

async def start_aladdin_system():
    print("🚀 СИСТЕМА 'АЛАДДИН' ЗАПУЩЕНА НА МАКСИМАЛКАХ")
    print("✅ Логика: Корневая структура")
    print("✅ Статус: Готов к анализу")

    try:
        # Запуск процесса приема сообщений
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"❌ Критическая ошибка при работе бота: {e}")
    finally:
        # Закрываем сессию при остановке
        await bot.session.close()
        print("🔌 Система Аладдин отключена")

if __name__ == "__main__":
    try:
        asyncio.run(start_aladdin_system())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен пользователем")
