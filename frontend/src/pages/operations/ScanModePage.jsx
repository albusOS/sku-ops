import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Send, Trash2, ScanLine, Loader2, Camera, Keyboard, Package } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { QuantityControl } from "@/components/QuantityControl";
import { UnknownBarcodeSheet } from "@/components/UnknownBarcodeSheet";
import { CameraScanner } from "@/components/CameraScanner";
import { PageSkeleton } from "@/components/LoadingSkeleton";
import { QueryError } from "@/components/QueryError";
import { JobPicker } from "@/components/JobPicker";
import { AddressPicker } from "@/components/AddressPicker";
import { useBarcodeScanner } from "@/hooks/useBarcodeScanner";
import { useCart } from "@/hooks/useCart";
import { useProducts } from "@/hooks/useProducts";
import { useCreateWithdrawal } from "@/hooks/useWithdrawals";
import { getErrorMessage } from "@/lib/api-client";

const STATUS_CONFIG = {
  added: {
    color: "text-success",
    bg: "bg-success/10 border-success/30",
    ring: "ring-success/20",
    label: "Added",
  },
  not_found: {
    color: "text-warning",
    bg: "bg-warning/10 border-warning/30",
    ring: "ring-warning/20",
    label: "Not found",
  },
  invalid: {
    color: "text-destructive",
    bg: "bg-destructive/10 border-destructive/30",
    ring: "ring-destructive/20",
    label: "Invalid barcode",
  },
  out_of_stock: {
    color: "text-muted-foreground",
    bg: "bg-muted border-border",
    ring: "ring-border",
    label: "Out of stock",
  },
};

const ScanModePage = () => {
  const navigate = useNavigate();
  const [lastScanned, setLastScanned] = useState(null);
  const [unknownBarcode, setUnknownBarcode] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [cameraMode, setCameraMode] = useState(true);
  const [jobId, setJobId] = useState("");
  const [serviceAddress, setServiceAddress] = useState("");

  const {
    items,
    addItem,
    updateQuantity,
    removeItem,
    clear: clearCart,
    total: subtotal,
  } = useCart({ persist: true });
  const {
    data: productsData,
    isLoading: productsLoading,
    isError: productsIsError,
    error: productsError,
  } = useProducts();
  const allProducts = Array.isArray(productsData) ? productsData : productsData?.items || [];
  const createWithdrawal = useCreateWithdrawal();

  const scanner = useBarcodeScanner({
    onSuccess: (product) => {
      if ((product.sell_quantity ?? product.quantity) <= 0) {
        toast.error("Out of stock");
        setLastScanned({ sku: product.sku, status: "out_of_stock" });
        return;
      }
      addItem(product);
      setLastScanned({ sku: product.sku, name: product.name, status: "added" });
    },
    onNotFound: ({ barcode }) => {
      setUnknownBarcode(barcode);
      setLastScanned({ sku: barcode, status: "not_found" });
    },
    onInvalidCheckDigit: (barcode) => {
      toast.error("Bad check digit");
      setLastScanned({ sku: barcode, status: "invalid" });
    },
  });

  const handleSubmit = async () => {
    if (items.length === 0) {
      toast.error("Cart is empty");
      return;
    }
    if (!jobId.trim()) {
      toast.error("Job ID is required");
      return;
    }
    if (!serviceAddress.trim()) {
      toast.error("Service address is required");
      return;
    }
    setSubmitting(true);
    try {
      await createWithdrawal.mutateAsync({
        items: items.map(({ product_id, sku, name, quantity, unit_price, unit }) => ({
          product_id,
          sku,
          name,
          quantity,
          unit_price,
          cost: 0,
          subtotal: quantity * unit_price,
          unit: unit || "each",
        })),
        job_id: jobId.trim(),
        service_address: serviceAddress.trim(),
      });
      toast.success("Sale complete!", {
        action: { label: "View transactions", onClick: () => navigate("/pos") },
      });
      clearCart();
      setLastScanned(null);
      setJobId("");
      setServiceAddress("");
    } catch (err) {
      const data = err.response?.data;
      if (data?.error_type === "insufficient_stock") {
        toast.error(`Not enough ${data.sku} — only ${data.available} available`);
      } else {
        toast.error(getErrorMessage(err));
      }
    } finally {
      setSubmitting(false);
      if (!cameraMode) scanner.inputRef.current?.focus();
    }
  };

  const status = lastScanned ? STATUS_CONFIG[lastScanned.status] : null;
  const canSubmit = items.length > 0 && jobId.trim() && serviceAddress.trim();
  const itemCount = items.reduce((sum, i) => sum + i.quantity, 0);

  if (productsLoading) return <PageSkeleton />;
  if (productsIsError) {
    return (
      <div className="flex flex-col h-screen bg-muted">
        <QueryError
          error={productsError}
          onRetry={() => window.location.reload()}
          className="flex-1"
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-muted/50">
      {/* ── Header: Job + Address ── */}
      <div className="flex-shrink-0 bg-card border-b border-border px-6 pt-5 pb-4">
        <div className="max-w-2xl mx-auto">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-lg font-semibold text-foreground tracking-tight">
              Scan & Checkout
            </h1>
            {items.length > 0 && (
              <Badge variant="secondary" className="text-xs">
                {itemCount} item{itemCount !== 1 ? "s" : ""}
              </Badge>
            )}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-muted-foreground text-xs font-medium mb-1.5 block">
                Job *
              </Label>
              <JobPicker value={jobId} onChange={setJobId} required />
            </div>
            <div>
              <Label className="text-muted-foreground text-xs font-medium mb-1.5 block">
                Address *
              </Label>
              <AddressPicker value={serviceAddress} onChange={setServiceAddress} required />
            </div>
          </div>
        </div>
      </div>

      {/* ── Mode toggle + Scanner ── */}
      <div className="flex-shrink-0 bg-card border-b border-border px-6 py-4">
        <div className="max-w-2xl mx-auto">
          {/* Mode toggle */}
          <div className="flex gap-1 bg-muted rounded-xl p-1 mb-4">
            <button
              onClick={() => setCameraMode(true)}
              className={`flex-1 flex items-center justify-center gap-2 rounded-lg px-3 py-2.5 text-sm font-medium transition-all ${
                cameraMode
                  ? "bg-card text-foreground shadow-sm ring-1 ring-border/50"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Camera className="w-4 h-4" />
              Camera
            </button>
            <button
              onClick={() => setCameraMode(false)}
              className={`flex-1 flex items-center justify-center gap-2 rounded-lg px-3 py-2.5 text-sm font-medium transition-all ${
                !cameraMode
                  ? "bg-card text-foreground shadow-sm ring-1 ring-border/50"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Keyboard className="w-4 h-4" />
              Manual
            </button>
          </div>

          {/* Scanner area */}
          {cameraMode ? (
            <CameraScanner
              onScan={(code) => scanner.submit(code)}
              onClose={() => setCameraMode(false)}
              scanning={scanner.scanning}
            />
          ) : (
            <div
              className={`rounded-2xl border-2 p-5 transition-all ${
                status ? status.bg : "bg-muted/50 border-border"
              }`}
            >
              <div className="flex items-center gap-3 mb-3">
                <div
                  className={`w-10 h-10 rounded-xl flex items-center justify-center ring-1 ${
                    status ? `${status.bg} ${status.ring}` : "bg-muted ring-border"
                  }`}
                >
                  <ScanLine
                    className={`w-5 h-5 ${status ? status.color : "text-muted-foreground"}`}
                  />
                </div>
                <span
                  className={`font-semibold text-base ${status ? status.color : "text-muted-foreground"}`}
                >
                  {lastScanned
                    ? `${status?.label}: ${lastScanned.name || lastScanned.sku}`
                    : "Ready to scan…"}
                </span>
              </div>
              <Input
                ref={scanner.inputRef}
                type="text"
                value={scanner.value}
                onChange={(e) => scanner.setValue(e.target.value)}
                onKeyDown={scanner.onKeyDown}
                placeholder="Scan barcode or type SKU…"
                className="text-lg h-14 font-mono text-center tracking-widest bg-card"
                autoFocus
                disabled={scanner.scanning}
              />
              <p className="text-xs text-center text-muted-foreground mt-2">
                {scanner.scanning ? "Looking up…" : "Type a barcode or SKU and press Enter"}
              </p>
            </div>
          )}

          {/* Camera mode status toast */}
          {cameraMode && lastScanned && status && (
            <div
              className={`mt-3 rounded-xl border-2 px-4 py-3 flex items-center gap-3 transition-all ${status.bg}`}
            >
              <div
                className={`w-8 h-8 rounded-lg flex items-center justify-center ring-1 ${status.ring} ${status.bg}`}
              >
                <ScanLine className={`w-4 h-4 ${status.color}`} />
              </div>
              <span className={`text-sm font-medium ${status.color}`}>
                {status.label}: {lastScanned.name || lastScanned.sku}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* ── Cart ── */}
      <div className="flex-1 overflow-auto px-6 py-4">
        <div className="max-w-2xl mx-auto">
          {items.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <div className="w-14 h-14 rounded-2xl bg-muted flex items-center justify-center mb-4">
                <Package className="w-7 h-7 text-muted-foreground/40" />
              </div>
              <p className="text-sm font-medium text-muted-foreground">Cart is empty</p>
              <p className="text-xs text-muted-foreground/70 mt-1">
                Scan items to add them to your cart
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {items.map((item) => (
                <div
                  key={item.product_id}
                  className="bg-card border border-border/80 rounded-xl px-4 py-3 flex items-center gap-3 shadow-soft"
                >
                  <div className="flex-1 min-w-0">
                    <p className="font-mono text-[10px] text-muted-foreground">{item.sku}</p>
                    <p className="font-medium text-foreground truncate">{item.name}</p>
                  </div>
                  <QuantityControl
                    value={item.quantity}
                    onChange={(v) => updateQuantity(item.product_id, v)}
                    max={item.max_quantity}
                  />
                  <span className="font-semibold text-sm text-foreground tabular-nums min-w-[60px] text-right">
                    ${(item.quantity * item.unit_price).toFixed(2)}
                  </span>
                  <button
                    onClick={() => removeItem(item.product_id)}
                    className="text-muted-foreground/50 hover:text-destructive transition-colors p-1.5 rounded-lg hover:bg-destructive/5"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* ── Footer ── */}
      <div className="flex-shrink-0 bg-card border-t border-border px-6 py-4 safe-area-bottom">
        <div className="max-w-2xl mx-auto flex items-center gap-4">
          <div className="flex-1">
            <p className="text-xs text-muted-foreground">
              {itemCount} item{itemCount !== 1 ? "s" : ""}
            </p>
            <p className="text-xl font-bold text-foreground tabular-nums">${subtotal.toFixed(2)}</p>
          </div>
          <Button
            onClick={handleSubmit}
            disabled={!canSubmit || submitting}
            className="btn-primary h-14 px-10 text-base font-semibold shadow-sm"
          >
            {submitting ? (
              <>
                <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                Processing…
              </>
            ) : (
              <>
                <Send className="w-5 h-5 mr-2" />
                Checkout
              </>
            )}
          </Button>
        </div>
      </div>

      <UnknownBarcodeSheet
        open={!!unknownBarcode}
        onOpenChange={(open) => {
          if (!open) setUnknownBarcode(null);
        }}
        barcode={unknownBarcode}
        products={allProducts}
        onAddProduct={(product) => {
          addItem(product);
          setLastScanned({
            sku: product.sku,
            name: product.name,
            status: "added",
          });
          toast.success(`Added: ${product.sku} (+1)`);
          setUnknownBarcode(null);
        }}
      />
    </div>
  );
};

export default ScanModePage;
