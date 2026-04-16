import json
import os
import pytz
from datetime import datetime
from deep_translator import GoogleTranslator

class TimeManager:
    """Конвертирует время из UTC в Московское (MSK)"""
    @staticmethod
    def to_msk(utc_time_str):
        try:
            # Парсинг ISO формата: 2024-05-20T18:00:00Z
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
        if not os.path.exists(self.config_path):
            return {"football": {}, "hockey": {}}
        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)

class HistoryManager:
    """Запись истории в bet_history.json"""
    def __init__(self, path="bet_history.json"):
        self.path = path
        if not os.path.exists(self.path):
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump([], f)

    def save_bet(self, bet_data):
        with open(self.path, "r", encoding="utf-8") as f:
            history = json.load(f)
        history.append(bet_data)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)

# Инициализируем менеджеры для работы
time_manager = TimeManager()
translator = TranslateManager()
weight_manager = WeightManager()
history_logger = HistoryManager()
