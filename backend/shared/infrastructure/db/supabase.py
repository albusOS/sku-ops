"""Lazy Supabase client access for backend infrastructure and helpers."""

from __future__ import annotations

import os

from shared.infrastructure.config import SUPABASE_URL

_sync_clients: dict[bool, object | None] = {False: None, True: None}
_async_clients: dict[bool, object | None] = {False: None, True: None}


def _get_key(admin: bool) -> str:
    if admin:
        return os.environ.get("SUPABASE_SERVICE_KEY", "").strip()
    return os.environ.get("PUBLIC_SUPABASE_ANON_KEY", "").strip()


def _build_sync(admin: bool):
    if not SUPABASE_URL or not _get_key(admin):
        return None
    from supabase import create_client

    return create_client(SUPABASE_URL, _get_key(admin))


def _build_async(admin: bool):
    if not SUPABASE_URL or not _get_key(admin):
        return None
    from supabase import acreate_client

    return acreate_client(SUPABASE_URL, _get_key(admin))


def get_supabase(admin: bool = False):
    client = _sync_clients[admin]
    if client is None:
        client = _build_sync(admin)
        _sync_clients[admin] = client
    return client


async def get_async_supabase(admin: bool = False):
    client = _async_clients[admin]
    if client is None:
        client = await _build_async(admin)
        _async_clients[admin] = client
    return client


class _LazyClientProxy:
    def __init__(self, factory) -> None:
        self._factory = factory

    def __getattr__(self, name: str):
        client = self._factory()
        if client is None:
            raise RuntimeError(
                "Supabase client is not configured for this environment."
            )
        return getattr(client, name)


supabase = _LazyClientProxy(lambda: get_supabase(False))
supabase_admin = _LazyClientProxy(lambda: get_supabase(True))
