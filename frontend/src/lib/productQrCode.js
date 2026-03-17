/**
 * Deep link URL encoding/decoding for product QR codes.
 *
 * QR labels encode: {origin}/product/scan/{code}
 * The camera scanner extracts the code from scanned URLs.
 * Native iPad camera or third-party QR readers open the URL directly.
 */

const SCAN_PATH_PREFIX = "/product/scan/";

/** Build the deep link URL to encode in a QR label. */
export function buildProductQrValue(code) {
  return `${window.location.origin}${SCAN_PATH_PREFIX}${encodeURIComponent(code)}`;
}

/**
 * Extract the product code from a scanned value.
 * - If the value is a deep link URL from our QR labels → extract the code
 * - Otherwise return the raw value (vendor barcode number, typed SKU, etc.)
 */
export function extractCodeFromScan(scannedValue) {
  if (!scannedValue) return "";
  const trimmed = scannedValue.trim();

  try {
    const url = new URL(trimmed);
    if (url.pathname.startsWith(SCAN_PATH_PREFIX)) {
      const encoded = url.pathname.slice(SCAN_PATH_PREFIX.length);
      return decodeURIComponent(encoded);
    }
  } catch {
    // Not a URL — that's fine, it's a raw barcode string
  }

  return trimmed;
}
