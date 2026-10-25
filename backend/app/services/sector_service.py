from typing import List, Dict, Any

# Standard sector mapping for key monitored companies
COMPANY_SECTORS = {
    "Apple": "Technology",
    "Microsoft": "Technology",
    "Alphabet": "Technology",
    "Google": "Technology",
    "Nvidia": "Technology",
    "Amazon": "Consumer Cyclical",
    "Tesla": "Consumer Cyclical",
    "Meta": "Communication Services",
    "JPMorgan Chase": "Financials",
    "Goldman Sachs": "Financials",
    "Bank of America": "Financials",
    "Johnson & Johnson": "Healthcare",
    "Pfizer": "Healthcare",
    "Eli Lilly": "Healthcare",
    "ExxonMobil": "Energy",
    "Chevron": "Energy",
}

SECTORS = ["Technology", "Financials", "Consumer Cyclical", "Healthcare", "Communication Services", "Energy"]

class SectorService:
    @staticmethod
    def get_sector_for_company(company: str) -> str:
        for k, v in COMPANY_SECTORS.items():
            if k.lower() in company.lower():
                return v
        return "General Market"

    @classmethod
    def calculate_sector_heatmaps(cls, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Aggregates sentiment across market sectors."""
        sector_data = {s: {"positive": 0, "negative": 0, "neutral": 0, "companies": set(), "articles": 0} for s in SECTORS}
        sector_data["General Market"] = {"positive": 0, "negative": 0, "neutral": 0, "companies": set(), "articles": 0}

        for article in articles:
            if article.get("is_duplicate"):
                continue

            company = article.get("company", "General Market")
            sector = cls.get_sector_for_company(company)
            sentiment = (article.get("sentiment") or "neutral").lower()

            if sector not in sector_data:
                sector_data[sector] = {"positive": 0, "negative": 0, "neutral": 0, "companies": set(), "articles": 0}

            sector_data[sector]["articles"] += 1
            sector_data[sector]["companies"].add(company)
            if sentiment == "positive":
                sector_data[sector]["positive"] += 1
            elif sentiment == "negative":
                sector_data[sector]["negative"] += 1
            else:
                sector_data[sector]["neutral"] += 1

        results = []
        for sector_name, data in sector_data.items():
            total = data["articles"]
            if total == 0:
                results.append({
                    "sector": sector_name,
                    "article_count": 0,
                    "bullish_pct": 0.0,
                    "bearish_pct": 0.0,
                    "neutral_pct": 0.0,
                    "net_sentiment_score": 0.0,
                    "status": "Insufficient Data",
                    "companies": []
                })
                continue

            bullish_pct = round((data["positive"] / total) * 100, 1)
            bearish_pct = round((data["negative"] / total) * 100, 1)
            neutral_pct = round((data["neutral"] / total) * 100, 1)
            # Net score: (positive - negative) / total -> from -1.0 to +1.0
            net_score = round((data["positive"] - data["negative"]) / total, 2)

            if net_score >= 0.2:
                status = "Bullish"
            elif net_score <= -0.2:
                status = "Bearish"
            else:
                status = "Neutral / Balanced"

            results.append({
                "sector": sector_name,
                "article_count": total,
                "bullish_pct": bullish_pct,
                "bearish_pct": bearish_pct,
                "neutral_pct": neutral_pct,
                "net_sentiment_score": net_score,
                "status": status,
                "companies": sorted(list(data["companies"]))
            })

        # Return sectors with articles first
        results.sort(key=lambda x: (x["article_count"] > 0, x["article_count"]), reverse=True)
        return results

sector_service = SectorService()
