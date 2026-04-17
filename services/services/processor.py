import asyncio
import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum

# --- ТВОИ КЛАССЫ И ЛОГИКА ---
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
    # Поля для совместимости с bot.py
    league_name: str = "League"
    match_time: str = "00:00"
    h2h_results: list = field(default_factory=list)
    home_form_results: list = field(default_factory=list)
    total_form_results: list = field(default_factory=list)

class MatchAnalyzer:
    WEIGHTS = {
        Sport.FOOTBALL: {"h2h": 0.35, "home_form": 0.25, "away_form": 0.20, "total": 0.20},
        Sport.HOCKEY: {"h2h": 0.25, "home_form": 0.45, "away_form": 0.15, "total": 0.15}
    }

    def __init__(self, sport: Sport):
        self.sport = sport
        self.weights = self.WEIGHTS[sport]

    def analyze_single_match(self, match_data: Dict) -> MatchAnalysis:
        # Здесь твоя логика расчета
        analysis = MatchAnalysis(
            home_team=match_data.get("home_team", "Team A"),
            away_team=match_data.get("away_team", "Team B"),
            home_odd=match_data.get("home_odd", 1.0),
            away_odd=match_data.get("away_odd", 1.0),
            league_name=match_data.get("league", "🇷🇺 РПЛ"),
            match_time=match_data.get("time", "20:00")
        )
        
        # Генерация случайных чисел для теста (теперь random импортирован!)
        analysis.total_score = round(random.uniform(3.0, 9.5), 2)
        analysis.safe_handicap = 1.5
        analysis.h2h_results = ["win", "win", "draw"]
        analysis.confidence = "MEDIUM"
        analysis.bet_reason = "Статистический перевес на основе весов модели."
        
        return analysis

# --- КЛАСС-ОБОЛОЧКА ДЛЯ БОТА ---
class AladdinProcessor:
    def __init__(self, sport_type="football"):
        self.sport = Sport.FOOTBALL if sport_type == "football" else Sport.HOCKEY
        self.analyzer = MatchAnalyzer(self.sport)

    async def get_analysis(self) -> List[Dict]:
        # Временный тестовый матч
        test_match = {
            "home_team": "Спартак", "away_team": "Зенит",
            "home_odd": 2.5, "away_odd": 2.1,
            "league": "РПЛ", "time": "19:30"
        }
        
        analysis = self.analyzer.analyze_single_match(test_match)
        # Превращаем объект в словарь, чтобы bot.py его «съел»
        return [analysis.__dict__]

    async def get_express_333(self):
        # Логика подбора 4-х матчей
        matches = [
            {"match": "Матч 1", "bet": "+1.5", "koef": "1.45"},
            {"match": "Матч 2", "bet": "+1.0", "koef": "1.30"},
            {"match": "Матч 3", "bet": "+2.5", "koef": "1.80"},
            {"match": "Матч 4", "bet": "+1.5", "koef": "1.55"}
        ]
        return matches, "10.45"

