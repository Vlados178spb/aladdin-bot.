from datetime import datetime

def format_match(m):
    t = datetime.fromisoformat(m["time"].replace("Z","")).strftime("%H:%M")

    return f"""
⚽ {m['home']} — {m['away']}
🕒 {t} (МСК)

📊 {m['home_odd']} / {m['away_odd']}

🎯 {m['bet']}
💪 {m['conf']} ({m['score']})

──────────────
"""
