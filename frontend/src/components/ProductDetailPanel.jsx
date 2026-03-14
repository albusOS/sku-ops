import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import {
  X,
  Edit2,
  Trash2,
  SlidersHorizontal,
  Printer,
  History,
  Package,
  Star,
  Truck,
  TrendingUp,
  TrendingDown,
  Minus,
} from "lucide-react";
import { format } from "date-fns";
import { TX_TYPE_LABELS } from "@/lib/constants";
import {
  useStockHistory,
  useVendorItems,
  useRemoveVendorItem,
  useSetPreferredVendor,
} from "@/hooks/useProducts";
import { StockBadge } from "@/components/StatusBadge";
import { toast } from "sonner";

function DeltaBadge({ delta }) {
  if (delta > 0)
    return (
      <span className="inline-flex items-center gap-1 font-mono text-success text-xs">
        <TrendingUp className="w-3 h-3" />+{delta}
      </span>
    );
  if (delta < 0)
    return (
      <span className="inline-flex items-center gap-1 font-mono text-destructive text-xs">
        <TrendingDown className="w-3 h-3" />
        {delta}
      </span>
    );
  return (
    <span className="inline-flex items-center gap-1 font-mono text-muted-foreground text-xs">
      <Minus className="w-3 h-3" />0
    </span>
  );
}

function StatRow({ label, value, mono = false, muted = false }) {
  return (
    <div className="flex items-center justify-between py-2.5 border-b border-border/40 last:border-0">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span
        className={`text-sm font-medium ${mono ? "font-mono" : ""} ${muted ? "text-muted-foreground" : ""}`}
      >
        {value}
      </span>
    </div>
  );
}

/**
 * Slide-in product detail panel — rendered alongside the table, not as a modal.
 * Parent must position this absolutely or use a flex/grid split layout.
 */
export function ProductDetailPanel({
  product,
  open,
  onClose,
  onEdit,
  onAdjust,
  onDelete,
  onPrintLabels,
  onViewHistory,
}) {
  const [printQty, setPrintQty] = useState(1);

  const { data: historyData, isLoading: historyLoading } = useStockHistory(
    open ? product?.id : null,
  );
  const recentHistory = (historyData?.history || []).slice(0, 8);

  const { data: vendorItems = [], isLoading: vendorsLoading } = useVendorItems(
    open ? product?.id : null,
  );
  const removeVendorItem = useRemoveVendorItem();
  const setPreferred = useSetPreferredVendor();

  useEffect(() => {
    if (open && product) setPrintQty(1);
  }, [open, product]);

  const hasBarcode = (product?.barcode || product?.sku)?.toString().trim();

  const handlePrint = () => {
    if (!hasBarcode) return;
    const copies = Array.from({ length: Math.max(1, Math.min(99, printQty)) }, () => product);
    onPrintLabels?.(copies);
  };

  const margin =
    product?.price > 0
      ? (((product.price - (product.cost || 0)) / product.price) * 100).toFixed(1)
      : null;

  return (
    <AnimatePresence>
      {open && product && (
        <motion.div
          key="product-panel"
          initial={{ x: "100%", opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: "100%", opacity: 0 }}
          transition={{ type: "spring", stiffness: 340, damping: 38 }}
          className="flex flex-col h-full bg-card border-l border-border/60 overflow-hidden shadow-xl"
          style={{ width: "100%" }}
        >
          {/* Header */}
          <div className="px-5 pt-5 pb-4 border-b border-border/50 shrink-0">
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-2.5 min-w-0">
                <div className="w-8 h-8 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center shrink-0">
                  <Package className="w-4 h-4 text-accent" />
                </div>
                <div className="min-w-0">
                  <h2 className="font-semibold text-sm leading-tight truncate">{product.name}</h2>
                  <p className="font-mono text-xs text-muted-foreground mt-0.5">{product.sku}</p>
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <StockBadge product={product} />
                <button
                  onClick={onClose}
                  className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                  aria-label="Close panel"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Quick stats strip */}
            <div className="grid grid-cols-3 gap-2 mt-4">
              {[
                { label: "Price", value: `$${(product.price || 0).toFixed(2)}`, accent: false },
                {
                  label: "Stock",
                  value: product.quantity ?? 0,
                  accent: product.quantity <= (product.min_stock ?? 5),
                },
                { label: "Margin", value: margin ? `${margin}%` : "—", accent: false },
              ].map(({ label, value, accent }) => (
                <div
                  key={label}
                  className={`rounded-lg px-3 py-2 text-center ${accent ? "bg-warning/10 border border-warning/20" : "bg-muted/50 border border-border/40"}`}
                >
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-0.5">
                    {label}
                  </p>
                  <p className={`font-mono font-semibold text-sm ${accent ? "text-warning" : ""}`}>
                    {value}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Tabs */}
          <Tabs defaultValue="info" className="flex-1 flex flex-col min-h-0">
            <TabsList className="grid grid-cols-4 mx-5 mt-3 shrink-0">
              <TabsTrigger value="info" className="text-xs">
                Info
              </TabsTrigger>
              <TabsTrigger value="suppliers" className="text-xs">
                Suppliers{vendorItems.length > 0 ? ` (${vendorItems.length})` : ""}
              </TabsTrigger>
              <TabsTrigger value="labels" className="text-xs">
                Labels
              </TabsTrigger>
              <TabsTrigger value="history" className="text-xs">
                History
              </TabsTrigger>
            </TabsList>

            <TabsContent value="info" className="flex-1 overflow-auto px-5 mt-3 pb-5">
              <div className="rounded-xl border border-border/50 overflow-hidden">
                <StatRow label="Category" value={product.category_name || "—"} />
                <StatRow
                  label="Unit"
                  value={`${product.sell_uom || "each"}${(product.pack_qty || 1) > 1 ? ` ×${product.pack_qty}` : ""}`}
                />
                <StatRow label="Cost" value={`$${(product.cost || 0).toFixed(2)}`} mono muted />
                <StatRow label="Min Stock" value={product.min_stock ?? 5} mono />
                <StatRow label="Scan code" value={product.barcode || product.sku || "—"} mono />
                {product.purchase_uom && product.purchase_uom !== "each" && (
                  <StatRow
                    label="Purchase UOM"
                    value={`${product.purchase_uom}${(product.purchase_pack_qty || 1) > 1 ? ` ×${product.purchase_pack_qty}` : ""}`}
                  />
                )}
              </div>

              {product.description && (
                <div className="mt-4 rounded-xl border border-border/50 px-4 py-3">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
                    Description
                  </p>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {product.description}
                  </p>
                </div>
              )}

              <div className="mt-4 flex flex-col gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full justify-start"
                  onClick={() => {
                    onEdit?.(product);
                    onClose();
                  }}
                >
                  <Edit2 className="w-3.5 h-3.5 mr-2" />
                  Edit product
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full justify-start"
                  onClick={() => {
                    onAdjust?.(product);
                    onClose();
                  }}
                >
                  <SlidersHorizontal className="w-3.5 h-3.5 mr-2" />
                  Adjust stock
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full justify-start text-destructive hover:text-destructive hover:bg-destructive/10 border-destructive/20"
                  onClick={() => {
                    onDelete?.(product);
                    onClose();
                  }}
                >
                  <Trash2 className="w-3.5 h-3.5 mr-2" />
                  Delete product
                </Button>
              </div>
            </TabsContent>

            <TabsContent value="suppliers" className="flex-1 overflow-auto px-5 mt-3 pb-5">
              {vendorsLoading ? (
                <p className="text-sm text-muted-foreground">Loading…</p>
              ) : vendorItems.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <Truck className="w-8 h-8 text-muted-foreground/40 mb-3" />
                  <p className="text-sm text-muted-foreground">No suppliers linked yet</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {vendorItems.map((vi) => (
                    <div key={vi.id} className="rounded-xl border border-border/50 p-3 bg-muted/20">
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2 min-w-0">
                          <span className="font-medium text-sm truncate">
                            {vi.vendor_name || "Unknown vendor"}
                          </span>
                          {vi.is_preferred && (
                            <Star className="w-3.5 h-3.5 text-amber-500 fill-amber-500 shrink-0" />
                          )}
                        </div>
                        <div className="flex gap-1 shrink-0">
                          {!vi.is_preferred && (
                            <button
                              className="p-1.5 text-muted-foreground hover:text-amber-500 rounded-md transition-colors"
                              title="Set as preferred"
                              onClick={() =>
                                setPreferred.mutate(
                                  { skuId: product.id, itemId: vi.id },
                                  { onSuccess: () => toast.success("Preferred supplier set") },
                                )
                              }
                            >
                              <Star className="w-3.5 h-3.5" />
                            </button>
                          )}
                          <button
                            className="p-1.5 text-muted-foreground hover:text-destructive rounded-md transition-colors"
                            title="Remove supplier"
                            onClick={() =>
                              removeVendorItem.mutate(
                                { skuId: product.id, itemId: vi.id },
                                { onSuccess: () => toast.success("Supplier removed") },
                              )
                            }
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-x-3 gap-y-0.5 mt-2 text-xs text-muted-foreground">
                        {vi.vendor_sku && (
                          <span>
                            SKU: <span className="font-mono">{vi.vendor_sku}</span>
                          </span>
                        )}
                        <span>
                          Cost: <span className="font-mono">${(vi.cost || 0).toFixed(2)}</span>
                        </span>
                        {vi.purchase_uom !== "each" && (
                          <span>
                            {vi.purchase_uom}
                            {(vi.purchase_pack_qty || 1) > 1 && ` ×${vi.purchase_pack_qty}`}
                          </span>
                        )}
                        {vi.lead_time_days != null && <span>{vi.lead_time_days}d lead</span>}
                        {vi.moq != null && <span>MOQ: {vi.moq}</span>}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </TabsContent>

            <TabsContent value="labels" className="flex-1 overflow-auto px-5 mt-3 pb-5 space-y-4">
              <p className="text-xs text-muted-foreground">
                Print barcode labels (2×1&quot; format).
              </p>
              {hasBarcode ? (
                <div className="flex flex-col gap-3">
                  <div className="flex items-center gap-3">
                    <label className="text-sm font-medium">Labels</label>
                    <Input
                      type="number"
                      min={1}
                      max={99}
                      value={printQty}
                      onChange={(e) => {
                        const v = parseInt(e.target.value, 10);
                        setPrintQty(isNaN(v) ? 1 : Math.min(99, Math.max(1, v)));
                      }}
                      className="w-20"
                    />
                  </div>
                  <Button onClick={handlePrint} className="w-full">
                    <Printer className="w-4 h-4 mr-2" />
                    Print {printQty} label{printQty !== 1 ? "s" : ""}
                  </Button>
                </div>
              ) : (
                <p className="text-sm text-accent">No barcode or SKU set.</p>
              )}
            </TabsContent>

            <TabsContent value="history" className="flex-1 overflow-auto px-5 mt-3 pb-5">
              {historyLoading ? (
                <p className="text-sm text-muted-foreground">Loading…</p>
              ) : recentHistory.length === 0 ? (
                <p className="text-sm text-muted-foreground">No transactions yet</p>
              ) : (
                <div className="rounded-xl border border-border/50 overflow-hidden">
                  {recentHistory.map((tx, i) => (
                    <div
                      key={tx.id}
                      className={`flex items-center justify-between px-4 py-2.5 text-sm ${i < recentHistory.length - 1 ? "border-b border-border/40" : ""}`}
                    >
                      <span className="text-muted-foreground text-xs">
                        {TX_TYPE_LABELS[tx.transaction_type] || tx.transaction_type}
                      </span>
                      <DeltaBadge delta={tx.quantity_delta} />
                      <span className="text-muted-foreground text-xs">
                        {tx.created_at ? format(new Date(tx.created_at), "MMM d, HH:mm") : "—"}
                      </span>
                    </div>
                  ))}
                </div>
              )}
              <Button
                variant="outline"
                size="sm"
                className="mt-4 w-full"
                onClick={() => {
                  onViewHistory?.(product);
                  onClose();
                }}
              >
                <History className="w-4 h-4 mr-2" />
                Full history
              </Button>
            </TabsContent>
          </Tabs>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
