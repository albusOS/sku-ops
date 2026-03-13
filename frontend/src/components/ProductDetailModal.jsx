import { useState, useEffect } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "./ui/dialog";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import { Separator } from "./ui/separator";
import {
  Edit2,
  Trash2,
  SlidersHorizontal,
  Printer,
  History,
  Package,
  Star,
  Truck,
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

export function ProductDetailModal({
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
  const recentHistory = (historyData?.history || []).slice(0, 5);

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

  const handleDelete = () => {
    onDelete?.(product);
    onOpenChange(false);
  };

  if (!product) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg rounded-2xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-3">
            <Package className="w-5 h-5 text-muted-foreground" />
            <span>{product.name}</span>
            <StockBadge product={product} />
          </DialogTitle>
          <div className="rounded-lg bg-muted border border-border/60 px-3 py-2 mt-2 inline-block">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              SKU (permanent ID)
            </p>
            <p className="font-mono font-semibold text-foreground">{product.sku}</p>
          </div>
        </DialogHeader>

        <Tabs defaultValue="info" className="flex-1 flex flex-col min-h-0">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="info">Info</TabsTrigger>
            <TabsTrigger value="suppliers">
              Suppliers{vendorItems.length > 0 && ` (${vendorItems.length})`}
            </TabsTrigger>
            <TabsTrigger value="printables">Labels</TabsTrigger>
            <TabsTrigger value="history">History</TabsTrigger>
          </TabsList>

          <TabsContent value="info" className="flex-1 overflow-auto mt-4 space-y-4">
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <p className="text-muted-foreground">Category</p>
                <p className="font-medium">{product.category_name || "—"}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Unit</p>
                <p className="font-medium">
                  {product.sell_uom || "each"}
                  {(product.pack_qty || 1) > 1 ? ` ×${product.pack_qty}` : ""}
                </p>
              </div>
              <div>
                <p className="text-muted-foreground">Price</p>
                <p className="font-mono font-medium">${product.price?.toFixed(2) ?? "—"}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Cost</p>
                <p className="font-mono text-muted-foreground">${(product.cost || 0).toFixed(2)}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Quantity</p>
                <p className="font-mono font-medium">{product.quantity ?? 0}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Min Stock</p>
                <p className="font-mono">{product.min_stock ?? 5}</p>
              </div>
              <div className="col-span-2">
                <p className="text-muted-foreground">Scan code (barcode)</p>
                <p className="font-mono text-sm">
                  {product.barcode || product.sku || "—"}
                  {!product.barcode && product.sku && (
                    <span className="text-muted-foreground font-normal ml-1">(uses SKU)</span>
                  )}
                </p>
              </div>
              {product.purchase_uom && product.purchase_uom !== "each" && (
                <div>
                  <p className="text-muted-foreground">Purchase UOM</p>
                  <p className="font-medium">
                    {product.purchase_uom}
                    {(product.purchase_pack_qty || 1) > 1 ? ` ×${product.purchase_pack_qty}` : ""}
                  </p>
                </div>
              )}
            </div>
            {product.description && (
              <>
                <Separator />
                <div>
                  <p className="text-muted-foreground text-sm">Description</p>
                  <p className="text-sm">{product.description}</p>
                </div>
              </>
            )}
            <Separator />
            <div className="flex flex-wrap gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  onEdit?.(product);
                  onOpenChange(false);
                }}
              >
                <Edit2 className="w-4 h-4 mr-1.5" />
                Edit
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  onAdjust?.(product);
                  onOpenChange(false);
                }}
              >
                <SlidersHorizontal className="w-4 h-4 mr-1.5" />
                Adjust Stock
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="text-destructive hover:text-destructive hover:bg-destructive/10"
                onClick={handleDelete}
              >
                <Trash2 className="w-4 h-4 mr-1.5" />
                Delete
              </Button>
            </div>
          </TabsContent>

          <TabsContent value="suppliers" className="flex-1 overflow-auto mt-4">
            {vendorsLoading ? (
              <p className="text-sm text-muted-foreground">Loading…</p>
            ) : vendorItems.length === 0 ? (
              <p className="text-sm text-muted-foreground py-6 text-center">
                No suppliers linked to this SKU yet.
              </p>
            ) : (
              <div className="space-y-2">
                {vendorItems.map((vi) => (
                  <div
                    key={vi.id}
                    className="flex items-start gap-3 rounded-lg border border-border p-3"
                  >
                    <Truck className="w-4 h-4 text-muted-foreground mt-0.5 shrink-0" />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-sm truncate">
                          {vi.vendor_name || "Unknown vendor"}
                        </span>
                        {vi.is_preferred && (
                          <Star className="w-3.5 h-3.5 text-amber-500 fill-amber-500 shrink-0" />
                        )}
                      </div>
                      <div className="flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-muted-foreground mt-1">
                        {vi.vendor_sku && (
                          <span>
                            Vendor SKU: <span className="font-mono">{vi.vendor_sku}</span>
                          </span>
                        )}
                        <span>
                          Cost: <span className="font-mono">${(vi.cost || 0).toFixed(2)}</span>
                        </span>
                        {vi.purchase_uom !== "each" && (
                          <span>
                            UOM: {vi.purchase_uom}
                            {(vi.purchase_pack_qty || 1) > 1 && ` ×${vi.purchase_pack_qty}`}
                          </span>
                        )}
                        {vi.lead_time_days != null && <span>{vi.lead_time_days}d lead</span>}
                        {vi.moq != null && <span>MOQ: {vi.moq}</span>}
                      </div>
                    </div>
                    <div className="flex gap-1 shrink-0">
                      {!vi.is_preferred && (
                        <button
                          className="p-1.5 text-muted-foreground hover:text-amber-500 rounded-sm transition-colors"
                          title="Set as preferred"
                          onClick={() => {
                            setPreferred.mutate(
                              { skuId: product.id, itemId: vi.id },
                              { onSuccess: () => toast.success("Preferred supplier set") },
                            );
                          }}
                        >
                          <Star className="w-3.5 h-3.5" />
                        </button>
                      )}
                      <button
                        className="p-1.5 text-muted-foreground hover:text-destructive rounded-sm transition-colors"
                        title="Remove supplier"
                        onClick={() => {
                          removeVendorItem.mutate(
                            { skuId: product.id, itemId: vi.id },
                            { onSuccess: () => toast.success("Supplier removed") },
                          );
                        }}
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="printables" className="flex-1 overflow-auto mt-4 space-y-4">
            <p className="text-sm text-muted-foreground">
              Print barcode labels for this product (2×1&quot; format).
            </p>
            {hasBarcode ? (
              <div className="flex flex-col gap-3">
                <div className="flex items-center gap-3">
                  <label className="text-sm font-medium">Number of labels</label>
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
                <Button onClick={handlePrint}>
                  <Printer className="w-4 h-4 mr-2" />
                  Print {printQty} label{printQty !== 1 ? "s" : ""}
                </Button>
              </div>
            ) : (
              <p className="text-sm text-accent">
                No barcode or SKU set. Edit the product to add a barcode.
              </p>
            )}
          </TabsContent>

          <TabsContent value="history" className="flex-1 overflow-auto mt-4">
            {historyLoading ? (
              <p className="text-sm text-muted-foreground">Loading…</p>
            ) : recentHistory.length === 0 ? (
              <p className="text-sm text-muted-foreground">No transactions yet</p>
            ) : (
              <div className="space-y-2">
                {recentHistory.map((tx) => (
                  <div
                    key={tx.id}
                    className="flex items-center justify-between text-sm py-2 border-b border-border/50 last:border-0"
                  >
                    <span className="text-muted-foreground">
                      {TX_TYPE_LABELS[tx.transaction_type] || tx.transaction_type}
                    </span>
                    <span className="font-mono">
                      {tx.quantity_delta > 0 ? "+" : ""}
                      {tx.quantity_delta}
                    </span>
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
                onOpenChange(false);
              }}
            >
              <History className="w-4 h-4 mr-2" />
              View full history
            </Button>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
