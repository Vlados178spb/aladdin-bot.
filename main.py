import asyncio
import logging
from datetime import datetime
from typing import List

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import Config
from odds_api import OddsAPI
from analyzer import MatchAnalyzer, MatchAnalysis, Sport
from formatter import MessageFormatter

from loguru import logger
import pytz
import schedule
import time
import threading

# --- Инициализация бота ---
bot = Bot(
    token=Config.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# --- Глобальные объекты ---
analyzer_football = MatchAnalyzer(Sport.FOOTBALL)
analyzer_hockey = MatchAnalyzer(Sport.HOCKEY)
formatter = MessageFormatter()

# --- Статистика ---
stats = {
    "total_analyzed": 0,
    "successful": 0,
    "accuracy": 0.0,
    "min_home": Config.MIN_HOME_ODD,
    "max_away": Config.MAX_AWAY_ODD
}

# --- Функции анализа ---
async def analyze_all_matches() -> List[MatchAnalysis]:
    """Анализирует все матчи (футбол + хоккей)"""
    all_analyses = []
    
    # Футбол
    api_football = OddsAPI("football")
    try:
        matches = await api_football.fetch_matches()
        for match in matches:
            analysis = analyzer_football.analyze_single_match(match)
            if analysis.confidence.value != "LOW":  # Пропускаем LOW
                all_analyses.append(analysis)
        await api_football.close()
    except Exception as e:
        logger.error(f"Ошибка футбол API: {e}")
    
    # Хоккей
    api_hockey = OddsAPI("hockey")
    try:
        matches = await api_hockey.fetch_matches()
        for match in matches:
            analysis = analyzer_hockey.analyze_single_match(match)
            if analysis.confidence.value != "LOW":
                all_analyses.append(analysis)
        await api_hockey.close()
    except Exception as e:
        logger.error(f"Ошибка хоккей API: {e}")
    
    stats["total_analyzed"] = len(all_analyses)
    return all_analyses

# --- Команды бота ---
@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Приветственное сообщение"""
    await message.answer(
        "🧞‍♂️ **Aladdin Bot** приветствует тебя!\n\n"
        "Я анализирую футбольные и хоккейные матчи по уникальной стратегии:\n"
        f"• 🏠 Домашний кэф ≥ {Config.MIN_HOME_ODD}\n"
        f"• 🚌 Гостевой кэф ≤ {Config.MAX_AWAY_ODD}\n\n"
        "Ищу выгодные форы для домашней команды!\n\n"
        "Команды:\n"
        "/today — Прогнозы на сегодня\n"
        "/express — Экспресс дня (4 матча)\n"
        "/stats — Статистика бота"
    )

@dp.message(Command("today"))
async def cmd_today(message: Message):
    """Показывает все прогнозы на сегодня"""
    await message.answer("🔍 Анализирую матчи... (это может занять до 30 секунд)")
    
    analyses = await analyze_all_matches()
    
    if not analyses:
        await message.answer(
            "😔 Сегодня нет подходящих матчей.\n"
            "Попробуйте позже или проверьте /express"
        )
        return
    
    # Сортируем по уверенности
    analyses.sort(key=lambda x: (
        x.confidence.value == "HIGH",
        x.total_score
    ), reverse=True)
    
    # Отправляем топ-10
    response = ["🎯 **ЛУЧШИЕ ПРОГНОЗЫ НА СЕГОДНЯ**\n"]
    for analysis in analyses[:10]:
        response.append(formatter.format_match(analysis))
    
    response.append("⚠️ Помните: ставки — это риск. Анализируйте самостоятельно!")
    
    await message.answer("\n".join(response))

@dp.message(Command("express"))
async def cmd_express(message: Message):
    """Формирует экспресс из 4 самых надежных матчей"""
    await message.answer("🔥 Собираю экспресс дня...")
    
    analyses = await analyze_all_matches()
    
    # Фильтруем только HIGH и MEDIUM
    reliable = [a for a in analyses if a.confidence.value in ["HIGH", "MEDIUM"]]
    reliable.sort(key=lambda x: (x.confidence.value == "HIGH", x.total_score), reverse=True)
    
    if len(reliable) < 4:
        await message.answer(
            f"❌ Недостаточно надежных матчей для экспресса.\n"
            f"Найдено: {len(reliable)}/4\n"
            f"Попробуйте /today для просмотра всех прогнозов."
        )
        return
    
    # Берем топ-4
    top4 = reliable[:4]
    express_text = formatter.format_express(top4)
    
    await message.answer(express_text)

@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    """Показывает статистику бота"""
    stats_text = formatter.format_stats(stats)
    await message.answer(stats_text)

# --- Фоновый планировщик ---
def run_scheduler():
    """Запускает ежедневное обновление в 10:00 МСК"""
    async def daily_update():
        logger.info("Ежедневное обновление матчей...")
        await analyze_all_matches()
    
    def job():
        asyncio.run(daily_update())
    
    schedule.every().day.at("10:00").do(job)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

# --- Запуск ---
async def main():
    logger.info("🚀 Aladdin Bot запускается...")
    
    # Запускаем планировщик в отдельном потоке
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    # Запускаем бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
