"""
Central configuration - environment-aware settings.

Set ENV to control behavior:
  - development  Local dev; permissive defaults, local auth allowed
  - test         Pytest in-process; stub adapters, test Postgres DB (conftest sets this)
  - production   Live; requires explicit secrets, strict CORS, dangerous flags forbidden

When ENV is unset, defaults to development.
"""

import logging
import os
from pathlib import Path
from urllib.parse import urlparse

import jwt
import yaml
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


# Project root = backend/ (walk up from this file to find it)
def _find_backend_root() -> Path:
    """Locate the backend root by finding the directory containing server.py."""
    d = Path(__file__).resolve().parent
    for _ in range(10):
        if (d / "server.py").exists():
            return d
        d = d.parent
    return Path.cwd()


PROJECT_ROOT = _find_backend_root()

# Resolve the runtime environment from the real process environment first.
# Deployed environments must inject vars explicitly rather than inheriting
# a stray local backend/.env file from the filesystem.
_requested_env = os.environ.get("ENV", "").lower().strip()
_ENV = _requested_env or "development"

# Load .env for local-style runs. Root .env first (shared: API keys, Docker vars),
# then backend/.env (backend-specific overrides). Production relies on injected vars.
if _ENV in {"development", "test"}:
    _repo_root = PROJECT_ROOT.parent
    _root_env = _repo_root / ".env"
    if _root_env.exists():
        load_dotenv(_root_env)
    _backend_env = PROJECT_ROOT / ".env"
    if _backend_env.exists():
        load_dotenv(_backend_env)


def _is(env: str) -> bool:
    """Check if current env matches."""
    return env == _ENV


# ── Environment flags ─────────────────────────────────────────────────────────
# Three canonical environments: development, test, production.
# There is no staging environment — production is the only deployed env.
# If staging is needed in the future, add it here and in _VALID_ENVS.
_VALID_ENVS = {"development", "test", "production"}
if _ENV not in _VALID_ENVS:
    raise RuntimeError(
        f"ENV must be one of {sorted(_VALID_ENVS)}, got '{_ENV}'. Check your .env file or environment variable."
    )

is_development = _is("development")
is_production = _is("production")
is_test = _is("test")

# Public alias — use ENV instead of _ENV when importing the environment name
ENV = _ENV

# Kept for backward compatibility with any code that checks is_deployed.
# In this codebase there is exactly one deployed environment: production.
is_deployed = is_production

# ── Database ──────────────────────────────────────────────────────────────────
_local_supabase_db_url = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
DATABASE_URL = os.environ.get("DATABASE_URL", _local_supabase_db_url)

if not DATABASE_URL.startswith(("postgresql://", "postgres://")):
    raise RuntimeError(
        "DATABASE_URL must be a PostgreSQL connection string. Set DATABASE_URL=postgresql://user:pass@host:5432/db"
    )

# True when DATABASE_URL points at a local host (localhost, 127.0.0.1, or the
# Docker Compose service name "db"). Used by startup.py to warn when dev mode
# is active against a non-local DB — the warning is emitted there (after
# logging is configured) rather than here at import time.
try:
    _db_host = urlparse(DATABASE_URL).hostname or ""
    db_is_local = _db_host in ("localhost", "127.0.0.1", "::1", "db")
except Exception:
    db_is_local = True  # parse failure: assume local to avoid false-positive warning

# PostgreSQL connection pool
PG_POOL_MIN = int(os.environ.get("PG_POOL_MIN", "2"))
PG_POOL_MAX = int(os.environ.get("PG_POOL_MAX", "10"))
PG_ACQUIRE_TIMEOUT = float(os.environ.get("PG_ACQUIRE_TIMEOUT", "10"))
PG_COMMAND_TIMEOUT = int(os.environ.get("PG_COMMAND_TIMEOUT", "30"))

# ── Redis ─────────────────────────────────────────────────────────────────────
REDIS_URL = os.environ.get("REDIS_URL", "").strip()

# ── Auth / JWT ────────────────────────────────────────────────────────────────
_DEV_JWT_FALLBACK = "hardware-store-" + "secret-key"


def _resolve_jwt_secret() -> str:
    raw = os.environ.get("JWT_SECRET", "").strip()
    if is_production and (not raw or raw == _DEV_JWT_FALLBACK):
        raise RuntimeError("JWT_SECRET must be set in production. Do not use default.")
    return raw or _DEV_JWT_FALLBACK


JWT_SECRET = _resolve_jwt_secret()
JWT_ALGORITHM = "HS256"
_default_token_expiry = "15" if is_production else "480"  # 8 hours in dev, 15 min in prod
JWT_ACCESS_EXPIRATION_MINUTES = int(os.environ.get("JWT_ACCESS_EXPIRATION_MINUTES", _default_token_expiry))
REFRESH_TOKEN_EXPIRATION_DAYS = int(os.environ.get("REFRESH_TOKEN_EXPIRATION_DAYS", "7"))

# ── Supabase JWKS (ES256 token verification) ─────────────────────────────────
_local_supabase_url = "http://127.0.0.1:54321" if is_development or is_test else ""
SUPABASE_URL = os.environ.get("SUPABASE_URL", _local_supabase_url).strip().rstrip("/")
PUBLIC_SUPABASE_PUBLISHABLE_KEY = os.environ.get("PUBLIC_SUPABASE_PUBLISHABLE_KEY", "").strip()
SUPABASE_SECRET_KEY = os.environ.get("SUPABASE_SECRET_KEY", "").strip()
_SUPABASE_JWKS_URL = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json" if SUPABASE_URL else ""
# Expected issuer for Supabase tokens: {project_url}/auth/v1
_SUPABASE_ISSUER = f"{SUPABASE_URL}/auth/v1" if SUPABASE_URL else ""

if is_production and not SUPABASE_URL:
    raise RuntimeError(
        "SUPABASE_URL must be set in production. Supabase is the sole auth provider in deployed environments."
    )

_jwks_client = None


def _get_jwks_client():
    """Lazy-init a PyJWKClient for Supabase ES256 token verification."""
    global _jwks_client
    if _jwks_client is None and _SUPABASE_JWKS_URL:
        _jwks_client = jwt.PyJWKClient(
            _SUPABASE_JWKS_URL,
            cache_keys=True,
            lifespan=3600,
            timeout=5,
        )
    return _jwks_client


def decode_token(token: str) -> dict:
    """Decode a JWT using the strategy matching the current environment.

    Production: ES256 via Supabase JWKS with issuer verification.
    Development: Supabase local issues ES256 (JWKS); pytest still uses HS256.
    Test:        HS256 with JWT_SECRET only (no Supabase in unit API tests).

    Raises jwt.ExpiredSignatureError or jwt.InvalidTokenError on failure.
    """

    def _decode_es256() -> dict:
        jwks = _get_jwks_client()
        if jwks is None:
            raise jwt.InvalidTokenError("SUPABASE_URL not configured for JWKS token verification")
        try:
            signing_key = jwks.get_signing_key_from_jwt(token)
        except jwt.PyJWKClientError as e:
            logger.warning("JWKS key fetch failed: %s", e)
            raise jwt.InvalidTokenError("Unable to verify token signing key") from e
        except Exception as e:
            logger.warning("JWKS key fetch failed unexpectedly: %s", e)
            raise jwt.InvalidTokenError("Unable to verify token signing key") from e
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            issuer=_SUPABASE_ISSUER,
            options={"verify_aud": False, "verify_iss": True},
        )

    if is_production:
        return _decode_es256()

    if not is_test:
        try:
            header = jwt.get_unverified_header(token)
        except jwt.InvalidTokenError:
            header = {}
        if header.get("alg") == "ES256" and _SUPABASE_JWKS_URL:
            return _decode_es256()

    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


# ── CORS ──────────────────────────────────────────────────────────────────────
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")
CORS_ORIGIN_REGEX = os.environ.get("CORS_ORIGIN_REGEX", "").strip()
cors_is_permissive = not CORS_ORIGINS.strip() or CORS_ORIGINS == "*" or "*" in CORS_ORIGINS.split(",")
cors_warn_in_deployed = is_deployed and cors_is_permissive


def _enforce_cors() -> None:
    if is_production and cors_is_permissive:
        raise RuntimeError(
            "CORS_ORIGINS must not be '*' or empty in production. Set CORS_ORIGINS=https://your-vercel-app.vercel.app"
        )


_enforce_cors()

# ── Sentry ────────────────────────────────────────────────────────────────────
SENTRY_DSN = os.environ.get("SENTRY_DSN", "").strip()

ALLOW_PUBLIC_AUTH = False

# ── Auth provider ─────────────────────────────────────────────────────────────
# Supabase is the auth provider in every environment.

# ── AI providers ──────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
ANTHROPIC_AVAILABLE = bool(ANTHROPIC_API_KEY)
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6").strip() or "claude-sonnet-4-6"
ANTHROPIC_FAST_MODEL = os.environ.get("ANTHROPIC_FAST_MODEL", "claude-sonnet-4-6").strip() or "claude-sonnet-4-6"

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
OPENAI_AVAILABLE = bool(OPENAI_API_KEY)

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()
OPENROUTER_BASE_URL = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").strip()
OPENROUTER_AVAILABLE = bool(OPENROUTER_API_KEY)

# Embeddings (OpenAI-compatible API: tool index, domain search, query router).
# Set EMBEDDING_MODEL to change model; default text-embedding-3-small.
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small").strip() or "text-embedding-3-small"


# ── Agent model ───────────────────────────────────────────────────────────────
def _load_agent_model() -> str:
    env_override = os.environ.get("AGENT_PRIMARY_MODEL", "").strip()
    if env_override:
        return env_override
    try:
        _yaml_path = PROJECT_ROOT / "assistant" / "config" / "models.yaml"
        if _yaml_path.exists():
            data = yaml.safe_load(_yaml_path.read_text()) or {}
            model = (data.get("primary") or "").strip()
            if model:
                return model
    except (OSError, ValueError, KeyError):
        logging.getLogger(__name__).warning("Failed to parse models.yaml, using built-in default", exc_info=True)
    return "anthropic:claude-sonnet-4-6"


AGENT_PRIMARY_MODEL: str = _load_agent_model()


def _load_synthesis_model() -> str:
    """Load synthesis model for history compression and memory extraction."""
    env_override = os.environ.get("MODEL_REGISTRY_INFRA_SYNTHESIS", "").strip()
    if env_override:
        return env_override
    try:
        _yaml_path = PROJECT_ROOT / "assistant" / "config" / "models.yaml"
        if _yaml_path.exists():
            data = yaml.safe_load(_yaml_path.read_text()) or {}
            model = (data.get("synthesis") or "").strip()
            if model:
                return model
    except (OSError, ValueError, KeyError):
        logging.getLogger(__name__).warning("Failed to parse synthesis from models.yaml", exc_info=True)
    return "anthropic:claude-haiku-4-5"


INFRA_SYNTHESIS_MODEL: str = _load_synthesis_model()


def _load_classifier_model() -> str:
    """Load classifier model for intent classification (high-volume, short JSON responses)."""
    env_override = os.environ.get("MODEL_REGISTRY_INFRA_CLASSIFIER", "").strip()
    if env_override:
        return env_override
    try:
        _yaml_path = PROJECT_ROOT / "assistant" / "config" / "models.yaml"
        if _yaml_path.exists():
            data = yaml.safe_load(_yaml_path.read_text()) or {}
            model = (data.get("classifier") or "").strip()
            if model:
                return model
    except (OSError, ValueError, KeyError):
        logging.getLogger(__name__).warning("Failed to parse classifier from models.yaml", exc_info=True)
    return "anthropic:claude-haiku-4-5"


INFRA_CLASSIFIER_MODEL: str = _load_classifier_model()
LLM_SETUP_URL = "https://console.anthropic.com/"
SESSION_COST_CAP = float(os.environ.get("SESSION_COST_CAP", "2.00"))

# ── Frontend / OAuth ──────────────────────────────────────────────────────────
FRONTEND_URL = os.environ.get("FRONTEND_URL", "").strip().rstrip("/")

# ── Xero OAuth 2.0 ───────────────────────────────────────────────────────────
XERO_CLIENT_ID = os.environ.get("XERO_CLIENT_ID", "").strip()
XERO_CLIENT_SECRET = os.environ.get("XERO_CLIENT_SECRET", "").strip()
XERO_REDIRECT_URI = os.environ.get("XERO_REDIRECT_URI", "").strip()
XERO_SYNC_HOUR = int(os.environ.get("XERO_SYNC_HOUR", "2"))


# ── Startup config summary ────────────────────────────────────────────────────
def startup_summary() -> dict:
    """Return a dict summarising the effective runtime configuration.

    Called once during lifespan startup so operators can confirm the process
    is running with the expected identity, DB target, auth shape, and feature
    flag state at a glance from the first log lines.
    """
    try:
        _parsed = urlparse(DATABASE_URL)
        db_display = f"{_parsed.hostname}:{_parsed.port or 5432}{_parsed.path}"
    except Exception:
        db_display = "<unparseable>"

    flags: list[str] = []
    if cors_is_permissive:
        flags.append("CORS=*")

    return {
        "env": ENV,
        "auth_provider": "supabase",
        "db": db_display,
        "cors": CORS_ORIGINS if not cors_is_permissive else "*",
        "redis": "yes" if REDIS_URL else "no",
        "sentry": "yes" if SENTRY_DSN else "no",
        "ai": ("openrouter" if OPENROUTER_AVAILABLE else ("anthropic" if ANTHROPIC_AVAILABLE else "none")),
        "embeddings": "openai" if OPENAI_AVAILABLE else "none",
        "flags": flags or None,
    }
