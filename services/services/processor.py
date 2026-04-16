import datetime

class AladdinEngine:
    """Глобальный движок для обработки всего мирового спорта"""
    
    # Все виды спорта, доступные в РФ
    SPORTS = {
        "FOOTBALL": "Футбол (Весь мир)",
        "HOCKEY": "Хоккей (Весь мир)"
    }

    # Специальный фильтр по форам (наш приоритет)
    HOME_ADVANTAGE_MARKETS = {
        "FOOTBALL": [
            "Ф1(0)", "Ф1(-1)", "Ф1(-1.5)", "Ф1(+1)", "Ф1(1.5)", 
            "ИТБ1 (1.5)", "1X"
        ],
        "HOCKEY": [
            "Ф1(0)", "Ф1(-1)", "Победа в матче (1)", "ИТБ1 (2.5)", "1X"
        ]
    }

class WorldLeagues:
    """Динамический справочник всех стран и лиг"""
    
    @staticmethod
    def get_full_coverage():
        """
        Логика охвата: Бот не ограничен списком. 
        Он принимает ЛЮБУЮ пару команд и ЛЮБУЮ лигу из линии БК.
        """
        return "GLOBAL_SCAN_ENABLED"

class MatchAnalyzer:
    """Модуль анализа и фильтрации для кнопок 'Футбол' и 'Хоккей'"""
    
    def __init__(self, matches):
        self.matches = matches # Список всех игр из парсера/API

    def apply_home_handicap_filter(self, sport_type):
        """
        Главный фильтр: Ищет игры, где фора на домашнюю команду 
        имеет максимальную математическую надежность.
        """
        priority_bets = AladdinEngine.HOME_ADVANTAGE_MARKETS.get(sport_type, [])
        # Здесь будет логика сравнения коэффициентов и вероятностей
        return priority_bets

    def get_top_4_express(self):
        """
        Функция для Экспресса: выбирает 4 самых надежных исхода
        с учетом нашего акцента на домашнюю фору.
        """
        # Сортировка по весам надежности
        # Возвращает ровно 4 объекта для "Формата 333"
        pass

# Утилита для формирования данных под картинку (Формат 333)
def prepare_express_data(selected_4_matches):
    """
    Подготовка финального списка для image_generator.py
    selected_4_matches: список из 4-х словарей/объектов
    """
    express_list = []
    total_odds = 1.0
    
    for m in selected_4_matches:
        express_list.append({
            "Матч": f"{m['home']} - {m['away']}",
            "Ставка": m['bet'], # Наш акцент на Ф1
            "Коэффициент": m['odds']
        })
        total_odds *= float(m['odds'])
        
    return express_list, round(total_odds, 2)
