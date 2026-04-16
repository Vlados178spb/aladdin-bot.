import aiohttp
import asyncio
from datetime import datetime
from typing import List, Dict, Optional

class OddsAPI:
    """
    Универсальный загрузчик коэффициентов и статистики.
    Поддерживает: hockey, football.
    """
    
    # Конфигурация по видам спорта
    SPORT_CONFIG = {
        "football": {
            "min_home_odd": 3.5,
            "max_away_odd": 2.2,
            "handicap_step": 0.5,      # шаг форы в футболе
            "max_handicap": 5.5,
            "history_years": 3
        },
        "hockey": {
            "min_home_odd": 2.8,       # в хоккее андердог чаще побеждает
            "max_away_odd": 2.0,
            "handicap_step": 1.5,      # шаг форы в хоккее (1.5 шайбы)
            "max_handicap": 4.5,
            "history_years": 2         # в хоккее ротация составов выше
        }
    }
    
    def __init__(self, sport: str, api_key: Optional[str] = None):
        self.sport = sport.lower()
        self.config = self.SPORT_CONFIG.get(self.sport)
        if not self.config:
            raise ValueError(f"Спорт {sport} не поддерживается")
        self.api_key = api_key
        self.base_url = "https://api.the-odds-api.com/v4"  # пример
    
    async def fetch_matches(self, date: str = None) -> List[Dict]:
        """
        Загружает все матчи на заданную дату с коэффициентами.
        Возвращает только те, что проходят фильтр по коэффициентам.
        """
        # Эмуляция запроса к API
        # В реальности: запрос к TheOddsAPI / Pinnacle / Bet365
        
        matches = await self._fetch_raw_odds(date)
        filtered = []
        
        for match in matches:
            home_odd = match.get("home_odd", 0)
            away_odd = match.get("away_odd", 0)
            
            # Фильтр по коэффициентам (главное условие)
            if home_odd >= self.config["min_home_odd"] and away_odd <= self.config["max_away_odd"]:
                # Догружаем расширенную статистику
                stats = await self._fetch_match_stats(match["home_team"], match["away_team"])
                match.update(stats)
                filtered.append(match)
        
        return filtered
    
    async def _fetch_raw_odds(self, date: str) -> List[Dict]:
        """Заглушка для реального API-запроса"""
        # Здесь будет реальный HTTP-запрос
        await asyncio.sleep(0.1)
        return []  # Заглушка
    
    async def _fetch_match_stats(self, home_team: str, away_team: str) -> Dict:
        """
        Загружает статистику:
        - История личных встреч дома (3 года)
        - Последние 5 домашних игр
        - Последние 5 выездных игр гостей
        - Медианная разница поражений
        """
        # Заглушка структуры данных
        return {
            "h2h_home": [],      # личные встречи дома
            "home_last_5": [],   # последние 5 дома (любые соперники)
            "away_last_5": [],   # последние 5 в гостях (для гостей)
            "median_loss_diff": 1.0,  # медианная разница при поражениях дома
            "home_xg": 1.2,      # средний xG дома
            "away_xg_conceded": 1.5  # средний xG пропущенный гостями в гостях
        }
    
    def get_available_handicaps(self, match: Dict) -> List[float]:
        """Возвращает доступные форы для матча с шагом из конфига"""
        step = self.config["handicap_step"]
        max_hdp = self.config["max_handicap"]
        
        handicaps = []
        current = 0.5
        while current <= max_hdp:
            handicaps.append(round(current, 2))
            current += step
        
        return handicaps
