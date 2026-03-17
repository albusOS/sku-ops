import { useRef, useState, useCallback, useEffect } from "react";
import { BrowserMultiFormatReader } from "@zxing/browser";
import { DecodeHintType, BarcodeFormat, NotFoundException } from "@zxing/library";

const DEBOUNCE_MS = 600;

const hints = new Map();
hints.set(DecodeHintType.POSSIBLE_FORMATS, [
  BarcodeFormat.QR_CODE,
  BarcodeFormat.UPC_A,
  BarcodeFormat.EAN_13,
  BarcodeFormat.CODE_128,
]);
hints.set(DecodeHintType.TRY_HARDER, true);

/**
 * Manages camera lifecycle for barcode + QR scanning via @zxing/browser.
 *
 * Supports both vendor barcodes (UPC-A, EAN-13, CODE-128) and QR codes
 * from printed labels. Requests 1280×720 for reliable iPad decoding.
 *
 * Does NOT perform product lookup — it only decodes and calls onScan(code).
 * Wire onScan to useBarcodeScanner.submit(code) in the parent.
 */
export function useCameraScanner({ onScan } = {}) {
  const readerRef = useRef(null);
  const controlsRef = useRef(null);
  const videoRef = useRef(null);
  const lastCodeRef = useRef(null);
  const lastTimeRef = useRef(0);
  const onScanRef = useRef(onScan);
  const [active, setActive] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    onScanRef.current = onScan;
  }, [onScan]);

  const stop = useCallback(async () => {
    try {
      if (controlsRef.current) {
        controlsRef.current.stop();
        controlsRef.current = null;
      }
    } catch {
      controlsRef.current = null;
    }
    readerRef.current = null;
    setActive(false);
  }, []);

  const start = useCallback(async () => {
    setError(null);

    if (controlsRef.current) await stop();

    if (!videoRef.current) {
      setError("Scanner element not ready");
      return;
    }

    try {
      const reader = new BrowserMultiFormatReader(hints);
      readerRef.current = reader;

      const controls = await reader.decodeFromConstraints(
        {
          video: {
            facingMode: "environment",
            width: { min: 640, ideal: 1280 },
            height: { min: 480, ideal: 720 },
          },
        },
        videoRef.current,
        (result, err) => {
          if (result) {
            const code = result.getText();
            const now = Date.now();
            if (code === lastCodeRef.current && now - lastTimeRef.current < DEBOUNCE_MS) return;
            lastCodeRef.current = code;
            lastTimeRef.current = now;
            onScanRef.current?.(code);
          } else if (err && !(err instanceof NotFoundException)) {
            // NotFoundException is thrown every frame when no code is visible — expected
          }
        },
      );

      controlsRef.current = controls;
      setActive(true);
    } catch (err) {
      controlsRef.current = null;
      readerRef.current = null;
      const msg = err?.message || String(err) || "Camera not available";
      if (msg.includes("NotAllowedError") || msg.includes("Permission") || msg.includes("denied")) {
        setError("Camera permission denied. Allow camera access in your browser settings.");
      } else if (msg.includes("NotFoundError") || msg.includes("no camera")) {
        setError("No camera found on this device.");
      } else if (msg.includes("NotReadableError") || msg.includes("in use")) {
        setError("Camera is in use by another app. Close other apps and try again.");
      } else {
        setError(`Camera error: ${msg}`);
      }
    }
  }, [stop]);

  useEffect(() => {
    return () => {
      if (controlsRef.current) {
        try {
          controlsRef.current.stop();
        } catch {
          /* unmount cleanup — best effort */
        }
        controlsRef.current = null;
      }
    };
  }, []);

  return { videoRef, start, stop, active, error };
}
