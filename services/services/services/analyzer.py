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
    """Результат анализа одного матча"""
    home_team: str
    away_team: str
    home_odd: float
    away_odd: float
    
    # Баллы по блокам
    h2h_score: float = 0.0      # личные встречи дома (max 3.0)
    home_form_score: float = 0.0 # форма дома (max 3.0)
    away_form_score: float = 0.0 # уязвимость гостей (max 3.0)
    total_score: float = 0.0     # сумма баллов
    
    # Расчетные форы
    fair_handicap: float = 0.0   # справедливая фора по модели
    safe_handicap: float = 0.0   # безопасная фора для ставки
    recommended_handicap: float = 0.0
    
    # Итоговая рекомендация
    confidence: str = "LOW"      # HIGH / MEDIUM / LOW
    bet_reason: str = ""
    coefficient: float = 0.0     # кэф на рекомендуемую фору


@dataclass
class ExpressAnalysis:
    """Результат анализа экспресса из 4 матчей"""
    matches: List[MatchAnalysis] = field(default_factory=list)
    total_confidence: str = "LOW"
    combined_odd: float = 1.0
    recommended_handicaps: List[float] = field(default_factory=list)
    is_valid: bool = False       # прошел ли экспресс фильтр качества
    reject_reason: str = ""


class MatchAnalyzer:
    """
    Анализатор матчей.
    Содержит логику расчета баллов и определения безопасной форы.
    """
    
    # Весовые коэффициенты (настраиваются под спорт)
    WEIGHTS = {
        Sport.FOOTBALL: {
            "h2h": 0.35,          # история личек важнее в футболе
            "home_form": 0.35,
            "away_form": 0.30,
            "median_loss": 0.5    # бонус к форе за "потолок поражений"
        },
        Sport.HOCKEY: {
            "h2h": 0.25,          # в хоккее история менее показательна
            "home_form": 0.45,    # текущая форма решает
            "away_form": 0.30,
            "median_loss": 0.75   # в хоккее разрывы в счете выше
        }
    }
    
    def init(self, sport: Sport):
        self.sport = sport
        self.weights = self.WEIGHTS[sport]
    
    def analyze_single_match(self, match_data: Dict) -> MatchAnalysis:
        """
        Полный анализ одного матча.
        Возвращает MatchAnalysis с рекомендацией.
        """
        analysis = MatchAnalysis(
            home_team=match_data["home_team"],
            away_team=match_data["away_team"],
            home_odd=match_data["home_odd"],
            away_odd=match_data["away_odd"]
        )
        
        # 1. Расчет баллов по блокам
        analysis.h2h_score = self._calc_h2h_score(match_data.get("h2h_home", []))
        analysis.home_form_score = self._calc_home_form_score(match_data.get("home_last_5", []))
        analysis.away_form_score = self._calc_away_vulnerability(match_data.get("away_last_5", []))
        
        # 2. Взвешенная сумма
        analysis.total_score = (
            analysis.h2h_score * self.weights["h2h"] +
            analysis.home_form_score * self.weights["home_form"] +
            analysis.away_form_score * self.weights["away_form"]
        ) * 3  # нормировка к 9.0
        
        # 3. Расчет справедливой форы
        base_hdp = self._calc_base_handicap(analysis.home_odd, analysis.away_odd)
        analysis.fair_handicap = base_hdp + (analysis.total_score / 2.0)
        
        # 4. Определение безопасной форы
        median_diff = match_data.get("median_loss_diff", 1.5)
        analysis.safe_handicap = self._determine_safe_handicap(
            analysis.fair_handicap, 
            median_diff
        )
        
        # 5. Формирование рекомендации
        analysis.recommended_handicap = self._round_handicap(analysis.safe_handicap)

analysis.confidence = self._calc_confidence(analysis)
        analysis.bet_reason = self._generate_reason(analysis)
        
        return analysis
    
    def _calc_h2h_score(self, h2h_matches: List[Dict]) -> float:
        """
        Расчет баллов за историю личных встреч дома.
        Шкала:
        - Последний год (2026): П1=3.0, Х=1.0, П2=0
        - 2 года назад (2025): П1=2.0, Х=0.5, П2=0
        - 3 года назад (2024): П1=1.0, Х=0.25, П2=0
        """
        if not h2h_matches:
            return 1.5  # нейтральное значение при отсутствии данных
        
        score = 0.0
        weights = [3.0, 2.0, 1.0]  # веса по годам (от свежих к старым)
        draw_weights = [1.0, 0.5, 0.25]
        
        for i, match in enumerate(h2h_matches[:3]):
            if i >= len(weights):
                break
            
            result = match.get("result", "")  # "W", "D", "L"
            if result == "W":
                score += weights[i]
            elif result == "D":
                score += draw_weights[i]
            # L = 0
        
        return min(score, 3.0)  # максимум 3.0
    
    def _calc_home_form_score(self, last_5_home: List[Dict]) -> float:
        """
        Расчет формы дома за последние 5 игр.
        Модифицированная шкала для андердога:
        - Победа над фаворитом: 3 очка
        - Победа над равным: 2 очка
        - Ничья с фаворитом: 2 очка
        - Ничья с равным: 1 очко
        - Поражение в 1 гол: 1 очко
        - Поражение в 2+ гола: 0 очков
        """
        if not last_5_home:
            return 1.5
        
        total = 0.0
        for match in last_5_home[:5]:
            result = match.get("result", "")
            opponent_strength = match.get("opponent_odd", 2.0)
            goal_diff = match.get("goal_diff", 0)
            
            if result == "W":
                total += 3.0 if opponent_strength < 2.5 else 2.0
            elif result == "D":
                total += 2.0 if opponent_strength < 2.5 else 1.0
            elif result == "L":
                total += 1.0 if abs(goal_diff) <= 1 else 0.0
        
        return (total / 15.0) * 3.0  # нормировка к 3.0
    
    def _calc_away_vulnerability(self, away_last_5: List[Dict]) -> float:
        """
        Расчет уязвимости гостей на выезде.
        Чем хуже играют гости, тем ВЫШЕ балл хозяев.
        """
        if not away_last_5:
            return 1.5
        
        score = 0.0
        for match in away_last_5[:5]:
            result = match.get("result", "")
            goal_diff = match.get("goal_diff", 0)
            
            if result == "W" and goal_diff >= 2:
                score -= 1.5  # гости громят всех
            elif result == "W":
                score -= 0.5  # гости побеждают
            elif result == "D":
                score += 1.0  # гости теряют очки
            elif result == "L":
                score += 2.0  # гости проигрывают на выезде
        
        # Нормировка к 3.0 (сдвиг шкалы)
        normalized = (score + 7.5) / 5.0
        return max(0.0, min(3.0, normalized))
    
    def _calc_base_handicap(self, home_odd: float, away_odd: float) -> float:
        """
        Вычисляет базовую фору из коэффициентов.
        Фора = ожидаемая разница в счете в пользу гостей (положительная).
        """
        prob_home = 1 / home_odd
        prob_away = 1 / away_odd
        
        # Убираем маржу
        margin = (prob_home + prob_away) - 1.0
        prob_home_adj = prob_home - margin / 2
        prob_away_adj = prob_away - margin / 2
        
        # Грубая оценка разницы в голах
        # Для футбола: разница 20% вероятности ≈ 0.5 гола
        # Для хоккея: разница 15% вероятности ≈ 0.5 гола
        multiplier = 0.5 / 0.20 if self.sport == Sport.FOOTBALL else 0.5 / 0.15

diff = (prob_away_adj - prob_home_adj) * multiplier
        
        return diff
    
    def _determine_safe_handicap(self, fair_hdp: float, median_loss: float) -> float:
        """
        Определяет безопасную фору с учетом "потолка поражений".
        """
        # Добавляем запас прочности
        safety_margin = median_loss * self.weights["median_loss"]
        
        # Безопасная фора = справедливая + запас
        safe = fair_hdp + safety_margin
        
        # Ограничиваем максимальной форой
        max_hdp = 5.5 if self.sport == Sport.FOOTBALL else 4.5
        return min(safe, max_hdp)
    
    def _round_handicap(self, hdp: float) -> float:
        """Округление форы до шага букмекера"""
        if self.sport == Sport.FOOTBALL:
            step = 0.5
        else:
            step = 1.5
        
        return round(hdp / step) * step
    
    def _calc_confidence(self, analysis: MatchAnalysis) -> str:
        """Определение уверенности в ставке"""
        gap = analysis.fair_handicap - analysis.recommended_handicap
        
        if analysis.total_score >= 6.5 and gap >= 1.0:
            return "HIGH"
        elif analysis.total_score >= 5.0 and gap >= 0.5:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _generate_reason(self, analysis: MatchAnalysis) -> str:
        """Генерация текстового обоснования ставки"""
        reasons = []
        
        if analysis.h2h_score >= 2.0:
            reasons.append(f"✅ Успешная история личек дома ({analysis.h2h_score:.1f}/3.0)")
        if analysis.home_form_score >= 2.0:
            reasons.append(f"✅ Сильная домашняя форма ({analysis.home_form_score:.1f}/3.0)")
        if analysis.away_form_score >= 2.0:
            reasons.append(f"✅ Гости уязвимы на выезде ({analysis.away_form_score:.1f}/3.0)")
        
        if not reasons:
            reasons.append("⚠️ Нейтральные показатели")
        
        return " | ".join(reasons)


class ExpressBuilder:
    """
    Строитель экспрессов из 4 "железных" матчей.
    """
    
    def init(self, analyzer: MatchAnalyzer):
        self.analyzer = analyzer
        self.min_express_confidence = "MEDIUM"
    
    def build_express(self, matches_data: List[Dict]) -> Optional[ExpressAnalysis]:
        """
        Строит экспресс из 4 матчей с максимальной надежностью.
        Возвращает None если недостаточно качественных матчей.
        """
        # Анализируем все матчи
        analyses = [self.analyzer.analyze_single_match(m) for m in matches_data]
        
        # Фильтруем только HIGH и MEDIUM уверенность
        reliable = [a for a in analyses if a.confidence in ["HIGH", "MEDIUM"]]
        
        # Сортируем по уверенности и total_score
        reliable.sort(key=lambda x: (x.confidence == "HIGH", x.total_score), reverse=True)
        
        # Нужно минимум 4 матча для экспресса
        if len(reliable) < 4:
            return ExpressAnalysis(
                matches=reliable,
                is_valid=False,
                reject_reason=f"Недостаточно надежных матчей: {len(reliable)}/4"
            )
        
        # Берем топ-4
        top4 = reliable[:4]
        
        # Проверяем, что все имеют confidence не ниже MEDIUM
        if any(m.confidence == "LOW" for m in top4):
            return ExpressAnalysis(
                matches=top4,
                is_valid=False,
                reject_reason="В топ-4 попал матч с LOW уверенностью"
            )
        
        # Формируем экспресс
        express = ExpressAnalysis(
            matches=top4,
            is_valid=True,
            recommended_handicaps=[m.recommended_handicap for m in top4]
        )
        
        # Определяем общую уверенность
        high_count = sum(1 for m in top4 if m.confidence == "HIGH")

if high_count >= 3:
            express.total_confidence = "HIGH"
        elif high_count >= 2:
            express.total_confidence = "MEDIUM"
        else:
            express.total_confidence = "MEDIUM"
        
        # Коэффициенты будут подставлены из букмекерской линии
        # Здесь заглушка
        express.combined_odd = 1.0
        for m in top4:
            express.combined_odd *= (m.coefficient if m.coefficient > 0 else 1.9)
        
        return express
