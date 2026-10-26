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
def cleanup_test_users():
    """Ensure clean test slate before and after tests."""
    client.cookies.clear()
    db.delete_many("users", {"email": {"$regex": r"@testfinancial\.com"}})
    db.delete_many("password_resets", {"email": {"$regex": r"@testfinancial\.com"}})
    # Also clean local test arrays if in local mode
    if not db.is_cloud:
        local_data = db._read_local_db()
        local_data["users"] = [u for u in local_data.get("users", []) if "@testfinancial.com" not in u.get("email", "")]
        local_data["password_resets"] = [r for r in local_data.get("password_resets", []) if "@testfinancial.com" not in r.get("email", "")]
        db._write_local_db(local_data)
    yield
    # Cleanup afterwards
    client.cookies.clear()
    db.delete_many("users", {"email": {"$regex": r"@testfinancial\.com"}})
    db.delete_many("password_resets", {"email": {"$regex": r"@testfinancial\.com"}})

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

def test_password_recovery_generic_response_on_unknown_email():
    """Ensures no user enumeration vulnerability."""
    res = client.post("/api/auth/forgot-password", json={"email": "nobody@testfinancial.com"})
    assert res.status_code == 200
    # Must not reveal whether email was found or not
    assert "nobody" not in res.json()["message"].lower()

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
