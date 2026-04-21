from datetime import datetime
import pytz

FLAGS = {
    "england": "🇬🇧", "spain": "🇪🇸", "italy": "🇮🇹", "germany": "🇩🇪",
    "france": "🇫🇷", "netherlands": "🇳🇱", "portugal": "🇵🇹", "brazil": "🇧🇷",
    "argentina": "🇦🇷", "russia": "🇷🇺", "usa": "🇺🇸", "canada": "🇨🇦",
    "sweden": "🇸🇪", "finland": "🇫🇮", "czech": "🇨🇿", "switzerland": "🇨🇭",
    "belarus": "🇧🇾", "kazakhstan": "🇰🇿", "ukraine": "🇺🇦", "turkey": "🇹🇷",
    "scotland": "🇳🇴", "denmark": "🇩🇰", "poland": "🇵🇱"
}

def get_flag(team: str) -> str:
    team_lower = team.lower()
    for country, flag in FLAGS.items():
        if country in team_lower:
            return flag
    return "🌍"

def format_matches(matches: list) -> str:
    if not matches:
        return "😔 Нет подходящих матчей."

    msk = pytz.timezone("Europe/Moscow")
    lines = []
    for m in matches:
        try:
            dt = datetime.fromisoformat(m["commence_time"].replace("Z", "+00:00"))
            time_str = dt.astimezone(msk).strftime("%H:%M")
        except:
            time_str = "--:--"

        home_flag = get_flag(m["home_team"])
        away_flag = get_flag(m["away_team"])

        lines.append(
            f"{home_flag} {m['home_team']} ({m['home_odd']}) — "
            f"{away_flag} {m['away_team']} ({m['away_odd']})\n"
            f"🕐 {time_str} МСК\n"
        )
    return "\n".join(lines)
