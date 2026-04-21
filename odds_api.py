from typing import List, Dict, Any, Optional
from loguru import logger
from config import Config
from odds_api import AsyncOddsAPIClient

class OddsAPI:
    """Загрузчик коэффициентов через Odds-API.io с фильтром Дома >= 3.4 и Гости <= 2.0"""

    def __init__(self, sport: str):
        self.sport = sport.lower()
        self.api_key = Config.ODDS_API_IO_KEY
        self.sport_key = "football" if self.sport == "football" else "icehockey"
        self.client: Optional[AsyncOddsAPIClient] = None

    async def _get_client(self) -> AsyncOddsAPIClient:
        if self.client is None:
            self.client = AsyncOddsAPIClient(api_key=self.api_key)
        return self.client

    async def fetch_matches(self) -> List[Dict[str, Any]]:
        client = await self._get_client()
        filtered = []
        try:
            # Получаем события на сегодня
            events = await client.get_events(sport=self.sport_key)
            
            for event in events:
                home_team = event.get("home")
                away_team = event.get("away")
                event_id = event.get("id")
                commence_time = event.get("commenceTime")

                if not home_team or not away_team:
                    continue

                # Получаем коэффициенты для события
                odds_data = await client.get_odds(event_id=event_id, market="h2h")
                
                home_odds = []
                away_odds = []
                for bookmaker in odds_data.get("bookmakers", []):
                    for market in bookmaker.get("markets", []):
                        if market.get("market") == "h2h":
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
                    match_info = {
                        "id": event_id,
                        "sport": self.sport,
                        "home_team": home_team,
                        "away_team": away_team,
                        "commence_time": commence_time,
                        "home_odd": round(avg_home, 2),
                        "away_odd": round(avg_away, 2)
                    }
                    filtered.append(match_info)
                    logger.debug(f"✅ {home_team} ({avg_home:.2f}) vs {away_team} ({avg_away:.2f})")
                else:
                    logger.debug(f"❌ Отброшен: {home_team} ({avg_home:.2f}) vs {away_team} ({avg_away:.2f})")

            logger.info(f"🏁 {self.sport}: {len(filtered)} матчей после фильтрации")
            return filtered
        except Exception as e:
            logger.error(f"Ошибка при получении матчей: {e}")
            return []
        finally:
            if self.client:
                await self.client.close()
