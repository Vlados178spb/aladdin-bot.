def analyze(match):
    score = 0

    diff = match["home_odd"] - match["away_odd"]

    # основной перекос
    score += diff * 1.2

    # value фактор
    if match["home_odd"] >= 4:
        score += 1.5

    if match["away_odd"] <= 1.5:
        score += 1

    # тотал
    if match["total"] <= 1.7:
        score += 0.5

    # ОЗ
    if match["btts"] <= 1.8:
        score += 0.5

    # 🎯 расчёт форы
    handicap = round(diff / 2, 1)

    # ИТ1
    it1 = 0.5 if handicap < 1 else 1.0

    # уверенность
    if score >= 5:
        conf = "🔥 ВЫСОКАЯ"
    elif score >= 3:
        conf = "✅ СРЕДНЯЯ"
    else:
        conf = "⚠️ НИЗКАЯ"

    return {
        **match,
        "score": round(score, 2),
        "handicap": handicap,
        "it1": it1,
        "conf": conf
    }
