"""E2E test fixtures — full ASGI app with WebSocket event collection.

These fixtures boot the real app (with lifespan), provide an HTTP client
and a parallel WebSocket collector so tests can assert both HTTP responses
AND the domain events that arrive over the wire.
"""

import contextlib
import json
import threading
import time

import anyio
import pytest
from starlette.testclient import TestClient

from shared.kernel.constants import DEFAULT_ORG_ID
from tests.helpers.auth import (
    CONTRACTOR_USER_ID,
    admin_headers,
    admin_token,
    contractor_headers,
)

# ── Full-app client with lifespan ────────────────────────────────────────────


def _seed_contractor(app_client: TestClient) -> str:
    """Ensure the contractor test user row exists in the DB.

    The JWT in ``contractor_headers()`` references the seeded contractor user ID.
    We insert directly via the app's DB connection since there's no public
    API to create contractor users in test mode.
    """

    from shared.infrastructure.db import sql_execute

    async def _insert():
        cursor = await sql_execute("SELECT id FROM users WHERE id = $1", (CONTRACTOR_USER_ID,))
        if cursor.rows:
            return
        await sql_execute(
            "INSERT INTO users (id, email, password, name, role, company, billing_entity, is_active, organization_id, created_at)"
            " VALUES ($1, $2, $3, $4, $5, $6, $7, TRUE, $8, NOW())",
            (
                CONTRACTOR_USER_ID,
                "contractor@test.com",
                "unused",
                "E2E Contractor",
                "contractor",
                "E2E Corp",
                "E2E Corp",
                DEFAULT_ORG_ID,
            ),
        )

    app_client.portal.call(_insert)
    return CONTRACTOR_USER_ID


def _seed_dept(client: TestClient, headers: dict) -> str:
    """Create the Hardware department via API, return its ID.

    Idempotent — if the department already exists, returns its ID.
    """
    resp = client.get("/api/beta/catalog/departments", headers=headers)
    if resp.status_code == 200:
        for dept in resp.json():
            if dept.get("code") == "HDW":
                return dept["id"]

    resp = client.post(
        "/api/beta/catalog/departments",
        json={
            "name": "Hardware",
            "code": "HDW",
            "description": "Hardware dept",
        },
        headers=headers,
    )
    assert resp.status_code == 200, f"Department seed failed: {resp.status_code} {resp.text}"
    return resp.json()["id"]


@pytest.fixture(scope="session")
def app_client(_app_client):
    """Alias for the root session-scoped TestClient.

    E2E tests use app_client; we reuse the single shared instance to avoid
    spinning up a second lifespan that would fight over the DB pool singleton.
    """
    return _app_client


@pytest.fixture(scope="session")
def seed_dept_id(app_client, seed_contractor_id):
    """Seed the Hardware department once and expose its ID to all tests.

    Depends on seed_contractor_id so contractor exists for withdrawal tests.
    """
    return _seed_dept(app_client, admin_headers())


@pytest.fixture(scope="session")
def seed_contractor_id(app_client):
    """Seed the contractor test user once and expose its ID to all tests."""
    return _seed_contractor(app_client)


@pytest.fixture
def client(app_client):
    """Per-test alias — lets tests declare just ``client``."""
    return app_client


@pytest.fixture
def auth() -> dict[str, str]:
    """Admin auth headers for HTTP requests."""
    return admin_headers()


@pytest.fixture
def contractor_auth() -> dict[str, str]:
    """Contractor auth headers for HTTP requests."""
    return contractor_headers()


# ── WebSocket event collector ────────────────────────────────────────────────


class WSEventCollector:
    """Connects to /api/beta/shared/ws and records all events in a background thread.

    Uses anyio timed receives through the TestClient portal so the reader
    thread can be cleanly stopped without blocking indefinitely.
    """

    def __init__(self) -> None:
        self.events: list[dict] = []
        self._ws = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._lock = threading.Lock()

    def start(self, client: TestClient, token: str | None = None) -> None:
        token = token or admin_token()
        self._ws = client.websocket_connect(f"/api/beta/shared/ws?token={token}")
        self._ws.__enter__()
        self._thread = threading.Thread(target=self._reader, daemon=True)
        self._thread.start()

    def _reader(self) -> None:
        while not self._stop.is_set():
            try:
                msg = self._receive_with_timeout(0.3)
            except Exception:
                if self._stop.is_set():
                    return
                continue
            if msg is None:
                continue
            if msg.get("type") == "ping":
                continue
            with self._lock:
                self.events.append(msg)

    def _receive_with_timeout(self, timeout: float) -> dict | None:
        """Receive one WS message with a timeout, returning None on timeout."""
        ws = self._ws

        async def _timed_recv():
            with anyio.move_on_after(timeout) as scope:  # type: ignore[misc]
                return await ws._send_rx.receive()
            if scope.cancelled_caught:
                return None
            return None

        message = ws.portal.call(_timed_recv)
        if message is None:
            return None
        if message.get("type") == "websocket.close":
            return None
        text = message.get("text")
        if not text:
            return None
        return json.loads(text)

    def wait_for(self, event_type: str, *, timeout: float = 3.0) -> dict | None:
        """Block until an event of *event_type* arrives, or timeout."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with self._lock:
                for ev in self.events:
                    if ev.get("type") == event_type:
                        return ev
            time.sleep(0.05)
        return None

    def all_of_type(self, event_type: str) -> list[dict]:
        with self._lock:
            return [e for e in self.events if e.get("type") == event_type]

    def close(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
        if self._ws:
            with contextlib.suppress(Exception):
                self._ws.__exit__(None, None, None)

    def clear(self) -> None:
        with self._lock:
            self.events.clear()


@pytest.fixture
def ws_events(client):
    """A connected WebSocket collector that records events during the test."""
    collector = WSEventCollector()
    collector.start(client)
    yield collector
    collector.close()
