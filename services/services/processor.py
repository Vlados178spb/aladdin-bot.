import random

class AladdinProcessor:
    def __init__(self, engine):
        self.engine = engine

    def filter_matches(self, all_world_matches, sport_type):
        """
        Фильтрует входящий поток игр по твоим критериям:
        Форы до +5, ИТБ1, ОЗ, П1, 1Х.
        """
        criteria = self.engine.HOME_ADVANTAGE_MARKETS.get(sport_type, {})
        filtered = []
        
        for match in all_world_matches:
            # Логика: если в линии БК есть подходящий маркет из нашего списка
            # В данном прототипе мы имитируем выборку лучших из доступных
            if match['home_power'] > match['away_power']:
                match['recommended_bet'] = random.choice(criteria.get('HANDICAPS', ['Ф1(0)']))
                filtered.append(match)
        
        return filtered

    def select_top_4(self, filtered_matches):
        """Выбирает 4 самые надежные игры для экспресса 333"""
        if len(filtered_matches) < 4:
            return filtered_matches
        
        # Сортировка по надежности (имитация) и возврат топ-4
        return random.sample(filtered_matches, 4)

def format_for_express(top_4):
    """Подготовка данных для финальной картинки"""
    results = []
    total_koef = 1.0
    for m in top_4:
        koef = float(m.get('odds', 1.85))
        results.append({
            "match": f"{m['home']} - {m['away']}",
            "bet": m['recommended_bet'],
            "koef": f"{koef:.2f}"
        })
        total_koef *= koef
    return results, round(total_koef, 2)
