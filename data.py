import aiohttp
from datetime import datetime, timezone, timedelta
from config import ODDS_API_KEY, ODDS_API_IO_KEY


class DataService:

    async def get_matches(self):
        matches = []

        matches += await self._odds_api()
        matches += await self._odds_api_io()

        # удаляем дубли
        unique = {(m["home"], m["away"]): m for m in matches}
        return list(unique.values())

    async def _odds_api(self):
        url = f"https://api.the-odds-api.com/v4/sports/soccer/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h,totals,btts"

        return await self._fetch(url)

    async def _odds_api_io(self):
        url = f"https://api.odds-api.io/v3/odds?sport=soccer&apiKey={ODDS_API_IO_KEY}"

        return await self._fetch(url)

    async def _fetch(self, url):
        results = []

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                data = await r.json()

        for game in data:
            try:
                home = game["home_team"]
                away = game["away_team"]

                home_odd = float(game["home_odds"])
                away_odd = float(game["away_odds"])

                # фильтр по времени (только сегодня МСК)
                utc_time = datetime.fromisoformat(game["commence_time"].replace("Z",""))
                msk_time = utc_time + timedelta(hours=3)

                now = datetime.utcnow() + timedelta(hours=3)

                if msk_time.date() != now.date():
                    continue

                # 🔥 ФИЛЬТР
                if not (home_odd >= 3.6 and away_odd <= 1.8):
                    continue

                results.append({
                    "home": home,
                    "away": away,
                    "home_odd": home_odd,
                    "away_odd": away_odd,
                    "time": msk_time,
                    "btts": game.get("btts_yes", 1.8),
                    "total": game.get("over_2_5", 1.9)
                })

            except:
                continue

        return results
