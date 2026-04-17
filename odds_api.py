import aiohttp
from datetime import datetime, timedelta
from config import ODDS_API_KEY

class OddsAPI:

    def __init__(self, sport: str):
        self.sport = sport

    async def fetch_matches(self):
        sport_key = "soccer" if self.sport == "football" else "icehockey"

        url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()

        matches = []

        for game in data:
            try:
                home = game["home_team"]
                away = [t for t in game["teams"] if t != home][0]

                odds = game["bookmakers"][0]["markets"][0]["outcomes"]

                home_odd = next(o["price"] for o in odds if o["name"] == home)
                away_odd = next(o["price"] for o in odds if o["name"] == away)

                # ⏱ фильтр по дате (только сегодня)
                game_time = datetime.fromisoformat(game["commence_time"].replace("Z",""))
                now = datetime.utcnow()

                if game_time.date() != now.date():
                    continue

                # 🔥 ТВОИ ФИЛЬТРЫ
                if self.sport == "football":
                    if not (home_odd >= 3.6 and away_odd <= 1.8):
                        continue
                else:
                    if not (home_odd >= 2.8 and away_odd <= 2.0):
                        continue

                matches.append({
                    "home_team": home,
                    "away_team": away,
                    "home_odd": home_odd,
                    "away_odd": away_odd,
                    "time": game["commence_time"]
                })

            except:
                continue

        return matches
