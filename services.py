import json
import os

class WeightOptimizer:
    def __init__(self):
        self.config_path = "sport_weights.json"
        self.history_path = "bet_history.json"

    def load_weights(self, sport: str):
        """Загрузка весов для конкретного спорта"""
        with open(self.config_path, "r") as f:
            data = json.load(f)
        return data.get(sport)

    def optimize(self, history: list):
        """Анализирует результаты и меняет веса самостоятельно"""
        if len(history) < 10: 
            return None # Ждем накопления статистики
        
        # Логика: если за неделю много минусов, бот меняет приоритет 
        # (например, уменьшает вес H2H и увеличивает вес формы дома)
        with open(self.config_path, "r") as f:
            weights = json.load(f)
            
        # Пример автоматической корректировки
        weights["football"]["home_form"] += 0.05
        weights["football"]["h2h"] -= 0.05
        
        with open(self.config_path, "w") as f:
            json.dump(weights, f, indent=2)
        return weights

class HistoryManager:
    """Управление базой данных для обучения"""
    def __init__(self):
        self.path = "bet_history.json"
        if not os.path.exists(self.path):
            with open(self.path, "w") as f:
                json.dump([], f)

    def add_entry(self, entry: dict):
        with open(self.path, "r+") as f:
            data = json.load(f)
            data.append(entry)
            f.seek(0)
            json.dump(data, f, indent=2)
