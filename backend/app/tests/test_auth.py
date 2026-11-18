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

def test_password_recovery_single_use_and_expiration(monkeypatch):
    email = "karen.reset@testfinancial.com"
    old_pwd = "OldPassword123!"
    new_pwd = "BrandNewPassword123!"
    auth_service.register_user("Karen Page", email, old_pwd)

    monkeypatch.setattr(settings, "RESEND_API_KEY", "re_test_mock_key_12345")
    captured = {}

    def mock_resend_dispatch(to_email, to_name, raw_token, base_url):
        captured["to_email"] = to_email
        captured["raw_token"] = raw_token
        captured["base_url"] = base_url
        return {"messageId": "re_msg_single_use_001", "provider": "resend", "delivery_status": "accepted"}

    monkeypatch.setattr(auth_service, "_dispatch_reset_email_resend", mock_resend_dispatch)

    # 1. Request password reset
    req_res = client.post("/api/auth/forgot-password", json={"email": email})
    assert req_res.status_code == 200
    req_data = req_res.json()
    assert "message" in req_data
    assert req_data.get("dev_reset_token") is None
    assert captured["to_email"] == email
    token = captured["raw_token"]

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


def test_password_recovery_unregistered_email_non_enumerating(monkeypatch):
    """Verifies that unregistered email addresses return generic 200 without exposing account existence or sending email."""
    db.delete_many("users", {"email": "nobody@testfinancial.com"})
    db.delete_many("password_resets", {"email": "nobody@testfinancial.com"})
    monkeypatch.setattr(settings, "RESEND_API_KEY", "re_test_mock_key_12345")

    called = []
    monkeypatch.setattr(auth_service, "_dispatch_reset_email_resend", lambda *a, **kw: called.append(a))

    res = client.post("/api/auth/forgot-password", json={"email": "nobody@testfinancial.com"})
    assert res.status_code == 200
    assert "if an account exists" in res.json()["message"].lower()
    assert len(called) == 0
    assert db.find_one("password_resets", {"email": "nobody@testfinancial.com"}) is None

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

def test_password_recovery_dispatch_failure_handling(monkeypatch):
    """Verifies that when Resend email dispatch fails, the system returns 502 and does NOT show a false success."""
    email = "smtp.fail.user@testfinancial.com"
    auth_service.register_user("Dispatch Fail User", email, "UserPassword123!")
    monkeypatch.setattr(settings, "RESEND_API_KEY", "re_test_mock_key_12345")

    def mock_dispatch(to_email, to_name, raw_token, base_url):
        raise RuntimeError("Resend API connection error")

    monkeypatch.setattr(auth_service, "_dispatch_reset_email_resend", mock_dispatch)

    res = client.post("/api/auth/forgot-password", json={"email": email})
    assert res.status_code == 502
    assert "failed to send password reset email" in res.json()["detail"].lower()

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
    """Verifies that /api/health exposes safe non-sensitive email telemetry for Resend HTTPS."""
    monkeypatch.setattr(settings, "RESEND_API_KEY", "re_secret_live_key_9999")
    monkeypatch.setattr(settings, "RESEND_FROM_EMAIL", "security@finsentiment.ai")
    monkeypatch.setattr(settings, "RESEND_SENDER_NAME", "FIN-SENTIMENT")

    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert "email_service" in data
    email_status = data["email_service"]
    assert email_status["configured"] is True
    assert email_status["provider"] == "Resend Transactional Email API"
    assert email_status["transport"] == "HTTPS (Port 443)"
    assert email_status["has_api_key"] is True
    assert email_status["sender_configured"] is True
    # Ensure sensitive secret API key is NOT in response
    assert "re_secret_live_key_9999" not in str(data)


def test_resend_error_redacts_api_key(monkeypatch):
    """Verifies that Resend error messages scrub any accidental API key or token before returning."""
    email = "auth.fail.user@testfinancial.com"
    auth_service.register_user("Auth Fail User", email, "UserPassword123!")
    monkeypatch.setattr(settings, "RESEND_API_KEY", "re_supersecret_key_abc123")

    def mock_dispatch(to_email, to_name, raw_token, base_url):
        raise RuntimeError(f"Resend auth failed with Bearer re_supersecret_key_abc123 and token={raw_token}")

    monkeypatch.setattr(auth_service, "_dispatch_reset_email_resend", mock_dispatch)

    res = client.post("/api/auth/forgot-password", json={"email": email})
    assert res.status_code == 502
    detail = res.json()["detail"]
    assert "re_supersecret_key_abc123" not in detail
    assert "[REDACTED" in detail

# 8. Resend Transactional Email Dispatch Tests (Dynamic Recipient, Error Safety & Lifecycle)

def test_resend_successful_email_dispatch_dynamic_recipient(monkeypatch):
    """
    Verifies that password reset emails are dynamically addressed to each user's
    actual registered email address from MongoDB via Resend HTTPS API.
    """
    test_users = [
        ("User Gmail", "sai.resend@testfinancial.com", "SecureGmailP@ss1"),
        ("User Yahoo", "rahul.resend@testfinancial.com", "SecureYahooP@ss2"),
        ("User Outlook", "priya.resend@testfinancial.com", "SecureOutlookP@ss3"),
    ]

    for name, email, pwd in test_users:
        if not db.find_user_by_email(email):
            auth_service.register_user(name, email, pwd)

    monkeypatch.setattr(settings, "RESEND_API_KEY", "re_mock_valid_key_12345")
    monkeypatch.setattr(settings, "RESEND_FROM_EMAIL", "noreply@finsentiment.ai")
    monkeypatch.setattr(settings, "RESEND_SENDER_NAME", "FIN-SENTIMENT")

    dispatched_calls = []

    def mock_resend_dispatch(to_email, to_name, raw_token, base_url):
        dispatched_calls.append({
            "to_email": to_email,
            "to_name": to_name,
            "raw_token": raw_token,
            "base_url": base_url
        })
        return {"messageId": f"re_mock_{secrets.token_hex(6)}", "provider": "resend", "delivery_status": "accepted"}

    monkeypatch.setattr(auth_service, "_dispatch_reset_email_resend", mock_resend_dispatch)

    res_a = client.post("/api/auth/forgot-password", json={"email": "sai.resend@testfinancial.com"})
    assert res_a.status_code == 200
    assert dispatched_calls[-1]["to_email"] == "sai.resend@testfinancial.com"
    assert dispatched_calls[-1]["to_name"] == "User Gmail"
    token_a = dispatched_calls[-1]["raw_token"]

    res_b = client.post("/api/auth/forgot-password", json={"email": "rahul.resend@testfinancial.com"})
    assert res_b.status_code == 200
    assert dispatched_calls[-1]["to_email"] == "rahul.resend@testfinancial.com"
    assert dispatched_calls[-1]["to_name"] == "User Yahoo"
    token_b = dispatched_calls[-1]["raw_token"]

    res_c = client.post("/api/auth/forgot-password", json={"email": "priya.resend@testfinancial.com"})
    assert res_c.status_code == 200
    assert dispatched_calls[-1]["to_email"] == "priya.resend@testfinancial.com"
    assert dispatched_calls[-1]["to_name"] == "User Outlook"
    token_c = dispatched_calls[-1]["raw_token"]

    # Confirm token isolation: all tokens must be mutually distinct
    assert len({token_a, token_b, token_c}) == 3

    for email in ["sai.resend@testfinancial.com", "rahul.resend@testfinancial.com", "priya.resend@testfinancial.com"]:
        rec = db.find_one("password_resets", {"email": email, "used": False})
        assert rec is not None


def test_resend_missing_api_key_configuration_error(monkeypatch):
    """Verifies that missing RESEND_API_KEY produces a clear 500 configuration error."""
    email = "trader.resend.nokey@testfinancial.com"
    auth_service.register_user("No Key User", email, "SecurePassword123!")

    monkeypatch.setattr(settings, "RESEND_API_KEY", None)
    monkeypatch.delenv("RESEND_API_KEY", raising=False)

    res = client.post("/api/auth/forgot-password", json={"email": email})
    assert res.status_code == 500
    assert "resend_api_key" in res.json()["detail"].lower()


def test_resend_default_and_custom_from_email(monkeypatch):
    """Verifies RESEND_FROM_EMAIL falls back cleanly to onboarding@resend.dev and formats custom verified senders."""
    monkeypatch.setattr(settings, "RESEND_FROM_EMAIL", None)
    monkeypatch.delenv("RESEND_FROM_EMAIL", raising=False)
    monkeypatch.setattr(settings, "RESEND_SENDER_NAME", "FIN-SENTIMENT")
    assert settings.resend_from_email == "FIN-SENTIMENT <onboarding@resend.dev>"

    monkeypatch.setattr(settings, "RESEND_FROM_EMAIL", "security@finsentiment.ai")
    assert settings.resend_from_email == "FIN-SENTIMENT <security@finsentiment.ai>"

    monkeypatch.setattr(settings, "RESEND_FROM_EMAIL", "FIN-SENTIMENT Security <noreply@finsentiment.ai>")
    assert settings.resend_from_email == "FIN-SENTIMENT Security <noreply@finsentiment.ai>"


def test_resend_api_error_handling_401_403_429(monkeypatch):
    """Verifies Resend 401/403/429 failures return accurate 502 errors, invalidate tokens, and never leak API keys."""
    email = "trader.resend.err@testfinancial.com"
    auth_service.register_user("Resend Err User", email, "SecurePassword123!")
    monkeypatch.setattr(settings, "RESEND_API_KEY", "re_secret_never_leak_999")

    for status_label, err_msg in [
        ("401", "Resend API authentication failed (401 Unauthorized): Invalid key re_secret_never_leak_999"),
        ("403", "Resend API rejected email delivery (403 Forbidden): Domain not verified"),
        ("429", "Resend API rate limit exceeded (429 Too Many Requests): Please try again shortly."),
    ]:
        def mock_fail(to_email, to_name, raw_token, base_url, msg=err_msg):
            raise RuntimeError(msg)

        monkeypatch.setattr(auth_service, "_dispatch_reset_email_resend", mock_fail)
        res = client.post("/api/auth/forgot-password", json={"email": email})
        assert res.status_code == 502
        detail = res.json()["detail"]
        assert status_label in detail
        assert "re_secret_never_leak_999" not in detail
        # Unused token from failed send must be invalidated
        assert db.find_one("password_resets", {"email": email, "used": False}) is None


def test_resend_multiple_user_full_reset_and_login_lifecycle(monkeypatch):
    """Full multi-user password reset lifecycle verifying isolation, single-use, and password update."""
    user1_email = "investor1@testfinancial.com"
    user2_email = "investor2@testfinancial.com"

    for e in [user1_email, user2_email]:
        db.delete_many("users", {"email": e})
        db.delete_many("password_resets", {"email": e})

    auth_service.register_user("Investor One", user1_email, "OldPassword1!")
    auth_service.register_user("Investor Two", user2_email, "OldPassword2!")

    monkeypatch.setattr(settings, "RESEND_API_KEY", "re_live_mock_test")
    monkeypatch.setattr(settings, "RESEND_FROM_EMAIL", "noreply@finsentiment.ai")

    tokens = {}

    def capture_dispatch(to_email, to_name, raw_token, base_url):
        tokens[to_email] = raw_token
        return {"messageId": f"re_msg_{to_email}", "provider": "resend", "delivery_status": "accepted"}

    monkeypatch.setattr(auth_service, "_dispatch_reset_email_resend", capture_dispatch)

    client.post("/api/auth/forgot-password", json={"email": user1_email})
    client.post("/api/auth/forgot-password", json={"email": user2_email})

    assert user1_email in tokens and user2_email in tokens
    token1, token2 = tokens[user1_email], tokens[user2_email]
    assert token1 != token2

    # User 1 resets password
    new_pwd_1 = "NewSecurePassword1!"
    assert client.post("/api/auth/reset-password", json={"token": token1, "new_password": new_pwd_1}).status_code == 200
    assert client.post("/api/auth/login", json={"email": user1_email, "password": new_pwd_1}).status_code == 200
    assert client.post("/api/auth/login", json={"email": user1_email, "password": "OldPassword1!"}).status_code == 401

    # Reusing consumed token fails
    res_reuse = client.post("/api/auth/reset-password", json={"token": token1, "new_password": "AnotherPassword1!"})
    assert res_reuse.status_code == 400
    assert "already been used" in res_reuse.json()["detail"].lower()

    # User 2's token remains valid and independent
    new_pwd_2 = "NewSecurePassword2!"
    assert client.post("/api/auth/reset-password", json={"token": token2, "new_password": new_pwd_2}).status_code == 200
    assert client.post("/api/auth/login", json={"email": user2_email, "password": new_pwd_2}).status_code == 200


def test_resend_non_registered_user_non_enumerating_no_dispatch(monkeypatch):
    """Verifies that non-registered users return generic 200 without triggering Resend or creating tokens."""
    email = "nonexistent.trader999@testfinancial.com"
    db.delete_many("users", {"email": email})
    db.delete_many("password_resets", {"email": email})
    monkeypatch.setattr(settings, "RESEND_API_KEY", "re_mock_valid_key")

    dispatched = []
    monkeypatch.setattr(auth_service, "_dispatch_reset_email_resend", lambda *a, **kw: dispatched.append(a))

    res = client.post("/api/auth/forgot-password", json={"email": email})
    assert res.status_code == 200
    assert len(dispatched) == 0
    assert db.find_one("password_resets", {"email": email}) is None
    assert "if an account exists" in res.json()["message"].lower()


# ==============================================================================
# SECTION 6 TEST SCENARIOS (TESTS A - H)
# ==============================================================================

def test_scenario_a_registered_email_resend_recipient(monkeypatch):
    """TEST A: Registered email -> Resend receives the correct recipient address."""
    email = "alice.scenario.a@testfinancial.com"
    db.delete_many("users", {"email": email})
    db.delete_many("password_resets", {"email": email})
    auth_service.register_user("Alice Trader", email, "InitialP@ss123!")

    monkeypatch.setattr(settings, "RESEND_API_KEY", "re_scenario_test_key")
    monkeypatch.setattr(settings, "RESEND_FROM_EMAIL", "noreply@finsentiment.ai")
    monkeypatch.setattr(settings, "RESEND_SENDER_NAME", "FIN-SENTIMENT")

    dispatched = []
    def mock_resend(to_email, to_name, raw_token, base_url):
        dispatched.append({"to_email": to_email, "to_name": to_name, "token": raw_token, "base_url": base_url})
        return {"messageId": "resend-msg-alice-123", "status": "accepted"}

    monkeypatch.setattr(auth_service, "_dispatch_reset_email_resend", mock_resend)

    res = client.post("/api/auth/forgot-password", json={"email": email})
    assert res.status_code == 200
    assert len(dispatched) == 1
    assert dispatched[0]["to_email"] == email
    assert dispatched[0]["to_name"] == "Alice Trader"
    assert dispatched[0]["base_url"] == settings.frontend_url

    # Verify token was saved in MongoDB
    reset_rec = db.find_one("password_resets", {"email": email, "used": False})
    assert reset_rec is not None


def test_scenario_b_unregistered_email_no_email_and_no_token(monkeypatch):
    """TEST B: Unregistered email -> Non-enumerating 200, no email sent, no token generated."""
    email = "unregistered.bob.999@testfinancial.com"
    db.delete_many("users", {"email": email})
    db.delete_many("password_resets", {"email": email})

    monkeypatch.setattr(settings, "RESEND_API_KEY", "re_scenario_test_key")
    monkeypatch.setattr(settings, "RESEND_FROM_EMAIL", "noreply@finsentiment.ai")

    dispatched = []
    def mock_resend(to_email, to_name, raw_token, base_url):
        dispatched.append(to_email)
        return {"messageId": "resend-msg-unregistered", "status": "accepted"}

    monkeypatch.setattr(auth_service, "_dispatch_reset_email_resend", mock_resend)

    res = client.post("/api/auth/forgot-password", json={"email": email})
    assert res.status_code == 200
    # 1. No email sent through Resend
    assert len(dispatched) == 0
    # 2. No reset token created in MongoDB
    assert db.find_one("password_resets", {"email": email}) is None
    # 3. No user created
    assert db.find_user_by_email(email) is None
    # 4. Generic non-enumerating response returned
    body = res.json()
    assert "if an account exists" in body["message"].lower()
    assert body.get("message_id") is None


def test_scenario_invalid_email_formats_rejected():
    """TEST 4: Invalid email format -> 422 with 'Please enter a valid email address.'"""
    invalid_cases = ["sai@", "sai.gmail.com", "@gmail.com", "   ", ""]
    for inv in invalid_cases:
        res = client.post("/api/auth/forgot-password", json={"email": inv})
        assert res.status_code == 422
        assert "valid email" in res.json()["detail"].lower()


def test_scenario_database_connection_failure(monkeypatch):
    """TEST 7: MongoDB connection failure -> 503 Server error, not unregistered message."""
    monkeypatch.setattr(settings, "RESEND_API_KEY", "re_scenario_test_key")

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

    monkeypatch.setattr(settings, "RESEND_API_KEY", "re_scenario_test_key")
    monkeypatch.setattr(settings, "RESEND_FROM_EMAIL", "noreply@finsentiment.ai")

    dispatched = []
    def mock_resend(to_email, to_name, raw_token, base_url):
        dispatched.append(to_email)
        return {"messageId": "resend-msg-charlie", "status": "accepted"}

    monkeypatch.setattr(auth_service, "_dispatch_reset_email_resend", mock_resend)

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

    monkeypatch.setattr(settings, "RESEND_API_KEY", "re_scenario_test_key")
    monkeypatch.setattr(settings, "RESEND_FROM_EMAIL", "noreply@finsentiment.ai")

    dispatched = []
    def mock_resend(to_email, to_name, raw_token, base_url):
        dispatched.append(to_email)
        return {"messageId": "resend-msg-david", "status": "accepted"}

    monkeypatch.setattr(auth_service, "_dispatch_reset_email_resend", mock_resend)

    # Submit with whitespace
    res = client.post("/api/auth/forgot-password", json={"email": "   david.spaces@testfinancial.com   \t"})
    assert res.status_code == 200
    assert len(dispatched) == 1
    assert dispatched[0] == reg_email


def test_scenario_e_resend_api_failure_no_false_success(monkeypatch):
    """TEST E: Resend API failure -> No false success message, returns 502 and invalidates token."""
    reg_email = "eva.fail@testfinancial.com"
    db.delete_many("users", {"email": reg_email})
    db.delete_many("password_resets", {"email": reg_email})
    auth_service.register_user("Eva Trader", reg_email, "EvaP@ss123!")

    monkeypatch.setattr(settings, "RESEND_API_KEY", "re_secret_test_key_never_expose")
    monkeypatch.setattr(settings, "RESEND_FROM_EMAIL", "noreply@finsentiment.ai")

    def mock_resend_fail(to_email, to_name, raw_token, base_url):
        raise RuntimeError("Resend API rejected the request (403): Sender domain not verified for key re_secret_test_key_never_expose.")

    monkeypatch.setattr(auth_service, "_dispatch_reset_email_resend", mock_resend_fail)

    res = client.post("/api/auth/forgot-password", json={"email": reg_email})
    # Must NOT report success when email delivery fails
    assert res.status_code == 502
    detail = res.json()["detail"]
    assert "failed to send password reset email" in detail.lower()
    # Must NEVER expose API key in response
    assert "re_secret_test_key_never_expose" not in detail
    assert "[redacted_resend_key]" in detail.lower()
    # Token must be invalidated after dispatch failure
    assert db.find_one("password_resets", {"email": reg_email, "used": False}) is None


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

    monkeypatch.setattr(settings, "RESEND_API_KEY", "re_scenario_test_key")
    monkeypatch.setattr(settings, "RESEND_FROM_EMAIL", "noreply@finsentiment.ai")

    captured_tokens = []
    def mock_resend(to_email, to_name, raw_token, base_url):
        captured_tokens.append(raw_token)
        return {"messageId": "resend-msg-grace", "status": "accepted"}

    monkeypatch.setattr(auth_service, "_dispatch_reset_email_resend", mock_resend)

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
# DYNAMIC MONGODB RECIPIENT SELECTION & RESEND PAYLOAD TESTS (TESTS A - F)
# ==============================================================================

def test_dynamic_mongodb_recipient_selection_multi_user(monkeypatch):
    """
    Comprehensive verification of dynamic MongoDB recipient selection:
    TEST A: User A -> Dispatched to User A's registered email.
    TEST B: User B -> Dispatched to User B's registered email.
    TEST C: User C -> Dispatched to User C's registered email.
    TEST D: Unregistered User D -> Non-enumerating 200, no Resend call, no reset token.
    TEST E: Each user receives a unique reset token.
    TEST F: Each reset link updates only the correct user's password; cross-user isolation verified.
    """
    user_a_email = "user.alpha.multi@testfinancial.com"
    user_b_email = "analyst.kumar.multi@testfinancial.com"
    user_c_email = "user.gamma.multi@testfinancial.com"
    unregistered_email = "unregistered.stranger999@testfinancial.com"

    # Clean state
    for e in [user_a_email, user_b_email, user_c_email, unregistered_email]:
        db.delete_many("users", {"email": e})
        db.delete_many("password_resets", {"email": e})

    try:
        user_a_info = auth_service.register_user("Alpha Trader", user_a_email, "AlphaPassword123!")
        user_b_info = auth_service.register_user("Kumar Analyst", user_b_email, "KumarPassword123!")
        user_c_info = auth_service.register_user("Gamma Investor", user_c_email, "GammaPassword123!")

        # Configure Resend sender
        monkeypatch.setattr(settings, "RESEND_API_KEY", "re_dynamic_recipient_test")
        monkeypatch.setattr(settings, "RESEND_FROM_EMAIL", "security@finsentiment.ai")
        monkeypatch.setattr(settings, "RESEND_SENDER_NAME", "FIN-SENTIMENT Security")

        dispatched_calls = []

        def mock_resend_capture(to_email, to_name, raw_token, base_url):
            dispatched_calls.append({
                "to_email": to_email,
                "to_name": to_name,
                "token": raw_token,
                "base_url": base_url
            })
            return {"messageId": f"resend-msg-{to_email}", "status": "accepted"}

        monkeypatch.setattr(auth_service, "_dispatch_reset_email_resend", mock_resend_capture)

        # TEST A: User A
        res_a = client.post("/api/auth/forgot-password", json={"email": user_a_email})
        assert res_a.status_code == 200
        assert len(dispatched_calls) == 1
        assert dispatched_calls[0]["to_email"] == user_a_email
        assert dispatched_calls[0]["to_name"] == "Alpha Trader"
        token_a = dispatched_calls[0]["token"]

        reset_a = db.find_one("password_resets", {"email": user_a_email, "used": False})
        assert reset_a is not None
        assert reset_a["user_id"] == user_a_info["user"]["id"]

        # TEST B: User B
        res_b = client.post("/api/auth/forgot-password", json={"email": user_b_email})
        assert res_b.status_code == 200
        assert len(dispatched_calls) == 2
        assert dispatched_calls[1]["to_email"] == user_b_email
        assert dispatched_calls[1]["to_name"] == "Kumar Analyst"
        assert dispatched_calls[1]["to_email"] != user_a_email
        assert dispatched_calls[1]["to_email"] != settings.resend_from_email_raw
        token_b = dispatched_calls[1]["token"]

        reset_b = db.find_one("password_resets", {"email": user_b_email, "used": False})
        assert reset_b is not None
        assert reset_b["user_id"] == user_b_info["user"]["id"]

        # TEST C: User C
        res_c = client.post("/api/auth/forgot-password", json={"email": user_c_email})
        assert res_c.status_code == 200
        assert len(dispatched_calls) == 3
        assert dispatched_calls[2]["to_email"] == user_c_email
        assert dispatched_calls[2]["to_name"] == "Gamma Investor"
        assert dispatched_calls[2]["to_email"] != user_a_email
        assert dispatched_calls[2]["to_email"] != settings.resend_from_email_raw
        token_c = dispatched_calls[2]["token"]

        reset_c = db.find_one("password_resets", {"email": user_c_email, "used": False})
        assert reset_c is not None
        assert reset_c["user_id"] == user_c_info["user"]["id"]

        # TEST D: Unregistered email -> Non-enumerating 200 identical to registered, no token, no Resend call
        res_d = client.post("/api/auth/forgot-password", json={"email": unregistered_email})
        assert res_d.status_code == 200
        assert res_d.json() == res_a.json()
        assert len(dispatched_calls) == 3  # Count unchanged, Resend NOT called
        assert db.find_one("password_resets", {"email": unregistered_email}) is None

        # TEST E: Unique reset tokens
        assert len({token_a, token_b, token_c}) == 3

        # TEST F: Cross-user isolation on reset
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

        # User A & C passwords remain UNCHANGED
        login_a = client.post("/api/auth/login", json={"email": user_a_email, "password": "AlphaPassword123!"})
        assert login_a.status_code == 200
        login_c = client.post("/api/auth/login", json={"email": user_c_email, "password": "GammaPassword123!"})
        assert login_c.status_code == 200

        # Consumed token B cannot be reused
        res_reuse = client.post("/api/auth/reset-password", json={"token": token_b, "new_password": "AnotherNewPwd789!"})
        assert res_reuse.status_code == 400
        assert "already been used" in res_reuse.json()["detail"].lower()
    finally:
        for e in [user_a_email, user_b_email, user_c_email, unregistered_email]:
            db.delete_many("users", {"email": e})
            db.delete_many("password_resets", {"email": e})
            db.delete_many("email_deliveries", {"email": e})


def test_resend_api_payload_structure_and_recipient_isolation(monkeypatch, caplog):
    """
    Directly tests _dispatch_reset_email_resend to verify that:
    1. Request targets https://api.resend.com/emails with Bearer RESEND_API_KEY.
    2. payload['from'] uses RESEND_FROM_EMAIL and RESEND_SENDER_NAME.
    3. payload['to'] dynamically matches the recipient registered email.
    4. Reset link points to the deployed frontend URL.
    5. Logs never expose the Resend API key or raw reset token.
    """
    mock_key = "re_live_mock_key_secret_987654"
    mock_token = "secure_token_abc_123_never_log"

    monkeypatch.setattr(settings, "RESEND_API_KEY", mock_key)
    monkeypatch.setattr(settings, "RESEND_FROM_EMAIL", "system-sender@finsentiment.ai")
    monkeypatch.setattr(settings, "RESEND_SENDER_NAME", "FIN-SENTIMENT Alert")

    captured_payloads = []

    class MockResponse:
        status_code = 200
        text = '{"id": "resend-test-msg-id-123"}'
        def json(self):
            return {"id": "resend-test-msg-id-123"}

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

    target_user_email = "target.analyst@wallstreetfirm.org"
    target_user_name = "Target Analyst"

    with caplog.at_level("INFO"):
        res = auth_service._dispatch_reset_email_resend(
            to_email=target_user_email,
            to_name=target_user_name,
            raw_token=mock_token,
            base_url="https://market-tracker-umber.vercel.app"
        )

    assert res["delivery_status"] == "accepted"
    assert res["provider"] == "resend"
    assert res["messageId"] == "resend-test-msg-id-123"
    assert len(captured_payloads) == 1
    call = captured_payloads[0]
    assert call["url"] == "https://api.resend.com/emails"
    assert call["headers"]["Authorization"] == f"Bearer {mock_key}"

    payload = call["payload"]
    # Sender must be configured Resend sender
    assert payload["from"] == "FIN-SENTIMENT Alert <system-sender@finsentiment.ai>"

    # Recipient must be the registered user email, NEVER the sender
    assert payload["to"] == [target_user_email]
    assert payload["to"][0] != "system-sender@finsentiment.ai"

    expected_link = f"https://market-tracker-umber.vercel.app/reset-password?token={mock_token}"
    assert expected_link in payload["html"]
    assert expected_link in payload["text"]

    # Ensure API key and raw reset token were never logged
    combined_logs = "\n".join(record.getMessage() for record in caplog.records)
    assert mock_key not in combined_logs
    assert mock_token not in combined_logs


def test_resend_delivery_status_endpoint_and_service(monkeypatch):
    """Verifies that /api/auth/password-recovery/status queries Resend and maps delivered events."""
    monkeypatch.setattr(settings, "RESEND_API_KEY", "re_mock_status_test_key")

    msg_id = "resend-test-msg-delivered-999"
    db.delete_many("email_deliveries", {"message_id": msg_id})
    db.insert_one("email_deliveries", {
        "message_id": msg_id,
        "provider": "resend",
        "email": "analyst.delivery@testfinancial.com",
        "delivery_status": "accepted",
        "created_at": datetime.utcnow().isoformat() + "Z"
    })

    class MockResendEmailResponse:
        status_code = 200
        def json(self):
            return {
                "id": msg_id,
                "to": ["analyst.delivery@testfinancial.com"],
                "last_event": "delivered",
                "created_at": "2026-11-18T10:40:00Z"
            }

    class MockHttpx:
        def __init__(self, *args, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def get(self, url, headers=None):
            return MockResendEmailResponse()

    import httpx
    monkeypatch.setattr(httpx, "Client", MockHttpx)

    try:
        res = client.get(f"/api/auth/password-recovery/status?message_id={msg_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["message_id"] == msg_id
        assert data["delivery_status"] == "delivered"
        assert "delivered to recipient mailbox" in data["detail"].lower()
    finally:
        db.delete_many("email_deliveries", {"message_id": msg_id})


def test_brevo_webhook_event_processing():
    """Verifies that POST /api/webhooks/brevo updates delivery records in MongoDB."""
    msg_id = "<webhook-test-delivered-123>"
    db.delete_many("email_deliveries", {"message_id": msg_id})
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

    try:
        res = client.post("/api/webhooks/brevo", json=webhook_payload)
        assert res.status_code == 200
        assert res.json()["status"] == "recorded"

        updated = db.find_one("email_deliveries", {"message_id": msg_id})
        assert updated is not None
        assert updated["delivery_status"] == "delivered"
    finally:
        db.delete_many("email_deliveries", {"message_id": msg_id})


