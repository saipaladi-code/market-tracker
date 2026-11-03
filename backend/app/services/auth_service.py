import os
import json
import urllib.request
import re
import secrets
import hashlib
import smtplib
import socket
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
    def get_recovery_base_url(self, request_origin: Optional[str] = None) -> str:
        """
        Determines the public frontend URL for password reset links.
        Ensures recovery links always point to the production Vercel frontend,
        not localhost or an invalid destination.
        """
        configured_url = settings.frontend_url

        # 1. If incoming request has an origin header from Vercel, prioritize it
        if request_origin:
            clean = request_origin.strip().rstrip("/")
            if "market-tracker" in clean or "vercel.app" in clean:
                return clean
            # If in local dev without RENDER environment and request origin is localhost, allow it
            if not os.getenv("RENDER") and ("localhost" in clean or "127.0.0.1" in clean):
                return clean

        # 2. Default to configured production FRONTEND_URL
        return configured_url

    def request_password_reset(
        self,
        email: str,
        client_ip: str = "unknown",
        request_origin: Optional[str] = None
    ) -> Dict[str, Any]:
        normalized_email = email.strip().lower()

        # Rate limit password reset requests: allow 15 attempts per 5 minutes to prevent developer lockout
        rate_key = f"pwd_reset:{client_ip}:{normalized_email}"
        auth_rate_limiter.check_rate_limit(rate_key, max_attempts=15, window_seconds=300, action_name="password reset")
        auth_rate_limiter.record_attempt(rate_key)

        user = db.find_user_by_email(normalized_email)
        is_configured = settings.is_email_service_configured

        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        expires_at = datetime.utcnow() + timedelta(minutes=15)

        base_url = self.get_recovery_base_url(request_origin)

        # 1. Configuration Validation: Check if Resend or SMTP email service is configured
        if not is_configured:
            # If user explicitly configured RESEND_FROM_EMAIL but forgot RESEND_API_KEY
            explicit_from = getattr(settings, "RESEND_FROM_EMAIL", None) or os.getenv("RESEND_FROM_EMAIL")
            if explicit_from and not settings.resend_api_key:
                auth_rate_limiter.reset_key(rate_key)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to send password recovery email: RESEND_API_KEY environment variable is missing on Render. Please configure RESEND_API_KEY in your Render dashboard."
                )

            # In local dev / test environment without RENDER, allow dev token evaluation if neither is configured
            is_dev = not os.getenv("RENDER")
            if is_dev:
                if user:
                    try:
                        db.update_many(
                            "password_resets",
                            {"email": normalized_email, "used": False},
                            {"used": True, "invalidated_at": datetime.utcnow().isoformat() + "Z"}
                        )
                    except Exception:
                        pass
                    reset_doc = {
                        "token_hash": token_hash,
                        "user_id": user.get("id") or user.get("_id"),
                        "email": normalized_email,
                        "expires_at": expires_at.isoformat() + "Z",
                        "used": False,
                        "created_at": datetime.utcnow().isoformat() + "Z"
                    }
                    db.insert_one("password_resets", reset_doc)
                return {
                    "message": "If that email address is registered, you will receive a password reset link shortly.",
                    "status": "email_unconfigured",
                    "smtp_configured": False,
                    "dev_reset_token": raw_token if user else None
                }
            auth_rate_limiter.reset_key(rate_key)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send password recovery email: Outbound email service is not configured on Render. Please configure RESEND_API_KEY and RESEND_FROM_EMAIL in your Render dashboard."
            )

        # 2. If user exists, invalidate previous active tokens and dispatch new recovery email
        if user:
            # Invalidate any previous active tokens for this user account
            try:
                db.update_many(
                    "password_resets",
                    {"email": normalized_email, "used": False},
                    {"used": True, "invalidated_at": datetime.utcnow().isoformat() + "Z"}
                )
            except Exception as e:
                logger.warning(f"Could not invalidate prior reset tokens: {e}")

            reset_doc = {
                "token_hash": token_hash,
                "user_id": user.get("id") or user.get("_id"),
                "email": normalized_email,
                "expires_at": expires_at.isoformat() + "Z",
                "used": False,
                "created_at": datetime.utcnow().isoformat() + "Z"
            }
            db.insert_one("password_resets", reset_doc)

            # Primary: Resend HTTPS API
            if settings.resend_api_key:
                try:
                    self._dispatch_reset_email_resend(normalized_email, raw_token, base_url)
                except Exception as e:
                    auth_rate_limiter.reset_key(rate_key)
                    logger.error(f"[RESEND_DISPATCH_ERROR] Failed to dispatch password recovery email via Resend HTTPS: {e}", exc_info=True)
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Failed to send password recovery email: {str(e)}"
                    )
            elif settings.is_smtp_configured:
                # Secondary legacy SMTP fallback
                try:
                    self._dispatch_reset_email(normalized_email, raw_token, base_url)
                except Exception as e:
                    auth_rate_limiter.reset_key(rate_key)
                    logger.error(f"Failed to dispatch password recovery email via SMTP: {e}", exc_info=True)
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Failed to send password recovery email: {str(e)}"
                    )

        # 3. Always return consistent, generic response to prevent user enumeration
        return {
            "message": "If that email address is registered, you will receive a password reset link shortly.",
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

        # Check expiration (15 minutes)
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
        updated = db.update_user_password(user_id, new_hashed)
        if not updated:
            user_email = user.get("email") or record.get("email")
            if user_email:
                db.update_one(
                    "users",
                    {"email": user_email.strip().lower()},
                    {"password_hash": new_hashed, "updated_at": datetime.utcnow().isoformat() + "Z"}
                )

        # Mark token and any other active tokens for this user as single-use consumed
        db.update_one("password_resets", {"token_hash": token_hash}, {
            "used": True,
            "used_at": datetime.utcnow().isoformat() + "Z"
        })
        try:
            db.update_many("password_resets", {"user_id": user_id, "used": False}, {
                "used": True,
                "invalidated_at": datetime.utcnow().isoformat() + "Z"
            })
        except Exception:
            pass

        logger.info("Password successfully reset for authenticated user.")
        return {
            "message": "Password updated successfully. You may now sign in with your new password.",
            "status": "success"
        }

    def _dispatch_reset_email_resend(self, to_email: str, raw_token: str, base_url: str) -> Dict[str, Any]:
        """
        Dispatches an HTML password recovery email via the Resend HTTPS API (Port 443).
        Eliminates reliance on raw SMTP socket ports (587/465) which are blocked by cloud firewalls.
        """
        api_key = settings.resend_api_key
        if not api_key:
            raise RuntimeError("RESEND_API_KEY is not configured in backend environment variables.")

        from_email = settings.resend_from_email
        if not from_email:
            raise RuntimeError("RESEND_FROM_EMAIL is not configured. Please specify a verified sender in Render environment variables.")

        sender = from_email if ("<" in from_email and ">" in from_email) else f"FIN-SENTIMENT Security <{from_email}>"
        reset_url = f"{base_url.rstrip('/')}/reset-password?token={raw_token}"

        text_content = (
            f"FIN-SENTIMENT Password Reset\n\n"
            f"You requested a password reset for your FIN-SENTIMENT account.\n"
            f"Use the link below to set a new password:\n{reset_url}\n\n"
            f"This single-use link expires in 15 minutes.\n"
            f"If you did not request this, please ignore this email.\n"
        )
        html_content = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #070b14; color: #f8fafc; padding: 32px 16px;">
            <div style="max-width: 520px; margin: 0 auto; background-color: #0f172a; border: 1px solid #1c2b4a; border-radius: 16px; padding: 32px;">
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 24px;">
                    <span style="font-size: 18px; font-weight: 800; color: #ffffff; letter-spacing: 0.05em;">FIN-SENTIMENT</span>
                    <span style="background: rgba(59,130,246,0.2); color: #60a5fa; border: 1px solid rgba(59,130,246,0.3); font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 4px;">SECURITY</span>
                </div>
                <h2 style="font-size: 20px; font-weight: 700; color: #ffffff; margin-top: 0;">Reset your FIN-SENTIMENT password</h2>
                <p style="color: #94a3b8; font-size: 14px; line-height: 1.6;">You recently requested to reset the password for your FIN-SENTIMENT intelligence terminal account. Click the button below to establish a new password.</p>
                <div style="margin: 28px 0; text-align: center;">
                    <a href="{reset_url}" target="_blank" rel="noopener noreferrer" style="display: inline-block; background: linear-gradient(135deg, #2563eb, #06b6d4); color: #ffffff; font-weight: 600; font-size: 14px; text-decoration: none; padding: 12px 28px; border-radius: 8px;">Reset Password</a>
                </div>
                <p style="color: #64748b; font-size: 12px; line-height: 1.5;">This single-use token will expire in <strong>15 minutes</strong>. If you did not make this request, you can safely ignore this email.</p>
                <p style="color: #475569; font-size: 11px; word-break: break-all; margin-top: 20px;">If the button above does not work, copy and paste this link into your browser:<br/><a href="{reset_url}" target="_blank" rel="noopener noreferrer" style="color: #38bdf8;">{reset_url}</a></p>
            </div>
        </div>
        """

        payload = {
            "from": sender,
            "to": [to_email],
            "subject": "Reset your FIN-SENTIMENT password",
            "html": html_content,
            "text": text_content
        }

        try:
            import httpx
            with httpx.Client(timeout=10.0) as client:
                res = client.post(
                    "https://api.resend.com/emails",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "User-Agent": "FIN-SENTIMENT-Auth/1.0"
                    }
                )
                if res.status_code in (200, 201):
                    res_json = res.json()
                    logger.info(f"Password reset email accepted by Resend API (id={res_json.get('id')}) for recipient.")
                    return res_json

                try:
                    err_json = res.json()
                    err_detail = err_json.get("message") or str(err_json)
                except Exception:
                    err_detail = res.text or f"HTTP {res.status_code}"

                logger.error(f"Resend HTTPS API returned error ({res.status_code}): {err_detail}")
                raise RuntimeError(f"Resend API error ({res.status_code}): {err_detail}")
        except ImportError:
            req_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                "https://api.resend.com/emails",
                data=req_bytes,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "FIN-SENTIMENT-Auth/1.0"
                },
                method="POST"
            )
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    logger.info(f"Password reset email accepted by Resend API (id={resp_data.get('id')}) for recipient.")
                    return resp_data
            except urllib.error.HTTPError as he:
                err_text = he.read().decode("utf-8", errors="replace")
                try:
                    err_j = json.loads(err_text)
                    err_detail = err_j.get("message") or err_text
                except Exception:
                    err_detail = err_text
                logger.error(f"Resend HTTPS API HTTPError ({he.code}): {err_detail}")
                raise RuntimeError(f"Resend API error ({he.code}): {err_detail}") from he
            except Exception as ue:
                logger.error(f"Resend HTTPS API connection failure: {ue}")
                raise RuntimeError(f"Failed to connect to Resend API: {str(ue)}") from ue
        except RuntimeError:
            raise
        except Exception as e:
            logger.error(f"Resend dispatch unexpected error: {e}")
            raise RuntimeError(f"Resend delivery error: {str(e)}") from e

    def _dispatch_reset_email(self, to_email: str, raw_token: str, base_url: str):
        """Sends an HTML password recovery email via configured SMTP relay."""
        host = settings.smtp_host
        if not host:
            raise RuntimeError("SMTP relay host is not configured.")

        port = settings.smtp_port
        user = settings.smtp_username
        password = settings.smtp_password
        from_email = settings.smtp_from_email or (f"noreply@{host}" if host else "noreply@finsentiment.ai")

        reset_url = f"{base_url.rstrip('/')}/reset-password?token={raw_token}"
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "FIN-SENTIMENT – Password Reset Request"
        msg["From"] = f"FIN-SENTIMENT Security <{from_email}>"
        msg["To"] = to_email

        text_content = (
            f"FIN-SENTIMENT Password Reset\n\n"
            f"You requested a password reset for your FIN-SENTIMENT account.\n"
            f"Use the link below to set a new password:\n{reset_url}\n\n"
            f"This single-use link expires in 15 minutes.\n"
            f"If you did not request this, please ignore this email.\n"
        )
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
                    <a href="{reset_url}" target="_blank" rel="noopener noreferrer" style="display: inline-block; background: linear-gradient(135deg, #2563eb, #06b6d4); color: #ffffff; font-weight: 600; font-size: 14px; text-decoration: none; padding: 12px 28px; border-radius: 8px;">Reset Password</a>
                </div>
                <p style="color: #64748b; font-size: 12px; line-height: 1.5;">This single-use token will expire in <strong>15 minutes</strong>. If you did not make this request, you can safely ignore this email.</p>
                <p style="color: #475569; font-size: 11px; word-break: break-all; margin-top: 20px;">If the button above does not work, copy and paste this link into your browser:<br/><a href="{reset_url}" target="_blank" rel="noopener noreferrer" style="color: #38bdf8;">{reset_url}</a></p>
            </div>
        </div>
        """
        msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))

        # Determine connection attempts (with smart fallback between 587 STARTTLS and 465 SSL)
        attempts = []
        if settings.smtp_use_ssl or port == 465:
            attempts = [(465, True), (587, False)]
        else:
            attempts = [(port, False), (465, True)]

        last_error = None
        sent = False

        for attempt_port, attempt_ssl in attempts:
            server = None
            try:
                if attempt_ssl:
                    server = smtplib.SMTP_SSL(host, attempt_port, timeout=10)
                else:
                    server = smtplib.SMTP(host, attempt_port, timeout=10)
                    server.starttls()

                if user and password:
                    try:
                        server.login(user, password)
                    except (smtplib.SMTPAuthenticationError, smtplib.SMTPServerDisconnected) as auth_err:
                        # Gmail sends 535 BadCredentials and immediately closes connection (SMTPServerDisconnected)
                        logger.error(f"SMTP Authentication Error ({host}:{attempt_port}) for {user}: {auth_err}")
                        raise RuntimeError(
                            f"Gmail SMTP authentication failed for '{user}'. "
                            "Please verify: 1) 2-Step Verification is ON in your Google account. "
                            "2) You configured a 16-character Google App Password (not your normal Google account password) in Render environment variables."
                        ) from auth_err

                server.send_message(msg)
                logger.info(f"Password reset email sent to {to_email} via {host}:{attempt_port} (SSL={attempt_ssl}).")
                sent = True
                break
            except RuntimeError:
                raise
            except smtplib.SMTPSenderRefused as sender_err:
                logger.error(f"SMTP Sender Refused ({from_email}): {sender_err}")
                raise RuntimeError(f"SMTP relay rejected sender '{from_email}'. For Gmail, the sender address must match your authenticated Google account.") from sender_err
            except smtplib.SMTPRecipientsRefused as recip_err:
                logger.error(f"SMTP Recipient Refused ({to_email}): {recip_err}")
                raise RuntimeError(f"SMTP relay rejected recipient '{to_email}'.") from recip_err
            except (smtplib.SMTPConnectError, ConnectionRefusedError, socket.timeout, TimeoutError, OSError) as conn_err:
                logger.warning(f"Connection failed on {host}:{attempt_port} (SSL={attempt_ssl}): {conn_err}. Trying alternate configuration if available...")
                last_error = conn_err
            except Exception as e:
                logger.error(f"SMTP error on {host}:{attempt_port}: {e}")
                last_error = e
            finally:
                if server:
                    try:
                        server.quit()
                    except Exception:
                        pass

        if not sent:
            logger.error(f"Failed all SMTP connection attempts to {host}: {last_error}")
            raise RuntimeError(f"Could not connect to SMTP server {host} on ports 587/465 ({type(last_error).__name__}: {last_error}).")

auth_service = AuthService()
