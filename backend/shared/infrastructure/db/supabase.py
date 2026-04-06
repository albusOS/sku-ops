"""Lazy Supabase client access for backend infrastructure and helpers."""

from __future__ import annotations

from supabase import acreate_client, create_client

from shared.infrastructure.config import config

_sync_clients: dict[bool, object | None] = {False: None, True: None}
_async_clients: dict[bool, object | None] = {False: None, True: None}
_sync_fingerprint: dict[bool, tuple[str, str] | None] = {False: None, True: None}
_async_fingerprint: dict[bool, tuple[str, str] | None] = {False: None, True: None}


def _get_key(admin: bool) -> str:
    if admin:
        return config.SUPABASE_SECRET_KEY
    return config.PUBLIC_SUPABASE_PUBLISHABLE_KEY


def _build_sync(admin: bool):
    url = config.SUPABASE_URL
    key = _get_key(admin)
    if not url or not key:
        return None

    return create_client(url, key)


def _build_async(admin: bool):
    url = config.SUPABASE_URL
    key = _get_key(admin)
    if not url or not key:
        return None

    return acreate_client(url, key)


def get_supabase(admin: bool = False):
    url = config.SUPABASE_URL
    key = _get_key(admin)
    fp = (url, key)
    if _sync_clients[admin] is not None and _sync_fingerprint[admin] == fp:
        return _sync_clients[admin]
    _sync_fingerprint[admin] = fp
    client = _build_sync(admin)
    _sync_clients[admin] = client
    return client


async def get_async_supabase(admin: bool = False):
    url = config.SUPABASE_URL
    key = _get_key(admin)
    fp = (url, key)
    if _async_clients[admin] is not None and _async_fingerprint[admin] == fp:
        return _async_clients[admin]
    _async_fingerprint[admin] = fp
    client = await _build_async(admin)
    _async_clients[admin] = client
    return client


class _LazyClientProxy:
    def __init__(self, factory) -> None:
        self._factory = factory

    def __getattr__(self, name: str):
        client = self._factory()
        if client is None:
            raise RuntimeError("Supabase client is not configured for this environment.")
        return getattr(client, name)


supabase = _LazyClientProxy(lambda: get_supabase(False))
supabase_admin = _LazyClientProxy(lambda: get_supabase(True))
