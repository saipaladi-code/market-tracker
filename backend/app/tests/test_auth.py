import secrets
import hashlib
import pytest

from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app.main import app

import app.database as database_module
from app.database import db

from app.config import settings

from app.services.auth_service import auth_service

from app.services.rate_limiter import auth_rate_limiter

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def isolate_auth_test_database(tmp_path_factory):
    """
    Isolates all auth unit tests into a temporary local JSON database so pytest
    can NEVER modify, overwrite, or pollute production MongoDB Atlas user accounts.
    """
    orig_is_cloud = db.is_cloud
    orig_db = db.db
    orig_local_file = database_module.LOCAL_DB_FILE

    temp_db_file = str(tmp_path_factory.mktemp("auth_test_db") / "local_auth_test_db.json")
    database_module.LOCAL_DB_FILE = temp_db_file
    db.is_cloud = False
    db.db = None
    db._ensure_local_db()

    try:
        yield
    finally:
        database_module.LOCAL_DB_FILE = orig_local_file
        db.is_cloud = orig_is_cloud
        db.db = orig_db


@pytest.fixture(autouse=True)
def cleanup_test_users(monkeypatch):
    """Ensure clean test slate before and after tests."""
    client.cookies.clear()
    auth_rate_limiter._attempts.clear()

    monkeypatch.setattr(settings, "BREVO_API_KEY", None)
    monkeypatch.setattr(settings, "BREVO_SENDER_EMAIL", None)
    monkeypatch.setattr(settings, "BREVO_FROM_EMAIL", None)
    monkeypatch.setattr(settings, "BREVO_SENDER_NAME", "FIN-SENTIMENT")
    monkeypatch.delenv("BREVO_API_KEY", raising=False)
    monkeypatch.delenv("BREVO_SENDER_EMAIL", raising=False)
    monkeypatch.delenv("BREVO_FROM_EMAIL", raising=False)
    monkeypatch.setattr(settings, "SMTP_HOST", None)

    local_data = db._read_local_db()
    local_data["users"] = []
    local_data["password_resets"] = []
    local_data["email_deliveries"] = []
    db._write_local_db(local_data)

    yield

    client.cookies.clear()
    auth_rate_limiter._attempts.clear()

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

    monkeypatch.setattr(settings, "BREVO_API_KEY", "xkeysib-test-mock-key-12345")
    monkeypatch.setattr(settings, "BREVO_SENDER_EMAIL", "noreply@finsentiment.ai")
    captured = {}

    def mock_brevo_dispatch(to_email, to_name, raw_token, base_url):
        captured["to_email"] = to_email
        captured["raw_token"] = raw_token
        captured["base_url"] = base_url
        return {"messageId": "<brevo-single-use-001>", "status": "accepted"}

    monkeypatch.setattr(auth_service, "_dispatch_reset_email_brevo", mock_brevo_dispatch)

    # 1. Request password reset
    req_res = client.post("/api/auth/forgot-password", json={"email": email})
    assert req_res.status_code == 200
    req_data = req_res.json()
    assert "message" in req_data
    assert req_data.get("message_id") == "<brevo-single-use-001>"
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
    monkeypatch.setattr(settings, "BREVO_API_KEY", "xkeysib-test-mock-key-12345")
    monkeypatch.setattr(settings, "BREVO_SENDER_EMAIL", "noreply@finsentiment.ai")

    called = []
    monkeypatch.setattr(auth_service, "_dispatch_reset_email_brevo", lambda *a, **kw: called.append(a))

    res = client.post("/api/auth/forgot-password", json={"email": "nobody@testfinancial.com"})
    assert res.status_code == 200
    assert "if an account exists" in res.json()["message"].lower()
    assert res.json().get("message_id") is None
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
    """Verifies that when Brevo email dispatch fails, the system returns 502 and does NOT show a false success."""
    email = "smtp.fail.user@testfinancial.com"
    auth_service.register_user("Dispatch Fail User", email, "UserPassword123!")
    monkeypatch.setattr(settings, "BREVO_API_KEY", "xkeysib-test-mock-key-12345")
    monkeypatch.setattr(settings, "BREVO_SENDER_EMAIL", "noreply@finsentiment.ai")

    def mock_dispatch(to_email, to_name, raw_token, base_url):
        raise RuntimeError("Brevo API connection error")

    monkeypatch.setattr(auth_service, "_dispatch_reset_email_brevo", mock_dispatch)

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
    """Verifies that /api/health exposes safe non-sensitive email telemetry for Brevo HTTPS."""
    monkeypatch.setattr(settings, "BREVO_API_KEY", "xkeysib-secret-live-key-9999")
    monkeypatch.setattr(settings, "BREVO_SENDER_EMAIL", "security@finsentiment.ai")
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


def test_brevo_error_redacts_api_key(monkeypatch):
    """Verifies that Brevo error messages scrub any accidental API key or token before returning."""
    email = "auth.fail.user@testfinancial.com"
    auth_service.register_user("Auth Fail User", email, "UserPassword123!")
    monkeypatch.setattr(settings, "BREVO_API_KEY", "xkeysib-supersecretkeyabc123")
    monkeypatch.setattr(settings, "BREVO_SENDER_EMAIL", "noreply@finsentiment.ai")

    def mock_dispatch(to_email, to_name, raw_token, base_url):
        raise RuntimeError(f"Brevo auth failed with xkeysib-supersecretkeyabc123 and token={raw_token}")

    monkeypatch.setattr(auth_service, "_dispatch_reset_email_brevo", mock_dispatch)

    res = client.post("/api/auth/forgot-password", json={"email": email})
    assert res.status_code == 502
    detail = res.json()["detail"]
    assert "xkeysib-supersecretkeyabc123" not in detail
    assert "[REDACTED" in detail


# 8. Brevo Transactional Email Dispatch Tests (Dynamic Recipient, Env Vars, Error Safety & Lifecycle)

def test_brevo_successful_email_dispatch_dynamic_recipient(monkeypatch):
    """
    Verifies that password reset emails are dynamically addressed to each user's
    actual registered email address from MongoDB via Brevo HTTPS API.
    """
    test_users = [
        ("User Gmail", "sai.brevo@testfinancial.com", "SecureGmailP@ss1"),
        ("User Yahoo", "rahul.brevo@testfinancial.com", "SecureYahooP@ss2"),
        ("User Outlook", "priya.brevo@testfinancial.com", "SecureOutlookP@ss3"),
    ]

    for name, email, pwd in test_users:
        if not db.find_user_by_email(email):
            auth_service.register_user(name, email, pwd)

    monkeypatch.setattr(settings, "BREVO_API_KEY", "xkeysib-mock-valid-key-12345")
    monkeypatch.setattr(settings, "BREVO_SENDER_EMAIL", "noreply@finsentiment.ai")
    monkeypatch.setattr(settings, "BREVO_SENDER_NAME", "FIN-SENTIMENT")

    dispatched_calls = []

    def mock_brevo_dispatch(to_email, to_name, raw_token, base_url):
        dispatched_calls.append({
            "to_email": to_email,
            "to_name": to_name,
            "raw_token": raw_token,
            "base_url": base_url
        })
        return {"messageId": f"<brevo_mock_{secrets.token_hex(6)}>", "status": "accepted"}

    monkeypatch.setattr(auth_service, "_dispatch_reset_email_brevo", mock_brevo_dispatch)

    res_a = client.post("/api/auth/forgot-password", json={"email": "sai.brevo@testfinancial.com"})
    assert res_a.status_code == 200
    assert dispatched_calls[-1]["to_email"] == "sai.brevo@testfinancial.com"
    assert dispatched_calls[-1]["to_name"] == "User Gmail"
    token_a = dispatched_calls[-1]["raw_token"]

    res_b = client.post("/api/auth/forgot-password", json={"email": "rahul.brevo@testfinancial.com"})
    assert res_b.status_code == 200
    assert dispatched_calls[-1]["to_email"] == "rahul.brevo@testfinancial.com"
    assert dispatched_calls[-1]["to_name"] == "User Yahoo"
    token_b = dispatched_calls[-1]["raw_token"]

    res_c = client.post("/api/auth/forgot-password", json={"email": "priya.brevo@testfinancial.com"})
    assert res_c.status_code == 200
    assert dispatched_calls[-1]["to_email"] == "priya.brevo@testfinancial.com"
    assert dispatched_calls[-1]["to_name"] == "User Outlook"
    token_c = dispatched_calls[-1]["raw_token"]

    # Confirm token isolation: all tokens must be mutually distinct
    assert len({token_a, token_b, token_c}) == 3

    for email in ["sai.brevo@testfinancial.com", "rahul.brevo@testfinancial.com", "priya.brevo@testfinancial.com"]:
        rec = db.find_one("password_resets", {"email": email, "used": False})
        assert rec is not None


def test_brevo_missing_api_key_or_sender_configuration_error(monkeypatch):
    """Verifies that missing BREVO_API_KEY or BREVO_SENDER_EMAIL produces a clear 500 configuration error."""
    email = "trader.brevo.nokey@testfinancial.com"
    auth_service.register_user("No Key User", email, "SecurePassword123!")

    # 1. Missing BREVO_API_KEY -> 500
    monkeypatch.setattr(settings, "BREVO_API_KEY", None)
    monkeypatch.setattr(settings, "BREVO_SENDER_EMAIL", "noreply@finsentiment.ai")
    res_no_key = client.post("/api/auth/forgot-password", json={"email": email})
    assert res_no_key.status_code == 500
    assert "brevo_api_key" in res_no_key.json()["detail"].lower()

    # 2. Missing BREVO_SENDER_EMAIL and BREVO_FROM_EMAIL -> 500
    monkeypatch.setattr(settings, "BREVO_API_KEY", "xkeysib-present-key")
    monkeypatch.setattr(settings, "BREVO_SENDER_EMAIL", None)
    monkeypatch.setattr(settings, "BREVO_FROM_EMAIL", None)
    res_no_sender = client.post("/api/auth/forgot-password", json={"email": email})
    assert res_no_sender.status_code == 500
    assert "brevo_sender_email" in res_no_sender.json()["detail"].lower()


def test_brevo_sender_email_env_var_precedence(monkeypatch):
    """Verifies BREVO_SENDER_EMAIL is supported with BREVO_FROM_EMAIL as backward-compatible alias."""
    monkeypatch.setattr(settings, "BREVO_SENDER_EMAIL", None)
    monkeypatch.setattr(settings, "BREVO_FROM_EMAIL", "legacy@finsentiment.ai")
    assert settings.brevo_sender_email == "legacy@finsentiment.ai"
    assert settings.brevo_from_email == "legacy@finsentiment.ai"

    monkeypatch.setattr(settings, "BREVO_SENDER_EMAIL", "verified@finsentiment.ai")
    assert settings.brevo_sender_email == "verified@finsentiment.ai"
    assert settings.brevo_from_email == "verified@finsentiment.ai"


def test_brevo_api_error_handling_400_401_403_429_and_unconfirmed_message_id(monkeypatch):
    """Verifies Brevo 400/401/403/429 and missing messageId return 502, invalidate tokens, and never leak API keys."""
    email = "trader.brevo.err@testfinancial.com"
    auth_service.register_user("Brevo Err User", email, "SecurePassword123!")
    monkeypatch.setattr(settings, "BREVO_API_KEY", "xkeysib-secretneverleak999")
    monkeypatch.setattr(settings, "BREVO_SENDER_EMAIL", "noreply@finsentiment.ai")

    for status_label, err_msg in [
        ("400", "Brevo API rejected request (400 Bad Request): Sender not verified"),
        ("401", "Brevo API authentication failed (401 Unauthorized): Invalid key xkeysib-secretneverleak999"),
        ("403", "Brevo API error (403 Forbidden): Account not activated"),
        ("429", "Brevo API rate limit exceeded (429 Too Many Requests): Please try again shortly."),
    ]:
        def mock_fail(to_email, to_name, raw_token, base_url, msg=err_msg):
            raise RuntimeError(msg)

        monkeypatch.setattr(auth_service, "_dispatch_reset_email_brevo", mock_fail)
        res = client.post("/api/auth/forgot-password", json={"email": email})
        assert res.status_code == 502
        detail = res.json()["detail"]
        assert status_label in detail
        assert "xkeysib-secretneverleak999" not in detail
        assert db.find_one("password_resets", {"email": email, "used": False}) is None

    # Never report success when Brevo does not return a confirmed messageId
    monkeypatch.setattr(auth_service, "_dispatch_reset_email_brevo", lambda *a, **kw: {"status": "accepted"})
    res_no_id = client.post("/api/auth/forgot-password", json={"email": email})
    assert res_no_id.status_code == 502
    assert "messageid" in res_no_id.json()["detail"].lower()
    assert db.find_one("password_resets", {"email": email, "used": False}) is None


def test_login_email_normalization_whitespace_and_case_insensitivity():
    """Verifies /api/auth/login normalizes email whitespace and casing consistently while rejecting wrong passwords."""
    reg_email = "Analyst.MixedCase@TestFinancial.com"
    pwd = "StrongLoginP@ss123!"
    auth_service.register_user("Mixed Case Analyst", reg_email, pwd)

    # Login with uppercase + surrounding whitespace succeeds
    res_ok = client.post("/api/auth/login", json={
        "email": "   ANALYST.MIXEDCASE@testfinancial.COM  ",
        "password": pwd,
        "remember_me": True
    })
    assert res_ok.status_code == 200
    assert res_ok.json()["user"]["email"] == reg_email.lower()
    assert "token" in res_ok.json()

    # Wrong password still returns 401
    res_bad = client.post("/api/auth/login", json={
        "email": reg_email.lower(),
        "password": "WrongPassword999!"
    })
    assert res_bad.status_code == 401


def test_brevo_multiple_user_full_reset_and_login_lifecycle(monkeypatch):
    """Full multi-user password reset lifecycle verifying isolation, single-use, and password update."""
    user1_email = "investor1@testfinancial.com"
    user2_email = "investor2@testfinancial.com"

    auth_service.register_user("Investor One", user1_email, "OldPassword1!")
    auth_service.register_user("Investor Two", user2_email, "OldPassword2!")

    monkeypatch.setattr(settings, "BREVO_API_KEY", "xkeysib-live-mock-test")
    monkeypatch.setattr(settings, "BREVO_SENDER_EMAIL", "noreply@finsentiment.ai")

    tokens = {}

    def capture_dispatch(to_email, to_name, raw_token, base_url):
        tokens[to_email] = raw_token
        return {"messageId": f"<brevo_msg_{to_email}>", "status": "accepted"}

    monkeypatch.setattr(auth_service, "_dispatch_reset_email_brevo", capture_dispatch)

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


def test_brevo_non_registered_user_non_enumerating_no_dispatch(monkeypatch):
    """Verifies that non-registered users return generic 200 without triggering Brevo or creating tokens."""
    email = "nonexistent.trader999@testfinancial.com"
    monkeypatch.setattr(settings, "BREVO_API_KEY", "xkeysib-mock-valid-key")
    monkeypatch.setattr(settings, "BREVO_SENDER_EMAIL", "noreply@finsentiment.ai")

    dispatched = []
    monkeypatch.setattr(auth_service, "_dispatch_reset_email_brevo", lambda *a, **kw: dispatched.append(a))

    res = client.post("/api/auth/forgot-password", json={"email": email})
    assert res.status_code == 200
    assert len(dispatched) == 0
    assert db.find_one("password_resets", {"email": email}) is None
    assert "if an account exists" in res.json()["message"].lower()


# ==============================================================================
# SECTION 6 TEST SCENARIOS (TESTS A - H)
# ==============================================================================

def test_scenario_a_registered_email_brevo_recipient(monkeypatch):
    """TEST A: Registered email -> Brevo receives the correct recipient address."""
    email = "alice.scenario.a@testfinancial.com"
    auth_service.register_user("Alice Trader", email, "InitialP@ss123!")

    monkeypatch.setattr(settings, "BREVO_API_KEY", "xkeysib-scenario-test-key")
    monkeypatch.setattr(settings, "BREVO_SENDER_EMAIL", "noreply@finsentiment.ai")
    monkeypatch.setattr(settings, "BREVO_SENDER_NAME", "FIN-SENTIMENT")

    dispatched = []
    def mock_brevo(to_email, to_name, raw_token, base_url):
        dispatched.append({"to_email": to_email, "to_name": to_name, "token": raw_token, "base_url": base_url})
        return {"messageId": "<brevo-msg-alice-123>", "status": "accepted"}

    monkeypatch.setattr(auth_service, "_dispatch_reset_email_brevo", mock_brevo)

    res = client.post("/api/auth/forgot-password", json={"email": email})
    assert res.status_code == 200
    assert res.json()["message_id"] == "<brevo-msg-alice-123>"
    assert len(dispatched) == 1
    assert dispatched[0]["to_email"] == email
    assert dispatched[0]["to_name"] == "Alice Trader"
    assert dispatched[0]["base_url"] == settings.frontend_url

    reset_rec = db.find_one("password_resets", {"email": email, "used": False})
    assert reset_rec is not None


def test_scenario_b_unregistered_email_no_email_and_no_token(monkeypatch):
    """TEST B: Unregistered email -> Non-enumerating 200, no email sent, no token generated."""
    email = "unregistered.bob.999@testfinancial.com"

    monkeypatch.setattr(settings, "BREVO_API_KEY", "xkeysib-scenario-test-key")
    monkeypatch.setattr(settings, "BREVO_SENDER_EMAIL", "noreply@finsentiment.ai")

    dispatched = []
    def mock_brevo(to_email, to_name, raw_token, base_url):
        dispatched.append(to_email)
        return {"messageId": "<brevo-msg-unregistered>", "status": "accepted"}

    monkeypatch.setattr(auth_service, "_dispatch_reset_email_brevo", mock_brevo)

    res = client.post("/api/auth/forgot-password", json={"email": email})
    assert res.status_code == 200
    assert len(dispatched) == 0
    assert db.find_one("password_resets", {"email": email}) is None
    assert db.find_user_by_email(email) is None
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
    monkeypatch.setattr(settings, "BREVO_API_KEY", "xkeysib-scenario-test-key")
    monkeypatch.setattr(settings, "BREVO_SENDER_EMAIL", "noreply@finsentiment.ai")

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
    auth_service.register_user("Charlie Analyst", reg_email, "CharlieP@ss123!")

    monkeypatch.setattr(settings, "BREVO_API_KEY", "xkeysib-scenario-test-key")
    monkeypatch.setattr(settings, "BREVO_SENDER_EMAIL", "noreply@finsentiment.ai")

    dispatched = []
    def mock_brevo(to_email, to_name, raw_token, base_url):
        dispatched.append(to_email)
        return {"messageId": "<brevo-msg-charlie>", "status": "accepted"}

    monkeypatch.setattr(auth_service, "_dispatch_reset_email_brevo", mock_brevo)

    res = client.post("/api/auth/forgot-password", json={"email": "ChArLiE.CaSe@TestFinancial.COM"})
    assert res.status_code == 200
    assert len(dispatched) == 1
    assert dispatched[0] == reg_email


def test_scenario_d_email_leading_trailing_spaces(monkeypatch):
    """TEST D: Email with leading or trailing spaces -> Correct account is found."""
    reg_email = "david.spaces@testfinancial.com"
    auth_service.register_user("David Trader", reg_email, "DavidP@ss123!")

    monkeypatch.setattr(settings, "BREVO_API_KEY", "xkeysib-scenario-test-key")
    monkeypatch.setattr(settings, "BREVO_SENDER_EMAIL", "noreply@finsentiment.ai")

    dispatched = []
    def mock_brevo(to_email, to_name, raw_token, base_url):
        dispatched.append(to_email)
        return {"messageId": "<brevo-msg-david>", "status": "accepted"}

    monkeypatch.setattr(auth_service, "_dispatch_reset_email_brevo", mock_brevo)

    res = client.post("/api/auth/forgot-password", json={"email": "   david.spaces@testfinancial.com   \t"})
    assert res.status_code == 200
    assert len(dispatched) == 1
    assert dispatched[0] == reg_email


def test_scenario_e_brevo_api_failure_no_false_success(monkeypatch):
    """TEST E: Brevo API failure -> No false success message, returns 502 and invalidates token."""
    reg_email = "eva.fail@testfinancial.com"
    auth_service.register_user("Eva Trader", reg_email, "EvaP@ss123!")

    monkeypatch.setattr(settings, "BREVO_API_KEY", "xkeysib-secrettestkeyneverexpose")
    monkeypatch.setattr(settings, "BREVO_SENDER_EMAIL", "noreply@finsentiment.ai")

    def mock_brevo_fail(to_email, to_name, raw_token, base_url):
        raise RuntimeError("Brevo API rejected request (400 Bad Request): Sender not verified for key xkeysib-secrettestkeyneverexpose.")

    monkeypatch.setattr(auth_service, "_dispatch_reset_email_brevo", mock_brevo_fail)

    res = client.post("/api/auth/forgot-password", json={"email": reg_email})
    assert res.status_code == 502
    detail = res.json()["detail"]
    assert "failed to send password reset email" in detail.lower()
    assert "xkeysib-secrettestkeyneverexpose" not in detail
    assert "[redacted_key]" in detail.lower()
    assert db.find_one("password_resets", {"email": reg_email, "used": False}) is None


def test_scenario_f_expired_reset_token_rejected():
    """TEST F: Expired reset token -> Password reset rejected."""
    reg_email = "frank.expired@testfinancial.com"
    user_info = auth_service.register_user("Frank Trader", reg_email, "FrankOld123!")

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
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
    old_pwd = "OriginalP@ssword123!"
    new_pwd = "UpdatedP@ssword456!"

    auth_service.register_user("Grace Analyst", reg_email, old_pwd)

    monkeypatch.setattr(settings, "BREVO_API_KEY", "xkeysib-scenario-test-key")
    monkeypatch.setattr(settings, "BREVO_SENDER_EMAIL", "noreply@finsentiment.ai")

    captured_tokens = []
    def mock_brevo(to_email, to_name, raw_token, base_url):
        captured_tokens.append(raw_token)
        return {"messageId": "<brevo-msg-grace>", "status": "accepted"}

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
    Comprehensive verification of dynamic recipient selection via Brevo:
    TEST A-C: Users A, B, C each receive reset email at their own registered email.
    TEST D: Unregistered User D -> Generic 200, no Brevo call, no reset token.
    TEST E: Each user receives a unique reset token.
    TEST F: Each reset link updates only the correct user's password; cross-user isolation verified.
    """
    user_a_email = "user.alpha.multi@testfinancial.com"
    user_b_email = "analyst.kumar.multi@testfinancial.com"
    user_c_email = "user.gamma.multi@testfinancial.com"
    unregistered_email = "unregistered.stranger999@testfinancial.com"

    user_a_info = auth_service.register_user("Alpha Trader", user_a_email, "AlphaPassword123!")
    user_b_info = auth_service.register_user("Kumar Analyst", user_b_email, "KumarPassword123!")
    user_c_info = auth_service.register_user("Gamma Investor", user_c_email, "GammaPassword123!")

    monkeypatch.setattr(settings, "BREVO_API_KEY", "xkeysib-dynamic-recipient-test")
    monkeypatch.setattr(settings, "BREVO_SENDER_EMAIL", "security@finsentiment.ai")
    monkeypatch.setattr(settings, "BREVO_SENDER_NAME", "FIN-SENTIMENT Security")

    dispatched_calls = []

    def mock_brevo_capture(to_email, to_name, raw_token, base_url):
        dispatched_calls.append({
            "to_email": to_email,
            "to_name": to_name,
            "token": raw_token,
            "base_url": base_url
        })
        return {"messageId": f"<brevo-msg-{to_email}>", "status": "accepted"}

    monkeypatch.setattr(auth_service, "_dispatch_reset_email_brevo", mock_brevo_capture)

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
    assert dispatched_calls[1]["to_email"] != settings.brevo_sender_email
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
    assert dispatched_calls[2]["to_email"] != settings.brevo_sender_email
    token_c = dispatched_calls[2]["token"]

    reset_c = db.find_one("password_resets", {"email": user_c_email, "used": False})
    assert reset_c is not None
    assert reset_c["user_id"] == user_c_info["user"]["id"]

    # TEST D: Unregistered email -> Non-enumerating 200, no token, no Brevo call
    res_d = client.post("/api/auth/forgot-password", json={"email": unregistered_email})
    assert res_d.status_code == 200
    assert res_d.json().get("message_id") is None
    assert len(dispatched_calls) == 3
    assert db.find_one("password_resets", {"email": unregistered_email}) is None

    # TEST E: Unique reset tokens
    assert len({token_a, token_b, token_c}) == 3

    # TEST F: Cross-user isolation on reset
    new_pwd_b = "UpdatedKumarPassword456!"
    res_reset_b = client.post("/api/auth/reset-password", json={"token": token_b, "new_password": new_pwd_b})
    assert res_reset_b.status_code == 200
    assert "success" in res_reset_b.json()["status"].lower()

    login_b_new = client.post("/api/auth/login", json={"email": user_b_email, "password": new_pwd_b})
    assert login_b_new.status_code == 200
    assert "token" in login_b_new.json()

    login_b_old = client.post("/api/auth/login", json={"email": user_b_email, "password": "KumarPassword123!"})
    assert login_b_old.status_code == 401

    login_a = client.post("/api/auth/login", json={"email": user_a_email, "password": "AlphaPassword123!"})
    assert login_a.status_code == 200
    login_c = client.post("/api/auth/login", json={"email": user_c_email, "password": "GammaPassword123!"})
    assert login_c.status_code == 200

    res_reuse = client.post("/api/auth/reset-password", json={"token": token_b, "new_password": "AnotherNewPwd789!"})
    assert res_reuse.status_code == 400
    assert "already been used" in res_reuse.json()["detail"].lower()


def test_brevo_api_payload_structure_and_recipient_isolation(monkeypatch, caplog):
    """
    Directly tests _dispatch_reset_email_brevo to verify that:
    1. Request targets https://api.brevo.com/v3/smtp/email with api-key BREVO_API_KEY.
    2. payload['sender']['email'] matches BREVO_SENDER_EMAIL.
    3. payload['to'][0]['email'] dynamically matches the recipient registered email.
    4. Reset link points to the deployed frontend URL.
    5. Logs never expose the Brevo API key or raw reset token.
    """
    mock_key = "xkeysib-livemockkeysecret987654"
    mock_token = "secure_token_abc_123_never_log"

    monkeypatch.setattr(settings, "BREVO_API_KEY", mock_key)
    monkeypatch.setattr(settings, "BREVO_SENDER_EMAIL", "system-sender@finsentiment.ai")
    monkeypatch.setattr(settings, "BREVO_SENDER_NAME", "FIN-SENTIMENT Alert")

    captured_payloads = []

    class MockResponse:
        status_code = 201
        text = '{"messageId": "<brevo-test-msg-id-123>"}'
        def json(self):
            return {"messageId": "<brevo-test-msg-id-123>"}

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
    monkeypatch.setattr(auth_service, "_ensure_recipient_not_blocked_in_brevo", lambda email, api_key: False)

    target_user_email = "target.analyst@wallstreetfirm.org"
    target_user_name = "Target Analyst"

    with caplog.at_level("INFO"):
        res = auth_service._dispatch_reset_email_brevo(
            to_email=target_user_email,
            to_name=target_user_name,
            raw_token=mock_token,
            base_url="https://market-tracker-umber.vercel.app"
        )

    assert res["status"] == "accepted"
    assert res["messageId"] == "<brevo-test-msg-id-123>"
    assert len(captured_payloads) == 1
    call = captured_payloads[0]
    assert call["url"] == "https://api.brevo.com/v3/smtp/email"
    assert call["headers"]["api-key"] == mock_key

    payload = call["payload"]
    assert payload["sender"]["email"] == "system-sender@finsentiment.ai"
    assert payload["sender"]["name"] == "FIN-SENTIMENT Alert"
    assert len(payload["to"]) == 1
    assert payload["to"][0]["email"] == target_user_email
    assert payload["to"][0]["name"] == target_user_name
    assert payload["to"][0]["email"] != payload["sender"]["email"]

    expected_link = f"https://market-tracker-umber.vercel.app/reset-password?token={mock_token}"
    assert expected_link in payload["htmlContent"]
    assert expected_link in payload["textContent"]

    combined_logs = "\n".join(record.getMessage() for record in caplog.records)
    assert mock_key not in combined_logs
    assert mock_token not in combined_logs


def test_brevo_delivery_status_endpoint_and_service(monkeypatch):
    """Verifies that /api/auth/password-recovery/status queries Brevo and maps delivered events."""
    monkeypatch.setattr(settings, "BREVO_API_KEY", "xkeysib-mock-status-test")

    msg_id = "<brevo-test-msg-delivered-999>"
    db.insert_one("email_deliveries", {
        "message_id": msg_id,
        "provider": "brevo",
        "email": "analyst.delivery@testfinancial.com",
        "delivery_status": "accepted",
        "created_at": datetime.utcnow().isoformat() + "Z"
    })

    class MockEventsResponse:
        status_code = 200
        def json(self):
            return {
                "events": [
                    {
                        "email": "analyst.delivery@testfinancial.com",
                        "event": "delivered",
                        "date": "2026-11-18T10:40:00Z",
                        "messageId": msg_id
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

    res = client.get("/api/auth/password-recovery/status?message_id=%3Cbrevo-test-msg-delivered-999%3E")
    assert res.status_code == 200
    data = res.json()
    assert data["message_id"] == msg_id
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


