import uuid
from typing import List, Dict, Any
from datetime import datetime
from app.database import db

class AlertService:
    def __init__(self):
        pass

    def evaluate_and_generate_alerts(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Scans current article sentiment aggregations against risk thresholds:
        1. Bearish Spikes: If negative headlines >= 3 and negative_pct >= 40%
        2. High Conflict: Bullish/Bearish opposing narratives
        """
        by_company = {}
        for a in articles:
            if a.get("is_duplicate"):
                continue
            c = a.get("company", "Unknown")
            by_company.setdefault(c, []).append(a)

        new_alerts = []
        now_str = datetime.utcnow().isoformat() + "Z"

        for company, items in by_company.items():
            total = len(items)
            if total < 2:
                continue

            neg_count = sum(1 for x in items if (x.get("sentiment") or "").lower() == "negative")
            pos_count = sum(1 for x in items if (x.get("sentiment") or "").lower() == "positive")
            neg_pct = round((neg_count / total) * 100, 1)

            # Check Bearish Threshold
            if neg_count >= 2 and neg_pct >= 40.0:
                alert_id = f"alert-{uuid.uuid4().hex[:8]}"
                alert_data = {
                    "id": alert_id,
                    "company": company,
                    "alert_type": "BEARISH_SURGE",
                    "severity": "high" if neg_pct >= 60 else "medium",
                    "message": f"Negative news tone surged for {company}: {neg_pct}% of {total} headlines are negative.",
                    "timestamp": now_str,
                    "is_read": False,
                    "metrics": {
                        "total_articles": total,
                        "negative_count": neg_count,
                        "negative_percentage": neg_pct
                    }
                }
                # Check if similar alert exists recently
                existing = db.find("alerts", {"company": company, "alert_type": "BEARISH_SURGE"}, limit=1)
                if not existing:
                    db.insert_one("alerts", alert_data)
                    new_alerts.append(alert_data)

            # Check High Conflict Threshold
            if pos_count >= 2 and neg_count >= 2:
                alert_id = f"alert-{uuid.uuid4().hex[:8]}"
                alert_data = {
                    "id": alert_id,
                    "company": company,
                    "alert_type": "SENTIMENT_DIVERGENCE",
                    "severity": "medium",
                    "message": f"Significant sentiment conflict detected for {company} ({pos_count} positive vs {neg_count} negative headlines).",
                    "timestamp": now_str,
                    "is_read": False,
                    "metrics": {
                        "total_articles": total,
                        "positive_count": pos_count,
                        "negative_count": neg_count
                    }
                }
                existing = db.find("alerts", {"company": company, "alert_type": "SENTIMENT_DIVERGENCE"}, limit=1)
                if not existing:
                    db.insert_one("alerts", alert_data)
                    new_alerts.append(alert_data)

        # Record company sentiment snapshots into sentiment_history
        for company, items in by_company.items():
            total = len(items)
            pos_count = sum(1 for x in items if (x.get("sentiment") or "").lower() == "positive")
            neg_count = sum(1 for x in items if (x.get("sentiment") or "").lower() == "negative")
            neu_count = total - (pos_count + neg_count)
            history_record = {
                "id": f"hist-{uuid.uuid4().hex[:8]}",
                "company": company,
                "timestamp": now_str,
                "total_articles": total,
                "positive_pct": round((pos_count / total) * 100, 1),
                "negative_pct": round((neg_count / total) * 100, 1),
                "neutral_pct": round((neu_count / total) * 100, 1),
                "dominant_sentiment": "positive" if pos_count > neg_count else ("negative" if neg_count > pos_count else "neutral")
            }
            db.insert_one("sentiment_history", history_record)

        return new_alerts

    def mark_as_read(self, alert_id: str) -> bool:
        return db.update_one("alerts", {"id": alert_id}, {"is_read": True})

    def get_alerts(self, unread_only: bool = False) -> List[Dict[str, Any]]:
        query = {"is_read": False} if unread_only else None
        alerts = db.find("alerts", query, limit=50)
        alerts.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return alerts

alert_service = AlertService()
