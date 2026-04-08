"""
Central configuration - environment-aware settings.

Use the singleton:

    from shared.infrastructure.config import config
    config.DATABASE_URL  # postgresql+asyncpg://... from PUBLIC_DB_* or PRIVATE_DATABASE_URL

``PUBLIC_ENV`` controls behavior: ``development`` | ``test`` | ``production``.
Legacy ``ENV`` is still read as a fallback until removed. When unset before
layered dotenv load, defaults to ``development``.

Layered env files (see ``docs/environment.md``): ``backend/.env``,
``backend/.env.{development|production}``, ``backend/.env.local``.

Hot reload: with ``PUBLIC_ENV=development``, dotenv files are re-applied on a
debounced timer when accessing settings (no extra dependencies).
``PUBLIC_ENV=test`` and ``PUBLIC_ENV=production`` do not reload files;
production caches reads.
"""

from __future__ import annotations

import logging
import os
from typing import Any, ClassVar, Self
from urllib.parse import urlparse

import jwt
import yaml
from sqlalchemy.engine import URL

from shared.infrastructure.env import (
    find_backend_root,
    load_backend_dotenv_initial,
    maybe_reload_backend_dotenv_development,
)

logger = logging.getLogger(__name__)

PROJECT_ROOT = find_backend_root()


def _runtime_env_from_process() -> str:
    """Process env only, before layered dotenv merge (used to pick .env.<profile>)."""
    return (
        os.environ.get("PUBLIC_ENV", "").strip().lower()
        or os.environ.get("ENV", "").strip().lower()
        or "development"
    )


_pre_load_env = _runtime_env_from_process()
load_backend_dotenv_initial(PROJECT_ROOT, env_name=_pre_load_env)

_REQUESTED_ENV = (
    os.environ.get("PUBLIC_ENV", "").strip().lower()
    or os.environ.get("ENV", "").strip().lower()
    or "development"
)
_ENV = _REQUESTED_ENV

_VALID_ENVS = frozenset({"development", "test", "production"})
if _ENV not in _VALID_ENVS:
    raise RuntimeError(
        f"PUBLIC_ENV must be one of {sorted(_VALID_ENVS)}, got '{_ENV}'. "
        "Check backend/.env or set PUBLIC_ENV (legacy ENV is still accepted)."
    )

_DEV_JWT_FALLBACK = "hardware-store-" + "secret-key"


class Config:
    """Process-wide settings. Use the module-level ``config`` instance."""

    _instance: ClassVar[Config | None] = None

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_instance()
        return cls._instance

    def _init_instance(self) -> None:
        self._backend_root = PROJECT_ROOT
        self._env = _ENV
        self._production_str_cache: dict[str, str] = {}
        self._jwks_client: jwt.PyJWKClient | None = None
        self._jwks_client_key: str = ""
        self._enforce_cors()

    @property
    def ENV(self) -> str:
        return self._env

    @property
    def is_development(self) -> bool:
        return self._env == "development"

    @property
    def is_production(self) -> bool:
        return self._env == "production"

    @property
    def is_test(self) -> bool:
        return self._env == "test"

    @property
    def is_deployed(self) -> bool:
        return self.is_production

    def _maybe_reload_dev(self) -> None:
        if self._env == "development":
            maybe_reload_backend_dotenv_development(self._backend_root)

    def _get_str(self, key: str, default: str = "") -> str:
        if self._env == "development":
            self._maybe_reload_dev()
        if self._env == "production":
            if key in self._production_str_cache:
                return self._production_str_cache[key]
            val = os.environ.get(key, default)
            self._production_str_cache[key] = val
            return val
        return os.environ.get(key, default)

    def _normalize_legacy_database_url(self, raw: str) -> str:
        stripped = raw.strip()
        if not stripped:
            return ""
        if stripped.startswith("postgresql+asyncpg://"):
            return stripped
        if stripped.startswith("postgresql://"):
            return stripped.replace("postgresql://", "postgresql+asyncpg://", 1)
        if stripped.startswith("postgres://"):
            return stripped.replace("postgres://", "postgresql+asyncpg://", 1)
        raise RuntimeError(
            "DATABASE_URL must be a PostgreSQL URI. "
            "Use postgresql://user:pass@host:port/db, or set DB_HOST and related keys."
        )

    def _reject_transaction_pooler_url(self, url: str) -> None:
        if ":6543" not in url:
            return
        msg = (
            "DATABASE_URL targets port 6543 (Supabase transaction pooler). "
            "Use direct Postgres (port 5432). "
            "asyncpg prepared statements are incompatible with transaction pooling."
        )
        if self.is_deployed:
            raise RuntimeError(msg)
        logger.warning(msg)

    @property
    def DB_USER(self) -> str:
        return self._get_str("PUBLIC_DB_USER", "postgres")

    @property
    def DB_PASSWORD(self) -> str:
        private = self._get_str("PRIVATE_DB_PASSWORD", "").strip()
        if private:
            return private
        public_pw = self._get_str("PUBLIC_DB_PASSWORD", "").strip()
        if public_pw:
            return public_pw
        return "postgres"

    @property
    def DB_HOST(self) -> str:
        return self._get_str("PUBLIC_DB_HOST", "127.0.0.1")

    @property
    def DB_PORT(self) -> int:
        return int(self._get_str("PUBLIC_DB_PORT", "54322"))

    @property
    def DB_NAME(self) -> str:
        return self._get_str("PUBLIC_DB_NAME", "postgres")

    @property
    def DB_SSL_MODE(self) -> str:
        return self._get_str("PUBLIC_DB_SSL_MODE", "").strip()

    @property
    def DATABASE_URL(self) -> str:
        raw = self._get_str("PRIVATE_DATABASE_URL", "").strip()
        if raw:
            url = self._normalize_legacy_database_url(raw)
            self._reject_transaction_pooler_url(url)
            return url

        url_obj = URL.create(
            drivername="postgresql+asyncpg",
            username=self.DB_USER,
            password=self.DB_PASSWORD,
            host=self.DB_HOST,
            port=self.DB_PORT,
            database=self.DB_NAME,
        )
        url = str(url_obj)
        self._reject_transaction_pooler_url(url)
        return url

    @property
    def DATABASE_URL_DISPLAY(self) -> str:
        try:
            parsed = urlparse(self.DATABASE_URL)
            host = parsed.hostname or ""
            port = parsed.port or 5432
            path = parsed.path or ""
            return f"{host}:{port}{path}"
        except Exception:
            return "<unparseable>"

    @property
    def db_is_local(self) -> bool:
        return self.DB_HOST in ("localhost", "127.0.0.1", "::1", "db")

    @property
    def PG_POOL_MIN(self) -> int:
        return int(self._get_str("PUBLIC_PG_POOL_MIN", "2"))

    @property
    def PG_POOL_MAX(self) -> int:
        return int(self._get_str("PUBLIC_PG_POOL_MAX", "10"))

    @property
    def PG_ACQUIRE_TIMEOUT(self) -> float:
        return float(self._get_str("PUBLIC_PG_ACQUIRE_TIMEOUT", "10"))

    @property
    def PG_COMMAND_TIMEOUT(self) -> int:
        return int(self._get_str("PUBLIC_PG_COMMAND_TIMEOUT", "30"))

    @property
    def REDIS_URL(self) -> str:
        return self._get_str("PUBLIC_REDIS_URL", "").strip()

    @property
    def JWT_SECRET(self) -> str:
        raw = self._get_str("PRIVATE_JWT_SECRET", "").strip()
        if self.is_production and (not raw or raw == _DEV_JWT_FALLBACK):
            raise RuntimeError("PRIVATE_JWT_SECRET must be set in production. Do not use default.")
        return raw or _DEV_JWT_FALLBACK

    @property
    def JWT_ALGORITHM(self) -> str:
        return self._get_str("PUBLIC_JWT_ALGORITHM", "HS256").strip() or "HS256"

    @property
    def JWT_ACCESS_EXPIRATION_MINUTES(self) -> int:
        raw = self._get_str("PUBLIC_JWT_ACCESS_EXPIRATION_MINUTES", "").strip()
        if raw:
            return int(raw)
        return 15 if self.is_production else 480

    @property
    def REFRESH_TOKEN_EXPIRATION_DAYS(self) -> int:
        return int(self._get_str("PUBLIC_REFRESH_TOKEN_EXPIRATION_DAYS", "7"))

    @property
    def SUPABASE_URL(self) -> str:
        default = "http://127.0.0.1:54321" if self.is_development or self.is_test else ""
        url = self._get_str("PUBLIC_SUPABASE_URL", default).strip().rstrip("/")
        if self.is_production and not url:
            raise RuntimeError(
                "PUBLIC_SUPABASE_URL must be set in production. "
                "Supabase is the sole auth provider in deployed environments."
            )
        return url

    @property
    def supabase_jwks_url(self) -> str:
        return f"{self.SUPABASE_URL}/auth/v1/.well-known/jwks.json" if self.SUPABASE_URL else ""

    @property
    def supabase_issuer(self) -> str:
        return f"{self.SUPABASE_URL}/auth/v1" if self.SUPABASE_URL else ""

    @property
    def PUBLIC_SUPABASE_PUBLISHABLE_KEY(self) -> str:
        return self._get_str("PUBLIC_SUPABASE_PUBLISHABLE_KEY", "").strip()

    @property
    def SUPABASE_SECRET_KEY(self) -> str:
        return self._get_str("PRIVATE_SUPABASE_SECRET_KEY", "").strip()

    @property
    def CORS_ORIGINS(self) -> str:
        return self._get_str("PUBLIC_CORS_ORIGINS", "*")

    @property
    def CORS_ORIGIN_REGEX(self) -> str:
        return self._get_str("PUBLIC_CORS_ORIGIN_REGEX", "").strip()

    @property
    def cors_is_permissive(self) -> bool:
        o = self.CORS_ORIGINS
        return not o.strip() or o == "*" or "*" in o.split(",")

    @property
    def cors_warn_in_deployed(self) -> bool:
        return self.is_deployed and self.cors_is_permissive

    def _enforce_cors(self) -> None:
        if self.is_production and self.cors_is_permissive:
            raise RuntimeError(
                "PUBLIC_CORS_ORIGINS must not be '*' or empty in production. "
                "Set PUBLIC_CORS_ORIGINS=https://your-vercel-app.vercel.app"
            )

    @property
    def SENTRY_DSN(self) -> str:
        return self._get_str("PRIVATE_SENTRY_DSN", "").strip()

    @property
    def ALLOW_PUBLIC_AUTH(self) -> bool:
        raw = self._get_str("PUBLIC_ALLOW_PUBLIC_AUTH", "").strip().lower()
        return raw in ("1", "true", "yes")

    @property
    def ANTHROPIC_API_KEY(self) -> str:
        return self._get_str("PRIVATE_ANTHROPIC_API_KEY", "").strip()

    @property
    def ANTHROPIC_AVAILABLE(self) -> bool:
        return bool(self.ANTHROPIC_API_KEY)

    @property
    def ANTHROPIC_MODEL(self) -> str:
        return (
            self._get_str("PUBLIC_ANTHROPIC_MODEL", "claude-sonnet-4-6").strip()
            or "claude-sonnet-4-6"
        )

    @property
    def ANTHROPIC_FAST_MODEL(self) -> str:
        return (
            self._get_str("PUBLIC_ANTHROPIC_FAST_MODEL", "claude-sonnet-4-6").strip()
            or "claude-sonnet-4-6"
        )

    @property
    def OPENAI_API_KEY(self) -> str:
        return self._get_str("PRIVATE_OPENAI_API_KEY", "").strip()

    @property
    def OPENAI_AVAILABLE(self) -> bool:
        return bool(self.OPENAI_API_KEY)

    @property
    def OPENROUTER_API_KEY(self) -> str:
        return self._get_str("PRIVATE_OPENROUTER_API_KEY", "").strip()

    @property
    def OPENROUTER_BASE_URL(self) -> str:
        return (
            self._get_str("PUBLIC_OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").strip()
            or "https://openrouter.ai/api/v1"
        )

    @property
    def OPENROUTER_AVAILABLE(self) -> bool:
        return bool(self.OPENROUTER_API_KEY)

    @property
    def EMBEDDING_MODEL(self) -> str:
        return (
            self._get_str("PUBLIC_EMBEDDING_MODEL", "text-embedding-3-small").strip()
            or "text-embedding-3-small"
        )

    def _load_agent_model(self) -> str:
        env_override = self._get_str("PUBLIC_AGENT_PRIMARY_MODEL", "").strip()
        if env_override:
            return env_override
        try:
            yaml_path = self._backend_root / "assistant" / "config" / "models.yaml"
            if yaml_path.exists():
                data = yaml.safe_load(yaml_path.read_text()) or {}
                model = (data.get("primary") or "").strip()
                if model:
                    return model
        except (OSError, ValueError, KeyError):
            logger.warning("Failed to parse models.yaml, using built-in default", exc_info=True)
        return "anthropic:claude-sonnet-4-6"

    @property
    def AGENT_PRIMARY_MODEL(self) -> str:
        if self._env == "production":
            if not hasattr(self, "_cached_agent_primary"):
                self._cached_agent_primary = self._load_agent_model()
            return self._cached_agent_primary
        return self._load_agent_model()

    def _load_synthesis_model(self) -> str:
        env_override = self._get_str("PUBLIC_MODEL_REGISTRY_INFRA_SYNTHESIS", "").strip()
        if env_override:
            return env_override
        try:
            yaml_path = self._backend_root / "assistant" / "config" / "models.yaml"
            if yaml_path.exists():
                data = yaml.safe_load(yaml_path.read_text()) or {}
                model = (data.get("synthesis") or "").strip()
                if model:
                    return model
        except (OSError, ValueError, KeyError):
            logger.warning("Failed to parse synthesis from models.yaml", exc_info=True)
        return "anthropic:claude-haiku-4-5"

    @property
    def INFRA_SYNTHESIS_MODEL(self) -> str:
        if self._env == "production":
            if not hasattr(self, "_cached_synthesis"):
                self._cached_synthesis = self._load_synthesis_model()
            return self._cached_synthesis
        return self._load_synthesis_model()

    def _load_classifier_model(self) -> str:
        env_override = self._get_str("PUBLIC_MODEL_REGISTRY_INFRA_CLASSIFIER", "").strip()
        if env_override:
            return env_override
        try:
            yaml_path = self._backend_root / "assistant" / "config" / "models.yaml"
            if yaml_path.exists():
                data = yaml.safe_load(yaml_path.read_text()) or {}
                model = (data.get("classifier") or "").strip()
                if model:
                    return model
        except (OSError, ValueError, KeyError):
            logger.warning("Failed to parse classifier from models.yaml", exc_info=True)
        return "anthropic:claude-haiku-4-5"

    @property
    def INFRA_CLASSIFIER_MODEL(self) -> str:
        if self._env == "production":
            if not hasattr(self, "_cached_classifier"):
                self._cached_classifier = self._load_classifier_model()
            return self._cached_classifier
        return self._load_classifier_model()

    LLM_SETUP_URL: str = "https://console.anthropic.com/"

    @property
    def SESSION_COST_CAP(self) -> float:
        return float(self._get_str("PUBLIC_SESSION_COST_CAP", "2.00"))

    @property
    def FRONTEND_URL(self) -> str:
        return self._get_str("PUBLIC_FRONTEND_URL", "").strip().rstrip("/")

    @property
    def XERO_CLIENT_ID(self) -> str:
        return self._get_str("PUBLIC_XERO_CLIENT_ID", "").strip()

    @property
    def XERO_CLIENT_SECRET(self) -> str:
        return self._get_str("PRIVATE_XERO_CLIENT_SECRET", "").strip()

    @property
    def XERO_REDIRECT_URI(self) -> str:
        return self._get_str("PUBLIC_XERO_REDIRECT_URI", "").strip()

    @property
    def XERO_SYNC_HOUR(self) -> int:
        return int(self._get_str("PUBLIC_XERO_SYNC_HOUR", "2"))

    @property
    def WORKERS(self) -> int:
        return int(self._get_str("PUBLIC_WORKERS", "1"))

    @property
    def LOG_LEVEL(self) -> str:
        return self._get_str("PUBLIC_LOG_LEVEL", "INFO").upper() or "INFO"

    @property
    def METRICS_TOKEN(self) -> str:
        return self._get_str("PRIVATE_METRICS_TOKEN", "").strip()

    @property
    def REQUEST_TIMEOUT(self) -> int:
        return int(self._get_str("PUBLIC_REQUEST_TIMEOUT", "30"))

    @property
    def AI_REQUEST_TIMEOUT(self) -> int:
        return int(self._get_str("PUBLIC_AI_REQUEST_TIMEOUT", "120"))

    @property
    def MAX_CONCURRENT_GENERATIONS(self) -> int:
        return int(self._get_str("PUBLIC_MAX_CONCURRENT_GENERATIONS", "4"))

    @property
    def GENERATION_QUEUE_TIMEOUT(self) -> float:
        return float(self._get_str("PUBLIC_GENERATION_QUEUE_TIMEOUT", "10"))

    def _get_jwks_client(self) -> jwt.PyJWKClient | None:
        key = self.supabase_jwks_url
        if key != self._jwks_client_key:
            self._jwks_client = None
            self._jwks_client_key = key
        if self._jwks_client is None and key:
            self._jwks_client = jwt.PyJWKClient(
                key,
                cache_keys=True,
                lifespan=3600,
                timeout=5,
            )
        return self._jwks_client

    def decode_token(self, token: str) -> dict:
        """Decode JWT for the current environment (Supabase ES256 vs HS256 in test)."""

        def _decode_es256() -> dict:
            jwks = self._get_jwks_client()
            if jwks is None:
                raise jwt.InvalidTokenError(
                    "SUPABASE_URL not configured for JWKS token verification"
                )
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
                issuer=self.supabase_issuer,
                options={"verify_aud": False, "verify_iss": True},
            )

        if self.is_production:
            return _decode_es256()

        if not self.is_test:
            try:
                header = jwt.get_unverified_header(token)
            except jwt.InvalidTokenError:
                header = {}
            if header.get("alg") == "ES256" and self.supabase_jwks_url:
                return _decode_es256()

        return jwt.decode(token, self.JWT_SECRET, algorithms=[self.JWT_ALGORITHM])

    def startup_summary(self) -> dict[str, Any]:
        db_display = self.DATABASE_URL_DISPLAY

        flags: list[str] = []
        if self.cors_is_permissive:
            flags.append("CORS=*")

        return {
            "env": self.ENV,
            "auth_provider": "supabase",
            "db": db_display,
            "cors": self.CORS_ORIGINS if not self.cors_is_permissive else "*",
            "redis": "yes" if self.REDIS_URL else "no",
            "sentry": "yes" if self.SENTRY_DSN else "no",
            "ai": (
                "openrouter"
                if self.OPENROUTER_AVAILABLE
                else ("anthropic" if self.ANTHROPIC_AVAILABLE else "none")
            ),
            "embeddings": "openai" if self.OPENAI_AVAILABLE else "none",
            "flags": flags or None,
        }


config = Config()


def decode_token(token: str) -> dict:
    """Module-level wrapper for callers that import the function."""
    return config.decode_token(token)


def startup_summary() -> dict[str, Any]:
    return config.startup_summary()
