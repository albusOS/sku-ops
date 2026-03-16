"""Health endpoint tests — liveness, readiness, and AI availability.

Validates response schemas, status codes, and that health checks
correctly report infrastructure state.
"""


# ── Liveness probe ───────────────────────────────────────────────────────────


def test_health_returns_ok(client):
    resp = client.get("/api/beta/shared/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "env" in data
    assert "uptime_seconds" in data
    assert isinstance(data["uptime_seconds"], (int, float))
    assert data["uptime_seconds"] >= 0


def test_health_no_auth_required(client):
    """Health endpoint must be accessible without authentication."""
    resp = client.get("/api/beta/shared/health")
    assert resp.status_code == 200


# ── Readiness probe ──────────────────────────────────────────────────────────


def test_ready_returns_checks(client):
    resp = client.get("/api/beta/shared/ready")
    data = resp.json()
    assert "status" in data
    assert "checks" in data
    checks = data["checks"]
    assert "database" in checks


def test_ready_db_check_has_latency(client):
    resp = client.get("/api/beta/shared/ready")
    if resp.status_code == 200:
        db_check = resp.json()["checks"]["database"]
        assert db_check["status"] == "ok"
        assert "latency_ms" in db_check
        assert db_check["latency_ms"] >= 0


def test_ready_no_auth_required(client):
    """Readiness endpoint must be accessible without authentication."""
    resp = client.get("/api/beta/shared/ready")
    assert resp.status_code in (200, 503)


# ── AI availability ──────────────────────────────────────────────────────────


def test_ai_health_returns_status(client):
    resp = client.get("/api/beta/shared/health/ai")
    data = resp.json()
    assert "status" in data
    assert data["status"] in ("ok", "unavailable")


def test_ai_health_no_auth_required(client):
    """AI health endpoint must be accessible without authentication."""
    resp = client.get("/api/beta/shared/health/ai")
    assert resp.status_code in (200, 503)
