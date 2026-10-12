"""Security headers on every response; per-user limit on OpenAI-backed endpoints."""
from fastapi.testclient import TestClient

from presentation.backend.app import http_hardening
from presentation.backend.app.main import app

client = TestClient(app, raise_server_exceptions=False)


def test_security_headers_on_public_and_refused_responses():
    for response in (client.get("/api/v1/health"), client.get("/api/v1/incidents")):
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["Referrer-Policy"] == "no-referrer"
        assert response.headers["Cache-Control"] == "no-store"


ALICE = {"Authorization": "Basic YWxpY2U6eA=="}  # alice:x
BOB = {"Authorization": "Basic Ym9iOng="}  # bob:x
URL = "/api/v1/investigator/evidence/ssh/S1/ask"


def as_signed_in(monkeypatch):
    """Requests pass authentication (the endpoint then fails for the dummy ID, which still counts)."""
    from presentation.backend.app.authentication import current_principal
    from presentation.backend.app.authorization import Principal
    app.dependency_overrides[current_principal] = lambda: Principal("x", frozenset({"administrator"}), frozenset({"ZONE-A"}))
    monkeypatch.setenv("DCG_INVESTIGATOR_ENABLED", "0")


def test_openai_backed_endpoints_are_rate_limited_per_user(monkeypatch):
    monkeypatch.setenv("DCG_OPENAI_CALLS_PER_MINUTE", "2")
    as_signed_in(monkeypatch)
    try:
        statuses = [client.post(URL, json={"question": "why?"}, headers=ALICE).status_code for _ in range(3)]
        assert 429 not in statuses[:2] and statuses[2] == 429
        limited = client.post(URL, json={"question": "why?"}, headers=ALICE)
        assert limited.status_code == 429 and int(limited.headers["Retry-After"]) >= 1
        assert client.post(URL, json={"question": "why?"}, headers=BOB).status_code != 429  # own window
    finally:
        app.dependency_overrides.clear()


def test_unauthenticated_requests_cannot_use_up_a_users_quota(monkeypatch):
    monkeypatch.setenv("DCG_OPENAI_CALLS_PER_MINUTE", "2")
    for _ in range(5):  # forged "alice" header, wrong password: 401, never counted
        assert client.post(URL, json={"question": "why?"}, headers=ALICE).status_code == 401
    as_signed_in(monkeypatch)
    try:
        assert client.post(URL, json={"question": "why?"}, headers=ALICE).status_code != 429
    finally:
        app.dependency_overrides.clear()


def test_other_endpoints_are_not_rate_limited(monkeypatch):
    monkeypatch.setenv("DCG_OPENAI_CALLS_PER_MINUTE", "1")
    assert all(client.get("/api/v1/health").status_code == 200 for _ in range(5))


def test_window_expires():
    http_hardening.reset()
    assert http_hardening.allow("u", now=0)[0]
    for t in range(1, 10):
        http_hardening.allow("u", now=t)
    assert not http_hardening.allow("u", now=30)[0]
    assert http_hardening.allow("u", now=61)[0]
