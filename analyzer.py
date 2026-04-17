def analyze(match):
    score = 0

    # перекос линии
    diff = match["home_odd"] - match["away_odd"]
    score += diff

    # усиление value
    if match["home_odd"] >= 4:
        score += 1.5

    if match["away_odd"] <= 1.5:
        score += 1

    # итог
    if score >= 4:
        conf = "🔥 ВЫСОКАЯ"
    elif score >= 2.5:
        conf = "✅ СРЕДНЯЯ"
    else:
        conf = "⚠️ НИЗКАЯ"

    match["score"] = round(score, 2)
    match["conf"] = conf

    # рекомендация
    match["bet"] = f"Фора +{round(diff/2,1)} на хозяев"

    return match
