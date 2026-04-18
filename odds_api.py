import aiohttp
from typing import List, Dict, Any, Optional
from loguru import logger
from config import Config

class OddsAPI:
    """Загрузчик коэффициентов с фильтром Дома >= 3.6 и Гости <= 1.8"""
    
    BASE_URL = "https://api.the-odds-api.com/v4"

    def __init__(self, sport: str):
        self.sport = sport.lower()
        self.api_key = Config.ODDS_API_KEY
        self.session: Optional[aiohttp.ClientSession] = None
        self.sport_key = "soccer" if self.sport == "football" else "icehockey"

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def fetch_matches(self) -> List[Dict[str, Any]]:
        session = await self._get_session()
        filtered_matches = []
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
                    text = await resp.text()
                    logger.error(f"❌ API error {resp.status}: {text}")
                    return []
                data = await resp.json()

            for event in data:
                home_team = event.get("home_team")
                away_team = event.get("away_team")
                if not home_team or not away_team:
                    continue

                bookmakers = event.get("bookmakers", [])
                if not bookmakers:
                    continue

                home_odds = []
                away_odds = []

                for bm in bookmakers:
                    markets = bm.get("markets", [])
                    for market in markets:
                        if market.get("key") == "h2h":
                            outcomes = market.get("outcomes", [])
                            for outcome in outcomes:
                                name = outcome.get("name")
                                price = outcome.get("price")
                                if name == home_team:
                                    home_odds.append(price)
                                elif name == away_team:
                                    away_odds.append(price)

                if not home_odds or not away_odds:
                    continue

                avg_home = sum(home_odds) / len(home_odds)
                avg_away = sum(away_odds) / len(away_odds)

                # ===== ГЛАВНЫЙ ФИЛЬТР =====
                if avg_home >= Config.MIN_HOME_ODD and avg_away <= Config.MAX_AWAY_ODD:
                    match_info = {
                        "id": event.get("id"),
                        "sport": self.sport,
                        "home_team": home_team,
                        "away_team": away_team,
                        "commence_time": event.get("commence_time"),
                        "home_odd": round(avg_home, 2),
                        "away_odd": round(avg_away, 2)
                    }
                    filtered_matches.append(match_info)
                    logger.debug(f"✅ {home_team} ({avg_home:.2f}) vs {away_team} ({avg_away:.2f})")
                else:
                    logger.debug(f"❌ Отброшен: {home_team} ({avg_home:.2f}) vs {away_team} ({avg_away:.2f})")

            logger.info(f"🏁 {self.sport}: {len(filtered_matches)} матчей после фильтрации")
            return filtered_matches

        except Exception as e:
            logger.error(f"Ошибка при получении матчей: {e}")
            return []

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
