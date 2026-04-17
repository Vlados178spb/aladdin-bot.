class MatchAnalysis:

    def __init__(self, match):
        self.home_team = match["home_team"]
        self.away_team = match["away_team"]
        self.home_odd = match["home_odd"]
        self.away_odd = match["away_odd"]
        self.time = match["time"]

        self.total_score = 0
        self.recommended_handicap = 0
        self.confidence = "LOW"
        self.bet_reason = ""


class MatchAnalyzer:

    def analyze_single_match(self, match):
        a = MatchAnalysis(match)

        # 🔥 ОСНОВА VALUE
        diff = a.home_odd - a.away_odd
        score = diff

        if a.home_odd >= 4:
            score += 1.5

        if a.away_odd <= 1.5:
            score += 1

        a.total_score = round(score, 2)

        # 🎯 ФОРА
        a.recommended_handicap = round(diff / 2, 1)

        # 💪 УВЕРЕННОСТЬ
        if score >= 4:
            a.confidence = "HIGH"
        elif score >= 2.5:
            a.confidence = "MEDIUM"
        else:
            a.confidence = "LOW"

        # 📝 ОБОСНОВАНИЕ
        a.bet_reason = f"Перекос линии ({a.home_odd} vs {a.away_odd})"

        return a
