import aiohttp
from typing import List, Dict, Any, Optional
from loguru import logger
from config import Config

class OddsAPI:
    """
    Загрузчик коэффициентов через Odds-API.io (прямые запросы)
    с фильтром Дома >= 3.4 и Гости <= 2.0
    """
    BASE_URL = "https://api.odds-api.io/v4"

    def __init__(self, sport: str):
        self.sport = sport.lower()
        self.api_key = Config.ODDS_API_IO_KEY
        self.session: Optional[aiohttp.ClientSession] = None
        # Определяем ключ спорта для API
        self.sport_key = "soccer" if self.sport == "football" else "icehockey"

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def fetch_matches(self) -> List[Dict[str, Any]]:
        session = await self._get_session()
        filtered = []
        
        # 1. Получаем все события (матчи) на сегодня
        events_url = f"{self.BASE_URL}/sports/{self.sport_key}/events"
        params = {"apiKey": self.api_key, "dateFormat": "iso"}
        
        try:
            async with session.get(events_url, params=params) as resp:
                if resp.status != 200:
                    logger.error(f"❌ Ошибка получения событий: {resp.status}")
                    return []
                events = await resp.json()

            # 2. Для каждого события получаем коэффициенты
            for event in events:
                home_team = event.get("home_team")
                away_team = event.get("away_team")
                event_id = event.get("id")
                commence_time = event.get("commence_time")

                if not home_team or not away_team:
                    continue

                # Запрос коэффициентов для конкретного события
                odds_url = f"{self.BASE_URL}/sports/{self.sport_key}/events/{event_id}/odds"
                async with session.get(odds_url, params={"apiKey": self.api_key, "markets": "h2h"}) as odds_resp:
                    if odds_resp.status != 200:
                        continue
                    odds_data = await odds_resp.json()

                # 3. Извлекаем и усредняем коэффициенты
                home_odds = []
                away_odds = []
                for bookmaker in odds_data.get("bookmakers", []):
                    for market in bookmaker.get("markets", []):
                        if market.get("key") == "h2h":
                            for outcome in market.get("outcomes", []):
                                if outcome.get("name") == home_team:
                                    home_odds.append(outcome.get("price"))
                                elif outcome.get("name") == away_team:
                                    away_odds.append(outcome.get("price"))
                
                if not home_odds or not away_odds:
                    continue

                avg_home = sum(home_odds) / len(home_odds)
                avg_away = sum(away_odds) / len(away_odds)

                # ===== ГЛАВНЫЙ ФИЛЬТР =====
                if avg_home >= Config.MIN_HOME_ODD and avg_away <= Config.MAX_AWAY_ODD:
                    filtered.append({
                        "id": event_id,
                        "sport": self.sport,
                        "home_team": home_team,
                        "away_team": away_team,
                        "commence_time": commence_time,
                        "home_odd": round(avg_home, 2),
                        "away_odd": round(avg_away, 2)
                    })

            logger.info(f"🏁 {self.sport}: {len(filtered)} матчей после фильтрации")
            return filtered
        except Exception as e:
            logger.error(f"Ошибка при получении матчей: {e}")
            return []

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
