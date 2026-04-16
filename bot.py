import asyncio
import logging
from enum import Enum
from typing import Optional

# Импорт ваших модулей
from services.odds_api import OddsAPI
from services.analyzer import MatchAnalyzer, ExpressBuilder, Sport, MatchAnalysis, ExpressAnalysis

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BotMode(Enum):
    FOOTBALL = "⚽ Футбол"
    HOCKEY = "🏒 Хоккей"
    EXPRESS = "🔥 Экспресс (4 матча)"


class ValueBetBot:
    """
    Главный класс бота.
    Реагирует на три кнопки: Футбол, Хоккей, Экспресс.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.current_mode: Optional[BotMode] = None
        
        # Инициализация анализаторов для каждого спорта
        self.football_analyzer = MatchAnalyzer(Sport.FOOTBALL)
        self.hockey_analyzer = MatchAnalyzer(Sport.HOCKEY)
        
        # Билдеры экспрессов
        self.football_express_builder = ExpressBuilder(self.football_analyzer)
        self.hockey_express_builder = ExpressBuilder(self.hockey_analyzer)
        
        # API клиенты
        self.football_api = OddsAPI("football", api_key)
        self.hockey_api = OddsAPI("hockey", api_key)
    
    async def start(self):
        """Запуск бота (эмуляция интерфейса)"""
        print("\n" + "="*50)
        print("🤖 БОТ ДЛЯ СТАВОК НА ФОРУ (Value Betting)")
        print("="*50)
        
        while True:
            self._show_menu()
            choice = input("\n👉 Выберите режим (1/2/3/0): ").strip()
            
            if choice == "1":
                await self._handle_football()
            elif choice == "2":
                await self._handle_hockey()
            elif choice == "3":
                await self._handle_express()
            elif choice == "0":
                print("\n👋 Выход из бота. Удачных ставок!")
                break
            else:
                print("\n❌ Неверный выбор. Попробуйте снова.")
    
    def _show_menu(self):
        """Отображение меню (три кнопки)"""
        print("\n" + "-"*30)
        print("📌 ВЫБЕРИТЕ РЕЖИМ:")
        print("1. ⚽ Футбол (одиночные матчи)")
        print("2. 🏒 Хоккей (одиночные матчи)")
        print("3. 🔥 Экспресс из 4 железных матчей")
        print("0. Выход")
        print("-"*30)
    
    async def _handle_football(self):
        """Обработка кнопки 'Футбол'"""
        print("\n⚽ ЗАГРУЖАЮ ФУТБОЛЬНЫЕ МАТЧИ...")
        print("Фильтр: Home >= 3.5, Away <= 2.2")
        
        try:
            matches = await self.football_api.fetch_matches()
            
            if not matches:
                print("\n❌ Нет матчей, проходящих фильтр по коэффициентам.")
                return
            
            print(f"\n✅ Найдено матчей: {len(matches)}")
            print("\n" + "="*60)
            print("📊 АНАЛИЗ МАТЧЕЙ (сортировка по надежности):")
            print("="*60)
            
            analyses = []
            for match in matches:
                analysis = self.football_analyzer.analyze_single_match(match)
                analyses.append(analysis)
            
            # Сортировка: HIGH -> MEDIUM -> LOW, внутри по total_score
            analyses.sort(key=lambda x: (
                0 if x.confidence == "HIGH" else 1 if x.confidence == "MEDIUM" else 2,
                -x.total_score
            ))
            
            for i, a in enumerate(analyses, 1):
                self._print_match_analysis(i, a, Sport.FOOTBALL)
            
        except Exception as e:
            logger.error(f"Ошибка в футбольном режиме: {e}")
            print(f"\n❌ Ошибка: {e}")
    
    async def _handle_hockey(self):
        """Обработка кнопки 'Хоккей'"""
        print("\n🏒 ЗАГРУЖАЮ ХОККЕЙНЫЕ МАТЧИ...")
        print("Фильтр: Home >= 2.8, Away <= 2.0")
        
        try:
            matches = await self.hockey_api.fetch_matches()
            
            if not matches:
                print("\n❌ Нет матчей, проходящих фильтр по коэффициентам.")
                return
            
            print(f"\n✅ Найдено матчей: {len(matches)}")
            print("\n" + "="*60)
            print("📊 АНАЛИЗ МАТЧЕЙ (сортировка по надежности):")
            print("="*60)
            
            analyses = []
            for match in matches:
                analysis = self.hockey_analyzer.analyze_single_match(match)
                analyses.append(analysis)
            
            analyses.sort(key=lambda x: (
                0 if x.confidence == "HIGH" else 1 if x.confidence == "MEDIUM" else 2,
                -x.total_score
            ))
            
            for i, a in enumerate(analyses, 1):
                self._print_match_analysis(i, a, Sport.HOCKEY)
                
        except Exception as e:
            logger.error(f"Ошибка в хоккейном режиме: {e}")
            print(f"\n❌ Ошибка: {e}")
    
    async def _handle_express(self):
        """Обработка кнопки 'Экспресс из 4 матчей'"""
        print("\n🔥 ФОРМИРУЮ ЭКСПРЕСС ИЗ 4 ЖЕЛЕЗНЫХ МАТЧЕЙ...")
        print("Анализирую футбол и хоккей одновременно...")
        
        try:
            # Собираем матчи из обоих видов спорта
            football_matches = await self.football_api.fetch_matches()
            hockey_matches = await self.hockey_api.fetch_matches()
            
            all_matches = football_matches + hockey_matches
            
            if len(all_matches) < 4:
                print(f"\n❌ Недостаточно матчей для экспресса. Найдено: {len(all_matches)}")
                return
            
            print(f"\n📊 Всего матчей в пуле: {len(all_matches)}")
            print("⏳ Анализирую и отбираю лучшие...")
            
            # Анализируем все матчи
            all_analyses = []
            for match in football_matches:
                all_analyses.append(self.football_analyzer.analyze_single_match(match))
            for match in hockey_matches:
                all_analyses.append(self.hockey_analyzer.analyze_single_match(match))
            
            # Фильтруем только HIGH и MEDIUM
            reliable = [a for a in all_analyses if a.confidence in ["HIGH", "MEDIUM"]]
            
            if len(reliable) < 4:
                print(f"\n❌ Недостаточно НАДЕЖНЫХ матчей. Найдено HIGH/MEDIUM: {len(reliable)}")
                return
            
            # Сортируем по качеству
            reliable.sort(key=lambda x: (
                0 if x.confidence == "HIGH" else 1,
                -x.total_score
            ))
            
            # Берем топ-4
            express_matches = reliable[:4]
            
            print("\n" + "="*70)
            print("🔥 ЭКСПРЕСС ИЗ 4 ЖЕЛЕЗНЫХ МАТЧЕЙ СФОРМИРОВАН!")
            print("="*70)
            
            total_odd = 1.0
            high_count = 0
            
            for i, match in enumerate(express_matches, 1):
                sport_icon = "⚽" if match.home_odd >= 3.5 else "🏒"
                
                # Эмуляция коэффициента на фору
                hdp_coef = self._estimate_handicap_odd(match)
                match.coefficient = hdp_coef
                total_odd *= hdp_coef
                
                if match.confidence == "HIGH":
                    high_count += 1
                
                print(f"\n{i}. {sport_icon} {match.home_team} vs {match.away_team}")
                print(f"   📈 Фора: +{match.recommended_handicap} | Кэф: {hdp_coef:.2f}")
                print(f"   💪 Уверенность: {match.confidence} | Score: {match.total_score:.1f}/9.0")
                print(f"   📝 {match.bet_reason}")
            
            # Общая уверенность
            if high_count >= 3:
                total_conf = "🔥 ВЫСОКАЯ (3+ HIGH матчей)"
            elif high_count >= 2:
                total_conf = "✅ СРЕДНЯЯ+ (2 HIGH матча)"
            else:
                total_conf = "⚠️ СРЕДНЯЯ"
            
            print("\n" + "-"*70)
            print(f"📊 ИТОГО ПО ЭКСПРЕССУ:")
            print(f"   Общий коэффициент: {total_odd:.2f}")
            print(f"   Уверенность: {total_conf}")
            print(f"   Ожидаемый ROI: ~{self._estimate_roi(express_matches):.1f}%")
            print("-"*70)
            
        except Exception as e:
            logger.error(f"Ошибка в экспресс-режиме: {e}")
            print(f"\n❌ Ошибка: {e}")
    
    def _print_match_analysis(self, index: int, analysis: MatchAnalysis, sport: Sport):
        """Форматированный вывод анализа одного матча"""
        conf_emoji = {"HIGH": "🔥", "MEDIUM": "✅", "LOW": "⚠️"}.get(analysis.confidence, "❓")
        
        print(f"\n{index}. {conf_emoji} {analysis.home_team} vs {analysis.away_team}")
        print(f"   Коэф: H={analysis.home_odd:.2f} / A={analysis.away_odd:.2f}")
        print(f"   📊 Баллы: Личка={analysis.h2h_score:.1f} | Форма={analysis.home_form_score:.1f} | Гости={analysis.away_form_score:.1f}")
        print(f"   💯 Total Score: {analysis.total_score:.1f}/9.0")
        print(f"   🎯 Рекомендуемая фора: +{analysis.recommended_handicap}")
        print(f"   💪 Уверенность: {analysis.confidence}")
        print(f"   📝 {analysis.bet_reason}")
    
    def _estimate_handicap_odd(self, analysis: MatchAnalysis) -> float:
        """
        Эмуляция получения коэффициента на фору.
        В реальности — запрос к API букмекера.
        """
        base = 1.85
        
        # Корректировка в зависимости от форы
        if analysis.recommended_handicap >= 2.5:
            return base - 0.15
        elif analysis.recommended_handicap >= 1.5:
            return base
        else:
            return base + 0.10
    
    def _estimate_roi(self, matches: list) -> float:
        """Оценка ROI на основе уверенности матчей"""
        avg_score = sum(m.total_score for m in matches) / len(matches)
        high_ratio = sum(1 for m in matches if m.confidence == "HIGH") / len(matches)
        
        return 15.0 + (avg_score * 2) + (high_ratio * 10)


# Точка входа
async def main():
    bot = ValueBetBot(api_key="YOUR_API_KEY_HERE")
    await bot.start()


if __name__ == "__main__":
    asyncio.run(main())
