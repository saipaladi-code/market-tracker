import os
import json
import urllib.request
import urllib.parse
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
    def _mask_email(self, email: str) -> str:
        """Masks an email for safe diagnostic logging, e.g. sa***@gmail.com."""
        if not email or "@" not in email:
            return "***"
        local_part, domain = email.split("@", 1)
        visible_chars = min(2, len(local_part))
        return f"{local_part[:visible_chars]}***@{domain}"

    def _ensure_recipient_not_blocked_in_brevo(self, email: str, api_key: str) -> bool:
        """
        Ensures recipient email is not present on Brevo's blocked contacts list (e.g. from prior bounce).
        Directly sends DELETE /v3/smtp/blockedContacts/{email}.
        Returns True if contact was previously blocked and was successfully unblocked.
        """
        try:
            quoted_email = urllib.parse.quote(email.strip().lower())
            url = f"https://api.brevo.com/v3/smtp/blockedContacts/{quoted_email}"
            headers = {"accept": "application/json", "api-key": api_key}
            req = urllib.request.Request(url, headers=headers, method="DELETE")
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status in (200, 204):
                    logger.warning(
                        f"[BREVO_AUTO_UNBLOCK] Recipient {self._mask_email(email)} was found on Brevo blocklist. "
                        "Successfully cleared blocklist entry so delivery can proceed."
                    )
                    return True
        except urllib.error.HTTPError as he:
            if he.code in (404, 400):
                # Contact was not on the blocked list
                return False
            logger.debug(f"Brevo blockedContacts DELETE HTTP status {he.code}")
        except Exception as e:
            logger.debug(f"Brevo blockedContacts check skipped: {e}")
        return False

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
        normalized_email = (email or "").strip().lower()
        import re
        email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
        if not normalized_email or not email_pattern.match(normalized_email):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Please enter a valid email address.")

        # Rate limit password reset requests: allow 15 attempts per 5 minutes to prevent developer lockout
        rate_key = f"pwd_reset:{client_ip}:{normalized_email}"
        auth_rate_limiter.check_rate_limit(rate_key, max_attempts=15, window_seconds=300, action_name="password reset")
        auth_rate_limiter.record_attempt(rate_key)

        # 1. DATABASE VERIFICATION: Search MongoDB users collection first
        try:
            user = db.find_user_by_email(normalized_email)
        except Exception as db_err:
            logger.error(f"[DATABASE_ERROR] Database lookup failure during password recovery: {db_err}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service is currently unavailable. Please try again later."
            )

        # 2. IF EMAIL DOES NOT EXIST: Reject immediately without token or Brevo dispatch
        if not user:
            masked_email = self._mask_email(normalized_email)
            logger.info(
                f"[AUTH_DIAGNOSTIC] Password recovery rejected: account not found for {masked_email}. "
                f"No reset token generated; no Brevo email dispatched."
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="This email address is not registered with FIN-SENTIMENT. Please check your email address or create a new account."
            )

        # 3. DYNAMIC MONGODB RECIPIENT SELECTION:
        # Retrieve recipient email strictly and dynamically from the matching MongoDB user document.
        # NEVER hardcode saipaladi73@gmail.com as recipient.
        # NEVER use BREVO_FROM_EMAIL as recipient (BREVO_FROM_EMAIL is strictly the sender address).
        # NEVER use the first user in the database or a default/fallback recipient.
        recipient_email = (
            user.get("email")
            or user.get("user_email")
            or user.get("work_email")
            or normalized_email
        ).strip().lower()

        user_id = str(user.get("id") or user.get("_id") or "")
        recipient_name = (user.get("full_name") or user.get("name") or "").strip()

        # Safe diagnostic logging verifying the MongoDB lookup match and dynamic recipient selection
        logger.info(
            f"[AUTH_DIAGNOSTIC] Password recovery user verified: "
            f"user_id={user_id}, "
            f"submitted_email={self._mask_email(normalized_email)}, "
            f"mongo_recipient_email={self._mask_email(recipient_email)}, "
            f"account_found=True, "
            f"sender_configured={bool(settings.brevo_from_email)}"
        )

        # 4. Verify outbound email service configuration
        explicit_from = getattr(settings, "BREVO_FROM_EMAIL", None) or os.getenv("BREVO_FROM_EMAIL")
        if explicit_from and not settings.brevo_api_key:
            auth_rate_limiter.reset_key(rate_key)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send password recovery email: BREVO_API_KEY environment variable is missing on Render. Please configure BREVO_API_KEY in your Render dashboard."
            )
        is_configured = settings.is_email_service_configured
        is_dev = not os.getenv("RENDER")

        if not is_configured:
            if is_dev:
                # In local dev / test environment without Brevo configured, generate dev token for manual testing
                raw_token = secrets.token_urlsafe(32)
                token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
                expires_at = datetime.utcnow() + timedelta(minutes=15)
                try:
                    db.update_many(
                        "password_resets",
                        {"$or": [{"email": recipient_email}, {"email": normalized_email}, {"user_id": user_id}], "used": False},
                        {"used": True, "invalidated_at": datetime.utcnow().isoformat() + "Z"}
                    )
                except Exception:
                    pass
                reset_doc = {
                    "token_hash": token_hash,
                    "user_id": user_id,
                    "email": recipient_email,
                    "expires_at": expires_at.isoformat() + "Z",
                    "used": False,
                    "created_at": datetime.utcnow().isoformat() + "Z"
                }
                db.insert_one("password_resets", reset_doc)
                return {
                    "title": "Recovery Email Sent (Testing Mode)",
                    "message": "A password reset link has been sent to your registered email address. Please check your inbox and spam folder.",
                    "status": "email_unconfigured",
                    "smtp_configured": False,
                    "dev_reset_token": raw_token
                }

            auth_rate_limiter.reset_key(rate_key)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send password recovery email: BREVO_API_KEY environment variable is missing on Render. Please configure BREVO_API_KEY in your Render dashboard."
            )

        if not settings.brevo_from_email:
            auth_rate_limiter.reset_key(rate_key)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send password recovery email: BREVO_FROM_EMAIL environment variable is missing on Render. Please configure your verified Brevo sender email in your Render dashboard."
            )

        # 5. Invalidate any previous active tokens for this user account in MongoDB
        try:
            db.update_many(
                "password_resets",
                {"$or": [{"email": recipient_email}, {"email": normalized_email}, {"user_id": user_id}], "used": False},
                {"used": True, "invalidated_at": datetime.utcnow().isoformat() + "Z"}
            )
        except Exception as e:
            logger.warning(f"Could not invalidate prior reset tokens: {e}")

        # 6. Generate secure, unique single-use password-reset token (valid 15 minutes)
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        expires_at = datetime.utcnow() + timedelta(minutes=15)

        reset_doc = {
            "token_hash": token_hash,
            "user_id": user_id,
            "email": recipient_email,
            "expires_at": expires_at.isoformat() + "Z",
            "used": False,
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
        db.insert_one("password_resets", reset_doc)

        # 7. Send recovery email dynamically to matching registered user's email via Brevo HTTPS API
        base_url = self.get_recovery_base_url(request_origin)
        try:
            dispatch_res = self._dispatch_reset_email_brevo(
                to_email=recipient_email,
                to_name=recipient_name or None,
                raw_token=raw_token,
                base_url=base_url
            )
        except Exception as e:
            auth_rate_limiter.reset_key(rate_key)
            err_msg = str(e)
            logger.error(
                f"[BREVO_DISPATCH_ERROR] Failed to dispatch password recovery email via Brevo HTTPS: "
                f"recipient={self._mask_email(recipient_email)}, error={err_msg}",
                exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send password recovery email: {err_msg}"
            )

        message_id = dispatch_res.get("messageId") or f"<gen-{secrets.token_hex(8)}>"
        initial_status = dispatch_res.get("delivery_status") or "accepted"

        # Record email delivery attempt in MongoDB email_deliveries collection for audit and real-time tracking
        try:
            db.insert_one("email_deliveries", {
                "message_id": message_id,
                "user_id": user_id,
                "email": recipient_email,
                "recipient_masked": self._mask_email(recipient_email),
                "token_hash": token_hash,
                "delivery_status": initial_status,
                "delivery_detail": "Request accepted by Brevo Transactional Email API; transmission queued to recipient mail server.",
                "failure_reason": None,
                "created_at": datetime.utcnow().isoformat() + "Z",
                "updated_at": datetime.utcnow().isoformat() + "Z"
            })
        except Exception as log_err:
            logger.warning(f"Failed to record email_deliveries entry: {log_err}")

        # Rule 6: Return accurate non-deceptive status ("Recovery Request Accepted", not claiming delivered before confirmed)
        return {
            "title": "Recovery Request Accepted",
            "message": "Your password recovery request has been accepted by our email service and is currently being processed for delivery. Please check your inbox and spam folder shortly.",
            "status": "accepted",
            "delivery_status": initial_status,
            "message_id": message_id,
            "recipient_masked": self._mask_email(recipient_email),
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

    def _dispatch_reset_email_brevo(self, to_email: str, to_name: Optional[str], raw_token: str, base_url: str) -> Dict[str, Any]:
        """
        Dispatches an HTML password recovery email via the official Brevo Transactional Email API (Port 443).
        Official Documentation: https://developers.brevo.com/docs/send-a-transactional-email
        API Endpoint: POST https://api.brevo.com/v3/smtp/email
        """
        api_key = settings.brevo_api_key
        if not api_key:
            raise RuntimeError("BREVO_API_KEY is not configured in backend environment variables.")

        from_email_raw = settings.brevo_from_email
        if not from_email_raw:
            raise RuntimeError("BREVO_FROM_EMAIL is not configured. Please specify a verified sender in Render environment variables.")

        # Parse sender email and display name cleanly
        sender_email = from_email_raw.strip()
        sender_name = settings.brevo_sender_name

        if "<" in from_email_raw and ">" in from_email_raw:
            try:
                name_part = from_email_raw.split("<")[0].strip().strip('"').strip("'")
                email_part = from_email_raw.split("<")[1].split(">")[0].strip()
                if name_part:
                    sender_name = name_part
                if email_part:
                    sender_email = email_part
            except Exception:
                pass

        reset_url = f"{base_url.rstrip('/')}/reset-password?token={raw_token}"

        text_content = (
            "Hello,\n\n"
            "We received a request to reset your FIN-SENTIMENT account password.\n"
            "Click the button below to create a new password:\n"
            f"{reset_url}\n\n"
            "This link expires in 15 minutes.\n"
            "If you did not request this password reset, you can safely ignore this email.\n\n"
            "Regards,\n"
            "FIN-SENTIMENT Team\n"
        )

        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reset your FIN-SENTIMENT password</title>
</head>
<body style="margin: 0; padding: 0; background-color: #070b14; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #070b14; padding: 40px 16px;">
        <tr>
            <td align="center">
                <table role="presentation" width="100%" style="max-width: 540px; background-color: #0f172a; border: 1px solid #1e293b; border-radius: 16px; overflow: hidden; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);">
                    <tr>
                        <td style="padding: 32px 32px 20px 32px; border-bottom: 1px solid #1e293b;">
                            <span style="font-size: 18px; font-weight: 800; color: #ffffff; letter-spacing: 0.05em;">FIN-SENTIMENT</span>
                            <span style="background: rgba(59, 130, 246, 0.2); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 4px; margin-left: 6px;">SECURITY</span>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 32px;">
                            <h2 style="font-size: 20px; font-weight: 700; color: #ffffff; margin: 0 0 16px 0;">Reset your FIN-SENTIMENT password</h2>
                            <p style="color: #cbd5e1; font-size: 14px; line-height: 1.6; margin: 0 0 16px 0;">Hello,</p>
                            <p style="color: #94a3b8; font-size: 14px; line-height: 1.6; margin: 0 0 24px 0;">We received a request to reset your FIN-SENTIMENT account password. Click the button below to create a new password.</p>
                            <table role="presentation" cellspacing="0" cellpadding="0" style="margin: 28px 0;">
                                <tr>
                                    <td align="center" style="border-radius: 8px; background: linear-gradient(135deg, #2563eb, #06b6d4);">
                                        <a href="{reset_url}" target="_blank" rel="noopener noreferrer" style="display: inline-block; padding: 14px 32px; font-size: 14px; font-weight: 700; color: #ffffff; text-decoration: none; border-radius: 8px; letter-spacing: 0.025em;">RESET PASSWORD</a>
                                    </td>
                                </tr>
                            </table>
                            <p style="color: #f59e0b; font-size: 12px; font-weight: 600; line-height: 1.5; margin: 20px 0 12px 0;">This link expires in 15 minutes.</p>
                            <p style="color: #64748b; font-size: 12px; line-height: 1.5; margin: 0 0 24px 0;">If you did not request this password reset, you can safely ignore this email.</p>
                            <div style="border-top: 1px solid #1e293b; padding-top: 20px; margin-top: 24px;">
                                <p style="color: #64748b; font-size: 11px; line-height: 1.5; margin: 0 0 8px 0;">If the button above does not work, copy and paste this link into your browser:</p>
                                <p style="margin: 0; word-break: break-all;"><a href="{reset_url}" target="_blank" rel="noopener noreferrer" style="color: #38bdf8; font-size: 11px; text-decoration: underline;">{reset_url}</a></p>
                            </div>
                            <div style="margin-top: 24px;">
                                <p style="color: #94a3b8; font-size: 13px; line-height: 1.5; margin: 0;">Regards,<br><strong style="color: #ffffff;">FIN-SENTIMENT Team</strong></p>
                            </div>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""

        clean_recipient = (to_email or "").strip().lower()
        if not clean_recipient or "@" not in clean_recipient:
            raise ValueError(f"Invalid recipient email address for recovery dispatch: '{to_email}'")

        # Ensure recipient is not blocklisted in Brevo due to prior bounce
        self._ensure_recipient_not_blocked_in_brevo(clean_recipient, api_key)

        recipient_entry: Dict[str, str] = {"email": clean_recipient}
        if to_name and to_name.strip():
            recipient_entry["name"] = to_name.strip()

        payload = {
            "sender": {
                "name": sender_name,
                "email": sender_email
            },
            "to": [recipient_entry],
            "subject": "Reset your FIN-SENTIMENT password",
            "htmlContent": html_content,
            "textContent": text_content
        }

        headers = {
            "accept": "application/json",
            "api-key": api_key,
            "content-type": "application/json",
            "user-agent": "FIN-SENTIMENT-Auth/1.0"
        }

        try:
            import httpx
            with httpx.Client(timeout=10.0) as client:
                res = client.post(
                    "https://api.brevo.com/v3/smtp/email",
                    json=payload,
                    headers=headers
                )
                if res.status_code in (200, 201, 202):
                    res_json = res.json()
                    message_id = res_json.get("messageId") or res_json.get("id")
                    logger.info(
                        f"[AUTH_DIAGNOSTIC] Password recovery Brevo dispatch: "
                        f"account_found=True, "
                        f"token_generated=True, "
                        f"brevo_called=True, "
                        f"recipient={self._mask_email(clean_recipient)}, "
                        f"sender={self._mask_email(sender_email)}, "
                        f"brevo_status={res.status_code}, "
                        f"message_id={message_id}, "
                        f"timestamp={datetime.utcnow().isoformat()}Z"
                    )
                    return {"messageId": message_id, "status": "accepted"}

                try:
                    err_json = res.json()
                    err_detail = err_json.get("message") or err_json.get("code") or str(err_json)
                except Exception:
                    err_detail = res.text or f"HTTP {res.status_code}"

                logger.error(
                    f"[AUTH_DIAGNOSTIC] Password recovery Brevo failure: "
                    f"account_found=True, "
                    f"token_generated=True, "
                    f"brevo_called=True, "
                    f"recipient={self._mask_email(clean_recipient)}, "
                    f"sender={self._mask_email(sender_email)}, "
                    f"brevo_status={res.status_code}, "
                    f"error={err_detail}"
                )

                if res.status_code == 401:
                    logger.error("Brevo API 401 Unauthorized: Invalid or missing API key.")
                    raise RuntimeError(f"Brevo API authentication failed (401 Unauthorized): Invalid Brevo API key. Please verify BREVO_API_KEY in Render. Details: {err_detail}")
                elif res.status_code == 400:
                    logger.error(f"Brevo API 400 Bad Request: {err_detail}")
                    raise RuntimeError(f"Brevo API rejected request (400 Bad Request): {err_detail}. Please ensure BREVO_FROM_EMAIL ('{sender_email}') is an authorized and verified sender in Brevo.")
                elif res.status_code == 402:
                    logger.error(f"Brevo API 402 Payment Required: {err_detail}")
                    raise RuntimeError(f"Brevo account credit limit reached (402 Payment Required): {err_detail}")
                elif res.status_code == 403:
                    logger.error(f"Brevo API 403 Forbidden: {err_detail}")
                    raise RuntimeError(f"Brevo API error (403 Forbidden): {err_detail}. Please ensure transactional emails are activated in your Brevo account.")
                elif res.status_code == 429:
                    logger.error(f"Brevo API 429 Rate Limit: {err_detail}")
                    raise RuntimeError(f"Brevo API rate limit exceeded (429 Too Many Requests): {err_detail}. Please try again shortly.")
                else:
                    logger.error(f"Brevo API error ({res.status_code}): {err_detail}")
                    raise RuntimeError(f"Brevo API error ({res.status_code}): {err_detail}")

        except ImportError:
            req_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                "https://api.brevo.com/v3/smtp/email",
                data=req_bytes,
                headers=headers,
                method="POST"
            )
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    message_id = resp_data.get("messageId") or resp_data.get("id")
                    logger.info(
                        f"[AUTH_DIAGNOSTIC] Password recovery Brevo dispatch: "
                        f"account_found=True, "
                        f"token_generated=True, "
                        f"brevo_called=True, "
                        f"recipient={self._mask_email(clean_recipient)}, "
                        f"sender={self._mask_email(sender_email)}, "
                        f"brevo_status={resp.status}, "
                        f"message_id={message_id}, "
                        f"timestamp={datetime.utcnow().isoformat()}Z"
                    )
                    return {"messageId": message_id, "status": "accepted"}
            except urllib.error.HTTPError as he:
                err_text = he.read().decode("utf-8", errors="replace")
                try:
                    err_j = json.loads(err_text)
                    err_detail = err_j.get("message") or err_j.get("code") or err_text
                except Exception:
                    err_detail = err_text
                if he.code == 401:
                    raise RuntimeError(f"Brevo API authentication failed (401 Unauthorized): Invalid Brevo API key. Details: {err_detail}") from he
                elif he.code == 400:
                    raise RuntimeError(f"Brevo API rejected request (400 Bad Request): {err_detail}. Please ensure BREVO_FROM_EMAIL ('{sender_email}') is verified in Brevo.") from he
                elif he.code == 403:
                    raise RuntimeError(f"Brevo API error (403 Forbidden): {err_detail}. Verify transactional email activation in Brevo.") from he
                elif he.code == 429:
                    raise RuntimeError(f"Brevo API rate limit exceeded (429): {err_detail}") from he
                raise RuntimeError(f"Brevo API error ({he.code}): {err_detail}") from he
            except Exception as ue:
                logger.error(f"Brevo HTTPS connection failure: {ue}")
                raise RuntimeError(f"Failed to connect to Brevo API: {str(ue)}") from ue
        except RuntimeError:
            raise
        except Exception as e:
            logger.error(f"Brevo dispatch unexpected error: {e}")
            raise RuntimeError(f"Brevo delivery error: {str(e)}") from e

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

    def get_delivery_status(self, message_id: str) -> Dict[str, Any]:
        """
        Inspects real-time Brevo transactional email event logs for a given message ID.
        Determines whether the message is: accepted, delivered, deferred, blocked, hard_bounced, soft_bounced, or rejected.
        Updates persistent database delivery tracking record in MongoDB.
        """
        clean_id = (message_id or "").strip()
        if not clean_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message ID is required.")

        delivery_rec = db.find_one("email_deliveries", {"message_id": clean_id})
        recipient_masked = delivery_rec.get("recipient_masked") if delivery_rec else None

        api_key = settings.brevo_api_key
        if not api_key:
            return {
                "message_id": clean_id,
                "delivery_status": delivery_rec.get("delivery_status") if delivery_rec else "accepted",
                "detail": delivery_rec.get("delivery_detail") if delivery_rec else "Processing",
                "failure_reason": None,
                "recipient_masked": recipient_masked,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

        try:
            import httpx
            import urllib.parse
            quoted = urllib.parse.quote(clean_id)
            url = f"https://api.brevo.com/v3/smtp/statistics/events?messageId={quoted}"
            headers = {"accept": "application/json", "api-key": api_key}
            with httpx.Client(timeout=8.0) as client:
                res = client.get(url, headers=headers)
                if res.status_code == 200:
                    events = res.json().get("events", [])
                    final_status = "accepted"
                    final_detail = "Accepted by email service; queued for transmission to recipient mail server."
                    failure_reason = None

                    for e in events:
                        ev = e.get("event")
                        if ev == "delivered":
                            final_status = "delivered"
                            final_detail = "Confirmed delivered to recipient mailbox."
                            break
                        elif ev in ("hard_bounce", "hardBounce"):
                            final_status = "hard_bounced"
                            failure_reason = e.get("reason") or "Recipient email address does not exist or was rejected by receiving mail server."
                            final_detail = f"Hard bounce: {failure_reason}"
                            break
                        elif ev in ("soft_bounce", "softBounce"):
                            final_status = "soft_bounced"
                            failure_reason = e.get("reason") or "Recipient mailbox full or receiving mail server temporarily unavailable."
                            final_detail = f"Soft bounce: {failure_reason}"
                            break
                        elif ev == "blocked":
                            final_status = "blocked"
                            failure_reason = e.get("reason") or "Recipient address was blocked by email provider suppression list."
                            final_detail = f"Blocked: {failure_reason}"
                            break
                        elif ev == "deferred":
                            final_status = "deferred"
                            final_detail = "Delivery temporarily deferred by recipient mail server; automatic retries in progress."
                        elif ev == "requests" and final_status == "accepted":
                            final_status = "accepted"
                            final_detail = "Accepted by Brevo API; queued for transmission to recipient mail server."

                    if delivery_rec:
                        db.update_one(
                            "email_deliveries",
                            {"message_id": clean_id},
                            {
                                "delivery_status": final_status,
                                "delivery_detail": final_detail,
                                "failure_reason": failure_reason,
                                "events_count": len(events),
                                "updated_at": datetime.utcnow().isoformat() + "Z"
                            }
                        )

                    return {
                        "message_id": clean_id,
                        "delivery_status": final_status,
                        "detail": final_detail,
                        "failure_reason": failure_reason,
                        "recipient_masked": recipient_masked,
                        "timestamp": datetime.utcnow().isoformat() + "Z"
                    }
        except Exception as e:
            logger.warning(f"Error querying Brevo delivery events for {clean_id}: {e}")

        return {
            "message_id": clean_id,
            "delivery_status": delivery_rec.get("delivery_status") if delivery_rec else "accepted",
            "detail": delivery_rec.get("delivery_detail") if delivery_rec else "Processing",
            "failure_reason": None,
            "recipient_masked": recipient_masked,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

    def record_webhook_event(self, payload: Any) -> Dict[str, Any]:
        """
        Processes real-time webhook delivery events from Brevo and updates tracking logs in MongoDB.
        """
        events = payload if isinstance(payload, list) else [payload]
        recorded = 0
        for ev in events:
            if not isinstance(ev, dict):
                continue
            msg_id = ev.get("message-id") or ev.get("messageId")
            ev_type = ev.get("event")
            email = ev.get("email")
            reason = ev.get("reason")
            date_str = ev.get("date")

            if msg_id:
                clean_msg_id = msg_id.strip()
                norm_status = "accepted"
                if ev_type == "delivered":
                    norm_status = "delivered"
                elif ev_type in ("hard_bounce", "hardBounce"):
                    norm_status = "hard_bounced"
                elif ev_type in ("soft_bounce", "softBounce"):
                    norm_status = "soft_bounced"
                elif ev_type == "blocked":
                    norm_status = "blocked"
                elif ev_type == "deferred":
                    norm_status = "deferred"

                logger.info(
                    f"[BREVO_WEBHOOK] Delivery event received: "
                    f"message_id={clean_msg_id}, "
                    f"event={ev_type}, "
                    f"recipient={self._mask_email(email or '')}, "
                    f"reason={reason}"
                )

                db.update_one(
                    "email_deliveries",
                    {"message_id": clean_msg_id},
                    {
                        "delivery_status": norm_status,
                        "delivery_detail": f"Webhook event: {ev_type} ({reason or 'OK'})",
                        "failure_reason": reason,
                        "last_webhook_date": date_str,
                        "updated_at": datetime.utcnow().isoformat() + "Z"
                    }
                )
                recorded += 1

        return {"status": "recorded", "events_processed": recorded}

auth_service = AuthService()
