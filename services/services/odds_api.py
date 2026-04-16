import requests
import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# КОНФИГУРАЦИЯ (Вставь свой ключ от The Odds API)
ODDS_API_KEY = "YOUR_ODDS_API_KEY_HERE" 
ODDS_BASE_URL = "https://api.the-odds-api.com/v4/sports"

class OddsLoader:
    """
    Загрузчик реальных данных: 
    The Odds API (Кэфы) + OpenLigaDB (История/Результаты)
    """
    
    def __init__(self):
        self.api_key = ODDS_API_KEY

    def get_current_season(self) -> str:
        """Динамический расчет текущего сезона (напр. 2025 или 2026)"""
        now = datetime.now()
        return str(now.year) if now.month >= 8 else str(now.year - 1)

    async def fetch_real_odds(self, sport: str) -> List[Dict]:
        """
        Получает реальные коэффициенты из The Odds API.
        sport: 'soccer_russia_premier_league', 'icehockey_nhl', 'soccer_epl'
        """
        params = {
            "api_key": self.api_key,
            "regions": "eu",
            "markets": "h2h,spreads", # Кэфы на победу и форы
            "oddsFormat": "decimal"
        }
        
        url = f"{ODDS_BASE_URL}/{sport}/odds"
        
        try:
            # Используем обычный requests в потоке, чтобы не блокировать бота
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                return self._parse_odds(data)
            else:
                logger.error(f"Ошибка Odds API: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Ошибка при запросе кэфОВ: {e}")
            return []

    def _parse_odds(self, data: List[Dict]) -> List[Dict]:
        """Парсинг ответа API в чистый формат для Аладдина"""
        parsed = []
        for item in data:
            match_info = {
                "id": item["id"],
                "home": item["home_team"],
                "away": item["away_team"],
                "commence_time": item["commence_time"],
                "odds": {}
            }
            # Берем кэфы первого доступного букмекера (обычно Pinnacle или Betfair)
            if item.get("bookmakers"):
                markets = item["bookmakers"][0].get("markets", [])
                for m in markets:
                    if m["key"] == "h2h":
                        for outcome in m["outcomes"]:
                            match_info["odds"][outcome["name"]] = outcome["price"]
            parsed.append(match_info)
        return parsed

    async def fetch_history_stats(self, team_name: str) -> Dict:
        """
        Получает историю из OpenLigaDB (бесплатно, без ключа).
        Используется для проверки формы команды.
        """
        season = self.get_current_season()
        # Пример для Бундеслиги/РПЛ (требует маппинга имен лиг)
        url = f"https://api.openligadb.de/getmatchdata/bl1/{season}"
        
        try:
            res = requests.get(url)
            if res.status_code == 200:
                matches = res.json()
                # Фильтруем матчи конкретной команды
                team_matches = [m for m in matches if m['team1']['teamName'] == team_name or m['team2']['teamName'] == team_name]
                return {"history_count": len(team_matches), "recent": team_matches[-3:]}
            return {}
        except:
            return {}

# Глобальный объект для использования в процессоре
data_loader = OddsLoader()

