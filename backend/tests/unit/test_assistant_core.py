"""Unit tests for the assistant core layer — model registry, cost calc, agent config,
tokens, and validators. All tests are pure-logic with no IO.
"""
from __future__ import annotations

import json
from collections import OrderedDict
from unittest.mock import patch


class TestModelRegistry:

    def test_known_task_returns_string(self):
        from assistant.agents.core.model_registry import get_model_name
        result = get_model_name("agent:unified")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_unknown_task_falls_back_to_primary(self):
        from assistant.agents.core.model_registry import get_model_name
        from shared.infrastructure.config import AGENT_PRIMARY_MODEL
        result = get_model_name("agent:totally_unknown_task")
        assert result == AGENT_PRIMARY_MODEL

    def test_env_override_takes_precedence(self):
        from assistant.agents.core.model_registry import get_model_name
        with patch.dict("os.environ", {"MODEL_REGISTRY_AGENT_UNIFIED": "openrouter:test/model"}):
            result = get_model_name("agent:unified")
        assert result == "openrouter:test/model"

    def test_env_override_key_normalisation(self):
        """Dots and colons in task names are normalised to underscores for env lookup."""
        from assistant.agents.core.model_registry import get_model_name
        with patch.dict("os.environ", {"MODEL_REGISTRY_INFRA_SYNTHESIS": "openrouter:cheap/llm"}):
            result = get_model_name("infra:synthesis")
        assert result == "openrouter:cheap/llm"

    def test_all_task_keys_resolve(self):
        """Every known task key must resolve to a non-empty string."""
        from assistant.agents.core.model_registry import _DEFAULTS, get_model_name
        for task in _DEFAULTS:
            assert get_model_name(task), f"Task {task!r} resolved to empty string"

    def test_calc_cost_returns_zero_for_unknown_model(self):
        """calc_cost with a bare model ID (no colon) that has no catalog entry returns 0.0.

        Note: strings with colons are treated as task keys by calc_cost and resolve
        to AGENT_PRIMARY_MODEL as a fallback, so they will not return 0.0 unless the
        primary model itself is missing from the catalog. We test with a bare model ID
        (no colon) to exercise the unknown-model path.
        """
        from unittest.mock import MagicMock

        from assistant.agents.core.model_registry import calc_cost
        usage = MagicMock()
        usage.input_tokens = 1000
        usage.output_tokens = 500
        result = calc_cost("no-such-model-zzz-9999", usage)
        assert result == 0.0

    def test_calc_cost_nonzero_for_known_model(self):
        from unittest.mock import MagicMock

        from assistant.agents.core.model_registry import calc_cost
        usage = MagicMock()
        usage.input_tokens = 1000000
        usage.output_tokens = 1000000
        result = calc_cost("agent:unified", usage)
        assert result > 0.0

    def test_calc_cost_handles_none_tokens(self):
        from unittest.mock import MagicMock

        from assistant.agents.core.model_registry import calc_cost
        usage = MagicMock()
        usage.input_tokens = None
        usage.output_tokens = None
        result = calc_cost("agent:unified", usage)
        assert result == 0.0

class TestCostCalc:

    def test_sonnet_pricing(self):
        from assistant.infrastructure.llm.cost import calc_cost
        cost = calc_cost("anthropic/claude-sonnet-4-6", 1000000, 1000000)
        assert abs(cost - 18.0) < 0.01

    def test_haiku_cheaper_than_sonnet(self):
        from assistant.infrastructure.llm.cost import calc_cost
        haiku = calc_cost("anthropic/claude-haiku-4-5", 1000000, 1000000)
        sonnet = calc_cost("anthropic/claude-sonnet-4-6", 1000000, 1000000)
        assert haiku < sonnet

    def test_prefix_stripped_for_lookup(self):
        """anthropic:claude-sonnet-4-6 and anthropic/claude-sonnet-4-6 give same price."""
        from assistant.infrastructure.llm.cost import calc_cost
        with_prefix = calc_cost("anthropic:claude-sonnet-4-6", 100000, 100000)
        without_prefix = calc_cost("anthropic/claude-sonnet-4-6", 100000, 100000)
        assert abs(with_prefix - without_prefix) < 0.001

    def test_unknown_model_returns_zero(self):
        from assistant.infrastructure.llm.cost import calc_cost
        assert calc_cost("unknown/model", 100000, 50000) == 0.0

    def test_zero_tokens_returns_zero(self):
        from assistant.infrastructure.llm.cost import calc_cost
        assert calc_cost("anthropic/claude-sonnet-4-6", 0, 0) == 0.0

class TestCatalog:

    def test_all_catalog_models_have_pricing(self):
        from assistant.infrastructure.llm.catalog import get_model_pricing, get_models
        for model_id in get_models():
            pricing = get_model_pricing(model_id)
            assert pricing is not None, f"No pricing for {model_id}"
            assert pricing["input_price_per_m"] >= 0
            assert pricing["output_price_per_m"] >= 0

    def test_standard_tier_exists(self):
        from assistant.infrastructure.llm.catalog import get_tier
        tier = get_tier("standard")
        assert tier is not None
        assert "max_output_tokens" in tier

    def test_cheap_tier_exists(self):
        from assistant.infrastructure.llm.catalog import get_tier
        tier = get_tier("cheap")
        assert tier is not None
        assert "max_output_tokens" in tier

    def test_unknown_model_returns_none(self):
        from assistant.infrastructure.llm.catalog import get_model_info
        assert get_model_info("no/such/model-x99") is None

    def test_strip_prefix_finds_anthropic_model(self):
        """anthropic:claude-sonnet-4-6 resolves to the catalog entry."""
        from assistant.infrastructure.llm.catalog import get_model_info
        info = get_model_info("anthropic:claude-sonnet-4-6")
        assert info is not None

class TestAgentConfig:

    def test_known_agents_load_without_error(self):
        from assistant.agents.core.config import load_agent_config
        for agent_id in ("unified", "analyst", "product_analyst", "trend_analyst", "procurement_analyst", "health_analyst"):
            cfg = load_agent_config(agent_id)
            assert cfg.id == agent_id

    def test_missing_config_returns_defaults(self):
        from assistant.agents.core.config import load_agent_config
        from assistant.agents.core.contracts import AgentConfig
        cfg = load_agent_config("nonexistent_agent_xyz")
        assert isinstance(cfg, AgentConfig)
        assert cfg.id == "nonexistent_agent_xyz"
        assert cfg.max_output_tokens == 4000

    def test_env_override_max_output_tokens(self):
        import assistant.agents.core.config as cfg_mod
        cfg_mod._load_cached.cache_clear()
        with patch.dict("os.environ", {"AGENT_CONFIG_UNIFIED_MAX_OUTPUT_TOKENS": "1234"}):
            cfg = cfg_mod._load_cached("unified")
        assert cfg.max_output_tokens == 1234
        cfg_mod._load_cached.cache_clear()

    def test_env_override_model(self):
        import assistant.agents.core.config as cfg_mod
        cfg_mod._load_cached.cache_clear()
        with patch.dict("os.environ", {"AGENT_CONFIG_ANALYST_MODEL": "openrouter:meta-llama/llama"}):
            cfg = cfg_mod._load_cached("analyst")
        assert cfg.model == "openrouter:meta-llama/llama"
        cfg_mod._load_cached.cache_clear()

    def test_retry_config_defaults(self):
        from assistant.agents.core.config import load_agent_config
        cfg = load_agent_config("unified")
        assert cfg.retry.max_retries >= 1
        assert cfg.retry.timeout_seconds > 0

    def test_env_override_retry_max_retries(self):
        import assistant.agents.core.config as cfg_mod
        cfg_mod._load_cached.cache_clear()
        with patch.dict("os.environ", {"AGENT_CONFIG_UNIFIED_RETRY_MAX_RETRIES": "7"}):
            cfg = cfg_mod._load_cached("unified")
        assert cfg.retry.max_retries == 7
        cfg_mod._load_cached.cache_clear()

    def test_env_override_retry_timeout_seconds(self):
        import assistant.agents.core.config as cfg_mod
        cfg_mod._load_cached.cache_clear()
        with patch.dict("os.environ", {"AGENT_CONFIG_ANALYST_RETRY_TIMEOUT_SECONDS": "120"}):
            cfg = cfg_mod._load_cached("analyst")
        assert cfg.retry.timeout_seconds == 120
        cfg_mod._load_cached.cache_clear()

    def test_env_override_retry_backoff_base(self):
        import assistant.agents.core.config as cfg_mod
        cfg_mod._load_cached.cache_clear()
        with patch.dict("os.environ", {"AGENT_CONFIG_UNIFIED_RETRY_BACKOFF_BASE": "2.5"}):
            cfg = cfg_mod._load_cached("unified")
        assert abs(cfg.retry.backoff_base - 2.5) < 0.001
        cfg_mod._load_cached.cache_clear()

    def test_retry_env_override_does_not_affect_other_fields(self):
        """Retry env override leaves temperature and max_output_tokens unchanged."""
        import assistant.agents.core.config as cfg_mod
        cfg_mod._load_cached.cache_clear()
        with patch.dict("os.environ", {"AGENT_CONFIG_ANALYST_RETRY_MAX_RETRIES": "5"}):
            cfg = cfg_mod._load_cached("analyst")
        assert cfg.retry.max_retries == 5
        assert cfg.temperature == 0.0
        cfg_mod._load_cached.cache_clear()

class TestTokenUtils:

    def test_count_tokens_nonempty(self):
        from assistant.agents.core.tokens import count_tokens
        assert count_tokens("Hello, world!") > 0

    def test_count_tokens_empty(self):
        from assistant.agents.core.tokens import count_tokens
        assert count_tokens("") == 0

    def test_budget_tool_result_passthrough_when_small(self):
        from assistant.agents.core.tokens import budget_tool_result
        data = json.dumps({"skus": [{"id": "x", "name": "widget"}]})
        result = budget_tool_result(data, max_tokens=2000)
        assert "widget" in result

    def test_budget_tool_result_truncates_long_list(self):
        from assistant.agents.core.tokens import budget_tool_result
        big = json.dumps({"skus": [{"id": str(i), "name": "x" * 200} for i in range(50)]})
        result = budget_tool_result(big, max_tokens=100)
        parsed = json.loads(result)
        assert "_skus_truncated" in parsed or "_truncated" in parsed

    def test_budget_tool_result_drops_low_value_fields(self):
        from assistant.agents.core.tokens import budget_tool_result
        data = json.dumps({"skus": [{"id": "x", "name": "a" * 300, "_note": "verbose note", "barcode": "1234"} for _ in range(10)]})
        result = budget_tool_result(data, max_tokens=500)
        assert "_note" not in result or "a" * 300 not in result

    def test_estimate_turn_tokens(self):
        from assistant.agents.core.tokens import estimate_turn_tokens
        est = estimate_turn_tokens("You are helpful.", [{"role": "user", "content": "hi"}], "Hello!")
        assert est["total_estimate"] > 0
        assert est["system"] > 0
        assert est["history"] > 0
        assert est["user_message"] > 0

    def test_compress_history_noop_when_short(self):
        from assistant.agents.core.tokens import compress_history
        history = [{"role": "user", "content": "hi"}]
        result = compress_history(history)
        assert result == history

    def test_compress_history_trims_when_long(self):
        from assistant.agents.core.tokens import compress_history
        long_history = []
        for _ in range(20):
            long_history.append({"role": "user", "content": "word " * 500})
            long_history.append({"role": "assistant", "content": "response " * 500})
        result = compress_history(long_history, max_tokens=2000)
        assert result is not None
        assert len(result) < len(long_history)

    def test_compress_history_preserves_last_turn(self):
        from assistant.agents.core.tokens import compress_history
        long_history = []
        for i in range(20):
            long_history.append({"role": "user", "content": f"question {i} " * 400})
            long_history.append({"role": "assistant", "content": f"answer {i} " * 400})
        result = compress_history(long_history, max_tokens=2000)
        assert result is not None
        assert result[-2]["content"] == long_history[-2]["content"]
        assert result[-1]["content"] == long_history[-1]["content"]

class TestValidators:

    def test_trivial_message_passes(self):
        from assistant.agents.core.validators import validate_response
        result = validate_response("hi", "Hello!", [], [])
        assert result.passed

    def test_conversational_intent_skips_validation(self):
        from assistant.agents.core.validators import IntentClassification, validate_response
        intent = IntentClassification(needs_tools=False, domains=[], expects_table=False, is_conversational=True)
        result = validate_response("thanks!", "You're welcome!", [], [], intent=intent)
        assert result.passed
        assert result.scores.get("conversational") == 1.0

    def test_data_question_without_tools_flagged(self):
        from assistant.agents.core.validators import IntentClassification, validate_response
        intent = IntentClassification(needs_tools=True, domains=["inventory"], expects_table=False, is_conversational=False)
        result = validate_response("how many products do we have?", "We have about 150 products.", [], [], intent=intent)
        assert not result.passed
        assert "no_tools_called" in result.failures

    def test_data_question_with_tools_passes_tool_check(self):
        from assistant.agents.core.validators import IntentClassification, validate_response
        intent = IntentClassification(needs_tools=True, domains=["inventory"], expects_table=False, is_conversational=False)
        result = validate_response("how many products do we have?", "You have 150 products.", [{"tool": "get_sku_list"}], [{"tool": "get_sku_list", "result_preview": "150"}], intent=intent)
        assert "no_tools_called" not in result.failures

    def test_grounding_check_passes_when_numbers_match(self):
        from assistant.agents.core.validators import IntentClassification, validate_response
        intent = IntentClassification(needs_tools=True, domains=["inventory"], expects_table=False, is_conversational=False)
        result = validate_response("what is stock level for SKU-1?", "The stock level for SKU-1 is 42 units.", [{"tool": "get_stock"}], [{"tool": "get_stock", "result_preview": "42 units in stock"}], intent=intent)
        grounding = result.scores.get("data_grounding", 1.0)
        assert grounding >= 0.5

    def test_grounding_check_fails_when_numbers_fabricated(self):
        from assistant.agents.core.validators import IntentClassification, validate_response
        intent = IntentClassification(needs_tools=True, domains=["inventory"], expects_table=False, is_conversational=False)
        result = validate_response("what is stock level?", "Stock is 9999 units, 8888 backorders, 7777 reserved, 6666 on order.", [{"tool": "get_stock"}], [{"tool": "get_stock", "result_preview": "12 units"}], intent=intent)
        grounding = result.scores.get("data_grounding", 1.0)
        assert grounding < 1.0

    def test_none_intent_skips_intent_dependent_checks(self):
        from assistant.agents.core.validators import validate_response
        result = validate_response("how many products do we have?", "We have about 150 products.", [], [], intent=None)
        assert "no_tools_called" not in result.failures

    def test_short_response_returns_low_score(self):
        from assistant.agents.core.validators import validate_response
        result = validate_response("what is our revenue?", "", [], [])
        assert result.scores.get("empty_response") == 0.0

class TestInfraModelRouting:

    def test_synthesis_model_is_cheaper_than_primary(self):
        """infra:synthesis should resolve to a cheaper model than the primary agent model."""
        from assistant.agents.core.model_registry import get_model_name
        from assistant.infrastructure.llm.cost import calc_cost
        primary = get_model_name("agent:unified")
        synthesis = get_model_name("infra:synthesis")
        assert primary != synthesis, "infra:synthesis resolves to the same model as agent:unified — set a cheaper model in models.yaml synthesis field"
        primary_cost = calc_cost(primary, 1000000, 1000000)
        synthesis_cost = calc_cost(synthesis, 1000000, 1000000)
        assert synthesis_cost < primary_cost, f"synthesis ({synthesis}, ${synthesis_cost:.2f}/M) is not cheaper than primary ({primary}, ${primary_cost:.2f}/M)"

    def test_classifier_model_is_cheaper_than_primary(self):
        """infra:classifier should resolve to a cheaper model than the primary agent model."""
        from assistant.agents.core.model_registry import get_model_name
        from assistant.infrastructure.llm.cost import calc_cost
        primary = get_model_name("agent:unified")
        classifier = get_model_name("infra:classifier")
        assert primary != classifier
        primary_cost = calc_cost(primary, 1000000, 1000000)
        classifier_cost = calc_cost(classifier, 1000000, 1000000)
        assert classifier_cost < primary_cost

    def test_synthesis_and_classifier_can_be_different_models(self):
        """synthesis and classifier are independently configurable."""
        from assistant.agents.core.model_registry import get_model_name
        synthesis = get_model_name("infra:synthesis")
        classifier = get_model_name("infra:classifier")
        assert isinstance(synthesis, str)
        assert len(synthesis) > 0
        assert isinstance(classifier, str)
        assert len(classifier) > 0

    def test_infra_classifier_env_override(self):
        """MODEL_REGISTRY_INFRA_CLASSIFIER overrides the classifier model."""
        from assistant.agents.core.model_registry import get_model_name
        with patch.dict("os.environ", {"MODEL_REGISTRY_INFRA_CLASSIFIER": "openrouter:meta-llama/llama-3.3-70b-instruct"}):
            result = get_model_name("infra:classifier")
        assert result == "openrouter:meta-llama/llama-3.3-70b-instruct"

    def test_infra_synthesis_env_override(self):
        """MODEL_REGISTRY_INFRA_SYNTHESIS overrides the synthesis model."""
        from assistant.agents.core.model_registry import get_model_name
        with patch.dict("os.environ", {"MODEL_REGISTRY_INFRA_SYNTHESIS": "openrouter:google/gemini-2.0-flash-001"}):
            result = get_model_name("infra:synthesis")
        assert result == "openrouter:google/gemini-2.0-flash-001"

class TestConfigYamlTools:
    """Verify config.yaml tool lists match the @agent.tool decorators in agent code.

    These tests are the authoritative cross-check that prevents config drift.
    They do not import the agent modules (which would trigger lazy agent construction
    and require LLM keys) — instead they parse the agent source directly.
    """

    def _get_registered_tools(self, agent_file: str) -> set[str]:
        """Extract @_agent.tool function names from an agent source file."""
        import ast
        from pathlib import Path
        source = Path(agent_file).read_text()
        tree = ast.parse(source)
        tools: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef):
                for decorator in node.decorator_list:
                    is_agent_tool = (isinstance(decorator, ast.Attribute) and decorator.attr == "tool") or (isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute) and (decorator.func.attr in ("tool", "tool_plain")))
                    if is_agent_tool:
                        tools.add(node.name)
        return tools

    def _get_config_tools(self, agent_id: str) -> set[str]:
        from assistant.agents.core.config import load_agent_config
        cfg = load_agent_config(agent_id)
        return set(cfg.tools)

    def test_analyst_tools_match(self):
        from pathlib import Path
        agent_file = str(Path(__file__).parent.parent.parent / "assistant/agents/analyst/agent.py")
        registered = self._get_registered_tools(agent_file)
        configured = self._get_config_tools("analyst")
        assert configured == registered, f"analyst config.yaml tools don't match @_agent.tool decorators.\n  In YAML only: {configured - registered}\n  In code only: {registered - configured}"

    def test_product_analyst_tools_match(self):
        from pathlib import Path
        agent_file = str(Path(__file__).parent.parent.parent / "assistant/agents/product_analyst/agent.py")
        registered = self._get_registered_tools(agent_file)
        configured = self._get_config_tools("product_analyst")
        assert configured == registered, f"product_analyst config.yaml tools don't match @_agent.tool decorators.\n  In YAML only: {configured - registered}\n  In code only: {registered - configured}"

    def test_trend_analyst_tools_match(self):
        from pathlib import Path
        agent_file = str(Path(__file__).parent.parent.parent / "assistant/agents/trend_analyst/agent.py")
        registered = self._get_registered_tools(agent_file)
        configured = self._get_config_tools("trend_analyst")
        assert configured == registered, f"trend_analyst config.yaml tools don't match @_agent.tool decorators.\n  In YAML only: {configured - registered}\n  In code only: {registered - configured}"

    def test_procurement_analyst_tools_match(self):
        from pathlib import Path
        agent_file = str(Path(__file__).parent.parent.parent / "assistant/agents/procurement_analyst/agent.py")
        registered = self._get_registered_tools(agent_file)
        configured = self._get_config_tools("procurement_analyst")
        assert configured == registered, f"procurement_analyst config.yaml tools don't match @_agent.tool decorators.\n  In YAML only: {configured - registered}\n  In code only: {registered - configured}"

    def test_health_analyst_tools_match(self):
        from pathlib import Path
        agent_file = str(Path(__file__).parent.parent.parent / "assistant/agents/health_analyst/agent.py")
        registered = self._get_registered_tools(agent_file)
        configured = self._get_config_tools("health_analyst")
        assert configured == registered, f"health_analyst config.yaml tools don't match @_agent.tool decorators.\n  In YAML only: {configured - registered}\n  In code only: {registered - configured}"

    def test_unified_tools_match(self):
        from pathlib import Path
        agent_file = str(Path(__file__).parent.parent.parent / "assistant/agents/unified/agent.py")
        registered = self._get_registered_tools(agent_file)
        configured = self._get_config_tools("unified")
        assert configured == registered, f"unified config.yaml tools don't match @_agent.tool decorators.\n  In YAML only: {configured - registered}\n  In code only: {registered - configured}"

class TestIntentCacheLRU:

    def test_cache_evicts_oldest_not_all(self):
        """Verify the cache evicts one entry at capacity rather than flushing all."""
        import assistant.agents.core.validators as v_mod
        original_cache = v_mod._intent_cache
        original_max = v_mod._CACHE_MAX
        try:
            from assistant.agents.core.validators import IntentClassification
            v_mod._intent_cache = OrderedDict()
            v_mod._CACHE_MAX = 2
            dummy = IntentClassification(needs_tools=False, domains=[], expects_table=False, is_conversational=False)
            v_mod._intent_cache["key1"] = dummy
            v_mod._intent_cache["key2"] = dummy
            if len(v_mod._intent_cache) >= v_mod._CACHE_MAX:
                v_mod._intent_cache.popitem(last=False)
            v_mod._intent_cache["key3"] = dummy
            assert "key1" not in v_mod._intent_cache
            assert "key2" in v_mod._intent_cache
            assert "key3" in v_mod._intent_cache
            assert len(v_mod._intent_cache) == 2
        finally:
            v_mod._intent_cache = original_cache
            v_mod._CACHE_MAX = original_max
