import asyncio
import logging
import sys
from dotenv import load_dotenv

# Загружаем переменные из .env ПЕРВЫМ ДЕЛОМ
load_dotenv()

# Импортируем объекты напрямую из корня
from bot import dp, bot

# Настройка логирования для Railway
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

async def start_aladdin_system():
    print("🚀 СИСТЕМА 'АЛАДДИН' ЗАПУЩЕНА")
    
    try:
        # Запуск бота
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка при работе бота: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(start_aladdin_system())
