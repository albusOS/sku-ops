"""Catalog-specific domain errors."""

from shared.kernel.errors import DomainError


class DuplicateBarcodeError(DomainError):
    """Raised when barcode is already used by another product."""

    status_hint = 409

    def __init__(self, barcode: str, product_name: str):
        self.barcode = barcode
        self.product_name = product_name
        super().__init__(f"Barcode already used by product: {product_name}")


class DuplicateSkuError(DomainError):
    """Raised when a SKU code is already used by another product."""

    status_hint = 409

    def __init__(self, sku_code: str, existing_name: str):
        self.sku_code = sku_code
        self.existing_name = existing_name
        super().__init__(f"SKU code '{sku_code}' already used by: {existing_name}")


class InvalidBarcodeError(DomainError):
    """Raised when barcode fails validation (e.g. invalid UPC check digit)."""

    def __init__(self, barcode: str, reason: str):
        self.barcode = barcode
        self.reason = reason
        super().__init__(f"Invalid barcode: {reason}")
