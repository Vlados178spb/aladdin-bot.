def flag(country):
    flags = {
        "England": "🏴",
        "Spain": "🇪🇸",
        "Germany": "🇩🇪",
        "France": "🇫🇷",
        "Italy": "🇮🇹"
    }
    return flags.get(country, "🌍")


def format_match(m):
    return f"""
{flag('')} {m['home']} — {m['away']}
🕒 {m['time'].strftime('%H:%M')} (МСК)

📊 Кэф: {m['home_odd']} / {m['away_odd']}

🎯 Фора: +{m['handicap']}
⚽ ИТ1: Больше {m['it1']}
🔥 ОЗ: Да

💪 {m['conf']} ({m['score']})

──────────────
"""
