"""Backward-compatibility shim — XeroAdapter now lives in finance.adapters.xero package."""

from finance.adapters.xero import XeroAdapter, _xero_status

__all__ = ["XeroAdapter", "_xero_status"]
