import { useRef, useState, useCallback } from "react";
import api from "@/lib/api-client";
import { extractCodeFromScan } from "@/lib/productQrCode";

/**
 * Encapsulates the barcode scan loop state machine for keyboard-wedge scanners.
 *
 * Usage:
 *   const { inputRef, value, setValue, onKeyDown, scanning } = useBarcodeScanner({
 *     onSuccess,       // (product) => void  — product resolved, add to cart
 *     onNotFound,      // ({ barcode }) => void  — no match, show recovery UI
 *     onInvalidCheckDigit, // (barcode) => void  — bad UPC/EAN digit
 *   });
 *
 * Wire inputRef to the <input ref={inputRef}> and onKeyDown to its onKeyDown.
 * The hook handles: Enter → lookup → dispatch → clear → re-focus.
 */
export function useBarcodeScanner({ onSuccess, onNotFound, onInvalidCheckDigit } = {}) {
  const inputRef = useRef(null);
  const [value, setValue] = useState("");
  const [scanning, setScanning] = useState(false);

  const submit = useCallback(
    async (code) => {
      const trimmed = extractCodeFromScan(code);
      if (!trimmed) return;

      setScanning(true);
      try {
        const product = await api.products.byBarcode(trimmed);
        onSuccess?.(product);
      } catch (err) {
        const detail = err?.response?.data?.detail;
        const errorCode = typeof detail === "object" ? detail?.code : null;

        if (errorCode === "invalid_check_digit") {
          onInvalidCheckDigit?.(trimmed);
        } else {
          // not_found or any unexpected error
          onNotFound?.({ barcode: trimmed });
        }
      } finally {
        setScanning(false);
        setValue("");
        // Re-focus immediately so the next scan is captured without the
        // contractor needing to tap the input again.
        requestAnimationFrame(() => inputRef.current?.focus());
      }
    },
    [onSuccess, onNotFound, onInvalidCheckDigit],
  );

  const onKeyDown = useCallback(
    (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        submit(e.target.value);
      }
    },
    [submit],
  );

  return { inputRef, value, setValue, onKeyDown, scanning, submit };
}
