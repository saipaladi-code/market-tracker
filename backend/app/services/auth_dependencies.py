import os
import logging
from typing import Optional, Dict, Any
from fastapi import Request, Response, HTTPException, status, Depends
from app.config import settings
from app.database import db
from app.services.auth_service import auth_service

logger = logging.getLogger("auth_dep")

def is_production_env() -> bool:
    """Returns True if running in Render/Cloud or production domain."""
    if os.getenv("RENDER") or os.getenv("VERCEL"):
        return True
    origin = settings.FRONTEND_ORIGIN.lower()
    return not ("localhost" in origin or "127.0.0.1" in origin)

def resolve_cookie_settings() -> Dict[str, Any]:
    """
    Computes secure cookie attributes.
    In production (cross-site Vercel to Render), SameSite must be None and Secure must be True.
    In local development (HTTP localhost:5173 to localhost:8000), SameSite is Lax and Secure is False.
    """
    is_prod = is_production_env()
    
    if settings.COOKIE_SECURE is not None:
        secure = settings.COOKIE_SECURE
    else:
        secure = True if is_prod else False

    if settings.COOKIE_SAMESITE is not None:
        samesite = settings.COOKIE_SAMESITE.lower()
    else:
        samesite = "none" if is_prod else "lax"

    return {
        "secure": secure,
        "samesite": samesite
    }

def set_auth_cookie(response: Response, token: str, remember_me: bool = False):
    cookie_cfg = resolve_cookie_settings()
    max_age = (
        settings.REMEMBER_ME_EXPIRE_MINUTES * 60
        if remember_me
        else settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=token,
        max_age=max_age,
        expires=max_age,
        httponly=True,
        secure=cookie_cfg["secure"],
        samesite=cookie_cfg["samesite"],
        path="/"
    )

def clear_auth_cookie(response: Response):
    cookie_cfg = resolve_cookie_settings()
    response.delete_cookie(
        key=settings.COOKIE_NAME,
        path="/",
        secure=cookie_cfg["secure"],
        samesite=cookie_cfg["samesite"],
        httponly=True
    )

async def get_current_user(request: Request) -> Dict[str, Any]:
    """
    FastAPI dependency that enforces authentication.
    Inspects HttpOnly cookie first, then Authorization: Bearer <token> header.
    Rejects missing, expired, or invalid sessions with HTTP 401.
    """
    token: Optional[str] = request.cookies.get(settings.COOKIE_NAME)

    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in to access this resource."
        )

    payload = auth_service.decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid credentials. Please sign in again."
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session token payload."
        )

    user = db.find_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account associated with this session no longer exists."
        )

    return {
        "id": str(user.get("id") or user.get("_id")),
        "email": user.get("email"),
        "full_name": user.get("full_name", "Financial Analyst"),
        "created_at": user.get("created_at")
    }

async def get_optional_current_user(request: Request) -> Optional[Dict[str, Any]]:
    try:
        return await get_current_user(request)
    except HTTPException:
        return None
