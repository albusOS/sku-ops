"""Factory for invoicing gateway. Returns real adapter when connected, stub otherwise."""

from finance.adapters.stub_xero import StubXeroAdapter
from finance.domain.xero_settings import XeroSettings

try:
    from finance.adapters.xero_adapter import XeroAdapter
except ImportError:
    XeroAdapter = None  # type: ignore[misc, assignment]


def get_invoicing_gateway(settings: XeroSettings):
    """Return XeroAdapter if org has active Xero tokens, otherwise StubXeroAdapter."""
    if (
        settings.xero_access_token
        and settings.xero_tenant_id
        and XeroAdapter is not None
    ):
        return XeroAdapter()
    return StubXeroAdapter()
