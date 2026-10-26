import pytest
from app.main import app
from app.services.auth_dependencies import get_current_user

MOCK_ANALYST_USER = {
    "id": "usr_test_analyst_01",
    "email": "senior.analyst@finsentiment.ai",
    "full_name": "Senior Market Analyst",
    "created_at": "2026-01-01T00:00:00Z"
}

@pytest.fixture(autouse=True)
def handle_test_auth(request):
    """
    Automatically supplies authenticated analyst session for existing market intelligence
    and inference tests, while allowing test_auth.py to test genuine unauthenticated (401),
    rate-limited (429), and session expiry scenarios.
    """
    if "test_auth" in request.node.nodeid:
        yield
    else:
        app.dependency_overrides[get_current_user] = lambda: MOCK_ANALYST_USER
        try:
            yield
        finally:
            app.dependency_overrides.pop(get_current_user, None)
