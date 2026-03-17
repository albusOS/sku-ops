import { useEffect } from "react";
import { Camera, CameraOff, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useCameraScanner } from "@/hooks/useCameraScanner";

/**
 * Camera viewfinder for barcode + QR scanning.
 *
 * Decodes vendor barcodes (UPC-A, EAN-13, CODE-128) and printed QR labels.
 * Calls onScan(code) — parent wires it to useBarcodeScanner.submit().
 */
export function CameraScanner({ onScan, onClose, scanning = false }) {
  const { videoRef, start, stop, active, error } = useCameraScanner({ onScan });

  useEffect(() => {
    start();
    return () => {
      stop();
    };
  }, [start, stop]);

  return (
    <div className="relative rounded-2xl overflow-hidden bg-black">
      <video
        ref={videoRef}
        className="w-full aspect-[4/3] object-cover"
        autoPlay
        playsInline
        muted
      />

      {/* Targeting reticle */}
      {active && !scanning && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div
            className="relative border-2 border-white/40 rounded-xl"
            style={{ width: "65%", height: "55%" }}
          >
            <div className="absolute -top-px -left-px w-6 h-6 border-t-[3px] border-l-[3px] border-white rounded-tl-lg" />
            <div className="absolute -top-px -right-px w-6 h-6 border-t-[3px] border-r-[3px] border-white rounded-tr-lg" />
            <div className="absolute -bottom-px -left-px w-6 h-6 border-b-[3px] border-l-[3px] border-white rounded-bl-lg" />
            <div className="absolute -bottom-px -right-px w-6 h-6 border-b-[3px] border-r-[3px] border-white rounded-br-lg" />
          </div>
          <p className="absolute bottom-4 text-white/70 text-xs font-medium">
            Point at barcode or QR code
          </p>
        </div>
      )}

      {scanning && (
        <div className="absolute inset-0 bg-black/40 flex items-center justify-center">
          <span className="text-white text-sm font-medium animate-pulse">Looking up…</span>
        </div>
      )}

      {error && (
        <div className="absolute inset-0 bg-card flex flex-col items-center justify-center gap-3 p-6 text-center">
          <CameraOff className="w-10 h-10 text-muted-foreground" />
          <p className="text-sm text-muted-foreground max-w-xs">{error}</p>
          <Button variant="outline" size="sm" onClick={start}>
            <Camera className="w-4 h-4 mr-2" />
            Try Again
          </Button>
        </div>
      )}

      {!error && !active && !scanning && (
        <div className="absolute inset-0 bg-card flex items-center justify-center">
          <span className="text-sm text-muted-foreground animate-pulse">Starting camera…</span>
        </div>
      )}

      <button
        onClick={() => {
          stop();
          onClose();
        }}
        className="absolute top-3 right-3 rounded-full bg-black/50 p-2 text-white hover:bg-black/70 transition-colors"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}
