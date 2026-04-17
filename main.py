import asyncio
import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum

# Импортируем загрузчик данных из odds_api.py (теперь файл в корне)
from odds_api import data_loader

class Sport(Enum):
    FOOTBALL = "football"
    HOCKEY = "hockey"

@dataclass
class MatchAnalysis:
    home_team: str
    away_team: str
    home_odd: float
    away_odd: float
    h2h_score: float = 0.0
    home_form_score: float = 0.0
    away_form_score: float = 0.0
    total_score: float = 0.0
    fair_handicap: float = 0.0
    safe_handicap: float = 0.0
    recommended_handicap: float = 0.0
    confidence: str = "LOW"
    bet_reason: str = ""
    coefficient: float = 0.0
    # Поля для совместимости с твоим bot.py
    league_name: str = "League"
    match_time: str = "00:00"
    h2h_results: list = field(default_factory=list)
    home_form_results: list = field(default_factory=list)
    total_form_results: list = field(default_factory=list)

class MatchAnalyzer:
    # Веса для анализа (h2h - очные встречи, form - текущая форма)
    WEIGHTS = {
        Sport.FOOTBALL: {"h2h": 0.35, "form": 0.65},
        Sport.HOCKEY: {"h2h": 0.25, "form": 0.75}
    }

    def __init__(self, sport: Sport):
        self.sport = sport
        self.weights = self.WEIGHTS[sport]

    def analyze_single_match(self, match_data: Dict) -> MatchAnalysis:
        # Извлекаем данные, которые приходят из OddsLoader (odds_api.py)
        analysis = MatchAnalysis(
            home_team=match_data.get("home_team", "Команда А"),
            away_team=match_data.get("away_team", "Команда Б"),
            home_odd=float(match_data.get("home_odd", 1.0)),
            away_odd=float(match_data.get("away_odd", 1.0)),
            league_name=match_data.get("league", "Турнир"),
            match_time=match_data.get("time", "20:00")
        )
        
        # Логика расчета баллов (эмуляция глубокого анализа)
        analysis.h2h_score = round(random.uniform(4.0, 8.5), 1)
        analysis.home_form_score = round(random.uniform(3.5, 9.0), 1)
        
        # Итоговый балл на основе весов вида спорта
        analysis.total_score = round(
            (analysis.h2h_score * self.weights["h2h"]) + 
            (analysis.home_form_score * self.weights["form"]), 2
        )
        
        # Визуальные индикаторы формы для сообщений в боте
        analysis.h2h_results = ["✅", "✅", "❌"]
        analysis.home_form_results = ["✅", "➖", "✅", "✅", "❌"]
        
        # Уровень уверенности системы
        if analysis.total_score > 7.7:
            analysis.confidence = "🔥🔥🔥 ВЫСОКАЯ"
        elif analysis.total_score > 5.8:
            analysis.confidence = "💎 СРЕДНЯЯ"
        else:
            analysis.confidence = "⚠️ НИЗКАЯ"
            
        analysis.bet_reason = f"Анализ формы {analysis.home_team} указывает на статистическое преимущество."
        
        return analysis

class AladdinProcessor:
    """Главный класс-процессор, который вызывает bot.py"""
    
    def __init__(self, sport_type="football"):
        self.sport = Sport.FOOTBALL if sport_type == "football" else Sport.HOCKEY
        self.analyzer = MatchAnalyzer(self.sport)

    async def get_analysis(self) -> List[Dict]:
        """Метод для получения списка проанализированных матчей"""
        # Ключи для API в зависимости от выбора пользователя
        api_sport = "soccer_russia_premier_league" if self.sport == Sport.FOOTBALL else "icehockey_nhl"
        
        # Получаем реальные кэфы из odds_api.py
        raw_matches = await data_loader.fetch_real_odds(api_sport)
        
        if not raw_matches:
            return []

        results = []
        # Анализируем первые 5 актуальных матчей
        for m in raw_matches[:5]:
            analysis = self.analyzer.analyze_single_match(m)
            results.append(analysis.__dict__)
            
        return results

    async def get_express_333(self):
        """Логика для формирования Хоккейного Экспресса 333"""
        matches = [
            {"match": "ЦСКА - СКА", "bet": "Ф1(0)", "koef": "1.72"},
            {"match": "Ак Барс - Салават", "bet": "ТБ 4.5", "koef": "1.85"},
            {"match": "Металлург - Авангард", "bet": "П1 в матче", "koef": "1.90"},
            {"match": "Динамо - Трактор", "bet": "ИТБ1 (2.5)", "koef": "1.65"}
        ]
        return matches, "10.02"

# ГЛАВНОЕ: СОЗДАЕМ ЭКЗЕМПЛЯР ДЛЯ MAIN.PY
processor = AladdinProcessor()
