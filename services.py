import json
import pytz
from datetime import datetime
from deep_translator import GoogleTranslator

class TimeManager:
    """Конвертирует время из UTC в Московское (MSK)"""
    @staticmethod
    def to_msk(utc_time_str):
        try:
            # Парсинг ISO формата из API (например, 2024-05-20T18:00:00Z)
            utc_dt = datetime.fromisoformat(utc_time_str.replace('Z', '+00:00'))
            msk_tz = pytz.timezone('Europe/Moscow')
            return utc_dt.astimezone(msk_tz).strftime('%H:%M')
        except Exception:
            return utc_time_str

class TranslateManager:
    """Автоматический перевод названий команд и лиг"""
    def __init__(self):
        self.translator = GoogleTranslator(source='en', target='ru')

    def translate_team(self, name):
        try:
            return self.translator.translate(name)
        except Exception:
            return name

class WeightManager:
    """Управление весами из sport_weights.json"""
    def __init__(self, config_path="sport_weights.json"):
        self.config_path = config_path

    def load_weights(self):
        with open(self.config_path, "r") as f:
            return json.load(f)

    def update_weights(self, sport, updates):
        weights = self.load_weights()
        if sport in weights:
            weights[sport].update(updates)
            with open(self.config_path, "w") as f:
                json.dump(weights, f, indent=2)
        return weights

class MatchAnalyzer:
    """Основная логика расчета Score (Формат 333)"""
    def __init__(self):
        self.weight_manager = WeightManager()
        self.translator = TranslateManager()

    def analyze(self, match_data, sport):
        weights = self.weight_manager.load_weights().get(sport, {})
        
        # Пример расчета (базовая логика)
        h2h_score = match_data.get('h2h', 0) * weights.get('h2h', 0.3)
        home_score = match_data.get('home_form', 0) * weights.get('home_form', 0.3)
        away_score = match_data.get('away_form', 0) * weights.get('away_form', 0.3)
        
        total_score = h2h_score + home_score + away_score
        
        return {
            "match": f"{self.translator.translate_team(match_data['home'])} vs {self.translator.translate_team(match_data['away'])}",
            "time_msk": TimeManager.to_msk(match_data.get('date', '')),
            "score": round(total_score, 2)
        }

class HistoryManager:
    """Управление базой данных для обучения"""
    def __init__(self, path="bet_history.json"):
        self.path = path

    def save_bet(self, bet_data):
        with open(self.path, "r") as f:
            history = json.load(f)
        history.append(bet_data)
        with open(self.path, "w") as f:
            json.dump(history, f, indent=2)
