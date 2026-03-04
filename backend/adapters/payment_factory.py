"""Factory for payment gateway. Uses config (env-aware) for adapter selection."""
from adapters.stub_payment import StubPaymentAdapter

from shared.infrastructure.config import STRIPE_API_KEY, payment_adapter


def get_payment_gateway(webhook_url: str = ""):
    """
    Return the active payment gateway.
    - test/ENV=test: always stub
    - dev: stub unless STRIPE_API_KEY set
    - staging/production: stripe when configured, else stub
    """
    if payment_adapter == "stub":
        return StubPaymentAdapter()
    if STRIPE_API_KEY:
        try:
            from adapters.stripe_payment import StripePaymentAdapter
            return StripePaymentAdapter(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
        except ImportError:
            pass
    return StubPaymentAdapter()
