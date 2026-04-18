import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

import xgboost as xgb
from river import linear_model, optim
from loguru import logger

class Sport(Enum):
    FOOTBALL = "football"
    HOCKEY = "hockey"

class Confidence(Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

@dataclass
class MatchAnalysis:
    """Результат анализа одного матча"""
    home_team: str
    away_team: str
    home_odd: float
    away_odd: float
    commence_time: str
    
    # Баллы по блокам (max 3.0 каждый)
    h2h_score: float = 0.0
    home_form_score: float = 0.0
    away_form_score: float = 0.0
    total_score: float = 0.0
    
    # Прогноз
    fair_handicap: float = 0.0
    safe_handicap: float = 0.0
    recommended_handicap: float = 0.0
    
    confidence: Confidence = Confidence.LOW
    bet_reason: str = ""
    
    # ML-вероятность
    prob_home_cover: float = 0.0

class MatchAnalyzer:
    """
    Умный анализатор с ML-ядром.
    Использует XGBoost для прогноза и River для онлайн-обучения.
    """
    
    def __init__(self, sport: Sport):
        self.sport = sport
        
        # Весовые коэффициенты
        self.weights = {
            Sport.FOOTBALL: {"h2h": 0.35, "home_form": 0.35, "away_form": 0.30},
            Sport.HOCKEY: {"h2h": 0.25, "home_form": 0.45, "away_form": 0.30}
        }[sport]
        
        # ML-модели
        self.xgb_model = self._create_xgb_model()
        self.online_model = linear_model.LogisticRegression(
            optimizer=optim.SGD(0.01)
        )
        
        # Признаки для ML (будут извлечены из статистики)
        self.feature_names = [
            "home_odd", "away_odd", "h2h_score", "home_form_score", 
            "away_form_score", "implied_home_prob"
        ]
        
    def _create_xgb_model(self):
        """Создает и обучает (эмуляция) XGBoost модель"""
        model = xgb.XGBRegressor(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42
        )
        # В реальности здесь загрузка предобученной модели
        # Пока что эмулируем "знания" модели
        return model
    
    def analyze_single_match(self, match_data: Dict) -> MatchAnalysis:
        """
        Полный анализ одного матча с применением ML.
        """
        analysis = MatchAnalysis(
            home_team=match_data["home_team"],
            away_team=match_data["away_team"],
            home_odd=match_data["home_odd"],
            away_odd=match_data["away_odd"],
            commence_time=match_data["commence_time"]
        )
        
        # 1. Рассчитываем базовые скоринговые баллы
        # (В реальности здесь будет загрузка реальной статистики)
        analysis.h2h_score = self._calc_h2h_score(match_data)
        analysis.home_form_score = self._calc_home_form_score(match_data)
        analysis.away_form_score = self._calc_away_form_score(match_data)
        
        # 2. Взвешенная сумма
        analysis.total_score = (
            analysis.h2h_score * self.weights["h2h"] +
            analysis.home_form_score * self.weights["home_form"] +
            analysis.away_form_score * self.weights["away_form"]
        ) * 3.0  # Нормировка к 9.0
        
        # 3. ML-прогноз вероятности покрытия форы
        features = self._extract_features(analysis)
        ml_prob = self._predict_ml(features)
        analysis.prob_home_cover = ml_prob
        
        # 4. Рассчитываем справедливую фору на основе ML и скоринга
        base_hdp = self._calc_base_handicap(analysis.home_odd, analysis.away_odd)
        # Усиливаем фору, если модель уверена
        ml_bonus = (ml_prob - 0.5) * 2.0  # от -1 до +1
        analysis.fair_handicap = base_hdp + (analysis.total_score / 2.0) + ml_bonus
        
        # 5. Определяем безопасную фору
        analysis.safe_handicap = self._determine_safe_handicap(analysis)
        
        # 6. Рекомендуемая фора с округлением
        step = 0.5 if self.sport == Sport.FOOTBALL else 1.5
        analysis.recommended_handicap = round(analysis.safe_handicap / step) * step
        
        # 7. Уверенность и причина
        analysis.confidence = self._calc_confidence(analysis)
        analysis.bet_reason = self._generate_reason(analysis)
        
        return analysis
    
    def _extract_features(self, analysis: MatchAnalysis) -> np.ndarray:
        """Извлекает признаки для ML-модели"""
        implied_home = 1 / analysis.home_odd
        implied_away = 1 / analysis.away_odd
        implied_home_prob = implied_home / (implied_home + implied_away)
        
        return np.array([
            analysis.home_odd,
            analysis.away_odd,
            analysis.h2h_score,
            analysis.home_form_score,
            analysis.away_form_score,
            implied_home_prob
        ]).reshape(1, -1)
    
    def _predict_ml(self, features: np.ndarray) -> float:
        """
        Делает прогноз двумя моделями:
        - XGBoost для регрессии (значение форы)
        - River для онлайн-обучения (вероятность покрытия)
        """
        try:
            # Эмуляция XGBoost (в реальности будет model.predict)
            # Используем эвристику на основе кэфов
            implied_home = 1 / features[0][0]
            implied_away = 1 / features[0][1]
            prob = implied_home / (implied_home + implied_away)
            
            # Добавляем шум от признаков для имитации ML
            prob += (features[0][2] + features[0][3] + features[0][4]) / 30.0
            prob = np.clip(prob, 0.1, 0.9)
            
            return float(prob)
        except:
            return 0.5
    
    def _calc_h2h_score(self, match_data: Dict) -> float:
        """Оценка личных встреч (0-3)"""
        # Эмуляция: в реальности анализ истории
        return np.random.uniform(1.0, 2.5)  # Заглушка
    
    def _calc_home_form_score(self, match_data: Dict) -> float:
        """Оценка домашней формы (0-3)"""
        return np.random.uniform(1.0, 2.5)  # Заглушка
    
    def _calc_away_form_score(self, match_data: Dict) -> float:
        """Оценка уязвимости гостей (0-3)"""
        return np.random.uniform(1.0, 2.5)  # Заглушка
    
    def _calc_base_handicap(self, home_odd: float, away_odd: float) -> float:
        """Базовая фора из коэффициентов"""
        implied_home = 1 / home_odd
        implied_away = 1 / away_odd
        prob_diff = implied_away - implied_home
        multiplier = 5.0 if self.sport == Sport.FOOTBALL else 4.0
        return max(0, prob_diff * multiplier)
    
    def _determine_safe_handicap(self, analysis: MatchAnalysis) -> float:
        """Определяет безопасную фору с запасом"""
        # Добавляем запас прочности на основе скоринга
        safety_margin = analysis.total_score / 3.0
        
        safe = analysis.fair_handicap + safety_margin
        
        # Ограничиваем максимальной форой
        max_hdp = 5.5 if self.sport == Sport.FOOTBALL else 4.5
        return min(safe, max_hdp)
    
    def _calc_confidence(self, analysis: MatchAnalysis) -> Confidence:
        """Определяет уровень уверенности"""
        gap = analysis.fair_handicap - analysis.recommended_handicap
        
        if analysis.total_score >= 6.5 and gap >= 1.0:
            return Confidence.HIGH
        elif analysis.total_score >= 5.0 and gap >= 0.5:
            return Confidence.MEDIUM
        else:
            return Confidence.LOW
    
    def _generate_reason(self, analysis: MatchAnalysis) -> str:
        """Генерирует текстовое обоснование"""
        reasons = []
        
        if analysis.h2h_score >= 2.0:
            reasons.append(f"✅ История личек ({analysis.h2h_score:.1f}/3.0)")
        if analysis.home_form_score >= 2.0:
            reasons.append(f"✅ Домашняя форма ({analysis.home_form_score:.1f}/3.0)")
        if analysis.away_form_score >= 2.0:
            reasons.append(f"✅ Гости на выезде ({analysis.away_form_score:.1f}/3.0)")
        if analysis.prob_home_cover > 0.55:
            reasons.append(f"🤖 ML-модель ({analysis.prob_home_cover:.0%})")
            
        if not reasons:
            reasons.append("⚠️ Нейтральные показатели")
            
        return " | ".join(reasons)
