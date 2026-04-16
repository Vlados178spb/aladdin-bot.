"""
Загрузчик реальных данных для футбола и хоккея.
Источники:
- The Odds API: текущие коэффициенты
- OpenLigaDB: история матчей (футбол)
- NHL API: история матчей (хоккей)

Все даты рассчитываются динамически от текущего дня.
"""

import requests
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)

# Конфигурация
ODDS_API_KEY = "YOUR_ODDS_API_KEY_HERE"
ODDS_BASE_URL = "https://api.the-odds-api.com/v4/sports"

# Кэш для истории (чтобы не перегружать API)
_history_cache = {}
CACHE_DURATION = timedelta(hours=2)

# ============================================================
# ДИНАМИЧЕСКОЕ ОПРЕДЕЛЕНИЕ СЕЗОНОВ
# ============================================================

def get_current_season() -> str:
    """
    Возвращает текущий сезон в формате YYYY.
    Сезон начинается в августе (футбол) или сентябре (хоккей).
    Если сейчас январь-июль 2026 — это сезон 2025/26 → "2025"
    Если сейчас август-декабрь 2026 — это сезон 2026/27 → "2026"
    """
    now = datetime.now()
    year = now.year
    month = now.month
    
    # Сезон начинается в августе
    if month >= 8:
        return str(year)
    else:
        return str(year - 1)


def get_last_n_seasons(n: int = 3) -> List[str]:
    """
    Возвращает список последних N сезонов для анализа истории.
    Пример: сейчас апрель 2026 → ["2023", "2024", "2025"]
    """
    current = int(get_current_season())
    
    # Если сейчас вторая половина сезона (январь-июль), текущий сезон = year-1
    # Например: апрель 2026 → текущий сезон 2025/26 → year = 2025
    # Предыдущие: 2024, 2023
    seasons = []
    for i in range(n):
        seasons.append(str(current - i))
    
    return seasons


def get_nhl_season_format(season_year: str) -> str:
    """
    NHL API использует формат YYYYYYYY (например "20242025").
    На вход: "2024" → "20242025"
    """
    year = int(season_year)
    return f"{year}{year + 1}"


def get_date_years_ago(years: int) -> str:
    """
    Возвращает дату N лет назад в формате YYYY-MM-DD.
    Используется для фильтрации истории.
    """
    now = datetime.now()
    past = now - timedelta(days=365 * years)
    return past.strftime("%Y-%m-%d")


def get_cutoff_date() -> str:
    """
    Возвращает дату 3 года назад для отсечки истории.
    Пример: 2026-04-15 → "2023-04-15"
    """
    return get_date_years_ago(3)


# ============================================================
# ОСНОВНАЯ ФУНКЦИЯ
# ============================================================

def get_odds(sport: str) -> List[Dict]:
    """
    Получает реальные данные для футбола и хоккея.
    sport: "soccer_epl" или "icehockey_nhl"
    """
    if sport not in ["soccer_epl", "icehockey_nhl"]:
        logger.error(f"Спорт {sport} не поддерживается")
        return []
    
    logger.info(f"Текущий сезон: {get_current_season()}")
    logger.info(f"Анализируем историю за сезоны: {get_last_n_seasons(3)}")
    logger.info(f"Отсечка по дате: {get_cutoff_date()}")
    
    # 1. Получаем текущие коэффициенты
    matches = _fetch_current_odds(sport)
    
    if not matches:
        logger.warning(f"Нет матчей после фильтрации для {sport}")
        return []
    
    # 2. Догружаем историю
    if sport == "soccer_epl":
        for match in matches:
            _enrich_football_history(match)
    else:
        for match in matches:
            _enrich_hockey_history(match)
    
    return matches


# ============================================================
# КОЭФФИЦИЕНТЫ (The Odds API)
# ============================================================

def _fetch_current_odds(sport: str) -> List[Dict]:
    """Запрос текущих коэффициентов"""
    url = f"{ODDS_BASE_URL}/{sport}/odds"
    
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "uk,eu,us",
        "markets": "h2h",
        "oddsFormat": "decimal"
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        remaining = response.headers.get('x-requests-remaining', 'unknown')
        logger.info(f"Odds API: осталось запросов {remaining}")
        
        if response.status_code != 200:
            logger.error(f"Ошибка Odds API: {response.status_code}")
            return []
        
        data = response.json()
        matches = []
        
        # Фильтры
        min_home = 3.5 if sport == "soccer_epl" else 2.8
        max_away = 2.2 if sport == "soccer_epl" else 2.0
        
        for event in data:
            match = _parse_odds_event(event, min_home, max_away, sport)
            if match:
                matches.append(match)
        
        logger.info(f"Найдено матчей: {len(matches)}/{len(data)}")
        return matches
        
    except Exception as e:
        logger.error(f"Ошибка получения коэффициентов: {e}")
        return []


def _parse_odds_event(event: Dict, min_home: float, max_away: float, sport: str) -> Optional[Dict]:
    """Парсит одно событие"""
    home_team = event.get('home_team')
    away_team = event.get('away_team')
    
    if not home_team or not away_team:
        return None
    
    bookmakers = event.get('bookmakers', [])
    if not bookmakers:
        return None
    
    # Выбор букмекера
    selected = None
    for bm in bookmakers:
        if 'bet365' in bm.get('key', '').lower():
            selected = bm
            break
    if not selected:
        for bm in bookmakers:
            if 'pinnacle' in bm.get('key', '').lower():
                selected = bm
                break
    if not selected:
        selected = bookmakers[0]
    
    # H2H маркет
    markets = selected.get('markets', [])
    h2h = next((m for m in markets if m.get('key') == 'h2h'), None)
    if not h2h:
        return None
    
    outcomes = h2h.get('outcomes', [])
    home_odd = away_odd = None
    
    for o in outcomes:
        if o.get('name') == home_team:
            home_odd = o.get('price')
        elif o.get('name') == away_team:
            away_odd = o.get('price')
    
    if home_odd and away_odd and home_odd >= min_home and away_odd <= max_away:
        return {
            "id": event.get('id'),
            "sport": sport,
            "home_team": home_team,
            "away_team": away_team,
            "home_odd": round(home_odd, 2),
            "away_odd": round(away_odd, 2),
            "commence_time": event.get('commence_time')
        }
    
    return None


# ============================================================
# ФУТБОЛ: OpenLigaDB (динамические сезоны)
# ============================================================

# Маппинг названий команд
FOOTBALL_TEAM_MAPPING = {
    "Manchester City": "Manchester City",
    "Arsenal": "Arsenal FC",
    "Liverpool": "Liverpool FC",
    "Chelsea": "Chelsea FC",
    "Manchester United": "Manchester United",
    "Tottenham": "Tottenham Hotspur",
    "Aston Villa": "Aston Villa",
    "Newcastle": "Newcastle United",
    "Brighton": "Brighton & Hove Albion",
    "West Ham": "West Ham United",
    "Brentford": "Brentford FC",
    "Crystal Palace": "Crystal Palace",
    "Everton": "Everton FC",
    "Fulham": "Fulham FC",
    "Wolves": "Wolverhampton Wanderers",
    "Bournemouth": "AFC Bournemouth",
    "Nottingham Forest": "Nottingham Forest",
    "Leicester": "Leicester City",
    "Southampton": "Southampton FC",
}


def _enrich_football_history(match: Dict):
    """Догружает историю футбола за последние 3 сезона"""
    home_team = match['home_team']
    away_team = match['away_team']
    
    cache_key = f"football_{home_team}_{away_team}"
    if cache_key in _history_cache:
        cached = _history_cache[cache_key]
        if datetime.now() - cached['timestamp'] < CACHE_DURATION:
            match.update(cached['data'])
            return
    
    ol_home = FOOTBALL_TEAM_MAPPING.get(home_team, home_team)
    ol_away = FOOTBALL_TEAM_MAPPING.get(away_team, away_team)
    
    # Получаем последние 3 сезона динамически
    seasons = get_last_n_seasons(3)
    all_matches = []
    
    for season in seasons:
        season_matches = _fetch_openligadb_season("bl1", season)
        if season_matches:
            logger.info(f"OpenLigaDB: сезон {season} — {len(season_matches)} матчей")
        all_matches.extend(season_matches)
    
    # H2H дома (только за последние 3 года)
    cutoff_date = get_cutoff_date()
    h2h_home = []
    
    for m in all_matches:
        match_date = m.get('matchDateTime', '')
        if match_date < cutoff_date:
            continue
        
        team1 = m.get('team1', {}).get('teamName', '')
        team2 = m.get('team2', {}).get('teamName', '')
        
        if ol_home.lower() in team1.lower() and ol_away.lower() in team2.lower():
            result = _football_result(m, is_home=True)
            h2h_home.append({
                "result": result,
                "date": match_date,
                "score": _extract_football_score(m)
            })
    
    h2h_home.sort(key=lambda x: x.get('date', ''), reverse=True)
    match['h2h_home'] = h2h_home[:3]
    
    # Последние 5 дома (любые соперники)
    home_last_5 = []
    for m in all_matches:
        match_date = m.get('matchDateTime', '')
        team1 = m.get('team1', {}).get('teamName', '')
        
        if ol_home.lower() in team1.lower():
            result = _football_result(m, is_home=True)
            goal_diff = _get_football_goal_diff(m, is_home=True)
            home_last_5.append({
                "result": result,
                "goal_diff": goal_diff,
                "date": match_date
            })
    
    home_last_5.sort(key=lambda x: x.get('date', ''), reverse=True)
    match['home_last_5'] = home_last_5[:5]
    
    # Последние 5 выездных игр гостей
    away_last_5 = []
    for m in all_matches:
        team2 = m.get('team2', {}).get('teamName', '')
        
        if ol_away.lower() in team2.lower():
            result = _football_result(m, is_home=False)
            goal_diff = _get_football_goal_diff(m, is_home=False)
            away_last_5.append({
                "result": result,
                "goal_diff": goal_diff,
                "date": m.get('matchDateTime', '')
            })
    
    away_last_5.sort(key=lambda x: x.get('date', ''), reverse=True)
    match['away_last_5'] = away_last_5[:5]
    
    # Медианная разница поражений дома
    home_losses = [m for m in home_last_5 if m.get('result') == 'L']
    if home_losses:
        diffs = sorted([abs(m.get('goal_diff', 1)) for m in home_losses])
        match['median_loss_diff'] = float(diffs[len(diffs) // 2])
    else:
        match['median_loss_diff'] = 1.0
    
    _history_cache[cache_key] = {
        'timestamp': datetime.now(),
        'data': {
            'h2h_home': match['h2h_home'],
            'home_last_5': match['home_last_5'],
            'away_last_5': match['away_last_5'],
            'median_loss_diff': match['median_loss_diff']
        }
    }


def _fetch_openligadb_season(league: str, season: str) -> List[Dict]:
    """Запрос к OpenLigaDB"""
    url = f"https://www.openligadb.de/api/getmatches/{league}/{season}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        logger.warning(f"OpenLigaDB {league}/{season}: {response.status_code}")
        return []
    except Exception as e:
        logger.error(f"OpenLigaDB ошибка: {e}")
        return []


def _football_result(match: Dict, is_home: bool) -> str:
    """W/D/L для футбола"""
    if not match.get('matchResults'):
        return '?'
    mr = match['matchResults'][0]
    p1 = mr.get('pointsTeam1', 0) or 0
    p2 = mr.get('pointsTeam2', 0) or 0
    
    if is_home:
        return 'W' if p1 > p2 else ('D' if p1 == p2 else 'L')
    else:
        return 'W' if p2 > p1 else ('D' if p2 == p1 else 'L')


def _get_football_goal_diff(match: Dict, is_home: bool) -> int:
    """Разница мячей"""
    if not match.get('matchResults'):
        return 0
    mr = match['matchResults'][0]
    p1 = mr.get('pointsTeam1', 0) or 0
    p2 = mr.get('pointsTeam2', 0) or 0
    return p1 - p2 if is_home else p2 - p1


def _extract_football_score(match: Dict) -> str:
    """Счёт матча"""
    if not match.get('matchResults'):
        return "?-?"
    mr = match['matchResults'][0]
    return f"{mr.get('pointsTeam1', 0)}-{mr.get('pointsTeam2', 0)}"


# ============================================================
# ХОККЕЙ: NHL API (динамические сезоны)
# ============================================================

NHL_TEAM_MAPPING = {
    "Boston Bruins": "BOS", "Toronto Maple Leafs": "TOR",
    "Tampa Bay Lightning": "TBL", "Florida Panthers": "FLA",
    "New York Rangers": "NYR", "Carolina Hurricanes": "CAR",
    "New Jersey Devils": "NJD", "Colorado Avalanche": "COL",
    "Edmonton Oilers": "EDM", "Vegas Golden Knights": "VGK",
    "Los Angeles Kings": "LAK", "Dallas Stars": "DAL",
    "Winnipeg Jets": "WPG", "Vancouver Canucks": "VAN",
    "Nashville Predators": "NSH", "Minnesota Wild": "MIN",
    "St Louis Blues": "STL", "St. Louis Blues": "STL",
    "Calgary Flames": "CGY", "Seattle Kraken": "SEA",
    "Pittsburgh Penguins": "PIT", "Washington Capitals": "WSH",
    "Philadelphia Flyers": "PHI", "New York Islanders": "NYI",
    "Detroit Red Wings": "DET", "Buffalo Sabres": "BUF",
    "Ottawa Senators": "OTT", "Montréal Canadiens": "MTL",
    "Montreal Canadiens": "MTL", "Columbus Blue Jackets": "CBJ",
    "Anaheim Ducks": "ANA", "San Jose Sharks": "SJS",
    "Chicago Blackhawks": "CHI", "Arizona Coyotes": "ARI",
    "Utah Hockey Club": "UTA"
}


def _enrich_hockey_history(match: Dict):
    """Догружает историю хоккея через NHL API"""
    home_team = match['home_team']
    away_team = match['away_team']
    
    cache_key = f"hockey_{home_team}_{away_team}"
    if cache_key in _history_cache:
        cached = _history_cache[cache_key]
        if datetime.now() - cached['timestamp'] < CACHE_DURATION:
            match.update(cached['data'])
            return
    
    home_abbr = _find_nhl_team_abbr(home_team)
    away_abbr = _find_nhl_team_abbr(away_team)
    
    if not home_abbr or not away_abbr:
        logger.warning(f"NHL: не найден маппинг для {home_team} или {away_team}")
        _set_empty_hockey_history(match)
        return
    
    # Получаем последние 3 сезона
    seasons = get_last_n_seasons(3)
    all_games = []
    
    for season_year in seasons:
        season_code = get_nhl_season_format(season_year)
        games = _fetch_nhl_team_schedule(home_abbr, season_code)
        all_games.extend(games)
        logger.info(f"NHL: сезон {season_code} — {len(games)} игр для {home_abbr}")
    
    # H2H дома
    cutoff_date = get_cutoff_date()
    h2h_home = []
    
    for game in all_games:
        game_date = game.get('gameDate', '')
        if game_date < cutoff_date:
            continue
        
        if not game.get('homeTeam') or not game.get('awayTeam'):
            continue
        
        game_home = game['homeTeam'].get('abbrev', '')
        game_away = game['awayTeam'].get('abbrev', '')
        
        if game_home == home_abbr and game_away == away_abbr:
            result = _hockey_result(game, is_home=True)
            h2h_home.append({
                "result": result,
                "date": game_date,
                "score": f"{game.get('homeScore', 0)}-{game.get('awayScore', 0)}"
            })
    
    h2h_home.sort(key=lambda x: x.get('date', ''), reverse=True)
    match['h2h_home'] = h2h_home[:3]
    
    # Последние 5 дома
    home_last_5 = []
    for game in all_games:
        if game.get('homeTeam', {}).get('abbrev') == home_abbr:
            result = _hockey_result(game, is_home=True)
            home_last_5.append({
                "result": result,
                "goal_diff": (game.get('homeScore', 0) or 0) - (game.get('awayScore', 0) or 0),
                "date": game.get('gameDate', '')
            })
    
    home_last_5.sort(key=lambda x: x.get('date', ''), reverse=True)
    match['home_last_5'] = home_last_5[:5]
    
    # Последние 5 выездных игр гостей
    away_games = []
    for season_year in seasons:
        season_code = get_nhl_season_format(season_year)
        games = _fetch_nhl_team_schedule(away_abbr, season_code)
        away_games.extend(games)
    
    away_last_5 = []
    for game in away_games:
        if game.get('awayTeam', {}).get('abbrev') == away_abbr:
            result = _hockey_result(game, is_home=False)
            away_last_5.append({
                "result": result,
                "goal_diff": (game.get('awayScore', 0) or 0) - (game.get('homeScore', 0) or 0),
                "date": game.get('gameDate', '')
            })
    
    away_last_5.sort(key=lambda x: x.get('date', ''), reverse=True)
    match['away_last_5'] = away_last_5[:5]
    
    # Медианная разница поражений
    home_losses = [g for g in home_last_5 if g.get('result') == 'L']
    if home_losses:
        diffs = sorted([abs(g.get('goal_diff', 1)) for g in home_losses])
        match['median_loss_diff'] = float(diffs[len(diffs) // 2])
    else:
        match['median_loss_diff'] = 1.5
    
    _history_cache[cache_key] = {
        'timestamp': datetime.now(),
        'data': {
            'h2h_home': match['h2h_home'],
            'home_last_5': match['home_last_5'],
            'away_last_5': match['away_last_5'],
            'median_loss_diff': match['median_loss_diff']
        }
    }


def _fetch_nhl_team_schedule(team_abbr: str, season: str) -> List[Dict]:
    """
    Запрос расписания команды через NHL API.
    season: "20242025"
    """
    url = f"https://api-web.nhle.com/v1/club-schedule-season/{team_abbr}/{season}"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('games', [])
        logger.warning(f"NHL API {team_abbr}/{season}: {response.status_code}")
        return []
    except Exception as e:
        logger.error(f"NHL API ошибка: {e}")
        return []


def _find_nhl_team_abbr(team_name: str) -> Optional[str]:
    """Поиск аббревиатуры команды NHL"""
    # Прямой поиск
    if team_name in NHL_TEAM_MAPPING:
        return NHL_TEAM_MAPPING[team_name]
    
    # Частичный поиск
    team_lower = team_name.lower()
    for full_name, abbr in NHL_TEAM_MAPPING.items():
        if team_lower in full_name.lower() or full_name.lower() in team_lower:
            return abbr
    
    return None


def _hockey_result(game: Dict, is_home: bool) -> str:
    """W/L для хоккея (ничьих в NHL нет)"""
    home_score = game.get('homeScore', 0) or 0
    away_score = game.get('awayScore', 0) or 0
    
    # Проверяем, завершён ли матч
    if game.get('gameState') not in ['OFF', 'FINAL']:
        return '?'
    
    if is_home:
        return 'W' if home_score > away_score else 'L'
    else:
        return 'W' if away_score > home_score else 'L'


def _set_empty_hockey_history(match: Dict):
    """Заглушка если не найден маппинг команды"""
    match['h2h_home'] = []
    match['home_last_5'] = []
    match['away_last_5'] = []
    match['median_loss_diff'] = 1.5
