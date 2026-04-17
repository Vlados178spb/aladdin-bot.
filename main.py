import asyncio
import logging
from enum import Enum

from odds_api import OddsAPI
from analyzer import MatchAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BotMode(Enum):
    FOOTBALL = "⚽ Футбол"
    HOCKEY = "🏒 Хоккей"
    EXPRESS = "🔥 Экспресс"


class ValueBetBot:

    def __init__(self):
        self.football_api = OddsAPI("football")
        self.hockey_api = OddsAPI("hockey")

        self.football_analyzer = MatchAnalyzer()
        self.hockey_analyzer = MatchAnalyzer()

    async def start(self):
        print("🤖 JIN BOT ЗАПУЩЕН")

        while True:
            print("\n1. Футбол\n2. Хоккей\n3. Экспресс\n0. Выход")
            choice = input("👉 ").strip()

            if choice == "1":
                await self._handle(self.football_api, self.football_analyzer, "⚽")
            elif choice == "2":
                await self._handle(self.hockey_api, self.hockey_analyzer, "🏒")
            elif choice == "3":
                await self._handle_express()
            elif choice == "0":
                break

    async def _handle(self, api, analyzer, icon):
        print("\n⏳ Загружаю матчи...")

        matches = await api.fetch_matches()

        if not matches:
            print("❌ Нет матчей")
            return

        analyses = [analyzer.analyze_single_match(m) for m in matches]

        analyses.sort(key=lambda x: -x.total_score)

        for i, a in enumerate(analyses[:10], 1):
            print(f"\n{i}. {icon} {a.home_team} vs {a.away_team}")
            print(f"   📊 {a.home_odd} / {a.away_odd}")
            print(f"   🎯 Фора +{a.recommended_handicap}")
            print(f"   💪 {a.confidence} | Score {a.total_score}")
            print(f"   📝 {a.bet_reason}")

    async def _handle_express(self):
        print("\n🔥 Собираю экспресс...")

        f = await self.football_api.fetch_matches()
        h = await self.hockey_api.fetch_matches()

        all_matches = f + h

        analyzer = MatchAnalyzer()
        analyses = [analyzer.analyze_single_match(m) for m in all_matches]

        analyses = [a for a in analyses if a.confidence in ["HIGH", "MEDIUM"]]

        if len(analyses) < 4:
            print("❌ Недостаточно матчей")
            return

        analyses.sort(key=lambda x: -x.total_score)

        top4 = analyses[:4]

        total = 1

        print("\n🔥 ЭКСПРЕСС:")

        for i, a in enumerate(top4, 1):
            coef = 1.8
            total *= coef

            print(f"{i}. {a.home_team} vs {a.away_team}")
            print(f"   Фора +{a.recommended_handicap} | кэф {coef}")

        print(f"\n📊 Общий кэф: {round(total,2)}")


async def main():
    bot = ValueBetBot()
    await bot.start()


if __name__ == "__main__":
    asyncio.run(main())
