import { useRef, useState, useEffect, useMemo } from "react";
import { useReactToPrint } from "react-to-print";
import { QRCodeSVG } from "qrcode.react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "./ui/dialog";
import { Printer, Search, CheckSquare, Square, Minus, Plus } from "lucide-react";
import { buildProductQrValue } from "@/lib/productQrCode";

/**
 * Printable QR code labels with product selection.
 *
 * Two modes based on the `products` prop:
 *  - Few items (≤5) → skip selection, go straight to print preview (e.g. from ProductDetailPanel)
 *  - Many items (>5) → show searchable selection list, user picks products + quantities
 *
 * Sizing: QR at 120px / 0.9in print, error correction "M", 1.15×1.6in labels, 3 per row.
 */
export function BarcodeLabelsModal({ products, open, onOpenChange }) {
  const printRef = useRef(null);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState(new Map());
  const [showPreview, setShowPreview] = useState(false);

  const available = useMemo(
    () => (products ?? []).filter((p) => (p.barcode || p.sku)?.toString().trim()),
    [products],
  );

  const skipSelection = available.length <= 5;

  useEffect(() => {
    if (!open) {
      setSearch("");
      setSelected(new Map());
      setShowPreview(false);
      return;
    }
    if (skipSelection) {
      const map = new Map();
      available.forEach((p) => {
        const existing = map.get(p.id) || 0;
        map.set(p.id, existing + 1);
      });
      setSelected(map);
      setShowPreview(true);
    }
  }, [open, skipSelection, available]);

  const filtered = useMemo(() => {
    if (!search.trim()) return available;
    const q = search.toLowerCase();
    return available.filter(
      (p) =>
        p.name?.toLowerCase().includes(q) ||
        p.sku?.toLowerCase().includes(q) ||
        p.barcode?.toLowerCase().includes(q),
    );
  }, [available, search]);

  const uniqueAvailable = useMemo(() => {
    const seen = new Set();
    return available.filter((p) => {
      if (seen.has(p.id)) return false;
      seen.add(p.id);
      return true;
    });
  }, [available]);

  const uniqueFiltered = useMemo(() => {
    const seen = new Set();
    return filtered.filter((p) => {
      if (seen.has(p.id)) return false;
      seen.add(p.id);
      return true;
    });
  }, [filtered]);

  const toggleProduct = (id) => {
    setSelected((prev) => {
      const next = new Map(prev);
      if (next.has(id)) next.delete(id);
      else next.set(id, 1);
      return next;
    });
  };

  const setQty = (id, qty) => {
    setSelected((prev) => {
      const next = new Map(prev);
      const clamped = Math.max(1, Math.min(99, qty));
      next.set(id, clamped);
      return next;
    });
  };

  const selectAll = () => {
    const next = new Map();
    uniqueAvailable.forEach((p) => next.set(p.id, selected.get(p.id) || 1));
    setSelected(next);
  };

  const deselectAll = () => setSelected(new Map());

  const labels = useMemo(() => {
    const result = [];
    const byId = new Map(uniqueAvailable.map((p) => [p.id, p]));
    for (const [id, qty] of selected) {
      const p = byId.get(id);
      if (!p) continue;
      for (let i = 0; i < qty; i++) result.push({ ...p, _labelIdx: `${id}-${i}` });
    }
    return result;
  }, [selected, uniqueAvailable]);

  const handlePrint = useReactToPrint({
    contentRef: printRef,
    documentTitle: "SKU Labels",
    pageStyle: `
      @page { size: 4in 6in; margin: 0.2in; }
      @media print {
        body { -webkit-print-color-adjust: exact; print-color-adjust: exact; margin: 0; }
        .qr-label-grid { gap: 0.08in !important; }
        .qr-label {
          width: 1.15in !important;
          height: 1.6in !important;
          padding: 0.06in !important;
          border: 0.5pt solid #ccc !important;
          page-break-inside: avoid;
        }
        .qr-label svg { width: 0.9in !important; height: 0.9in !important; }
        .qr-sku { font-size: 7pt !important; }
        .qr-name { font-size: 6pt !important; }
      }
    `,
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle>Print QR Code Labels</DialogTitle>
        </DialogHeader>

        {!showPreview ? (
          <>
            {/* ── Selection mode ── */}
            <div className="flex items-center gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search products…"
                  className="pl-9"
                />
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={selected.size === uniqueAvailable.length ? deselectAll : selectAll}
                className="text-xs shrink-0"
              >
                {selected.size === uniqueAvailable.length ? "Deselect all" : "Select all"}
              </Button>
            </div>

            <p className="text-sm text-muted-foreground">
              {selected.size} of {uniqueAvailable.length} selected · {labels.length} label
              {labels.length !== 1 ? "s" : ""} total
            </p>

            <div className="flex-1 overflow-auto border rounded-lg divide-y divide-border">
              {uniqueFiltered.length === 0 ? (
                <div className="flex items-center justify-center py-12 text-sm text-muted-foreground">
                  No products match &quot;{search}&quot;
                </div>
              ) : (
                uniqueFiltered.map((p) => {
                  const isSelected = selected.has(p.id);
                  const qty = selected.get(p.id) || 1;
                  return (
                    <div
                      key={p.id}
                      className={`flex items-center gap-3 px-4 py-2.5 cursor-pointer transition-colors ${
                        isSelected ? "bg-accent/5" : "hover:bg-muted/50"
                      }`}
                      onClick={() => toggleProduct(p.id)}
                    >
                      {isSelected ? (
                        <CheckSquare className="w-4 h-4 text-accent shrink-0" />
                      ) : (
                        <Square className="w-4 h-4 text-muted-foreground/50 shrink-0" />
                      )}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{p.name}</p>
                        <p className="text-xs font-mono text-muted-foreground">{p.sku}</p>
                      </div>
                      {isSelected && (
                        <div
                          className="flex items-center gap-1 shrink-0"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <button
                            className="w-7 h-7 rounded-md border border-border flex items-center justify-center hover:bg-muted transition-colors"
                            onClick={() => setQty(p.id, qty - 1)}
                          >
                            <Minus className="w-3 h-3" />
                          </button>
                          <Input
                            type="number"
                            min={1}
                            max={99}
                            value={qty}
                            onChange={(e) => setQty(p.id, parseInt(e.target.value, 10) || 1)}
                            className="w-12 h-7 text-center text-sm px-1 [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                          />
                          <button
                            className="w-7 h-7 rounded-md border border-border flex items-center justify-center hover:bg-muted transition-colors"
                            onClick={() => setQty(p.id, qty + 1)}
                          >
                            <Plus className="w-3 h-3" />
                          </button>
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>

            <div className="flex gap-2 pt-2">
              <Button
                onClick={() => setShowPreview(true)}
                disabled={selected.size === 0}
                className="flex-1"
              >
                <Printer className="w-4 h-4 mr-2" />
                Preview {labels.length} label{labels.length !== 1 ? "s" : ""}
              </Button>
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
            </div>
          </>
        ) : (
          <>
            {/* ── Print preview ── */}
            <div className="flex items-center gap-2">
              <p className="text-sm text-muted-foreground flex-1">
                {labels.length} label{labels.length !== 1 ? "s" : ""} · QR codes · Scannable by
                camera
              </p>
              {!skipSelection && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowPreview(false)}
                  className="text-xs"
                >
                  Back to selection
                </Button>
              )}
            </div>

            <div className="flex-1 overflow-auto border rounded-lg bg-card p-4">
              <div
                ref={printRef}
                className="qr-label-grid grid grid-cols-3 gap-3"
                style={{ minHeight: 200 }}
              >
                {labels.map((p) => {
                  const code = (p.barcode || p.sku).toString().trim();
                  const qrValue = buildProductQrValue(code);
                  return (
                    <div
                      key={p._labelIdx}
                      className="qr-label border border-border rounded-lg p-3 flex flex-col items-center justify-center"
                      style={{ minWidth: 140, minHeight: 160 }}
                    >
                      <div className="bg-white p-1 rounded">
                        <QRCodeSVG value={qrValue} size={120} level="M" marginSize={1} />
                      </div>
                      <div className="qr-sku text-[11px] font-mono mt-2 text-center truncate w-full font-semibold leading-tight">
                        {p.sku}
                      </div>
                      <div className="qr-name text-[9px] text-muted-foreground text-center truncate w-full max-w-[120px] leading-tight">
                        {p.name?.slice(0, 28)}
                        {p.name?.length > 28 ? "…" : ""}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="flex gap-2 pt-2">
              <Button onClick={handlePrint} disabled={labels.length === 0} className="flex-1">
                <Printer className="w-4 h-4 mr-2" />
                Print
              </Button>
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Close
              </Button>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
