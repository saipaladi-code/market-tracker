import os
import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Query, Path, Request, Response, Depends, BackgroundTasks
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
from app.models.auth_models import (
    UserRegisterRequest, UserLoginRequest, ForgotPasswordRequest,
    ResetPasswordRequest, UserResponse, AuthResponse,
    ForgotPasswordResponse, MessageResponse
)
from app.services.auth_service import auth_service
from app.services.auth_dependencies import (
    get_current_user, set_auth_cookie, clear_auth_cookie
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
from app.models.metals_models import (
    MetalsNewsResponse, MetalsPricesResponse,
    MetalsSentimentSummary, MetalsHistoryResponse,
    TranslateRequest, TranslateResponse
)
from app.services.metals_service import metals_service
from app.services.translation_service import translation_service
from app.models.trading_models import (
    CompanyTradingRoute, SupportedInstrumentsResponse, BrokerCapabilitiesResponse
)
from app.services.broker_routing_service import broker_routing_service

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

    try:
        logger.info("Pre-warming live news cache in background...")
        articles = news_service.fetch_articles()
        logger.info(f"News cache pre-warmed: {len(articles)} articles available (Status: {news_service.get_feed_status()}).")
    except Exception as e:
        logger.error(f"Error pre-warming news cache: {e}")

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
            "has_key": bool(settings.NEWS_API_KEY),
            "feed_status": news_service.get_feed_status(),
            "provider": getattr(settings, "NEWS_PROVIDER", "auto"),
            "last_synced": news_service.get_last_synced_iso()
        },
        "gemini_assistant": {
            "active": gemini_assistant_service.is_active,
            "has_key": bool(settings.GEMINI_API_KEY)
        }
    }


# ==============================================================================
# AUTHENTICATION & SESSION ENDPOINTS
# ==============================================================================

@app.post("/api/auth/register", response_model=AuthResponse)
def register_user(req: UserRegisterRequest, response: Response):
    """Creates a new authenticated user account and issues session credentials."""
    res = auth_service.register_user(req.full_name, req.email, req.password)
    set_auth_cookie(response, res["token"], remember_me=False)
    return res

@app.post("/api/auth/login", response_model=AuthResponse)
def login_user(req: UserLoginRequest, request: Request, response: Response):
    """Validates user credentials, rate-limits brute force, and initiates session."""
    client_ip = request.client.host if request.client else "unknown"
    res = auth_service.login_user(req.email, req.password, remember_me=req.remember_me, client_ip=client_ip)
    set_auth_cookie(response, res["token"], remember_me=req.remember_me)
    return res

@app.get("/api/auth/me", response_model=UserResponse)
def get_current_user_profile(current_user: dict = Depends(get_current_user)):
    """Returns profile for currently authenticated user session."""
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        full_name=current_user.get("full_name", "Financial Analyst"),
        created_at=current_user.get("created_at")
    )

@app.post("/api/auth/logout", response_model=MessageResponse)
def logout_user(response: Response):
    """Terminates session and clears HttpOnly authentication cookie."""
    clear_auth_cookie(response)
    return {"message": "Logged out successfully.", "status": "success"}

@app.post("/api/auth/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(req: ForgotPasswordRequest, request: Request):
    """Initiates single-use expiring password recovery flow."""
    client_ip = request.client.host if request.client else "unknown"
    return auth_service.request_password_reset(req.email, client_ip=client_ip)

@app.post("/api/auth/reset-password", response_model=MessageResponse)
def reset_password(req: ResetPasswordRequest):
    """Verifies single-use token and establishes updated password."""
    return auth_service.reset_password(req.token, req.new_password)

@app.post("/api/auth/demo", response_model=AuthResponse)
def demo_login(response: Response):
    """Provides instant 1-click evaluation access for analysts and recruiters."""
    demo_email = "demo.analyst@finsentiment.ai"
    user = db.find_user_by_email(demo_email)
    if not user:
        try:
            res = auth_service.register_user(
                full_name="Lead Market Analyst",
                email=demo_email,
                password="DemoPassword123!"
            )
            set_auth_cookie(response, res["token"], remember_me=True)
            return res
        except Exception:
            pass
    res = auth_service.login_user(demo_email, "DemoPassword123!", remember_me=True)
    set_auth_cookie(response, res["token"], remember_me=True)
    return res


# ==============================================================================
# PROTECTED ANALYTICS & MARKET INTELLIGENCE ENDPOINTS
# ==============================================================================

@app.get("/api/dashboard/stats")
def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
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
        "feed_status": news_service.get_feed_status(),
        "last_updated": news_service.get_last_synced_iso(),
        "model_status": "ready" if finbert_service.is_ready() else finbert_service.status
    }

@app.get("/api/news", response_model=NewsResponse)
def get_news(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    company: Optional[str] = Query(default=None),
    sentiment: Optional[str] = Query(default=None),
    query: Optional[str] = Query(default=None),
    today_only: Optional[bool] = Query(default=None),
    date: Optional[str] = Query(default=None),
    current_user: dict = Depends(get_current_user)
):
    articles, total, is_demo, feed_status, last_synced, filter_date, provider = news_service.query_articles(
        query=query, company=company, sentiment=sentiment, page=page, page_size=page_size,
        today_only=today_only, date=date
    )
    return NewsResponse(
        articles=articles,
        total_count=total,
        page=page,
        page_size=page_size,
        is_demo_dataset=is_demo,
        feed_status=feed_status,
        last_synced=last_synced,
        filter_date=filter_date,
        news_provider=provider
    )

@app.post("/api/news/search", response_model=NewsResponse)
def search_news(req: NewsSearchRequest, current_user: dict = Depends(get_current_user)):
    articles, total, is_demo, feed_status, last_synced, filter_date, provider = news_service.query_articles(
        query=req.query, company=req.company, sentiment=req.sentiment, page=req.page, page_size=req.page_size,
        today_only=req.today_only, date=req.date
    )
    return NewsResponse(
        articles=articles,
        total_count=total,
        page=req.page,
        page_size=req.page_size,
        is_demo_dataset=is_demo,
        feed_status=feed_status,
        last_synced=last_synced,
        filter_date=filter_date,
        news_provider=provider
    )

@app.api_route("/api/news/refresh", methods=["GET", "POST"])
def refresh_news(background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    """Triggers live ingestion in background to avoid gateway timeouts, and returns current articles."""
    articles = news_service.fetch_articles(force_refresh=False)
    background_tasks.add_task(news_service.ingest_live_news, force=True)
    new_alerts = alert_service.evaluate_and_generate_alerts(articles)
    return {
        "message": "News refresh initiated and live feed synchronized.",
        "articles_count": len(articles),
        "new_alerts_count": len(new_alerts),
        "is_demo_dataset": any(a.get("is_demo") for a in articles) if articles else bool(settings.USE_DEMO_DATA),
        "feed_status": news_service.get_feed_status(),
        "last_synced": news_service.get_last_synced_iso()
    }

@app.get("/api/news/{article_id}/explain", response_model=SentimentAnalysisResult)
def explain_article(article_id: str, current_user: dict = Depends(get_current_user)):
    """
    Returns the canonical sentiment inference result and token perturbation explanation for a specific article.
    Preserves the article's canonical prediction and confidence without recalculating overall sentiment.
    """
    article = db.find_one("news_articles", {"id": article_id})
    if not article:
        article = db.find_one("news_articles", {"canonical_id": article_id})

    if not article:
        raise HTTPException(status_code=404, detail=f"Article '{article_id}' not found.")

    sentiment = article.get("sentiment") or "neutral"
    confidence = float(article.get("confidence", 0.70))
    raw_scores = article.get("scores") or {}
    scores = {
        "positive": float(raw_scores.get("positive", confidence if sentiment == "positive" else 0.15)),
        "negative": float(raw_scores.get("negative", confidence if sentiment == "negative" else 0.15)),
        "neutral": float(raw_scores.get("neutral", confidence if sentiment == "neutral" else 0.70)),
    }

    tokens = article.get("tokens") or []
    explanation_note = article.get("explanation_note") or ""

    if not tokens:
        try:
            explanation = finbert_service.predict_one(
                article["title"],
                include_explanation=True,
                validate_input=False
            )
            tokens = explanation.get("tokens", [])
            explanation_note = explanation.get("explanation_note", "")
            # Cache computed tokens back to article
            db.update_one("news_articles", {"id": article["id"]}, {
                "tokens": tokens,
                "explanation_note": explanation_note
            })
        except Exception as e:
            logger.warning(f"Failed to generate explanation for article {article_id}: {e}")
            tokens = []
            explanation_note = "Attribution explanation temporarily unavailable."

    return {
        "article_id": article["id"],
        "text": article["title"],
        "sentiment": sentiment,
        "confidence": confidence,
        "scores": scores,
        "model_name": article.get("model_name") or ("ProsusAI/finbert (Offline Lexicon)" if article.get("is_fallback") else "ProsusAI/finbert"),
        "analyzed_at": article.get("published_at") or (datetime.utcnow().isoformat() + "Z"),
        "tokens": tokens,
        "explanation_note": explanation_note or "FinBERT token attribution explanation.",
        "is_fallback": bool(article.get("is_fallback", False)),
        "engine_mode": article.get("engine_mode")
    }

@app.post("/api/analyze", response_model=SentimentAnalysisResult)
def analyze_headline(req: AnalyzeRequest, current_user: dict = Depends(get_current_user)):
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
def analyze_headlines_batch(req: BatchAnalyzeRequest, current_user: dict = Depends(get_current_user)):
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
def get_companies(current_user: dict = Depends(get_current_user)):
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
def get_company_sentiment_detail(company: str = Path(...), current_user: dict = Depends(get_current_user)):
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
def get_sentiment_history(company: Optional[str] = Query(default=None), current_user: dict = Depends(get_current_user)):
    """Returns stored historical sentiment progression."""
    query = {"company": company} if company and company.lower() != "all" else None
    history = db.find("sentiment_history", query, limit=50)
    history.sort(key=lambda x: x.get("timestamp", ""))
    return history

@app.get("/api/sentiment/sectors", response_model=List[SectorSentiment])
def get_sector_sentiments(current_user: dict = Depends(get_current_user)):
    """Returns the market sector heatmap aggregations."""
    articles = news_service.fetch_articles()
    return sector_service.calculate_sector_heatmaps(articles)

@app.get("/api/conflicts", response_model=List[ConflictSignal])
def get_conflicts(current_user: dict = Depends(get_current_user)):
    """Returns all companies currently exhibiting Bullish/Bearish sentiment divergence."""
    articles = news_service.fetch_articles()
    return conflict_service.detect_conflicts(articles)

@app.get("/api/alerts", response_model=List[AlertRecord])
def get_alerts(unread_only: bool = Query(default=False), current_user: dict = Depends(get_current_user)):
    """Returns risk alerts triggered by sentiment swings or conflict spikes."""
    return alert_service.get_alerts(unread_only=unread_only)

@app.patch("/api/alerts/{alert_id}")
def mark_alert_read(alert_id: str = Path(...), current_user: dict = Depends(get_current_user)):
    """Marks an alert record as read."""
    success = alert_service.mark_as_read(alert_id)
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found.")
    return {"message": "Alert marked as read.", "alert_id": alert_id}

@app.get("/api/data-quality", response_model=DataQualityReport)
def get_data_quality(current_user: dict = Depends(get_current_user)):
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
def assistant_chat(req: AssistantChatRequest, current_user: dict = Depends(get_current_user)):
    """Conversational Financial News Assistant grounded in stored sentiment data."""
    result = gemini_assistant_service.answer_query(req.message, req.company_focus)
    return AssistantChatResponse(**result)



# -------------------------------------------------------------
# GOLD & SILVER MARKET INTELLIGENCE ENDPOINTS
# -------------------------------------------------------------
@app.get("/api/metals/news", response_model=MetalsNewsResponse)
def get_metals_news(
    metal: Optional[str] = Query(None, description="Filter metal: Gold, Silver, Both, or All"),
    category: Optional[str] = Query(None, description="Filter category: India, Global Markets, Investment Trends, or All"),
    days: int = Query(30, ge=1, le=90, description="Time window in days"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=50, description="Page size"),
    search: Optional[str] = Query(None, description="Search term in headline or summary")
):
    """Retrieves genuine precious metals news with FinBERT sentiment classifications."""
    return metals_service.get_news(
        metal=metal,
        category=category,
        days=days,
        page=page,
        page_size=page_size,
        search=search
    )

@app.get("/api/metals/prices", response_model=MetalsPricesResponse)
def get_metals_prices():
    """Retrieves COMEX International Futures quotes and Indian Domestic Benchmark prices."""
    return metals_service.get_market_prices()

@app.get("/api/metals/sentiment", response_model=MetalsSentimentSummary)
def get_metals_sentiment_summary(
    days: int = Query(30, ge=1, le=90, description="Days to summarize")
):
    """Returns aggregated FinBERT sentiment distribution and comparison for Gold vs Silver."""
    return metals_service.get_sentiment_summary(days=days)

@app.get("/api/metals/history", response_model=MetalsHistoryResponse)
def get_metals_history(
    days: int = Query(14, ge=7, le=60, description="Historical timeline days")
):
    """Returns daily sentiment timeline data points for Precious Metals."""
    return metals_service.get_historical_trends(days=days)

# -------------------------------------------------------------
# MULTILINGUAL TRANSLATION ENDPOINTS
# -------------------------------------------------------------
@app.post("/api/translate", response_model=TranslateResponse)
def translate_content(req: TranslateRequest):
    """Translates financial news headlines and explanations with caching."""
    res = translation_service.translate_text(
        text=req.text,
        target_lang=req.target_lang,
        article_id=req.article_id
    )
    return TranslateResponse(**res)

@app.get("/api/translate/languages")
def get_translation_languages():
    """Returns all supported languages with native names and text directions."""
    return translation_service.get_supported_languages()



# -------------------------------------------------------------
# BROKER TRADING ROUTING ENDPOINTS
# -------------------------------------------------------------
@app.get("/api/trading/route", response_model=CompanyTradingRoute)
def get_trading_route(
    company: Optional[str] = Query(None, description="Company name or alias"),
    ticker: Optional[str] = Query(None, description="Stock ticker symbol")
):
    """
    Resolves company/ticker to verified instrument and provides authorized broker destination:
    Upstox for Indian equities (NSE/BSE), Interactive Brokers (IBKR) for US equities (NASDAQ/NYSE).
    """
    return broker_routing_service.get_trading_route_by_identifiers(company=company, ticker=ticker)

@app.get("/api/trading/supported-instruments", response_model=SupportedInstrumentsResponse)
def get_supported_instruments():
    """Lists all verified Indian and international tradable instruments with official coverage."""
    return broker_routing_service.get_all_supported_instruments()

@app.get("/api/trading/brokers", response_model=BrokerCapabilitiesResponse)
def get_broker_capabilities():
    """Returns official broker partner capabilities, market coverage, and compliance statements."""
    return broker_routing_service.get_broker_capabilities()

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", getattr(settings, "PORT", 8000)))
    logger.info(f"Starting server on 0.0.0.0:{port} (workers=1)...")
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, workers=1)

