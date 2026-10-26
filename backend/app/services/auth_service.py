import os
import re
import secrets
import hashlib
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
import bcrypt
import jwt
from fastapi import HTTPException, status
from app.config import settings
from app.database import db
from app.services.rate_limiter import auth_rate_limiter

logger = logging.getLogger("auth")

class AuthService:
    def __init__(self):
        pass

    # 1. Password Hashing & Verification
    def hash_password(self, password: str) -> str:
        """Securely hashes plaintext password with bcrypt cost factor 12."""
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verifies password using constant-time comparison in bcrypt."""
        try:
            return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
        except Exception as e:
            logger.warning(f"Password verification comparison error: {e}")
            return False

    def validate_password_strength(self, password: str) -> Tuple[bool, Optional[str]]:
        """
        Enforces professional security standards:
        - Minimum 8 characters
        - At least one uppercase character
        - At least one lowercase character
        - At least one numeric digit
        """
        if len(password) < 8:
            return False, "Password must contain at least 8 characters."
        if not re.search(r"[A-Z]", password):
            return False, "Password must include at least one uppercase letter (A-Z)."
        if not re.search(r"[a-z]", password):
            return False, "Password must include at least one lowercase letter (a-z)."
        if not re.search(r"\d", password):
            return False, "Password must include at least one numeric digit (0-9)."
        return True, None

    # 2. Token / Session Management
    def create_access_token(self, user_id: str, email: str, expires_delta: Optional[timedelta] = None) -> Tuple[str, int]:
        now = datetime.utcnow()
        if expires_delta:
            expire = now + expires_delta
        else:
            expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

        expires_in = int((expire - now).total_seconds())
        payload = {
            "sub": str(user_id),
            "email": email.strip().lower(),
            "exp": expire,
            "iat": now,
            "type": "access"
        }
        token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        return token, expires_in

    def decode_access_token(self, token: str) -> Optional[Dict[str, Any]]:
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            logger.info("Access token expired.")
            return None
        except jwt.PyJWTError as e:
            logger.info(f"Invalid access token: {e}")
            return None

    # 3. User Registration Flow
    def register_user(self, full_name: str, email: str, password: str) -> Dict[str, Any]:
        normalized_email = email.strip().lower()

        # Enforce persistent storage validation
        if not db.is_storage_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Persistent storage is currently unavailable. Account registration cannot proceed."
            )

        # Enforce password strength
        is_strong, err_msg = self.validate_password_strength(password)
        if not is_strong:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=err_msg)

        # Check existing account
        existing_user = db.find_user_by_email(normalized_email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email address already exists. Please sign in or reset your password."
            )

        # Hash password and persist
        hashed = self.hash_password(password)
        now_iso = datetime.utcnow().isoformat() + "Z"
        user_doc = {
            "full_name": full_name.strip(),
            "email": normalized_email,
            "password_hash": hashed,
            "created_at": now_iso,
            "last_login": now_iso
        }

        try:
            user_id = db.insert_user(user_doc)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
        except Exception as e:
            logger.error(f"User registration persistence failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database storage failure occurred during user creation."
            )

        token, expires_in = self.create_access_token(user_id, normalized_email)
        return {
            "user": {
                "id": user_id,
                "email": normalized_email,
                "full_name": full_name.strip(),
                "created_at": now_iso
            },
            "token": token,
            "expires_in": expires_in,
            "message": "Account created successfully."
        }

    # 4. User Login Flow
    def login_user(self, email: str, password: str, remember_me: bool = False, client_ip: str = "unknown") -> Dict[str, Any]:
        normalized_email = email.strip().lower()

        # Brute-force protection: max 5 failed attempts per 5 minutes per IP/email
        rate_key_ip = f"login_ip:{client_ip}"
        rate_key_email = f"login_email:{normalized_email}"
        auth_rate_limiter.check_rate_limit(rate_key_ip, max_attempts=5, window_seconds=300, action_name="login")
        auth_rate_limiter.check_rate_limit(rate_key_email, max_attempts=5, window_seconds=300, action_name="login")

        user = db.find_user_by_email(normalized_email)
        if not user or not self.verify_password(password, user.get("password_hash", "")):
            auth_rate_limiter.record_attempt(rate_key_ip)
            auth_rate_limiter.record_attempt(rate_key_email)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password. Please verify your credentials and try again."
            )

        # Successful login: reset rate limit attempts
        auth_rate_limiter.reset_key(rate_key_ip)
        auth_rate_limiter.reset_key(rate_key_email)

        # Session duration: 30 days if remember_me, else 24 hours
        exp_delta = timedelta(minutes=settings.REMEMBER_ME_EXPIRE_MINUTES if remember_me else settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        user_id = user.get("id") or user.get("_id")
        token, expires_in = self.create_access_token(str(user_id), normalized_email, expires_delta=exp_delta)

        # Update last login
        now_iso = datetime.utcnow().isoformat() + "Z"
        db.update_one("users", {"email": normalized_email}, {"last_login": now_iso})

        return {
            "user": {
                "id": str(user_id),
                "email": normalized_email,
                "full_name": user.get("full_name", "Financial Analyst"),
                "created_at": user.get("created_at")
            },
            "token": token,
            "expires_in": expires_in,
            "remember_me": remember_me,
            "message": "Signed in successfully."
        }

    # 5. Password Reset Flow
    def request_password_reset(self, email: str, client_ip: str = "unknown") -> Dict[str, Any]:
        normalized_email = email.strip().lower()

        # Rate limit password reset requests: max 3 per 10 minutes
        rate_key = f"pwd_reset:{client_ip}:{normalized_email}"
        auth_rate_limiter.check_rate_limit(rate_key, max_attempts=3, window_seconds=600, action_name="password reset")
        auth_rate_limiter.record_attempt(rate_key)

        user = db.find_user_by_email(normalized_email)
        smtp_configured = bool(settings.SMTP_HOST)

        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        expires_at = datetime.utcnow() + timedelta(minutes=15)

        # Only create a reset record if user actually exists
        if user:
            reset_doc = {
                "token_hash": token_hash,
                "user_id": user.get("id") or user.get("_id"),
                "email": normalized_email,
                "expires_at": expires_at.isoformat() + "Z",
                "used": False,
                "created_at": datetime.utcnow().isoformat() + "Z"
            }
            db.insert_one("password_resets", reset_doc)

            # Attempt dispatch via SMTP if configured
            if smtp_configured:
                self._dispatch_reset_email(normalized_email, raw_token)

        # If SMTP is not configured, communicate status honestly
        if not smtp_configured:
            logger.info("SMTP email delivery is not configured on this server.")
            # For development / testing convenience, provide token only in non-production
            is_dev = not os.getenv("RENDER") and "localhost" in settings.FRONTEND_ORIGIN
            return {
                "message": "Password recovery requested. Note: SMTP email service is currently not configured on this backend server. Contact the system administrator or configure SMTP_HOST in backend environment variables.",
                "status": "smtp_unconfigured",
                "smtp_configured": False,
                "dev_reset_token": raw_token if (is_dev and user) else None
            }

        return {
            "message": "If an account with this email address exists, password reset instructions have been dispatched. Please check your inbox.",
            "status": "dispatched",
            "smtp_configured": True,
            "dev_reset_token": None
        }

    def reset_password(self, raw_token: str, new_password: str) -> Dict[str, Any]:
        """
        Verifies single-use, unexpired password reset token and updates user password.
        """
        is_strong, err_msg = self.validate_password_strength(new_password)
        if not is_strong:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=err_msg)

        token_hash = hashlib.sha256(raw_token.strip().encode("utf-8")).hexdigest()
        record = db.find_one("password_resets", {"token_hash": token_hash})

        if not record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid password reset token. Please request a new link."
            )

        if record.get("used"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This password reset token has already been used. Please request a new link."
            )

        # Check expiration
        try:
            exp_str = record.get("expires_at", "")
            exp_dt = datetime.fromisoformat(exp_str.replace("Z", "+00:00")).replace(tzinfo=None)
            if datetime.utcnow() > exp_dt:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="This password reset token has expired (valid for 15 minutes). Please request a new link."
                )
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Corrupted reset token expiration.")

        user_id = record.get("user_id")
        user = db.find_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account associated with this token not found.")

        # Update user's password with fresh bcrypt hash
        new_hashed = self.hash_password(new_password)
        db.update_user_password(user_id, new_hashed)

        # Mark token as single-use consumed
        db.update_one("password_resets", {"token_hash": token_hash}, {
            "used": True,
            "used_at": datetime.utcnow().isoformat() + "Z"
        })

        logger.info(f"Password successfully reset for user {user.get('email')}.")
        return {
            "message": "Password updated successfully. You may now sign in with your new password.",
            "status": "success"
        }

    def _dispatch_reset_email(self, to_email: str, raw_token: str):
        """Sends an HTML password recovery email via configured SMTP relay."""
        if not settings.SMTP_HOST:
            return
        try:
            reset_url = f"{settings.FRONTEND_ORIGIN.rstrip('/')}/reset-password?token={raw_token}"
            msg = MIMEMultipart("alternative")
            msg["Subject"] = "FIN-SENTIMENT — Password Reset Request"
            msg["From"] = settings.SMTP_FROM_EMAIL or f"FIN-SENTIMENT Security <noreply@{settings.SMTP_HOST}>"
            msg["To"] = to_email

            text_content = f"FIN-SENTIMENT Password Reset\n\nYou requested a password reset for your FIN-SENTIMENT account.\nUse the link below to set a new password:\n{reset_url}\n\nThis single-use link expires in 15 minutes.\nIf you did not request this, please ignore this email."
            html_content = f"""
            <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #070b14; color: #f8fafc; padding: 32px 16px;">
                <div style="max-width: 520px; margin: 0 auto; background-color: #0f172a; border: 1px solid #1c2b4a; border-radius: 16px; padding: 32px;">
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 24px;">
                        <span style="font-size: 18px; font-weight: 800; color: #ffffff; letter-spacing: 0.05em;">FIN-SENTIMENT</span>
                        <span style="background: rgba(59,130,246,0.2); color: #60a5fa; border: 1px solid rgba(59,130,246,0.3); font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 4px;">SECURITY</span>
                    </div>
                    <h2 style="font-size: 20px; font-weight: 700; color: #ffffff; margin-top: 0;">Password Reset Request</h2>
                    <p style="color: #94a3b8; font-size: 14px; line-height: 1.6;">You recently requested to reset the password for your FIN-SENTIMENT intelligence terminal account. Click the button below to establish a new password.</p>
                    <div style="margin: 28px 0; text-align: center;">
                        <a href="{reset_url}" style="display: inline-block; background: linear-gradient(135deg, #2563eb, #06b6d4); color: #ffffff; font-weight: 600; font-size: 14px; text-decoration: none; padding: 12px 28px; border-radius: 8px;">Reset Password</a>
                    </div>
                    <p style="color: #64748b; font-size: 12px; line-height: 1.5;">This single-use token will expire in <strong>15 minutes</strong>. If you did not make this request, you can safely ignore this email.</p>
                </div>
            </div>
            """
            msg.attach(MIMEText(text_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                if settings.SMTP_TLS:
                    server.starttls()
                if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.send_message(msg)
            logger.info(f"Password reset email sent to {to_email}.")
        except Exception as e:
            logger.error(f"Failed to send password reset email via SMTP: {e}")

auth_service = AuthService()
