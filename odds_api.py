import requests
import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Optional

# Настройка логов, чтобы видеть ошибки в Railway
logger = logging.getLogger(__name__)

# --- ТВОИ КЛЮЧИ (УЖЕ ВПИСАНЫ) ---
ODDS_API_KEY = "2be3c040e725dabfe695ae282049a8b0"
ODDS_BASE_URL = "https://api.the-odds-api.com/v4/sports"

class OddsLoader:
    """
    Загрузчик реальных данных: The Odds API
    """
    
    def __init__(self):
        self.api_key = ODDS_API_KEY

    async def fetch_real_odds(self, sport: str) -> List[Dict]:
        """
        Получает реальные коэффициенты.
        sport: 'soccer_russia_premier_league' или 'icehockey_nhl'
        """
        params = {
            "api_key": self.api_key,
            "regions": "eu",
            "markets": "h2h",
            "oddsFormat": "decimal"
        }
        
        # Для футбола (РПЛ) используем soccer_russia_premier_league
        # Для хоккея (НХЛ) используем icehockey_nhl
        url = f"{ODDS_BASE_URL}/{sport}/odds"
        
        try:
            # Используем requests.get
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                return self._parse_odds(data)
            else:
                logger.error(f"Ошибка Odds API: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            logger.error(f"Критическая ошибка при запросе кэфов: {e}")
            return []

    def _parse_odds(self, data: List[Dict]) -> List[Dict]:
        """Парсинг ответа API в чистый формат для процессора"""
        parsed = []
        for item in data:
            match_info = {
                "home_team": item.get("home_team"),
                "away_team": item.get("away_team"),
                "league": item.get("sport_title"),
                "time": item.get("commence_time"),
                "home_odd": 1.0, # Значение по умолчанию
                "away_odd": 1.0
            }
            
            # Извлекаем кэфы из первого доступного букмекера
            if item.get("bookmakers"):
                markets = item["bookmakers"][0].get("markets", [])
                for m in markets:
                    if m["key"] == "h2h":
                        for outcome in m["outcomes"]:
                            if outcome["name"] == item["home_team"]:
                                match_info["home_odd"] = outcome["price"]
                            else:
                                match_info["away_odd"] = outcome["price"]
            parsed.append(match_info)
        return parsed

# Глобальный объект для импорта в processor.py
data_loader = OddsLoader()

