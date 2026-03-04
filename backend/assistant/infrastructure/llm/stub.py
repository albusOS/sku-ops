"""Stub LLM provider for tests — returns canned responses, no API calls."""
from __future__ import annotations

from typing import Any


class StubProvider:
    """LLMProvider that requires no API keys; for test and offline development."""

    @property
    def provider_name(self) -> str:
        return "stub"

    @property
    def available(self) -> bool:
        return True

    def build_model(self, model_id: str) -> Any:
        return f"test:{model_id}"

    def estimate_cost(
        self,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        return 0.0

    def get_raw_client(self) -> Any:
        return None
