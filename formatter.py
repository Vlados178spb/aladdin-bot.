from typing import List, Dict
from datetime import datetime
import pytz
from analyzer import MatchAnalysis, Confidence

class MessageFormatter:
    """Красивое оформление сообщений для Telegram"""
    
    # Эмодзи для флагов (основные страны)
    FLAGS = {
        "England": "🇬🇧", "Spain": "🇪🇸", "Italy": "🇮🇹", "Germany": "🇩🇪",
        "France": "🇫🇷", "Netherlands": "🇳🇱", "Portugal": "🇵🇹", "Brazil": "🇧🇷",
        "Argentina": "🇦🇷", "Russia": "🇷🇺", "USA": "🇺🇸", "Canada": "🇨🇦",
        "Sweden": "🇸🇪", "Finland": "🇫🇮", "Czech": "🇨🇿", "Switzerland": "🇨🇭",
        "Belarus": "🇧🇾", "Kazakhstan": "🇰🇿", "China": "🇨🇳", "Japan": "🇯🇵",
        "Korea": "🇰🇷", "Australia": "🇦🇺"
    }
    
    @staticmethod
    def get_flag(team_name: str) -> str:
        """Пытается определить флаг по названию команды"""
        for country, flag in MessageFormatter.FLAGS.items():
            if country.lower() in team_name.lower():
                return flag
        return "🌍"
    
    @staticmethod
    def format_match(analysis: MatchAnalysis) -> str:
        """Форматирует один матч для вывода"""
        home_flag = MessageFormatter.get_flag(analysis.home_team)
        away_flag = MessageFormatter.get_flag(analysis.away_team)
        
        # Конвертация времени в МСК
        msk_tz = pytz.timezone("Europe/Moscow")
        try:
            dt = datetime.fromisoformat(analysis.commence_time.replace('Z', '+00:00'))
            dt_msk = dt.astimezone(msk_tz)
            time_str = dt_msk.strftime("%H:%M")
        except:
            time_str = "??:??"
        
        # Иконка уверенности
        conf_icon = {
            Confidence.HIGH: "🟢",
            Confidence.MEDIUM: "🟡",
            Confidence.LOW: "🔴"
        }.get(analysis.confidence, "⚪️")
        
        # Основная информация
        lines = [
            f"{conf_icon} **{home_flag} {analysis.home_team} vs {away_flag} {analysis.away_team}**",
            f"🕐 {time_str} МСК | 🏠 {analysis.home_odd} | 🚌 {analysis.away_odd}",
            f"📊 Скоринг: H2H {analysis.h2h_score:.1f} | Форма {analysis.home_form_score:.1f} | Гости {analysis.away_form_score:.1f}",
            f"🎯 **Рекомендуемая фора: Ф1 ({analysis.recommended_handicap:+.1f})**",
            f"💡 {analysis.bet_reason}",
            f"🤖 ML-вероятность: {analysis.prob_home_cover:.0%}",
            "",
        ]
        
        return "\n".join(lines)
    
    @staticmethod
    def format_express(analyses: List[MatchAnalysis]) -> str:
        """Форматирует экспресс из 4 матчей"""
        if len(analyses) < 4:
            return "❌ Недостаточно матчей для экспресса"
        
        total_odd = 1.0
        lines = [
            "🔥 **ЭКСПРЕСС ДНЯ (4 матча)** 🔥",
            ""
        ]
        
        for i, analysis in enumerate(analyses[:4], 1):
            home_flag = MessageFormatter.get_flag(analysis.home_team)
            away_flag = MessageFormatter.get_flag(analysis.away_team)
            
            # Предполагаемый кэф на фору (упрощенно)
            handicap_odd = analysis.home_odd * 0.6  # Примерная оценка
            total_odd *= handicap_odd
            
            lines.append(
                f"{i}. {home_flag} {analysis.home_team} vs {away_flag} {analysis.away_team}\n"
                f"   📈 Ф1 ({analysis.recommended_handicap:+.1f}) @ ~{handicap_odd:.2f}"
            )
        
        lines.extend([
            "",
            f"💰 **Общий коэффициент: ~{total_odd:.2f}**",
            f"🤖 Уверенность: {analyses[0].confidence.value}",
            "",
            "⚠️ Не является инвестиционной рекомендацией."
        ])
        
        return "\n".join(lines)
    
    @staticmethod
    def format_stats(stats: Dict) -> str:
        """Форматирует статистику бота"""
        return f"""
📊 **Статистика бота**

🎯 Проанализировано матчей: {stats.get('total_analyzed', 0)}
✅ Успешных прогнозов: {stats.get('successful', 0)}
📈 Точность: {stats.get('accuracy', 0):.1f}%

⚙️ Активные фильтры:
• Домашний кэф: ≥ {stats.get('min_home', 3.6)}
• Гостевой кэф: ≤ {stats.get('max_away', 1.8)}

🤖 ML-модели: XGBoost + River (онлайн-обучение)
"""
