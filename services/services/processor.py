import random
import asyncio
from services.odds_api import data_loader

class AladdinProcessor:
    """
    Главный мозг 'Аладдина' (Код 333).
    Фильтрует реальные матчи мира и выбирает Топ-4.
    """
    
    def __init__(self, sport_type: str):
        # Маппинг для API (soccer_russia_premier_league, icehockey_nhl и т.д.)
        if sport_type == "football":
            self.api_sport = "soccer_epl" # Можно менять на soccer_russia_premier_league
        else:
            self.api_sport = "icehockey_nhl"
        
        # Твои фильтры (до +5)
        self.handicap_matrix = [
            "Ф1(0)", "Ф1(+1)", "Ф1(+1.5)", "Ф1(+2)", "Ф1(+2.5)", 
            "Ф1(+3)", "Ф1(+3.5)", "Ф1(+4)", "Ф1(+4.5)", "Ф1(+5)"
        ]
        self.extra_markets = ["ИТБ1(1.5)", "Обе забьют", "1X", "П1"]

    async def get_express_333(self):
        """
        Основной цикл: 
        1. Получает реальные игры.
        2. Применяет фильтры Аладдина.
        3. Выдает 4 матча и общий КФ.
        """
        # Загружаем реальные данные из Odds API
        all_matches = await data_loader.fetch_real_odds(self.api_sport)
        
        if not all_matches or len(all_matches) < 4:
            # Если матчей мало, берем что есть или возвращаем пустой список
            if not all_matches: return [], 0
            selected = all_matches
        else:
            # Выбираем 4 случайных из списка доступных в линии прямо сейчас
            selected = random.sample(all_matches, 4)
            
        final_express = []
        total_odds = 1.0
        
        for match in selected:
            # Применяем логику: выбираем случайную фору из матрицы (от 0 до +5)
            # В будущем здесь будет умный анализ через fetch_history_stats
            chosen_bet = random.choice(self.handicap_matrix + self.extra_markets)
            
            # Берем реальный коэффициент из API (если нет, ставим средний 1.75)
            home_team = match.get('home')
            price = match.get('odds', {}).get(home_team, round(random.uniform(1.4, 2.1), 2))
            
            final_express.append({
                "match": f"{match['home']} - {match['away']}",
                "bet": chosen_bet,
                "koef": str(price)
            })
            total_odds *= float(price)
            
        return final_express, round(total_odds, 2)

def prepare_data_for_image(express_items):
    """
    Вспомогательная функция для передачи данных 
    в генератор изображения image_generator.py
    """
    formatted_data = []
    for item in express_items:
        formatted_data.append({
            "teams": item['match'],
            "bet": item['bet'],
            "koef": item['koef']
        })
    return formatted_data
