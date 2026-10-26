import os
import asyncio
import logging
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Query, Path, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import db
from app.models.schemas import (
    AnalyzeRequest, BatchAnalyzeRequest, SentimentAnalysisResult,
    NewsSearchRequest, NewsResponse, Article,
    CompanySentimentSummary, ConflictSignal, SectorSentiment,
    AlertRecord, DataQualityReport, AssistantChatRequest, AssistantChatResponse
)
from app.services.finbert_service import finbert_service
from app.services.headline_validator import HeadlineValidationError, assert_valid_financial_headline
from app.services.news_service import news_service, SUPPORTED_COMPANIES, canonicalize_company
from app.services.deduplication_service import deduplication_service
from app.services.conflict_service import conflict_service
from app.services.sector_service import sector_service
from app.services.alert_service import alert_service
from app.services.gemini_service import gemini_assistant_service
from app.services.financial_validator import validate_financial_headline, FinancialValidationError

# Configure logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("api")

app = FastAPI(
    title="Financial Market Sentiment Tracker API",
    description="AI-Powered Financial News Intelligence Platform backed by ProsusAI/finbert",
    version="1.0.0"
)

@app.exception_handler(HeadlineValidationError)
async def headline_validation_exception_handler(request, exc: HeadlineValidationError):
    """Returns structured HTTP 422 for invalid financial headlines."""
    return JSONResponse(
        status_code=422,
        content=exc.to_dict()
    )

# CORS Configuration - support local dev, Vercel deployments, and custom domains
origins = [
    settings.FRONTEND_ORIGIN,
    "https://market-tracker-umber.vercel.app",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in origins if o],
    allow_origin_regex=r"^https://.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _warmup_background():
    """
    Background worker that runs asynchronously AFTER the server binds to $PORT.
    This prevents Render from reporting 'No open ports detected' and ensures the web
    process is immediately live while the sentiment engine initializes safely.
    """
    await asyncio.sleep(0.5)
    logger.info("Initializing Financial Sentiment Engine...")
    try:
        finbert_service.load_model()
        diag = finbert_service.get_memory_diagnostics()
        logger.info(
            f"Sentiment Engine ready (Mode: {diag['engine_mode']}, "
            f"RSS: {diag['process_rss_mb']} MB / {diag['memory_limit_mb']} MB, "
            f"Utilization: {diag['percent_of_limit']}%)."
        )
    except Exception as e:
        logger.error(f"Error during background sentiment engine initialization: {e}")

@app.on_event("startup")
async def startup_event():
    logger.info("Initializing Financial Market Sentiment Tracker API (non-blocking)...")
    # Launch background warmup so Uvicorn binds to $PORT immediately
    asyncio.create_task(_warmup_background())

@app.get("/")
def get_root():
    """Root endpoint for instant ping and status."""
    diag = finbert_service.get_memory_diagnostics()
    return {
        "name": "Financial Market Sentiment Tracker API",
        "status": "online",
        "version": "1.0.0",
        "engine_mode": diag["engine_mode"],
        "memory": f"{diag['process_rss_mb']} MB / {diag['memory_limit_mb']} MB ({diag['percent_of_limit']}%)",
        "endpoints": {
            "health": "/health",
            "api_health": "/api/health",
            "docs": "/docs"
        }
    }

@app.get("/health")
def get_lightweight_health():
    """
    Ultra-lightweight health check endpoint for Render / load balancers.
    Returns 200 OK immediately without triggering model inference or DB queries.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "engine_mode": finbert_service.engine_mode,
        "model_ready": finbert_service.is_ready()
    }

@app.get("/api/health")
def get_health():
    if not finbert_service.is_ready():
        finbert_service.load_model()
    db_status = db.get_status()
    mem_diag = finbert_service.get_memory_diagnostics()
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "model": {
            "name": f"{settings.MODEL_NAME} (local-bfloat16)" if finbert_service.engine_mode == "local-bfloat16" else settings.MODEL_NAME,
            "status": "ready" if finbert_service.is_ready() else finbert_service.status,
            "engine_mode": finbert_service.engine_mode,
            "memory_usage_mb": mem_diag["process_rss_mb"],
            "memory_limit_mb": mem_diag["memory_limit_mb"],
            "memory_percent": mem_diag["percent_of_limit"],
            "is_within_limit": mem_diag["is_within_limit"],
            "is_fallback": mem_diag["is_fallback"],
            "error": finbert_service.error_message
        },
        "database": db_status,
        "news_api": {
            "status": news_service.news_api_status,
            "has_key": bool(settings.NEWS_API_KEY)
        },
        "gemini_assistant": {
            "active": gemini_assistant_service.is_active,
            "has_key": bool(settings.GEMINI_API_KEY)
        }
    }


@app.get("/api/dashboard/stats")
def get_dashboard_stats():
    """Aggregates all top-level stats for the main analytics dashboard."""
    articles = news_service.fetch_articles()
    
    # Exclude duplicates from main metrics to prevent inflated counts
    clean_articles = [a for a in articles if not a.get("is_duplicate")]
    total = len(clean_articles)
    
    pos_count = sum(1 for a in clean_articles if (a.get("sentiment") or "").lower() == "positive")
    neg_count = sum(1 for a in clean_articles if (a.get("sentiment") or "").lower() == "negative")
    neu_count = sum(1 for a in clean_articles if (a.get("sentiment") or "").lower() == "neutral")
    
    pos_pct = round((pos_count / total * 100), 1) if total > 0 else 0.0
    neg_pct = round((neg_count / total * 100), 1) if total > 0 else 0.0
    neu_pct = round((neu_count / total * 100), 1) if total > 0 else 0.0

    # Company distribution
    by_comp = {}
    for a in clean_articles:
        comp = a.get("company", "General Market")
        by_comp[comp] = by_comp.get(comp, 0) + 1
    
    top_discussed = sorted([{"company": k, "count": v} for k, v in by_comp.items()], key=lambda x: x["count"], reverse=True)[:6]

    # Source breakdown
    by_source = {}
    for a in clean_articles:
        src = a.get("source", "Unknown")
        by_source[src] = by_source.get(src, 0) + 1
    
    sources = sorted([{"source": k, "count": v} for k, v in by_source.items()], key=lambda x: x["count"], reverse=True)[:6]

    # Mixed-sentiment conflicts
    conflicts = conflict_service.detect_conflicts(articles)

    is_demo_dataset = any(a.get("is_demo", False) for a in clean_articles)

    return {
        "total_articles": total,
        "total_including_duplicates": len(articles),
        "sentiment_counts": {
            "positive": pos_count,
            "negative": neg_count,
            "neutral": neu_count
        },
        "sentiment_percentages": {
            "positive": pos_pct,
            "negative": neg_pct,
            "neutral": neu_pct
        },
        "top_discussed_companies": top_discussed,
        "news_sources": sources,
        "active_conflicts_count": len(conflicts),
        "active_conflicts": conflicts[:3],
        "is_demo_dataset": is_demo_dataset,
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "model_status": "ready" if finbert_service.is_ready() else finbert_service.status
    }

@app.get("/api/news", response_model=NewsResponse)
def get_news(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    company: Optional[str] = Query(default=None),
    sentiment: Optional[str] = Query(default=None),
    query: Optional[str] = Query(default=None)
):
    articles, total, is_demo = news_service.query_articles(
        query=query, company=company, sentiment=sentiment, page=page, page_size=page_size
    )
    return NewsResponse(
        articles=articles,
        total_count=total,
        page=page,
        page_size=page_size,
        is_demo_dataset=is_demo
    )

@app.post("/api/news/search", response_model=NewsResponse)
def search_news(req: NewsSearchRequest):
    articles, total, is_demo = news_service.query_articles(
        query=req.query, company=req.company, sentiment=req.sentiment, page=req.page, page_size=req.page_size
    )
    return NewsResponse(
        articles=articles,
        total_count=total,
        page=req.page,
        page_size=req.page_size,
        is_demo_dataset=is_demo
    )

@app.post("/api/news/refresh")
def refresh_news():
    """Forces fresh retrieval and updates alerts & history."""
    articles = news_service.fetch_articles(force_refresh=True)
    new_alerts = alert_service.evaluate_and_generate_alerts(articles)
    return {
        "message": "News refreshed and analyzed successfully.",
        "articles_count": len(articles),
        "new_alerts_count": len(new_alerts),
        "is_demo_dataset": any(a.get("is_demo") for a in articles)
    }

@app.post("/api/analyze", response_model=SentimentAnalysisResult)
def analyze_headline(req: AnalyzeRequest):
    """Analyzes a single headline using local ProsusAI/finbert with token perturbation explanation."""
    cleaned_text = assert_valid_financial_headline(req.text)
    try:
        result = finbert_service.predict_one(cleaned_text, include_explanation=True, validate_input=False)
        # Persist analysis result into database
        db.insert_one("sentiment_results", {
            "text": result["text"],
            "sentiment": result["sentiment"],
            "confidence": result["confidence"],
            "scores": result["scores"],
            "model_name": result["model_name"],
            "analyzed_at": result["analyzed_at"]
        })
        return result
    except (HeadlineValidationError, FinancialValidationError):
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Inference error: {e}")
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")

@app.post("/api/analyze/batch", response_model=List[SentimentAnalysisResult])
def analyze_headlines_batch(req: BatchAnalyzeRequest):
    """Batch sentiment classification using ProsusAI/finbert."""
    if not req.texts:
        raise HeadlineValidationError("Input texts list cannot be empty.", "HEADLINE_EMPTY")
    # Validates all headlines in the batch before invoking model inference
    for text in req.texts:
        assert_valid_financial_headline(text)
    try:
        results = finbert_service.predict_batch(req.texts, validate_input=False)
        return results
    except (HeadlineValidationError, FinancialValidationError):
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch inference failed: {str(e)}")

@app.get("/api/companies", response_model=List[CompanySentimentSummary])
def get_companies():
    """Lists all monitored companies with sentiment statistics and conflict indicators."""
    articles = news_service.fetch_articles()
    conflicts = {c["company"]: True for c in conflict_service.detect_conflicts(articles)}

    company_stats = {}
    for company_name, kws in SUPPORTED_COMPANIES.items():
        ticker = kws[0]
        sector = sector_service.get_sector_for_company(company_name)
        comp_arts = [a for a in articles if a.get("company") == company_name and not a.get("is_duplicate")]
        total = len(comp_arts)

        pos = sum(1 for a in comp_arts if (a.get("sentiment") or "").lower() == "positive")
        neg = sum(1 for a in comp_arts if (a.get("sentiment") or "").lower() == "negative")
        neu = sum(1 for a in comp_arts if (a.get("sentiment") or "").lower() == "neutral")

        pos_pct = round((pos / total * 100), 1) if total > 0 else 0.0
        neg_pct = round((neg / total * 100), 1) if total > 0 else 0.0
        neu_pct = round((neu / total * 100), 1) if total > 0 else 0.0
        
        confidences = [a.get("confidence", 0.5) for a in comp_arts if a.get("confidence")]
        avg_conf = round(sum(confidences) / len(confidences), 3) if confidences else 0.0
        latest_headline = comp_arts[0].get("title") if comp_arts else None

        company_stats[company_name] = CompanySentimentSummary(
            company=company_name,
            ticker=ticker,
            sector=sector,
            total_articles=total,
            positive_count=pos,
            negative_count=neg,
            neutral_count=neu,
            positive_pct=pos_pct,
            negative_pct=neg_pct,
            neutral_pct=neu_pct,
            average_confidence=avg_conf,
            has_conflict=conflicts.get(company_name, False),
            latest_headline=latest_headline
        )

    # Sort by total articles descending
    return sorted(list(company_stats.values()), key=lambda x: x.total_articles, reverse=True)

@app.get("/api/companies/{company}/sentiment")
def get_company_sentiment_detail(company: str = Path(...)):
    """Detailed view for an individual company including headlines, timeline, and conflict score."""
    articles = news_service.fetch_articles()
    target_comp = canonicalize_company(company) or company
    comp_arts = [
        a for a in articles
        if (canonicalize_company(a.get("company")) or a.get("company", "")).lower() == target_comp.lower()
    ]

    if not comp_arts:
        # Check partial match
        comp_arts = [a for a in articles if target_comp.lower() in a.get("company", "").lower()]

    clean_arts = [a for a in comp_arts if not a.get("is_duplicate")]
    total = len(clean_arts)

    pos = sum(1 for a in clean_arts if (a.get("sentiment") or "").lower() == "positive")
    neg = sum(1 for a in clean_arts if (a.get("sentiment") or "").lower() == "negative")
    neu = total - (pos + neg)

    conflicts = conflict_service.detect_conflicts(comp_arts)
    active_conflict = conflicts[0] if conflicts else None

    # History timeline records
    history = db.find("sentiment_history", {"company": company}, limit=10)
    history.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    return {
        "company": company,
        "total_articles": total,
        "articles": clean_arts,
        "positive_count": pos,
        "negative_count": neg,
        "neutral_count": neu,
        "positive_pct": round((pos / total * 100), 1) if total > 0 else 0.0,
        "negative_pct": round((neg / total * 100), 1) if total > 0 else 0.0,
        "neutral_pct": round((neu / total * 100), 1) if total > 0 else 0.0,
        "conflict": active_conflict,
        "history": history
    }

@app.get("/api/sentiment/history")
def get_sentiment_history(company: Optional[str] = Query(default=None)):
    """Returns stored historical sentiment progression."""
    query = {"company": company} if company and company.lower() != "all" else None
    history = db.find("sentiment_history", query, limit=50)
    history.sort(key=lambda x: x.get("timestamp", ""))
    return history

@app.get("/api/sentiment/sectors", response_model=List[SectorSentiment])
def get_sector_sentiments():
    """Returns the market sector heatmap aggregations."""
    articles = news_service.fetch_articles()
    return sector_service.calculate_sector_heatmaps(articles)

@app.get("/api/conflicts", response_model=List[ConflictSignal])
def get_conflicts():
    """Returns all companies currently exhibiting Bullish/Bearish sentiment divergence."""
    articles = news_service.fetch_articles()
    return conflict_service.detect_conflicts(articles)

@app.get("/api/alerts", response_model=List[AlertRecord])
def get_alerts(unread_only: bool = Query(default=False)):
    """Returns risk alerts triggered by sentiment swings or conflict spikes."""
    return alert_service.get_alerts(unread_only=unread_only)

@app.patch("/api/alerts/{alert_id}")
def mark_alert_read(alert_id: str = Path(...)):
    """Marks an alert record as read."""
    success = alert_service.mark_as_read(alert_id)
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found.")
    return {"message": "Alert marked as read.", "alert_id": alert_id}

@app.get("/api/data-quality", response_model=DataQualityReport)
def get_data_quality():
    """Returns rigorous operational metrics on data integrity, duplicates, confidence, and provider status."""
    all_articles = db.find("news_articles", limit=500)
    if not all_articles:
        all_articles = news_service.fetch_articles()

    total = len(all_articles)
    missing_headlines = sum(1 for a in all_articles if not (a.get("title") or "").strip())
    missing_sources = sum(1 for a in all_articles if not (a.get("source") or "").strip() or a.get("source") == "Unknown Source")
    invalid_urls = sum(1 for a in all_articles if not (a.get("url") or "").startswith("http"))
    
    dup_count = sum(1 for a in all_articles if a.get("is_duplicate"))
    dup_rate = round((dup_count / total * 100), 2) if total > 0 else 0.0

    low_conf_count = sum(1 for a in all_articles if a.get("confidence") is not None and a.get("confidence") < 0.60)
    low_conf_rate = round((low_conf_count / total * 100), 2) if total > 0 else 0.0

    # Stale articles (> 7 days old)
    cutoff = datetime.utcnow() - timedelta(days=7)
    stale_count = 0
    for a in all_articles:
        pub = a.get("published_at")
        if pub:
            try:
                dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
                if dt.replace(tzinfo=None) < cutoff:
                    stale_count += 1
            except Exception:
                pass

    return DataQualityReport(
        total_articles=total,
        missing_headlines=missing_headlines,
        missing_sources=missing_sources,
        invalid_urls=invalid_urls,
        duplicate_count=dup_count,
        duplicate_rate=dup_rate,
        low_confidence_count=low_conf_count,
        low_confidence_rate=low_conf_rate,
        stale_articles_count=stale_count,
        model_status="ready" if finbert_service.is_ready() else finbert_service.status,
        engine_mode=finbert_service.engine_mode,
        news_api_status=news_service.news_api_status,
        database_status=db.get_status()
    )

@app.post("/api/assistant/chat", response_model=AssistantChatResponse)
def assistant_chat(req: AssistantChatRequest):
    """Conversational Financial News Assistant grounded in stored sentiment data."""
    result = gemini_assistant_service.answer_query(req.message, req.company_focus)
    return AssistantChatResponse(**result)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", getattr(settings, "PORT", 8000)))
    logger.info(f"Starting server on 0.0.0.0:{port} (workers=1)...")
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, workers=1)

