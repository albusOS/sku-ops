"""Deterministic message router — classifies user messages and dispatches to
the right specialist agent(s).

Routing tiers (fastest first):
1. Heuristic keyword scoring — instant, handles ~60 % of messages
2. Embedding cosine similarity — ~5 ms, deterministic, handles ~35 %
3. LLM fallback via OpenRouter — ~300 ms, only for genuinely ambiguous queries

Merge is template-based (no LLM call).
"""
import asyncio
import json
import logging
from dataclasses import dataclass, field

import numpy as np

from shared.infrastructure.config import (
    OPENAI_API_KEY,
    OPENROUTER_AVAILABLE,
)
from assistant.agents.model_registry import get_model_name
from assistant.agents.contracts import Complexity, RouteDecision

logger = logging.getLogger(__name__)

_VALID_AGENTS = {"inventory", "ops", "finance", "insights", "general", "coordinator"}

_AGENT_LABELS = {
    "inventory": "Inventory",
    "ops": "Operations",
    "finance": "Financials",
    "insights": "Insights",
    "general": "Overview",
}


# ── Routing result ────────────────────────────────────────────────────────────

@dataclass
class RouteResult:
    agents: list[str]
    confidence: float = 1.0
    method: str = "heuristic"  # "heuristic" | "embedding" | "llm_fallback"


# ── Canonical query bank for embedding classification ─────────────────────────
# ~10-15 representative queries per agent.  Embeddings are computed once at
# startup and cached in the singleton _EmbeddingRouter.

CANONICAL_QUERIES: dict[str, list[str]] = {
    "inventory": [
        "do we have PVC pipes",
        "search for copper fittings",
        "find product by SKU",
        "low stock items",
        "what products need reordering",
        "department health breakdown",
        "show me slow movers",
        "what's our inventory worth",
        "out of stock products",
        "how many SKUs do we have",
        "list all departments",
        "who are our vendors",
        "barcode lookup",
        "product details for PLU-001",
    ],
    "ops": [
        "what has john smith taken",
        "pending material requests",
        "recent withdrawals this week",
        "materials for job 123",
        "contractor withdrawal history",
        "approve material request",
        "who pulled materials today",
        "show me all jobs",
        "service address for a job",
        "what was used on that project",
    ],
    "finance": [
        "what's our revenue this week",
        "who owes us money",
        "outstanding balances",
        "invoice summary",
        "profit and loss report",
        "gross margin this month",
        "weekly sales report",
        "how much have we collected",
        "unpaid accounts",
        "send invoice to customer",
        "payment status breakdown",
    ],
    "insights": [
        "top selling products",
        "best sellers this month",
        "stockout forecast",
        "what products are running out",
        "sales trend over time",
        "department activity report",
        "usage velocity for lumber",
        "which products move fastest",
        "analytics overview",
        "slow mover analysis",
    ],
    "general": [
        "hi",
        "hello",
        "help",
        "what can you do",
        "how's the business doing",
        "give me an overview",
        "dashboard summary",
        "thanks",
        "good morning",
        "what should I focus on today",
    ],
}


# ── Embedding Router (singleton) ─────────────────────────────────────────────

class EmbeddingRouter:
    """Cosine-similarity classifier backed by OpenAI text-embedding-3-small."""

    EMBEDDING_MODEL = "text-embedding-3-small"
    CONFIDENCE_THRESHOLD = 0.45
    MULTI_AGENT_GAP = 0.08  # if 2nd-best is within this gap of best, fan out

    def __init__(self):
        self._matrix: np.ndarray | None = None  # (N, dim)
        self._labels: list[str] = []             # agent name per row
        self._ready = False

    async def build(self) -> None:
        """Embed all canonical queries.  Call once at startup."""
        if not OPENAI_API_KEY:
            logger.info("EmbeddingRouter: no OPENAI_API_KEY, embedding tier disabled")
            return
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=OPENAI_API_KEY)
            all_texts: list[str] = []
            labels: list[str] = []
            for agent, queries in CANONICAL_QUERIES.items():
                for q in queries:
                    all_texts.append(q)
                    labels.append(agent)

            resp = await client.embeddings.create(
                model=self.EMBEDDING_MODEL, input=all_texts,
            )
            vecs = np.array([item.embedding for item in resp.data], dtype=np.float32)
            norms = np.linalg.norm(vecs, axis=1, keepdims=True)
            norms = np.where(norms == 0, 1, norms)
            self._matrix = vecs / norms
            self._labels = labels
            self._ready = True
            logger.info(f"EmbeddingRouter built: {len(all_texts)} canonical queries")
        except Exception as e:
            logger.warning(f"EmbeddingRouter build failed: {e}")

    async def classify(self, message: str) -> RouteResult | None:
        """Classify by embedding similarity.  Returns None if not ready or below threshold."""
        if not self._ready or self._matrix is None:
            return None
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=OPENAI_API_KEY)
            resp = await client.embeddings.create(
                model=self.EMBEDDING_MODEL, input=[message],
            )
            qvec = np.array(resp.data[0].embedding, dtype=np.float32)
            norm = np.linalg.norm(qvec)
            if norm > 0:
                qvec /= norm

            scores = self._matrix @ qvec

            # Aggregate per-agent: take the max similarity across canonical queries
            agent_scores: dict[str, float] = {}
            for score, label in zip(scores, self._labels):
                if label not in agent_scores or score > agent_scores[label]:
                    agent_scores[label] = float(score)

            ranked = sorted(agent_scores.items(), key=lambda x: x[1], reverse=True)
            best_agent, best_score = ranked[0]

            if best_score < self.CONFIDENCE_THRESHOLD:
                return None  # defer to LLM fallback

            agents = [best_agent]
            # Check if 2nd-best is close enough for multi-agent fan-out
            if len(ranked) > 1:
                second_agent, second_score = ranked[1]
                if second_score >= self.CONFIDENCE_THRESHOLD and (best_score - second_score) < self.MULTI_AGENT_GAP:
                    agents.append(second_agent)

            return RouteResult(agents=agents, confidence=best_score, method="embedding")
        except Exception as e:
            logger.warning(f"EmbeddingRouter classify failed: {e}")
            return None

    @property
    def ready(self) -> bool:
        return self._ready


_embedding_router = EmbeddingRouter()


async def ensure_router_ready() -> None:
    """Build the embedding router if not already done.  Safe to call multiple times."""
    if not _embedding_router.ready:
        await _embedding_router.build()


# ── Heuristic tier ────────────────────────────────────────────────────────────

def _heuristic_route(message: str) -> RouteResult | None:
    """Fast keyword-based routing for obvious cases.  Returns None to defer."""
    m = message.lower().strip()

    if len(m) < 15 and any(w in m for w in ("hi", "hello", "hey", "help", "thanks", "thank you")):
        return RouteResult(agents=["general"], confidence=1.0, method="heuristic")

    # "overview" / "summary" / "dashboard" → general (cross-domain tools)
    if any(w in m for w in ("overview", "summary", "dashboard")):
        return RouteResult(agents=["general"], confidence=0.9, method="heuristic")

    inv_words = ("stock", "reorder", "sku", "barcode", "product", "low stock", "out of stock", "department", "vendor")
    ops_words = ("withdrawal", "material request", "contractor", "job", "service address")
    fin_words = ("revenue", "invoice", "payment", "p&l", "profit", "margin", "outstanding", "owes", "xero", "balance")
    ins_words = ("trend", "forecast", "stockout", "velocity", "top sell", "best sell", "slow mover", "analytics")

    scores = {
        "inventory": sum(1 for w in inv_words if w in m),
        "ops": sum(1 for w in ops_words if w in m),
        "finance": sum(1 for w in fin_words if w in m),
        "insights": sum(1 for w in ins_words if w in m),
    }
    hits = {k: v for k, v in scores.items() if v > 0}

    if not hits:
        return None

    if len(hits) == 1:
        return RouteResult(agents=[list(hits.keys())[0]], confidence=0.85, method="heuristic")

    ranked = sorted(hits.items(), key=lambda x: x[1], reverse=True)
    return RouteResult(agents=[k for k, _ in ranked[:2]], confidence=0.75, method="heuristic")


# ── LLM fallback tier (via OpenRouter) ────────────────────────────────────────

_ROUTER_SYSTEM = """You classify user messages for a hardware store management system (SKU-Ops).
Pick the best specialist agent(s) for the question. Return ONLY valid JSON.

AGENTS:
- inventory: product search, stock levels, reorders, departments, vendors, SKUs, barcodes
- ops: withdrawals, material requests, contractors, jobs, service addresses
- finance: revenue, invoices, payments, P&L, outstanding balances, margins
- insights: trends, top products, forecasting, velocity, slow movers, analytics
- general: greetings, help, navigation, overview, or unclear questions

RULES:
- Single-domain → {"agents": ["inventory"]}
- Cross-domain → {"agents": ["inventory", "finance"]}
- Max 3 agents. If unsure → general.
- "overview" / "summary" / "dashboard" → general"""


async def _llm_fallback(message: str, history: list[dict] | None = None) -> RouteResult:
    """Last-resort LLM classification via OpenRouter."""
    if not OPENROUTER_AVAILABLE:
        return RouteResult(agents=["general"], confidence=0.3, method="llm_fallback")
    try:
        from openai import AsyncOpenAI
        from shared.infrastructure.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL

        client = AsyncOpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL)
        model = get_model_name("infra:router_fallback")

        context = ""
        if history and len(history) >= 2:
            recent = history[-4:]
            context = "\n".join(f"{h['role']}: {h['content'][:100]}" for h in recent)
            context = f"\nRecent conversation:\n{context}\n"

        resp = await asyncio.wait_for(
            client.chat.completions.create(
                model=model,
                max_tokens=80,
                messages=[
                    {"role": "system", "content": _ROUTER_SYSTEM},
                    {"role": "user", "content": f"{context}User message: {message}"},
                ],
            ),
            timeout=8,
        )

        text = (resp.choices[0].message.content or "").strip()
        if "```" in text:
            text = text.split("```")[1].strip()
            if text.startswith("json"):
                text = text[4:].strip()
        data = json.loads(text)
        agents = data.get("agents", ["general"])
        agents = [a for a in agents if a in _VALID_AGENTS]
        if not agents:
            agents = ["general"]
        return RouteResult(agents=agents[:3], confidence=0.6, method="llm_fallback")
    except Exception as e:
        logger.warning(f"LLM fallback classification failed: {e}")
        return RouteResult(agents=["general"], confidence=0.2, method="llm_fallback")


# ── Public API ────────────────────────────────────────────────────────────────

async def classify(message: str, history: list[dict] | None = None) -> list[str]:
    """Classify a user message into one or more agent types.

    Tier 1: heuristic keywords (instant)
    Tier 2: embedding similarity (~5ms, deterministic)
    Tier 3: LLM fallback via OpenRouter (only for ambiguous)
    """
    # Tier 1
    result = _heuristic_route(message)
    if result:
        logger.debug(f"Router heuristic → {result.agents} (confidence={result.confidence})")
        return result.agents

    # Tier 2
    await ensure_router_ready()
    result = await _embedding_router.classify(message)
    if result:
        logger.debug(f"Router embedding → {result.agents} (confidence={result.confidence})")
        return result.agents

    # Tier 3
    result = await _llm_fallback(message, history)
    logger.debug(f"Router LLM fallback → {result.agents} (confidence={result.confidence})")
    return result.agents


# ── Template-based merge (no LLM) ────────────────────────────────────────────

def merge_responses(question: str, results: list[dict]) -> dict:
    """Merge responses from multiple agents using deterministic templates."""
    if len(results) == 1:
        return results[0]

    successful = [r for r in results if r.get("response") and "ran into an issue" not in r.get("response", "")]
    if not successful:
        return results[0]
    if len(successful) == 1:
        return successful[0]

    sections = []
    all_tool_calls: list[dict] = []
    total_cost = 0.0
    total_input = 0
    total_output = 0
    agents_used: list[str] = []

    for r in successful:
        agent = r.get("agent", "unknown")
        agents_used.append(agent)
        label = _AGENT_LABELS.get(agent, agent.title())
        sections.append(f"## {label}\n\n{r.get('response', '')}")
        all_tool_calls.extend(r.get("tool_calls", []))
        usage = r.get("usage", {})
        total_cost += usage.get("cost_usd", 0)
        total_input += usage.get("input_tokens", 0)
        total_output += usage.get("output_tokens", 0)

    merged_text = "\n\n---\n\n".join(sections)
    best_history = max(successful, key=lambda r: len(r.get("history", []))).get("history", [])
    model_name = get_model_name("agent:general")

    return {
        "response": merged_text,
        "tool_calls": all_tool_calls,
        "thinking": [],
        "history": best_history,
        "usage": {
            "cost_usd": round(total_cost, 6),
            "input_tokens": total_input,
            "output_tokens": total_output,
            "model": model_name,
        },
        "agent": "+".join(agents_used),
        "routed_to": agents_used,
    }


# ── Complexity classifier ─────────────────────────────────────────────────────
# Runs *before* routing to steer each query to the cheapest viable execution path.

_TRIVIAL_SIGNALS = frozenset((
    "hi", "hello", "hey", "thanks", "thank you", "help", "ok", "okay",
    "sure", "yes", "no", "bye", "goodbye", "good morning", "good afternoon",
))

_INTERDEPENDENT_PAIRS = frozenset((
    frozenset({"inventory", "finance"}),
    frozenset({"inventory", "insights"}),
    frozenset({"ops", "finance"}),
))


def classify_complexity(message: str) -> Complexity:
    """Determine query complexity — no LLM call, instant.

    TRIVIAL:     greetings, help, thanks
    STRUCTURED:  matches a known DAG template
    SIMPLE:      single-domain, clear intent
    COMPLEX:     multi-domain, ambiguous, or needs coordination
    """
    m = message.lower().strip()

    if len(m) < 20 and any(w in m for w in _TRIVIAL_SIGNALS):
        return Complexity.TRIVIAL

    from assistant.agents.dag import match_plan
    if match_plan(message) is not None:
        return Complexity.STRUCTURED

    result = _heuristic_route(message)
    if result is None:
        return Complexity.SIMPLE

    if len(result.agents) > 1:
        return Complexity.COMPLEX

    if result.agents == ["general"]:
        if any(w in m for w in ("overview", "summary", "dashboard", "how's")):
            return Complexity.STRUCTURED if match_plan(message) else Complexity.COMPLEX
        return Complexity.TRIVIAL

    return Complexity.SIMPLE


async def route(message: str, history: list[dict] | None = None) -> RouteDecision:
    """Full routing pipeline: complexity classification + agent selection + strategy.

    Returns a RouteDecision that the orchestrator dispatches on.
    """
    complexity = classify_complexity(message)

    if complexity == Complexity.TRIVIAL:
        return RouteDecision(
            primary="coordinator",
            strategy="single",
            complexity=complexity,
            confidence=1.0,
            method="complexity",
        )

    if complexity == Complexity.STRUCTURED:
        from assistant.agents.dag import match_plan
        plan = match_plan(message)
        return RouteDecision(
            primary="dag",
            strategy="dag",
            complexity=complexity,
            confidence=1.0,
            method="complexity",
            dag_template=plan.template_name if plan else None,
        )

    agents = await classify(message, history)

    if len(agents) == 1:
        agent = agents[0]
        if agent == "general":
            agent = "coordinator"
        return RouteDecision(
            primary=agent,
            strategy="single",
            complexity=complexity,
            confidence=0.85,
            method="heuristic",
        )

    agent_set = frozenset(agents[:2])
    is_interdependent = agent_set in _INTERDEPENDENT_PAIRS
    strategy = "coordinate" if is_interdependent else "parallel"

    return RouteDecision(
        primary=agents[0],
        supporting=agents[1:],
        strategy=strategy,
        complexity=Complexity.COMPLEX,
        confidence=0.75,
        method="heuristic",
    )
