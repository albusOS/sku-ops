"""Integration tests for WebSocket endpoints.

Tests cover:
  - /api/beta/shared/ws     — realtime domain event broadcasting
  - /api/beta/assistant/ws/chat — AI chat streaming (protocol handshake only; LLM mocked)
"""

import threading

import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from shared.kernel import events
from shared.kernel.constants import DEFAULT_ORG_ID
from tests.helpers.auth import make_token as _make_token


def _assert_ws_close(client: TestClient, url: str, expected_code: int):
    """Connect and assert the server closes with the given code."""
    try:
        with client.websocket_connect(url):
            pass
        pytest.fail(f"Expected WebSocketDisconnect({expected_code})")
    except WebSocketDisconnect as exc:
        assert exc.code == expected_code, (
            f"Expected close code {expected_code}, got {exc.code}"
        )


# ── /api/beta/shared/ws (realtime domain events) ────────────────────────────────────────


class TestRealtimeWebSocket:
    def test_rejects_missing_token(self, client: TestClient):
        _assert_ws_close(client, "/api/beta/shared/ws", 4001)

    def test_rejects_expired_token(self, client: TestClient):
        token = _make_token(expired=True)
        _assert_ws_close(client, f"/api/beta/shared/ws?token={token}", 4001)

    def test_accepts_valid_token(self, client: TestClient):
        token = _make_token()
        with client.websocket_connect(
            f"/api/beta/shared/ws?token={token}"
        ) as ws:
            ws.close()

    def test_receives_heartbeat(self, client: TestClient):
        """Connection receives a ping heartbeat within HEARTBEAT_INTERVAL."""
        from unittest.mock import patch

        token = _make_token()
        with patch(
            "api.beta.routers.shared.sub_routers.websocket.websocket_router.HEARTBEAT_INTERVAL",
            0.1,
        ):
            with client.websocket_connect(
                f"/api/beta/shared/ws?token={token}"
            ) as ws:
                data = ws.receive_json()
                assert data["type"] == "ping"
                ws.close()


# ── /api/beta/assistant/ws/chat (AI chat streaming) ────────────────────────────────────────


class TestChatWebSocket:
    def test_rejects_missing_token(self, client: TestClient):
        _assert_ws_close(client, "/api/beta/assistant/ws/chat", 4001)

    def test_rejects_contractor_role(self, client: TestClient):
        token = _make_token(role="contractor")
        _assert_ws_close(
            client, f"/api/beta/assistant/ws/chat?token={token}", 4003
        )

    def test_accepts_admin_token(self, client: TestClient):
        token = _make_token(role="admin")
        with client.websocket_connect(
            f"/api/beta/assistant/ws/chat?token={token}"
        ) as ws:
            ws.close()

    def test_empty_message_returns_error(self, client: TestClient):
        token = _make_token()
        with client.websocket_connect(
            f"/api/beta/assistant/ws/chat?token={token}"
        ) as ws:
            ws.send_json({"type": "chat", "message": ""})
            resp = ws.receive_json()
            assert resp["type"] == "chat.error"
            assert "Empty" in resp["detail"]

    def test_chat_without_llm_returns_error(self, client: TestClient):
        from unittest.mock import patch

        token = _make_token()
        with (
            patch(
                "api.beta.routers.assistant.sub_routers.ws_chat.ws_chat_router.ANTHROPIC_AVAILABLE",
                False,
            ),
            patch(
                "api.beta.routers.assistant.sub_routers.ws_chat.ws_chat_router.OPENROUTER_AVAILABLE",
                False,
            ),
        ):
            with client.websocket_connect(
                f"/api/beta/assistant/ws/chat?token={token}"
            ) as ws:
                ws.send_json(
                    {
                        "type": "chat",
                        "message": "hello",
                        "session_id": "test-session",
                    }
                )
                resp = ws.receive_json()
                assert resp["type"] == "chat.error"
                assert "not configured" in resp["detail"].lower()


# ── Health endpoint verifies WS ─────────────────────────────────────────────


class TestHealthEndpoint:
    def test_ready_includes_websocket_check(self, client: TestClient):
        resp = client.get("/api/beta/shared/ready")
        data = resp.json()
        assert "websocket" in data["checks"]
        ws_check = data["checks"]["websocket"]
        assert ws_check["status"] == "ok"
        assert any("shared/ws" in e for e in ws_check["endpoints"])
        assert any(
            "assistant/ws" in e or "ws/chat" in e for e in ws_check["endpoints"]
        )

    def test_health_returns_ok(self, client: TestClient):
        resp = client.get("/api/beta/shared/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


# ── End-to-end event delivery tests ──────────────────────────────────────────
#
# These test the FULL pipeline: emit_sync() -> hub queue -> _sender asyncio
# task -> websocket.send_text() -> TestClient receives JSON.
#
# emit_sync uses call_soon_threadsafe so it works from the test thread while
# the ASGI app runs in TestClient's background event loop.  Events are
# emitted from a Timer thread with a small delay so that ws.receive_json()
# is already blocking when the event arrives.

_EMIT_DELAY = 0.15


def _delayed_emit(delay: float, event_type: str, **kwargs):
    """Schedule an emit_sync after *delay* seconds in a background thread."""
    from shared.infrastructure import event_hub

    def _do():
        event_hub.emit_sync(event_type, **kwargs)

    t = threading.Timer(delay, _do)
    t.start()
    return t


class TestEventDeliveryEndToEnd:
    """Full pipeline: event emitted -> arrives at connected WebSocket client."""

    def test_client_receives_emitted_event(self, client: TestClient):
        """Emit an event and verify the connected client gets it."""
        from unittest.mock import patch

        token = _make_token(org_id=DEFAULT_ORG_ID)
        with patch(
            "api.beta.routers.shared.sub_routers.websocket.websocket_router.HEARTBEAT_INTERVAL",
            999,
        ):
            with client.websocket_connect(
                f"/api/beta/shared/ws?token={token}"
            ) as ws:
                t = _delayed_emit(
                    _EMIT_DELAY,
                    events.INVENTORY_UPDATED,
                    org_id=DEFAULT_ORG_ID,
                    ids=["p-1"],
                )
                msg = ws.receive_json()
                t.join()
                assert msg["type"] == events.INVENTORY_UPDATED
                assert msg["ids"] == ["p-1"]
                ws.close()

    def test_hub_fan_out_to_multiple_subscribers(self):
        """Fan-out: _broadcast_local delivers to all subscriber queues.

        TestClient doesn't support two concurrent WebSocket connections, so
        fan-out is verified at the hub level where all the delivery logic lives.
        """
        from shared.infrastructure.event_hub import _Hub

        hub = _Hub()
        q1 = hub.subscribe()
        q2 = hub.subscribe()
        q3 = hub.subscribe()

        hub.emit_sync(
            events.WITHDRAWAL_CREATED, org_id=DEFAULT_ORG_ID, id="w-1"
        )

        for q in (q1, q2, q3):
            ev = q.get_nowait()
            assert ev.type == events.WITHDRAWAL_CREATED
            assert ev.data["id"] == "w-1"

    def test_wrong_org_event_not_delivered(self, client: TestClient):
        """Client for org-A should not receive events for org-B."""
        from unittest.mock import patch

        from shared.infrastructure import event_hub

        token = _make_token(org_id="org-A")
        with patch(
            "api.beta.routers.shared.sub_routers.websocket.websocket_router.HEARTBEAT_INTERVAL",
            999,
        ):
            with client.websocket_connect(
                f"/api/beta/shared/ws?token={token}"
            ) as ws:

                def _emit_pair():
                    event_hub.emit_sync(
                        events.INVENTORY_UPDATED, org_id="org-B"
                    )
                    event_hub.emit_sync(
                        events.INVENTORY_UPDATED, org_id="org-A", ids=["hit"]
                    )

                t = threading.Timer(_EMIT_DELAY, _emit_pair)
                t.start()
                msg = ws.receive_json()
                t.join()
                assert msg["type"] == events.INVENTORY_UPDATED
                assert msg.get("ids") == ["hit"]
                ws.close()

    def test_contractor_filtered_to_allowed_events(self, client: TestClient):
        """Contractor gets withdrawal.created but NOT inventory.updated."""
        from unittest.mock import patch

        from shared.infrastructure import event_hub

        token = _make_token(role="contractor")
        with patch(
            "api.beta.routers.shared.sub_routers.websocket.websocket_router.HEARTBEAT_INTERVAL",
            999,
        ):
            with client.websocket_connect(
                f"/api/beta/shared/ws?token={token}"
            ) as ws:

                def _emit_pair():
                    event_hub.emit_sync(
                        events.INVENTORY_UPDATED, org_id=DEFAULT_ORG_ID
                    )
                    event_hub.emit_sync(
                        events.WITHDRAWAL_CREATED,
                        org_id=DEFAULT_ORG_ID,
                        id="w-99",
                    )

                t = threading.Timer(_EMIT_DELAY, _emit_pair)
                t.start()
                msg = ws.receive_json()
                t.join()
                assert msg["type"] == events.WITHDRAWAL_CREATED
                assert msg["id"] == "w-99"
                ws.close()

    def test_user_scoped_event_skips_wrong_user(self, client: TestClient):
        """User-scoped events are filtered: user A doesn't get user B's chat.done.

        Emits a user-scoped event (for B) followed by a broadcast. The
        client connected as A should only see the broadcast.
        """
        from unittest.mock import patch

        from shared.infrastructure import event_hub

        ws_user_a = "00000000-0000-0000-0000-0000000000c1"
        ws_user_b = "00000000-0000-0000-0000-0000000000c2"
        token_u1 = _make_token(user_id=ws_user_a)
        with patch(
            "api.beta.routers.shared.sub_routers.websocket.websocket_router.HEARTBEAT_INTERVAL",
            999,
        ):
            with client.websocket_connect(
                f"/api/beta/shared/ws?token={token_u1}"
            ) as ws:

                def _emit_pair():
                    event_hub.emit_sync(
                        events.CHAT_DONE,
                        org_id=DEFAULT_ORG_ID,
                        user_id=ws_user_b,
                        response="hi",
                    )
                    event_hub.emit_sync(
                        events.INVENTORY_UPDATED,
                        org_id=DEFAULT_ORG_ID,
                        marker="broadcast",
                    )

                t = threading.Timer(_EMIT_DELAY, _emit_pair)
                t.start()
                msg = ws.receive_json()
                t.join()
                assert msg["type"] == events.INVENTORY_UPDATED
                assert msg.get("marker") == "broadcast"
                ws.close()

    def test_rapid_connect_disconnect(self, client: TestClient):
        """Rapid connect/disconnect cycles should not leak tasks or crash."""
        token = _make_token()
        for _ in range(10):
            with client.websocket_connect(
                f"/api/beta/shared/ws?token={token}"
            ) as ws:
                ws.close()
