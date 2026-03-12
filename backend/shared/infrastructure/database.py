"""Backward-compatibility shim — re-exports from the new db package.

All existing imports like ``from shared.infrastructure.database import get_connection``
continue to work unchanged.
"""

from shared.infrastructure.db import (
    close_db,
    get_connection,
    get_org_id,
    get_user_id,
    init_db,
    transaction,
)
from shared.infrastructure.logging_config import org_id_var, user_id_var

__all__ = [
    "close_db",
    "get_connection",
    "get_org_id",
    "get_user_id",
    "init_db",
    "org_id_var",
    "transaction",
    "user_id_var",
]
