import { useState, useEffect } from "react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import {
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
import { DetailPanel, DetailSection, DetailField } from "./DetailPanel";
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

export function ProductDetailPanel({
  product,
  open,
  onOpenChange,
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
    <DetailPanel
      open={open}
      onOpenChange={onOpenChange}
      title={product?.name || "Product"}
      subtitle={product?.sku}
      icon={Package}
      width="lg"
      actions={
        product && (
          <div className="flex items-center gap-2 w-full">
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5"
              onClick={() => onEdit?.(product)}
            >
              <Edit2 className="w-3.5 h-3.5" />
              Edit
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5"
              onClick={() => onAdjust?.(product)}
            >
              <SlidersHorizontal className="w-3.5 h-3.5" />
              Adjust Stock
            </Button>
            <div className="flex-1" />
            <Button
              variant="ghost"
              size="sm"
              className="text-destructive hover:text-destructive hover:bg-destructive/10 gap-1.5"
              onClick={() => onDelete?.(product)}
            >
              <Trash2 className="w-3.5 h-3.5" />
              Delete
            </Button>
          </div>
        )
      }
    >
      {product && (
        <>
          {/* Quick stats strip */}
          <div className="grid grid-cols-3 gap-2">
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

          <Tabs defaultValue="info" className="flex flex-col min-h-0">
            <TabsList className="grid grid-cols-4 shrink-0">
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

            <TabsContent value="info" className="mt-3">
              <DetailSection label="Details">
                <div className="grid grid-cols-2 gap-4">
                  <DetailField label="Category" value={product.category_name} />
                  <DetailField
                    label="Unit"
                    value={`${product.sell_uom || "each"}${(product.pack_qty || 1) > 1 ? ` ×${product.pack_qty}` : ""}`}
                  />
                  <DetailField label="Cost" value={`$${(product.cost || 0).toFixed(2)}`} mono />
                  <DetailField label="Min Stock" value={product.min_stock ?? 5} mono />
                  <DetailField label="Scan Code" value={product.barcode || product.sku} mono />
                  {product.purchase_uom && product.purchase_uom !== "each" && (
                    <DetailField
                      label="Purchase UOM"
                      value={`${product.purchase_uom}${(product.purchase_pack_qty || 1) > 1 ? ` ×${product.purchase_pack_qty}` : ""}`}
                    />
                  )}
                </div>
              </DetailSection>

              {product.variant_attrs && Object.keys(product.variant_attrs).length > 0 && (
                <DetailSection label="Variant Attributes" className="mt-4">
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(product.variant_attrs).map(([k, v]) => (
                      <span
                        key={k}
                        className="inline-flex items-center gap-1 rounded-md border border-border/60 bg-muted/40 px-2 py-0.5 text-xs"
                      >
                        <span className="text-muted-foreground">{k}:</span>
                        <span className="font-medium">{v}</span>
                      </span>
                    ))}
                  </div>
                </DetailSection>
              )}

              {product.description && (
                <DetailSection label="Description" className="mt-4">
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {product.description}
                  </p>
                </DetailSection>
              )}
            </TabsContent>

            <TabsContent value="suppliers" className="mt-3">
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

            <TabsContent value="labels" className="mt-3 space-y-4">
              <p className="text-xs text-muted-foreground">
                Print QR code labels (scannable by camera).
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

            <TabsContent value="history" className="mt-3">
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
                onClick={() => onViewHistory?.(product)}
              >
                <History className="w-4 h-4 mr-2" />
                Full history
              </Button>
            </TabsContent>
          </Tabs>
        </>
      )}
    </DetailPanel>
  );
}
