"""Unit tests for LLM config, service functions, and UOM classifier.

No DB, no network — only mocked LLM clients.
"""

import base64
from unittest.mock import MagicMock, patch

import pytest

from shared.infrastructure.config import (
    ANTHROPIC_API_KEY,
    ANTHROPIC_AVAILABLE,
    ANTHROPIC_FAST_MODEL,
    ANTHROPIC_MODEL,
    LLM_SETUP_URL,
)


class TestConfig:
    """Test AI config values."""

    def test_default_models(self):
        assert "claude-sonnet" in ANTHROPIC_MODEL
        assert "claude-haiku" in ANTHROPIC_FAST_MODEL

    def test_llm_setup_url(self):
        assert LLM_SETUP_URL == "https://console.anthropic.com/"

    def test_availability_tracks_api_key(self):
        assert isinstance(ANTHROPIC_AVAILABLE, bool)
        if not ANTHROPIC_API_KEY:
            assert ANTHROPIC_AVAILABLE is False


class TestLLMService:
    """Test services.llm functions."""

    def test_generate_text_returns_none_without_client(self):
        from assistant.application.llm import generate_text

        with patch("assistant.application.llm._get_client", return_value=None):
            result = generate_text("Hello")
        assert result is None

    def test_generate_text_returns_text_when_mocked(self):
        from assistant.application.llm import generate_text

        mock_client = MagicMock()
        mock_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text="Mocked response")]
        )

        with patch("assistant.application.llm._get_client", return_value=mock_client):
            result = generate_text("Hello", system_instruction="Be helpful")

        assert result == "Mocked response"
        mock_client.messages.create.assert_called_once()
        call_kw = mock_client.messages.create.call_args[1]
        assert call_kw["model"] == ANTHROPIC_FAST_MODEL
        assert call_kw["system"] == "Be helpful"
        assert call_kw["messages"][0]["content"] == "Hello"

    def test_generate_with_image_raises_without_client(self):
        from assistant.application.llm import generate_with_image

        with patch("assistant.application.llm._get_client", return_value=None):
            with pytest.raises(ValueError, match="LLM not configured"):
                generate_with_image("Describe this", b"\xff\xd8\xfffake-jpeg")

    def test_generate_with_image_succeeds_when_mocked(self):
        from assistant.application.llm import generate_with_image

        mock_client = MagicMock()
        mock_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text="A red apple")]
        )

        jpeg_bytes = b"\xff\xd8\xff\x00\x00\x00\x00\xff\xd9"

        with patch("assistant.application.llm._get_client", return_value=mock_client):
            result = generate_with_image("What is this?", jpeg_bytes)

        assert result == "A red apple"
        call_kw = mock_client.messages.create.call_args[1]
        assert call_kw["model"] == ANTHROPIC_MODEL
        content = call_kw["messages"][0]["content"]
        assert len(content) == 2
        assert content[0]["type"] == "image"
        assert content[0]["source"]["media_type"] == "image/jpeg"
        assert base64.standard_b64decode(content[0]["source"]["data"]) == jpeg_bytes
        assert content[1]["text"] == "What is this?"

    def test_generate_with_pdf_raises_without_client(self):
        from assistant.application.llm import generate_with_pdf

        with patch("assistant.application.llm._get_client", return_value=None):
            with pytest.raises(ValueError, match="LLM not configured"):
                generate_with_pdf("Extract items", "/nonexistent.pdf")


@pytest.mark.asyncio
class TestUOMClassifier:
    """Test UOM classifier (uses LLM when available)."""

    async def test_classify_uom_returns_default_when_llm_unavailable(self):
        from inventory.application.uom_classifier import classify_uom

        result = await classify_uom("Mystery product")
        assert result == {"base_unit": "each", "sell_uom": "each", "pack_qty": 1}

    async def test_classify_uom_uses_llm_when_mocked(self):
        from inventory.application.uom_classifier import classify_uom

        def mock_generate_text(_prompt, _system):
            return '{"base_unit":"gallon","sell_uom":"gallon","pack_qty":5}'

        result = await classify_uom("5 Gal Paint", generate_text=mock_generate_text)
        assert result["base_unit"] == "gallon"
        assert result["sell_uom"] == "gallon"
        assert result["pack_qty"] == 5
