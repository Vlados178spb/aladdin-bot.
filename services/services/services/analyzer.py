from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum

class BetType(Enum):
    SINGLE = "single"
    EXPRESS_4 = "express_4"

class Sport(Enum):
    FOOTBALL = "football"
    HOCKEY = "hockey"

@dataclass
class MatchAnalysis:
    """Результат глубокого анализа одного матча (Код 333)"""
    home_team: str
    away_team: str
    home_odd: float
    away_odd: float
    
    # Баллы (0.0 - 3.0 за блок)
    h2h_score: float = 0.0      
    home_form_score: float = 0.0 
    away_form_score: float = 0.0 
    total_score: float = 0.0     
    
    # Расчетные значения для фор до +5
    fair_handicap: float = 0.0   
    safe_handicap: float = 0.0   
    recommended_bet: str = ""    # Финальная строка (напр. "Ф1(+2.5)")
    
    confidence: str = "LOW"      
    bet_reason: str = ""
    coefficient: float = 0.0     

@dataclass
class ExpressAnalysis:
    """Результат анализа экспресса из 4 матчей"""
    matches: List[MatchAnalysis] = field(default_factory=list)
    total_confidence: str = "LOW"
    combined_odd: float = 1.0
    is_valid: bool = False       
    reject_reason: str = ""

class MatchAnalyzer:
    """
    Анализатор 'Аладдин'. Рассчитывает надежные форы на хозяев (Ф1).
    """
    
    WEIGHTS = {
        Sport.FOOTBALL: {
            "h2h": 0.35, "home_form": 0.35, "away_form": 0.30, "median_loss": 0.5
        },
        Sport.HOCKEY: {
            "h2h": 0.25, "home_form": 0.45, "away_form": 0.30, "median_loss": 0.75
        }
    }
    
    def __init__(self, sport: Sport):
        self.sport = sport
        self.weights = self.WEIGHTS[sport]
    
    def analyze_single_match(self, match_data: Dict) -> MatchAnalysis:
        """Анализирует матч, используя данные из Odds API и OpenLigaDB"""
        analysis = MatchAnalysis(
            home_team=match_data.get("home", "Home"),
            away_team=match_data.get("away", "Away"),
            home_odd=float(match_data.get("home_odd", 1.85)),
            away_odd=float(match_data.get("away_odd", 1.85))
        )
        
        # 1. Расчет баллов на основе истории (0-3 балла за блок)
        analysis.h2h_score = self._calc_score(match_data.get("h2h", []))
        analysis.home_form_score = self._calc_score(match_data.get("home_last_5", []))
        analysis.away_form_score = self._calc_score(match_data.get("away_last_5", []))
        
        # 2. Суммарный рейтинг (0-9 баллов)
        analysis.total_score = (
            analysis.h2h_score * self.weights["h2h"] +
            analysis.home_form_score * self.weights["home_form"] +
            analysis.away_form_score * self.weights["away_form"]
        ) * 3
        
        # 3. Логика подбора форы до +5
        # Чем ниже total_score (слабее хозяева), тем больше плюсовая фора
        if analysis.total_score > 7.0:
            hdp = 0.0
            analysis.confidence = "HIGH"
        elif analysis.total_score > 5.0:
            hdp = 1.5
            analysis.confidence = "MEDIUM"
        elif analysis.total_score > 3.0:
            hdp = 3.0
            analysis.confidence = "HIGH"
        else:
            hdp = 5.0 # Максимальная страховка
            analysis.confidence = "HIGH"

        analysis.recommended_bet = f"Ф1(+{hdp})" if hdp > 0 else "Ф1(0)"
        analysis.coefficient = analysis.home_odd # Здесь можно добавить логику поиска кф под фору
        
        return analysis

    def _calc_score(self, data_list) -> float:
        """Вспомогательный расчет баллов (заглушка для реальной статистики)"""
        if not data_list: return 1.5
        return min(3.0, len(data_list) * 0.5)

    def create_express(self, analyzed_matches: List[MatchAnalysis]) -> ExpressAnalysis:
        """Собирает ТОП-4 матча в экспресс 333"""
        # Сортируем по уверенности и баллу
        sorted_matches = sorted(analyzed_matches, key=lambda x: x.total_score, reverse=True)
        top_4 = sorted_matches[:4]
        
        express = ExpressAnalysis(matches=top_4)
        
        if len(top_4) == 4:
            for m in top_4:
                express.combined_odd *= m.coefficient
            express.is_valid = True
            express.total_confidence = "HIGH" if all(m.confidence == "HIGH" for m in top_4) else "MEDIUM"
        else:
            express.is_valid = False
            express.reject_reason = "Недостаточно матчей для экспресса 333"
            
        return express

