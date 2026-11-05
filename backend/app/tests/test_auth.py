import secrets
import hashlib
import pytest

from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app.main import app

from app.database import db

from app.config import settings

from app.services.auth_service import auth_service

from app.services.rate_limiter import auth_rate_limiter

client = TestClient(app)

@pytest.fixture(autouse=True)

def cleanup_test_users(monkeypatch):

    """Ensure clean test slate before and after tests."""

    client.cookies.clear()
    auth_rate_limiter._attempts.clear()

    monkeypatch.setattr(settings, "BREVO_API_KEY", None)

    monkeypatch.setattr(settings, "BREVO_FROM_EMAIL", None)

    monkeypatch.setattr(settings, "BREVO_SENDER_NAME", "FIN-SENTIMENT")

    monkeypatch.setattr(settings, "SMTP_HOST", None)

    db.delete_many("users", {"email": {"$regex": r"(@testfinancial\.com|\.brevo@|investor\d@)"}})

    db.delete_many("password_resets", {"email": {"$regex": r"(@testfinancial\.com|\.brevo@|investor\d@)"}})

    # Also clean local test arrays if in local mode

    if not db.is_cloud:

        local_data = db._read_local_db()

        local_data["users"] = [u for u in local_data.get("users", []) if "@testfinancial.com" not in u.get("email", "")]

        local_data["password_resets"] = [r for r in local_data.get("password_resets", []) if "@testfinancial.com" not in r.get("email", "")]

        db._write_local_db(local_data)

    yield

    # Cleanup afterwards

    client.cookies.clear()

    db.delete_many("users", {"email": {"$regex": r"(@testfinancial\.com|\.brevo@|investor\d@)"}})

    db.delete_many("password_resets", {"email": {"$regex": r"(@testfinancial\.com|\.brevo@|investor\d@)"}})

# 1. Registration Tests

def test_successful_registration():

    email = "trader.alice@testfinancial.com"

    payload = {

        "full_name": "Alice Montgomery",

        "email": email,

        "password": "SecurePassword123!"

    }

    res = client.post("/api/auth/register", json=payload)

    assert res.status_code == 200

    data = res.json()

    assert "user" in data

    assert data["user"]["email"] == email

    assert data["user"]["full_name"] == "Alice Montgomery"

    assert "token" in data

    # Verify cookie was set

    assert settings.COOKIE_NAME in res.cookies

    # Verify user in database has bcrypt hash, NOT plaintext password

    stored = db.find_user_by_email(email)

    assert stored is not None

    assert stored["password_hash"].startswith("$2b$")

    assert "SecurePassword123!" not in str(stored)

def test_duplicate_email_registration_rejected():

    payload = {

        "full_name": "Bob Vance",

        "email": "bob.vance@testfinancial.com",

        "password": "StrongPassword99$"

    }

    # Initial registration

    r1 = client.post("/api/auth/register", json=payload)

    assert r1.status_code == 200

    # Duplicate registration attempt with identical and case-varied email

    payload_dup = dict(payload)

    payload_dup["email"] = "BOB.VANCE@testfinancial.com"

    r2 = client.post("/api/auth/register", json=payload_dup)

    assert r2.status_code == 409

    assert "already exists" in r2.json()["detail"].lower()

def test_invalid_email_input():

    res = client.post("/api/auth/register", json={

        "full_name": "Charlie Day",

        "email": "not-a-valid-email",

        "password": "ValidPassword123!"

    })

    assert res.status_code == 422

def test_weak_password_rejected():

    weak_cases = [

        "short1A",             # too short (<8)

        "alllowercase1234",    # no uppercase

        "ALLUPPERCASE1234",    # no lowercase

        "NoDigitsHereAtAll!",  # no digit

    ]

    for weak_pwd in weak_cases:

        res = client.post("/api/auth/register", json={

            "full_name": "Test Analyst",

            "email": f"analyst.{weak_pwd[:5]}@testfinancial.com",

            "password": weak_pwd

        })

        assert res.status_code in (422, 400), f"Expected weak password '{weak_pwd}' to be rejected"

# 2. Login Tests

def test_successful_login_with_cookie_and_token():

    email = "david.login@testfinancial.com"

    pwd = "CorrectHorse99!"

    auth_service.register_user("David Miller", email, pwd)

    res = client.post("/api/auth/login", json={

        "email": email,

        "password": pwd,

        "remember_me": True

    })

    assert res.status_code == 200

    data = res.json()

    assert data["user"]["email"] == email

    assert "token" in data

    assert settings.COOKIE_NAME in res.cookies

def test_login_incorrect_password():

    email = "eva.auth@testfinancial.com"

    pwd = "ValidPassword123!"

    auth_service.register_user("Eva Green", email, pwd)

    res = client.post("/api/auth/login", json={

        "email": email,

        "password": "WrongPassword999!"

    })

    assert res.status_code == 401

    assert "invalid email or password" in res.json()["detail"].lower()

def test_login_nonexistent_user():

    res = client.post("/api/auth/login", json={

        "email": "ghost.user@testfinancial.com",

        "password": "SomePassword123!"

    })

    assert res.status_code == 401

# 3. Current User (/api/auth/me) Tests

def test_current_user_authenticated_via_cookie():

    email = "grace.me@testfinancial.com"

    pwd = "GraceP@ss123!"

    auth_service.register_user("Grace Hopper", email, pwd)

    # Login to acquire Set-Cookie automatically or set with testserver domain

    login_res = client.post("/api/auth/login", json={"email": email, "password": pwd})

    assert login_res.status_code == 200

    res = client.get("/api/auth/me")

    assert res.status_code == 200

    assert res.json()["email"] == email

    assert res.json()["full_name"] == "Grace Hopper"

def test_current_user_authenticated_via_bearer_header():

    email = "helen.bearer@testfinancial.com"

    reg = auth_service.register_user("Helen Keller", email, "HelenP@ss123!")

    # Explicitly verify header authorization with cleared cookies

    client.cookies.clear()

    headers = {"Authorization": f"Bearer {reg['token']}"}

    res = client.get("/api/auth/me", headers=headers)

    assert res.status_code == 200

    assert res.json()["email"] == email

def test_current_user_unauthenticated():

    client.cookies.clear()

    res = client.get("/api/auth/me")

    assert res.status_code == 401

# 4. Protected API Route Guards

def test_unauthenticated_access_to_protected_apis():

    client.cookies.clear()

    # Unauthenticated requests to private endpoints must return 401 Unauthorized

    protected_endpoints = [

        ("GET", "/api/dashboard/stats"),

        ("GET", "/api/news"),

        ("GET", "/api/companies"),

        ("GET", "/api/sentiment/sectors"),

        ("GET", "/api/conflicts"),

        ("GET", "/api/alerts"),

        ("GET", "/api/data-quality"),

        ("POST", "/api/news/refresh"),

    ]

    for method, path in protected_endpoints:

        if method == "GET":

            r = client.get(path)

        else:

            r = client.post(path)

        assert r.status_code == 401, f"Expected {method} {path} to require authentication, got {r.status_code}"

def test_authenticated_access_to_protected_apis():

    email = "iris.protected@testfinancial.com"

    reg = auth_service.register_user("Iris West", email, "IrisPassword123!")

    headers = {"Authorization": f"Bearer {reg['token']}"}

    # Verify protected endpoints respond successfully when authenticated

    r_stats = client.get("/api/dashboard/stats", headers=headers)

    assert r_stats.status_code == 200

    r_news = client.get("/api/news?page_size=2", headers=headers)

    assert r_news.status_code == 200

    r_comps = client.get("/api/companies", headers=headers)

    assert r_comps.status_code == 200

# 5. Session Expiration & Logout

def test_session_expiration():

    email = "jack.expire@testfinancial.com"

    reg = auth_service.register_user("Jack Reacher", email, "JackPassword123!")

    # Create an expired token manually (-10 seconds)

    expired_token, _ = auth_service.create_access_token(

        reg["user"]["id"],

        email,

        expires_delta=timedelta(seconds=-10)

    )

    headers = {"Authorization": f"Bearer {expired_token}"}

    res = client.get("/api/dashboard/stats", headers=headers)

    assert res.status_code == 401

    assert "expired" in res.json()["detail"].lower()

def test_logout_clears_cookie():

    res = client.post("/api/auth/logout")

    assert res.status_code == 200

    assert res.json()["status"] == "success"

# 6. Password Recovery (Expiring, Single-Use Token)

def test_password_recovery_single_use_and_expiration():

    email = "karen.reset@testfinancial.com"

    old_pwd = "OldPassword123!"

    new_pwd = "BrandNewPassword123!"

    auth_service.register_user("Karen Page", email, old_pwd)

    # 1. Request password reset

    req_res = client.post("/api/auth/forgot-password", json={"email": email})

    assert req_res.status_code == 200

    req_data = req_res.json()

    assert "message" in req_data

    # Retrieve dev token for testing

    token = req_data.get("dev_reset_token")

    if not token:

        # Fallback to inspecting hashed record

        reset_rec = db.find_one("password_resets", {"email": email})

        assert reset_rec is not None

        # Token cannot be reversed, so test through auth_service with known token

        from secrets import token_urlsafe

        token = token_urlsafe(32)

        import hashlib

        thash = hashlib.sha256(token.encode("utf-8")).hexdigest()

        db.insert_one("password_resets", {

            "token_hash": thash,

            "user_id": reset_rec["user_id"],

            "email": email,

            "expires_at": (datetime.utcnow() + timedelta(minutes=15)).isoformat() + "Z",

            "used": False,

            "created_at": datetime.utcnow().isoformat() + "Z"

        })

    # 2. Reset password successfully

    reset_res = client.post("/api/auth/reset-password", json={

        "token": token,

        "new_password": new_pwd

    })

    assert reset_res.status_code == 200

    assert "success" in reset_res.json()["status"].lower()

    # 3. Old password should fail

    fail_login = client.post("/api/auth/login", json={"email": email, "password": old_pwd})

    assert fail_login.status_code == 401

    # 4. New password should succeed

    succ_login = client.post("/api/auth/login", json={"email": email, "password": new_pwd})

    assert succ_login.status_code == 200

    # 5. Token reuse must be rejected (single-use validation)

    reuse_res = client.post("/api/auth/reset-password", json={

        "token": token,

        "new_password": "AnotherPassword123!"

    })

    assert reuse_res.status_code == 400

    assert "already been used" in reuse_res.json()["detail"].lower()

def test_password_recovery_unregistered_email_rejected():
    """Verifies that unregistered email addresses are rejected with 404 and clear message."""
    db.delete_many("users", {"email": "nobody@testfinancial.com"})
    res = client.post("/api/auth/forgot-password", json={"email": "nobody@testfinancial.com"})
    assert res.status_code == 404
    assert "not registered" in res.json()["detail"].lower()

# 7. Rate Limiting Tests

def test_rate_limiting_on_login_brute_force():

    email = "victim.bruteforce@testfinancial.com"

    auth_service.register_user("Victim User", email, "GoodPassword123!")

    # Attempt 5 consecutive failed logins

    for _ in range(5):

        client.post("/api/auth/login", json={"email": email, "password": "WrongPassword!"})

    # 6th attempt must be blocked by rate limiter with 429 Too Many Requests

    blocked_res = client.post("/api/auth/login", json={"email": email, "password": "WrongPassword!"})

    assert blocked_res.status_code == 429

    assert "too many" in blocked_res.json()["detail"].lower()

    assert "Retry-After" in blocked_res.headers

def test_password_recovery_invalid_token():

    """Verifies that an unrecorded/invalid token is rejected."""

    res = client.post("/api/auth/reset-password", json={

        "token": "completely_invalid_random_token_12345",

        "new_password": "ValidPassword123!"

    })

    assert res.status_code == 400

    assert "invalid password reset token" in res.json()["detail"].lower()

def test_password_recovery_expired_token():

    """Verifies that an expired recovery token (> 15 minutes old) is rejected."""

    email = "expired.token.user@testfinancial.com"

    auth_service.register_user("Expired User", email, "OldPassword123!")

    

    from secrets import token_urlsafe

    raw_token = token_urlsafe(32)

    import hashlib

    thash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    

    # Insert token that expired 5 minutes ago

    db.insert_one("password_resets", {

        "token_hash": thash,

        "user_id": "exp-usr-1",

        "email": email,

        "expires_at": (datetime.utcnow() - timedelta(minutes=5)).isoformat() + "Z",

        "used": False,

        "created_at": (datetime.utcnow() - timedelta(minutes=20)).isoformat() + "Z"

    })

    res = client.post("/api/auth/reset-password", json={

        "token": raw_token,

        "new_password": "NewStrongPassword123!"

    })

    assert res.status_code == 400

    assert "expired" in res.json()["detail"].lower()

def test_password_recovery_weak_password():

    """Verifies that weak new passwords are rejected with 422."""

    res = client.post("/api/auth/reset-password", json={

        "token": "valid_length_token_12345678",

        "new_password": "weak"

    })

    assert res.status_code in (400, 422)

def test_password_recovery_smtp_failure_handling(monkeypatch):

    """Verifies that when email dispatch fails, the system returns 500 and does NOT show a false success."""

    email = "smtp.fail.user@testfinancial.com"

    auth_service.register_user("SMTP Fail User", email, "UserPassword123!")

    # Simulate SMTP host being configured

    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.testserver.com")

    

    # Simulate SMTP delivery raising an exception

    def mock_dispatch(to_email, raw_token, base_url):

        raise ConnectionRefusedError("SMTP Connection Refused by server")

    monkeypatch.setattr(auth_service, "_dispatch_reset_email", mock_dispatch)

    res = client.post("/api/auth/forgot-password", json={"email": email})

    assert res.status_code == 500

    assert "failed to send password recovery email" in res.json()["detail"].lower()

def test_password_recovery_vercel_url_resolution():

    """Verifies that recovery links resolve to the deployed Vercel frontend URL."""

    # Test request coming from Vercel domain

    url_vercel = auth_service.get_recovery_base_url("https://market-tracker-umber.vercel.app")

    assert url_vercel == "https://market-tracker-umber.vercel.app"

    # Test fallback to production Vercel frontend when no origin provided

    url_default = auth_service.get_recovery_base_url(None)

    assert "market-tracker-umber.vercel.app" in url_default

# 7. SMTP Alias, Password Stripping & Telemetry Tests

def test_smtp_configuration_aliases_and_password_cleaning(monkeypatch):

    """Verifies that SMTP_USER, SMTP_PASS, SMTP_FROM aliases work and spaces in passwords are stripped."""

    # Reset any overrides

    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.gmail.com")

    monkeypatch.setattr(settings, "SMTP_PORT", 587)

    monkeypatch.setattr(settings, "SMTP_USERNAME", None)

    monkeypatch.setattr(settings, "SMTP_PASSWORD", None)

    monkeypatch.setattr(settings, "SMTP_FROM_EMAIL", None)

    

    # Set aliases

    monkeypatch.setattr(settings, "SMTP_USER", "saipaladi73@gmail.com")

    monkeypatch.setattr(settings, "SMTP_PASS", "abcd efgh ijkl mnop")

    monkeypatch.setattr(settings, "SMTP_FROM", None)

    assert settings.smtp_host == "smtp.gmail.com"

    assert settings.smtp_username == "saipaladi73@gmail.com"

    # Spaces must be stripped from Google App Password

    assert settings.smtp_password == "abcdefghijklmnop"

    # Fallback to username for from_email

    assert settings.smtp_from_email == "saipaladi73@gmail.com"

    assert settings.smtp_use_tls is True

    assert settings.smtp_use_ssl is False

    assert settings.is_smtp_configured is True

def test_smtp_ssl_port_465_detection(monkeypatch):

    """Verifies that port 465 automatically engages SSL."""

    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.gmail.com")

    monkeypatch.setattr(settings, "SMTP_PORT", 465)

    monkeypatch.setattr(settings, "SMTP_SSL", None)

    monkeypatch.setattr(settings, "SMTP_TLS", None)

    assert settings.smtp_port == 465

    assert settings.smtp_use_ssl is True

    assert settings.smtp_use_tls is False

def test_health_endpoint_email_telemetry(monkeypatch):
    """Verifies that /api/health exposes safe non-sensitive email telemetry for Brevo HTTPS."""
    monkeypatch.setattr(settings, "BREVO_API_KEY", "xkeysib-secret-live-key-9999")
    monkeypatch.setattr(settings, "BREVO_FROM_EMAIL", "security@finsentiment.ai")
    monkeypatch.setattr(settings, "BREVO_SENDER_NAME", "FIN-SENTIMENT")

    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert "email_service" in data
    email_status = data["email_service"]
    assert email_status["configured"] is True
    assert email_status["provider"] == "Brevo Transactional Email API"
    assert email_status["transport"] == "HTTPS (Port 443)"
    assert email_status["has_api_key"] is True
    assert email_status["sender_configured"] is True
    # Ensure sensitive secret API key is NOT in response
    assert "xkeysib-secret-live-key-9999" not in str(data)

def test_smtp_auth_error_diagnostic_detail(monkeypatch):

    """Verifies that SMTP authentication failures yield an informative diagnostic message."""

    email = "auth.fail.user@testfinancial.com"

    auth_service.register_user("Auth Fail User", email, "UserPassword123!")

    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.gmail.com")

    monkeypatch.setattr(settings, "SMTP_USER", "saipaladi73@gmail.com")

    monkeypatch.setattr(settings, "SMTP_PASS", "invalidpwd")

    import smtplib

    def mock_dispatch(to_email, raw_token, base_url):

        raise smtplib.SMTPAuthenticationError(535, b"5.7.8 Username and Password not accepted")

    monkeypatch.setattr(auth_service, "_dispatch_reset_email", mock_dispatch)

    res = client.post("/api/auth/forgot-password", json={"email": email})

    assert res.status_code == 500

    assert "failed to send password recovery email" in res.json()["detail"].lower()

# 8. Brevo Transactional Email Dispatch Tests (Dynamic Recipient & Lifecycle)

def test_brevo_successful_email_dispatch_dynamic_recipient(monkeypatch):
    """
    Verifies that password reset emails are dynamically addressed to each user's
    actual registered email address from MongoDB across different providers (Gmail, Yahoo, Outlook).
    """
    test_users = [
        ("User Gmail", "sai.brevo@gmail.com", "SecureGmailP@ss1"),
        ("User Yahoo", "rahul.brevo@yahoo.com", "SecureYahooP@ss2"),
        ("User Outlook", "priya.brevo@outlook.com", "SecureOutlookP@ss3"),
    ]

    for name, email, pwd in test_users:
        if not db.find_user_by_email(email):
            auth_service.register_user(name, email, pwd)

    monkeypatch.setattr(settings, "BREVO_API_KEY", "xkeysib-mock-valid-key")
    monkeypatch.setattr(settings, "BREVO_FROM_EMAIL", "noreply@finsentiment.ai")
    monkeypatch.setattr(settings, "BREVO_SENDER_NAME", "FIN-SENTIMENT")

    dispatched_calls = []

    def mock_brevo_dispatch(to_email, to_name, raw_token, base_url):
        dispatched_calls.append({
            "to_email": to_email,
            "to_name": to_name,
            "raw_token": raw_token,
            "base_url": base_url
        })
        return {"messageId": f"<mock-{secrets.token_hex(6)}@smtp-relay.brevo.com>", "status": "accepted"}

    monkeypatch.setattr(auth_service, "_dispatch_reset_email_brevo", mock_brevo_dispatch)

    # 1. Dispatch reset for User A (Gmail)
    res_a = client.post("/api/auth/forgot-password", json={"email": "sai.brevo@gmail.com"})
    assert res_a.status_code == 200
    assert dispatched_calls[-1]["to_email"] == "sai.brevo@gmail.com"
    assert dispatched_calls[-1]["to_name"] == "User Gmail"
    token_a = dispatched_calls[-1]["raw_token"]

    # 2. Dispatch reset for User B (Yahoo)
    res_b = client.post("/api/auth/forgot-password", json={"email": "rahul.brevo@yahoo.com"})
    assert res_b.status_code == 200
    assert dispatched_calls[-1]["to_email"] == "rahul.brevo@yahoo.com"
    assert dispatched_calls[-1]["to_name"] == "User Yahoo"
    token_b = dispatched_calls[-1]["raw_token"]

    # 3. Dispatch reset for User C (Outlook)
    res_c = client.post("/api/auth/forgot-password", json={"email": "priya.brevo@outlook.com"})
    assert res_c.status_code == 200
    assert dispatched_calls[-1]["to_email"] == "priya.brevo@outlook.com"
    assert dispatched_calls[-1]["to_name"] == "User Outlook"
    token_c = dispatched_calls[-1]["raw_token"]

    # Confirm token isolation: all tokens must be mutually distinct
    assert token_a != token_b
    assert token_b != token_c
    assert token_a != token_c

    # Confirm records exist in database with unconsumed status
    for email in ["sai.brevo@gmail.com", "rahul.brevo@yahoo.com", "priya.brevo@outlook.com"]:
        rec = db.find_one("password_resets", {"email": email, "used": False})
        assert rec is not None


def test_brevo_missing_api_key_configuration_error(monkeypatch):
    """Verifies that missing BREVO_API_KEY produces a clear configuration error."""
    email = "trader.brevo.nokey@testfinancial.com"
    auth_service.register_user("No Key User", email, "SecurePassword123!")

    monkeypatch.setattr(settings, "BREVO_API_KEY", None)
    monkeypatch.setattr(settings, "BREVO_FROM_EMAIL", "security@testfinancial.com")

    res = client.post("/api/auth/forgot-password", json={"email": email})
    assert res.status_code == 500
    assert "brevo_api_key" in res.json()["detail"].lower()


def test_brevo_missing_from_email_configuration_error(monkeypatch):
    """Verifies that missing BREVO_FROM_EMAIL produces a clear configuration error."""
    email = "trader.brevo.nofrom@testfinancial.com"
    auth_service.register_user("No From User", email, "SecurePassword123!")

    monkeypatch.setattr(settings, "BREVO_API_KEY", "xkeysib-mock-valid-key")
    monkeypatch.setattr(settings, "BREVO_FROM_EMAIL", None)

    res = client.post("/api/auth/forgot-password", json={"email": email})
    assert res.status_code == 500
    assert "brevo_from_email" in res.json()["detail"].lower()


def test_brevo_api_authentication_error_401(monkeypatch):
    """Verifies that Brevo 401 Unauthorized (invalid API key) returns descriptive diagnostic error."""
    email = "trader.brevo.401@testfinancial.com"
    auth_service.register_user("Brevo 401 User", email, "SecurePassword123!")

    monkeypatch.setattr(settings, "BREVO_API_KEY", "invalid_key")
    monkeypatch.setattr(settings, "BREVO_FROM_EMAIL", "security@testfinancial.com")

    def mock_dispatch_401(to_email, to_name, raw_token, base_url):
        raise RuntimeError("Brevo API authentication failed (401 Unauthorized): Invalid Brevo API key. Please verify BREVO_API_KEY in Render.")

    monkeypatch.setattr(auth_service, "_dispatch_reset_email_brevo", mock_dispatch_401)

    res = client.post("/api/auth/forgot-password", json={"email": email})
    assert res.status_code == 500
    assert "401 unauthorized" in res.json()["detail"].lower()


def test_brevo_unverified_sender_error_400(monkeypatch):
    """Verifies that Brevo 400 Bad Request (unverified sender) returns clear instructions to verify sender in Brevo."""
    email = "trader.brevo.400@testfinancial.com"
    auth_service.register_user("Brevo 400 User", email, "SecurePassword123!")

    monkeypatch.setattr(settings, "BREVO_API_KEY", "xkeysib-valid-key")
    monkeypatch.setattr(settings, "BREVO_FROM_EMAIL", "unverified@randomdomain.com")

    def mock_dispatch_400(to_email, to_name, raw_token, base_url):
        raise RuntimeError("Brevo API rejected request (400 Bad Request): Sender not verified. Please ensure BREVO_FROM_EMAIL ('unverified@randomdomain.com') is an authorized and verified sender in Brevo.")

    monkeypatch.setattr(auth_service, "_dispatch_reset_email_brevo", mock_dispatch_400)

    res = client.post("/api/auth/forgot-password", json={"email": email})
    assert res.status_code == 500
    assert "sender in brevo" in res.json()["detail"].lower()


def test_brevo_rate_limit_error_429(monkeypatch):
    """Verifies that Brevo 429 Too Many Requests returns clear rate limit notification."""
    email = "trader.brevo.429@testfinancial.com"
    auth_service.register_user("Brevo 429 User", email, "SecurePassword123!")

    monkeypatch.setattr(settings, "BREVO_API_KEY", "xkeysib-valid-key")
    monkeypatch.setattr(settings, "BREVO_FROM_EMAIL", "security@testfinancial.com")

    def mock_dispatch_429(to_email, to_name, raw_token, base_url):
        raise RuntimeError("Brevo API rate limit exceeded (429 Too Many Requests): Please try again shortly.")

    monkeypatch.setattr(auth_service, "_dispatch_reset_email_brevo", mock_dispatch_429)

    res = client.post("/api/auth/forgot-password", json={"email": email})
    assert res.status_code == 500
    assert "429" in res.json()["detail"] or "rate limit" in res.json()["detail"].lower()


def test_brevo_multiple_user_full_reset_and_login_lifecycle(monkeypatch):
    """
    Full lifecycle test across multiple distinct users:
    - User 1: Gmail
    - User 2: Yahoo
    - User 3: Outlook
    Tests:
    1. Forgot Password generates distinct tokens
    2. Reset Password updates database password
    3. New password authenticates successfully
    4. Old password fails authentication
    5. Used token cannot be reused
    6. User 2's token is still valid after User 1 resets
    """
    user1_email = "investor1@gmail.com"
    user2_email = "investor2@yahoo.com"
    user3_email = "investor3@outlook.com"

    for e in [user1_email, user2_email, user3_email]:
        db.delete_many("users", {"email": e})
        db.delete_many("password_resets", {"email": e})

    auth_service.register_user("Investor One", user1_email, "OldPassword1!")
    auth_service.register_user("Investor Two", user2_email, "OldPassword2!")
    auth_service.register_user("Investor Three", user3_email, "OldPassword3!")

    monkeypatch.setattr(settings, "BREVO_API_KEY", "xkeysib-live-test")
    monkeypatch.setattr(settings, "BREVO_FROM_EMAIL", "noreply@finsentiment.ai")

    tokens = {}

    def capture_dispatch(to_email, to_name, raw_token, base_url):
        tokens[to_email] = raw_token
        return {"messageId": f"<msg-{to_email}>", "status": "accepted"}

    monkeypatch.setattr(auth_service, "_dispatch_reset_email_brevo", capture_dispatch)

    # Request reset for User 1 & User 2
    client.post("/api/auth/forgot-password", json={"email": user1_email})
    client.post("/api/auth/forgot-password", json={"email": user2_email})

    assert user1_email in tokens
    assert user2_email in tokens
    token1 = tokens[user1_email]
    token2 = tokens[user2_email]
    assert token1 != token2

    # User 1 resets password
    new_pwd_1 = "NewSecurePassword1!"
    res_reset = client.post("/api/auth/reset-password", json={"token": token1, "new_password": new_pwd_1})
    assert res_reset.status_code == 200

    # User 1 signs in with new password -> SUCCESS
    res_login_new = client.post("/api/auth/login", json={"email": user1_email, "password": new_pwd_1})
    assert res_login_new.status_code == 200
    assert "token" in res_login_new.json()

    # User 1 signs in with old password -> FAILS (401)
    res_login_old = client.post("/api/auth/login", json={"email": user1_email, "password": "OldPassword1!"})
    assert res_login_old.status_code == 401

    # User 1 tries to reuse the consumed token -> FAILS (400)
    res_reuse = client.post("/api/auth/reset-password", json={"token": token1, "new_password": "AnotherPassword1!"})
    assert res_reuse.status_code == 400
    assert "already been used" in res_reuse.json()["detail"].lower()

    # User 2's token is still valid and can be reset independently
    new_pwd_2 = "NewSecurePassword2!"
    res_reset_2 = client.post("/api/auth/reset-password", json={"token": token2, "new_password": new_pwd_2})
    assert res_reset_2.status_code == 200

    # User 2 signs in with new password
    res_login_2 = client.post("/api/auth/login", json={"email": user2_email, "password": new_pwd_2})
    assert res_login_2.status_code == 200


def test_brevo_non_registered_user_rejected_no_dispatch(monkeypatch):
    """Verifies that non-registered users return 404 without triggering Brevo."""
    db.delete_many("users", {"email": "nonexistent.trader999@randomfirm.com"})
    monkeypatch.setattr(settings, "BREVO_API_KEY", "xkeysib-mock")
    monkeypatch.setattr(settings, "BREVO_FROM_EMAIL", "security@finsentiment.ai")

    dispatched = []
    def mock_brevo(to_email, to_name, raw_token, base_url):
        dispatched.append(to_email)
        return {"messageId": "<unregistered>"}

    monkeypatch.setattr(auth_service, "_dispatch_reset_email_brevo", mock_brevo)

    res = client.post("/api/auth/forgot-password", json={"email": "nonexistent.trader999@randomfirm.com"})
    assert res.status_code == 404
    assert len(dispatched) == 0
    assert "not registered" in res.json()["detail"].lower()


# ==============================================================================
# SECTION 6 TEST SCENARIOS (TESTS A - H)
# ==============================================================================

def test_scenario_a_registered_email_brevo_recipient(monkeypatch):
    """TEST A: Registered email -> Brevo receives the correct recipient address."""
    email = "alice.scenario.a@testfinancial.com"
    db.delete_many("users", {"email": email})
    db.delete_many("password_resets", {"email": email})
    auth_service.register_user("Alice Trader", email, "InitialP@ss123!")

    monkeypatch.setattr(settings, "BREVO_API_KEY", "xkeysib-scenario-test")
    monkeypatch.setattr(settings, "BREVO_FROM_EMAIL", "noreply@finsentiment.ai")
    monkeypatch.setattr(settings, "BREVO_SENDER_NAME", "FIN-SENTIMENT")

    dispatched = []
    def mock_brevo(to_email, to_name, raw_token, base_url):
        dispatched.append({"to_email": to_email, "to_name": to_name, "token": raw_token})
        return {"messageId": "<msg-alice-123>", "status": "accepted"}

    monkeypatch.setattr(auth_service, "_dispatch_reset_email_brevo", mock_brevo)

    res = client.post("/api/auth/forgot-password", json={"email": email})
    assert res.status_code == 200
    assert len(dispatched) == 1
    assert dispatched[0]["to_email"] == email
    assert dispatched[0]["to_name"] == "Alice Trader"

    # Verify token was saved in MongoDB
    reset_rec = db.find_one("password_resets", {"email": email, "used": False})
    assert reset_rec is not None


def test_scenario_b_unregistered_email_no_email_and_no_token(monkeypatch):
    """TEST B: Unregistered email -> Returns 404, no email is sent, no token generated."""
    email = "unregistered.bob.999@testfinancial.com"
    db.delete_many("users", {"email": email})
    db.delete_many("password_resets", {"email": email})

    monkeypatch.setattr(settings, "BREVO_API_KEY", "xkeysib-scenario-test")
    monkeypatch.setattr(settings, "BREVO_FROM_EMAIL", "noreply@finsentiment.ai")

    dispatched = []
    def mock_brevo(to_email, to_name, raw_token, base_url):
        dispatched.append(to_email)
        return {"messageId": "<msg-unregistered>"}

    monkeypatch.setattr(auth_service, "_dispatch_reset_email_brevo", mock_brevo)

    res = client.post("/api/auth/forgot-password", json={"email": email})
    assert res.status_code == 404
    # 1. No email sent through Brevo
    assert len(dispatched) == 0
    # 2. No reset token created in MongoDB
    assert db.find_one("password_resets", {"email": email}) is None
    # 3. No user created
    assert db.find_user_by_email(email) is None
    # 4. Clear not registered error returned
    assert "not registered" in res.json()["detail"].lower()
def test_scenario_invalid_email_formats_rejected():
    """TEST 4: Invalid email format -> 422 with 'Please enter a valid email address.'"""
    invalid_cases = ["sai@", "sai.gmail.com", "@gmail.com", "   ", ""]
    for inv in invalid_cases:
        res = client.post("/api/auth/forgot-password", json={"email": inv})
        assert res.status_code == 422
        assert "valid email" in res.json()["detail"].lower()


def test_scenario_database_connection_failure(monkeypatch):
    """TEST 7: MongoDB connection failure -> 503 Server error, not unregistered message."""
    def mock_find_user_fail(email):
        raise RuntimeError("MongoDB connection timeout: unable to reach replica set")

    monkeypatch.setattr(db, "find_user_by_email", mock_find_user_fail)

    res = client.post("/api/auth/forgot-password", json={"email": "alice.test@example.com"})
    assert res.status_code == 503
    assert "database service is currently unavailable" in res.json()["detail"].lower()
    assert "not registered" not in res.json()["detail"].lower()



def test_scenario_c_registered_email_different_capitalization(monkeypatch):
    """TEST C: Registered email with different capitalization -> Correct account is found."""
    reg_email = "charlie.case@testfinancial.com"
    db.delete_many("users", {"email": reg_email})
    db.delete_many("password_resets", {"email": reg_email})
    auth_service.register_user("Charlie Analyst", reg_email, "CharlieP@ss123!")

    monkeypatch.setattr(settings, "BREVO_API_KEY", "xkeysib-scenario-test")
    monkeypatch.setattr(settings, "BREVO_FROM_EMAIL", "noreply@finsentiment.ai")

    dispatched = []
    def mock_brevo(to_email, to_name, raw_token, base_url):
        dispatched.append(to_email)
        return {"messageId": "<msg-charlie>"}

    monkeypatch.setattr(auth_service, "_dispatch_reset_email_brevo", mock_brevo)

    # Submit with UPPERCASE and mixed case
    res = client.post("/api/auth/forgot-password", json={"email": "ChArLiE.CaSe@TestFinancial.COM"})
    assert res.status_code == 200
    assert len(dispatched) == 1
    assert dispatched[0] == reg_email


def test_scenario_d_email_leading_trailing_spaces(monkeypatch):
    """TEST D: Email with leading or trailing spaces -> Correct account is found."""
    reg_email = "david.spaces@testfinancial.com"
    db.delete_many("users", {"email": reg_email})
    db.delete_many("password_resets", {"email": reg_email})
    auth_service.register_user("David Trader", reg_email, "DavidP@ss123!")

    monkeypatch.setattr(settings, "BREVO_API_KEY", "xkeysib-scenario-test")
    monkeypatch.setattr(settings, "BREVO_FROM_EMAIL", "noreply@finsentiment.ai")

    dispatched = []
    def mock_brevo(to_email, to_name, raw_token, base_url):
        dispatched.append(to_email)
        return {"messageId": "<msg-david>"}

    monkeypatch.setattr(auth_service, "_dispatch_reset_email_brevo", mock_brevo)

    # Submit with whitespace
    res = client.post("/api/auth/forgot-password", json={"email": "   david.spaces@testfinancial.com   \t"})
    assert res.status_code == 200
    assert len(dispatched) == 1
    assert dispatched[0] == reg_email


def test_scenario_e_brevo_api_failure_no_false_success(monkeypatch):
    """TEST E: Brevo API failure -> No false success message, returns 500 with error."""
    reg_email = "eva.fail@testfinancial.com"
    db.delete_many("users", {"email": reg_email})
    db.delete_many("password_resets", {"email": reg_email})
    auth_service.register_user("Eva Trader", reg_email, "EvaP@ss123!")

    monkeypatch.setattr(settings, "BREVO_API_KEY", "xkeysib-scenario-test")
    monkeypatch.setattr(settings, "BREVO_FROM_EMAIL", "noreply@finsentiment.ai")

    def mock_brevo_fail(to_email, to_name, raw_token, base_url):
        raise RuntimeError("Brevo API rejected request (400 Bad Request): Sender not verified.")

    monkeypatch.setattr(auth_service, "_dispatch_reset_email_brevo", mock_brevo_fail)

    res = client.post("/api/auth/forgot-password", json={"email": reg_email})
    # Must NOT report success when email delivery fails
    assert res.status_code == 500
    assert "failed to send password recovery email" in res.json()["detail"].lower()
    assert "sender not verified" in res.json()["detail"].lower()


def test_scenario_f_expired_reset_token_rejected():
    """TEST F: Expired reset token -> Password reset rejected."""
    reg_email = "frank.expired@testfinancial.com"
    db.delete_many("users", {"email": reg_email})
    db.delete_many("password_resets", {"email": reg_email})
    user_info = auth_service.register_user("Frank Trader", reg_email, "FrankOld123!")

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    # Expired 5 minutes ago
    expired_at = (datetime.utcnow() - timedelta(minutes=5)).isoformat() + "Z"

    db.insert_one("password_resets", {
        "token_hash": token_hash,
        "user_id": user_info["user"]["id"],
        "email": reg_email,
        "expires_at": expired_at,
        "used": False,
        "created_at": datetime.utcnow().isoformat() + "Z"
    })

    res = client.post("/api/auth/reset-password", json={"token": raw_token, "new_password": "NewValidP@ss123!"})
    assert res.status_code == 400
    assert "expired" in res.json()["detail"].lower()


def test_scenario_g_and_h_valid_reset_token_password_updated_and_old_password_fails(monkeypatch):
    """
    TEST G: Valid reset token -> Password successfully updated.
    TEST H: Old password fails and new password works.
    """
    reg_email = "grace.lifecycle@testfinancial.com"
    db.delete_many("users", {"email": reg_email})
    db.delete_many("password_resets", {"email": reg_email})
    old_pwd = "OriginalP@ssword123!"
    new_pwd = "UpdatedP@ssword456!"

    auth_service.register_user("Grace Analyst", reg_email, old_pwd)

    monkeypatch.setattr(settings, "BREVO_API_KEY", "xkeysib-scenario-test")
    monkeypatch.setattr(settings, "BREVO_FROM_EMAIL", "noreply@finsentiment.ai")

    captured_tokens = []
    def mock_brevo(to_email, to_name, raw_token, base_url):
        captured_tokens.append(raw_token)
        return {"messageId": "<msg-grace>", "status": "accepted"}

    monkeypatch.setattr(auth_service, "_dispatch_reset_email_brevo", mock_brevo)

    # 1. Request recovery
    res_req = client.post("/api/auth/forgot-password", json={"email": reg_email})
    assert res_req.status_code == 200
    assert len(captured_tokens) == 1
    token = captured_tokens[0]

    # 2. Reset password (TEST G)
    res_reset = client.post("/api/auth/reset-password", json={"token": token, "new_password": new_pwd})
    assert res_reset.status_code == 200
    assert "success" in res_reset.json()["status"].lower()

    # 3. Old password fails (TEST H)
    res_fail = client.post("/api/auth/login", json={"email": reg_email, "password": old_pwd})
    assert res_fail.status_code == 401

    # 4. New password works (TEST H)
    res_ok = client.post("/api/auth/login", json={"email": reg_email, "password": new_pwd})
    assert res_ok.status_code == 200
    assert "token" in res_ok.json()

    # 5. Token reuse rejected
    res_reuse = client.post("/api/auth/reset-password", json={"token": token, "new_password": "YetAnotherP@ss789!"})
    assert res_reuse.status_code == 400


# ==============================================================================
# DYNAMIC MONGODB RECIPIENT SELECTION & BREVO PAYLOAD TESTS (TESTS A - F)
# ==============================================================================

def test_dynamic_mongodb_recipient_selection_multi_user(monkeypatch):
    """
    Comprehensive verification of dynamic MongoDB recipient selection:
    TEST A: User A (saipaladi73@gmail.com) -> Dispatched to saipaladi73@gmail.com.
    TEST B: User B (analyst.kumar@hedgefund.com) -> Dispatched to analyst.kumar@hedgefund.com.
    TEST C: User C (patllolasaikrishnareddy0@gmail.com) -> Dispatched to patllolasaikrishnareddy0@gmail.com.
    TEST D: Unregistered User D -> 404 rejection, no Brevo call, no reset token.
    TEST E: Each user receives a unique reset token.
    TEST F: Each reset link updates only the correct user's password; cross-user isolation verified.
    """
    user_a_email = "saipaladi73@gmail.com"
    user_b_email = "analyst.kumar@hedgefund.com"
    user_c_email = "patllolasaikrishnareddy0@gmail.com"
    unregistered_email = "unregistered.stranger999@domain.org"

    # Clean state
    for e in [user_a_email, user_b_email, user_c_email, unregistered_email]:
        db.delete_many("users", {"email": e})
        db.delete_many("password_resets", {"email": e})

    user_a_info = auth_service.register_user("Sai Paladi", user_a_email, "SaiPassword123!")
    user_b_info = auth_service.register_user("Kumar Analyst", user_b_email, "KumarPassword123!")
    user_c_info = auth_service.register_user("Sai Krishna Reddy", user_c_email, "KrishnaPassword123!")

    # Configure Brevo sender
    monkeypatch.setattr(settings, "BREVO_API_KEY", "xkeysib-dynamic-recipient-test")
    monkeypatch.setattr(settings, "BREVO_FROM_EMAIL", "security@finsentiment.ai")
    monkeypatch.setattr(settings, "BREVO_SENDER_NAME", "FIN-SENTIMENT Security")

    dispatched_calls = []

    def mock_brevo_capture(to_email, to_name, raw_token, base_url):
        dispatched_calls.append({
            "to_email": to_email,
            "to_name": to_name,
            "token": raw_token,
            "base_url": base_url
        })
        return {"messageId": f"<msg-{to_email}>", "status": "accepted"}

    monkeypatch.setattr(auth_service, "_dispatch_reset_email_brevo", mock_brevo_capture)

    # --------------------------------------------------------------------------
    # TEST A: Enter saipaladi73@gmail.com -> Expected recipient: saipaladi73@gmail.com
    # --------------------------------------------------------------------------
    res_a = client.post("/api/auth/forgot-password", json={"email": user_a_email})
    assert res_a.status_code == 200
    assert len(dispatched_calls) == 1
    assert dispatched_calls[0]["to_email"] == user_a_email
    assert dispatched_calls[0]["to_name"] == "Sai Paladi"
    token_a = dispatched_calls[0]["token"]

    # Verify MongoDB reset document is linked to User A
    reset_a = db.find_one("password_resets", {"email": user_a_email, "used": False})
    assert reset_a is not None
    assert reset_a["user_id"] == user_a_info["user"]["id"]

    # --------------------------------------------------------------------------
    # TEST B: Enter User B email -> Expected recipient: That user's own registered email
    # --------------------------------------------------------------------------
    res_b = client.post("/api/auth/forgot-password", json={"email": user_b_email})
    assert res_b.status_code == 200
    assert len(dispatched_calls) == 2
    assert dispatched_calls[1]["to_email"] == user_b_email
    assert dispatched_calls[1]["to_name"] == "Kumar Analyst"
    # CRITICAL: Verify recipient is NOT saipaladi73@gmail.com and NOT BREVO_FROM_EMAIL
    assert dispatched_calls[1]["to_email"] != user_a_email
    assert dispatched_calls[1]["to_email"] != settings.brevo_from_email
    token_b = dispatched_calls[1]["token"]

    # Verify MongoDB reset document is linked to User B
    reset_b = db.find_one("password_resets", {"email": user_b_email, "used": False})
    assert reset_b is not None
    assert reset_b["user_id"] == user_b_info["user"]["id"]

    # --------------------------------------------------------------------------
    # TEST C: Enter User C email -> Expected recipient: That third user's own registered email
    # --------------------------------------------------------------------------
    res_c = client.post("/api/auth/forgot-password", json={"email": user_c_email})
    assert res_c.status_code == 200
    assert len(dispatched_calls) == 3
    assert dispatched_calls[2]["to_email"] == user_c_email
    assert dispatched_calls[2]["to_name"] == "Sai Krishna Reddy"
    # CRITICAL: Verify recipient is NOT saipaladi73@gmail.com and NOT BREVO_FROM_EMAIL
    assert dispatched_calls[2]["to_email"] != user_a_email
    assert dispatched_calls[2]["to_email"] != settings.brevo_from_email
    token_c = dispatched_calls[2]["token"]

    # Verify MongoDB reset document is linked to User C
    reset_c = db.find_one("password_resets", {"email": user_c_email, "used": False})
    assert reset_c is not None
    assert reset_c["user_id"] == user_c_info["user"]["id"]

    # --------------------------------------------------------------------------
    # TEST D: Enter unregistered email -> Expected: 404, no token, no Brevo call
    # --------------------------------------------------------------------------
    res_d = client.post("/api/auth/forgot-password", json={"email": unregistered_email})
    assert res_d.status_code == 404
    assert len(dispatched_calls) == 3  # Count unchanged, Brevo NOT called
    assert db.find_one("password_resets", {"email": unregistered_email}) is None
    assert "not registered" in res_d.json()["detail"].lower()

    # --------------------------------------------------------------------------
    # TEST E: Verify each user receives a different unique reset link / token
    # --------------------------------------------------------------------------
    assert len({token_a, token_b, token_c}) == 3
    assert token_a != token_b
    assert token_b != token_c
    assert token_a != token_c

    # --------------------------------------------------------------------------
    # TEST F: Verify reset link updates only the correct user's password
    # --------------------------------------------------------------------------
    new_pwd_b = "UpdatedKumarPassword456!"
    res_reset_b = client.post("/api/auth/reset-password", json={"token": token_b, "new_password": new_pwd_b})
    assert res_reset_b.status_code == 200
    assert "success" in res_reset_b.json()["status"].lower()

    # User B signs in with new password -> SUCCESS
    login_b_new = client.post("/api/auth/login", json={"email": user_b_email, "password": new_pwd_b})
    assert login_b_new.status_code == 200
    assert "token" in login_b_new.json()

    # User B signs in with old password -> FAILS (401)
    login_b_old = client.post("/api/auth/login", json={"email": user_b_email, "password": "KumarPassword123!"})
    assert login_b_old.status_code == 401

    # User A's password remains UNCHANGED (original password works)
    login_a = client.post("/api/auth/login", json={"email": user_a_email, "password": "SaiPassword123!"})
    assert login_a.status_code == 200

    # User C's password remains UNCHANGED (original password works)
    login_c = client.post("/api/auth/login", json={"email": user_c_email, "password": "KrishnaPassword123!"})
    assert login_c.status_code == 200

    # Consumed token B cannot be reused
    res_reuse = client.post("/api/auth/reset-password", json={"token": token_b, "new_password": "AnotherNewPwd789!"})
    assert res_reuse.status_code == 400
    assert "already been used" in res_reuse.json()["detail"].lower()


def test_brevo_api_payload_structure_and_recipient_isolation(monkeypatch):
    """
    Directly tests _dispatch_reset_email_brevo to verify that:
    1. payload['sender']['email'] matches BREVO_FROM_EMAIL.
    2. payload['to'][0]['email'] dynamically matches the recipient registered email.
    3. The recipient is NEVER replaced with BREVO_FROM_EMAIL or any hardcoded address.
    """
    monkeypatch.setattr(settings, "BREVO_API_KEY", "xkeysib-live-mock-key")
    monkeypatch.setattr(settings, "BREVO_FROM_EMAIL", "system-sender@finsentiment.ai")
    monkeypatch.setattr(settings, "BREVO_SENDER_NAME", "FIN-SENTIMENT Alert")

    captured_payloads = []

    class MockResponse:
        status_code = 201
        def json(self):
            return {"messageId": "<test-msg-id-123>"}

    class MockHttpxClient:
        def __init__(self, *args, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def post(self, url, json=None, headers=None):
            captured_payloads.append({"url": url, "payload": json, "headers": headers})
            return MockResponse()

    import httpx
    monkeypatch.setattr(httpx, "Client", MockHttpxClient)
    # Mock auto-unblock check so it doesn't try actual network call
    monkeypatch.setattr(auth_service, "_ensure_recipient_not_blocked_in_brevo", lambda email, api_key: False)

    target_user_email = "target.analyst@wallstreetfirm.org"
    target_user_name = "Target Analyst"

    res = auth_service._dispatch_reset_email_brevo(
        to_email=target_user_email,
        to_name=target_user_name,
        raw_token="secure_token_abc_123",
        base_url="https://market-tracker-umber.vercel.app"
    )

    assert res["status"] == "accepted"
    assert len(captured_payloads) == 1
    call = captured_payloads[0]
    assert call["url"] == "https://api.brevo.com/v3/smtp/email"
    assert call["headers"]["api-key"] == "xkeysib-live-mock-key"

    payload = call["payload"]
    # Sender must be system sender
    assert payload["sender"]["email"] == "system-sender@finsentiment.ai"
    assert payload["sender"]["name"] == "FIN-SENTIMENT Alert"

    # Recipient must be the registered user email, NEVER the sender
    assert len(payload["to"]) == 1
    assert payload["to"][0]["email"] == target_user_email
    assert payload["to"][0]["name"] == target_user_name
    assert payload["to"][0]["email"] != payload["sender"]["email"]
    assert "reset-password?token=secure_token_abc_123" in payload["htmlContent"]


def test_brevo_delivery_status_endpoint_and_service(monkeypatch):
    """Verifies that /api/auth/password-recovery/status queries Brevo and maps delivered/blocked events."""
    monkeypatch.setattr(settings, "BREVO_API_KEY", "xkeysib-mock-status-test")

    class MockEventsResponse:
        status_code = 200
        def json(self):
            return {
                "events": [
                    {
                        "email": "analyst.delivery@firm.org",
                        "event": "delivered",
                        "date": "2026-11-05T21:40:00Z",
                        "messageId": "<test-msg-delivered-999>"
                    }
                ]
            }

    class MockHttpx:
        def __init__(self, *args, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def get(self, url, headers=None):
            return MockEventsResponse()

    import httpx
    monkeypatch.setattr(httpx, "Client", MockHttpx)

    res = client.get("/api/auth/password-recovery/status?message_id=%3Ctest-msg-delivered-999%3E")
    assert res.status_code == 200
    data = res.json()
    assert data["message_id"] == "<test-msg-delivered-999>"
    assert data["delivery_status"] == "delivered"
    assert "delivered to recipient mailbox" in data["detail"].lower()


def test_brevo_webhook_event_processing():
    """Verifies that POST /api/webhooks/brevo updates delivery records in MongoDB."""
    msg_id = "<webhook-test-delivered-123>"
    db.insert_one("email_deliveries", {
        "message_id": msg_id,
        "email": "analyst@firm.com",
        "delivery_status": "accepted",
        "created_at": datetime.utcnow().isoformat() + "Z"
    })

    webhook_payload = {
        "event": "delivered",
        "email": "analyst@firm.com",
        "message-id": msg_id,
        "date": "2026-11-05 21:50:00",
        "subject": "Reset your FIN-SENTIMENT password"
    }

    res = client.post("/api/webhooks/brevo", json=webhook_payload)
    assert res.status_code == 200
    assert res.json()["status"] == "recorded"

    updated = db.find_one("email_deliveries", {"message_id": msg_id})
    assert updated is not None
    assert updated["delivery_status"] == "delivered"


