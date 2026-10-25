from typing import List, Dict, Any, Optional
from datetime import datetime

class ConflictDetectorService:
    def __init__(self, min_positive: int = 1, min_negative: int = 1, min_conflict_score: float = 0.25):
        self.min_positive = min_positive
        self.min_negative = min_negative
        self.min_conflict_score = min_conflict_score

    def detect_conflicts(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Groups articles by company and identifies active Bullish/Bearish sentiment divergence.
        Only distinct (non-duplicate) articles are evaluated to ensure fair weighting.
        """
        by_company: Dict[str, Dict[str, Any]] = {}

        for article in articles:
            # Skip duplicates to avoid double counting conflicting signals
            if article.get("is_duplicate"):
                continue

            company = article.get("company", "Unknown")
            sentiment = (article.get("sentiment") or "neutral").lower()

            if company not in by_company:
                by_company[company] = {
                    "company": company,
                    "ticker": article.get("ticker", company[:4].upper()),
                    "positive_headlines": [],
                    "negative_headlines": [],
                    "neutral_headlines": []
                }

            title = article.get("title", "")
            if sentiment == "positive":
                by_company[company]["positive_headlines"].append(title)
            elif sentiment == "negative":
                by_company[company]["negative_headlines"].append(title)
            else:
                by_company[company]["neutral_headlines"].append(title)

        conflicts = []
        for company, data in by_company.items():
            pos_count = len(data["positive_headlines"])
            neg_count = len(data["negative_headlines"])
            neu_count = len(data["neutral_headlines"])
            total_directional = pos_count + neg_count

            if pos_count >= self.min_positive and neg_count >= self.min_negative:
                # Harmonic mean or min ratio representation:
                # If 5 positive and 5 negative: conflict score = 1.0 (maximal divergence)
                # If 9 positive and 1 negative: conflict score = 2 * (1 / 10) = 0.20
                conflict_score = round((2.0 * min(pos_count, neg_count)) / total_directional, 2)

                if conflict_score >= self.min_conflict_score:
                    explanation = (
                        f"Mixed-News Sentiment Signal: {company} exhibits notable opposing coverage with "
                        f"{pos_count} positive and {neg_count} negative headlines currently recorded. "
                        f"Media narratives reflect both growth catalysts and regulatory/operational headwinds."
                    )
                    conflicts.append({
                        "company": company,
                        "ticker": data["ticker"],
                        "conflict_score": conflict_score,
                        "positive_count": pos_count,
                        "negative_count": neg_count,
                        "neutral_count": neu_count,
                        "positive_headlines": data["positive_headlines"][:4],
                        "negative_headlines": data["negative_headlines"][:4],
                        "explanation": explanation,
                        "flagged_at": datetime.utcnow().isoformat() + "Z"
                    })

        # Sort by conflict score descending
        conflicts.sort(key=lambda x: x["conflict_score"], reverse=True)
        return conflicts

conflict_service = ConflictDetectorService()
