import asyncio
import aiohttp
from typing import List, Dict, Optional, Any
from loguru import logger
from config import Config

class OddsAPI:
    """
    Универсальный загрузчик коэффициентов и статистики.
    Работает напрямую с The Odds API v4.
    """
    
    BASE_URL = "https://api.the-odds-api.com/v4"
    
    def __init__(self, sport: str):
        self.sport = sport.lower()
        self.api_key = Config.ODDS_API_KEY
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Конфигурация по виду спорта
        self.sport_key = self._get_sport_key()
        self.config = {
            "football": {
                "min_home_odd": Config.MIN_HOME_ODD,
                "max_away_odd": Config.MAX_AWAY_ODD,
                "handicap_step": 0.5,
                "max_handicap": 5.5
            },
            "hockey": {
                "min_home_odd": Config.MIN_HOME_ODD,  # Используем те же фильтры
                "max_away_odd": Config.MAX_AWAY_ODD,
                "handicap_step": 1.5,
                "max_handicap": 4.5
            }
        }.get(self.sport, {})
        
    def _get_sport_key(self) -> str:
        """Возвращает ключ спорта для The Odds API"""
        return "soccer" if self.sport == "football" else "icehockey"
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def fetch_matches(self) -> List[Dict[str, Any]]:
        """
        Загружает все матчи на сегодня и фильтрует их по кэфам.
        """
        session = await self._get_session()
        filtered_matches = []
        
        # 1. Получаем все матчи на сегодня
        url = f"{self.BASE_URL}/sports/{self.sport_key}/odds"
        params = {
            "apiKey": self.api_key,
            "regions": "eu",
            "markets": "h2h",
            "oddsFormat": "decimal",
            "dateFormat": "iso"
        }
        
        try:
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    logger.error(f"Ошибка API: {resp.status}")
                    return []
                    
                data = await resp.json()
                
            # 2. Фильтруем по коэффициентам
            for event in data:
                bookmakers = event.get("bookmakers", [])
                if not bookmakers:
                    continue
                    
                # Берем средний коэффициент среди всех букмекеров
                home_odds = []
                away_odds = []
                for bm in bookmakers:
                    markets = bm.get("markets", [])
                    for market in markets:
                        if market.get("key") == "h2h":
                            outcomes = market.get("outcomes", [])
                            for outcome in outcomes:
                                if outcome.get("name") == event.get("home_team"):
                                    home_odds.append(outcome.get("price", 0))
                                elif outcome.get("name") == event.get("away_team"):
                                    away_odds.append(outcome.get("price", 0))
                
                if not home_odds or not away_odds:
                    continue
                    
                avg_home = sum(home_odds) / len(home_odds)
                avg_away = sum(away_odds) / len(away_odds)
                
                # Главный фильтр: Дома >= MIN_HOME_ODD, Гости <= MAX_AWAY_ODD
                if avg_home >= self.config.get("min_home_odd", 3.6) and avg_away <= self.config.get("max_away_odd", 1.8):
                    match_info = {
                        "id": event.get("id"),
                        "sport": self.sport,
                        "home_team": event.get("home_team"),
                        "away_team": event.get("away_team"),
                        "commence_time": event.get("commence_time"),
                        "home_odd": round(avg_home, 2),
                        "away_odd": round(avg_away, 2)
                    }
                    filtered_matches.append(match_info)
                    
            logger.info(f"Найдено {len(filtered_matches)} матчей в {self.sport} после фильтрации")
            return filtered_matches
            
        except Exception as e:
            logger.error(f"Ошибка при получении матчей: {e}")
            return []
    
    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
