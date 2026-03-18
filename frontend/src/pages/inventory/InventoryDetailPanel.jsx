import { useState, useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { CategoryCombobox } from "@/components/CategoryCombobox";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import {
  X,
  SlidersHorizontal,
  History,
  Package,
  TrendingUp,
  TrendingDown,
  Minus,
  Pencil,
  Check,
  ChevronRight,
  Settings2,
} from "lucide-react";
import { format } from "date-fns";
import { useStockHistory, useUpdateProduct } from "@/hooks/useProducts";
import { UnitCombobox } from "@/components/UnitCombobox";
import { TX_TYPE_LABELS } from "@/lib/constants";
import { toast } from "sonner";
import { getErrorMessage } from "@/lib/api-client";

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

function EditableValue({ label, value, field, productId, type = "number", prefix, suffix }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const inputRef = useRef(null);
  const updateMutation = useUpdateProduct();

  useEffect(() => {
    setDraft(value);
    setEditing(false);
  }, [value, productId]);

  useEffect(() => {
    if (editing) inputRef.current?.focus();
  }, [editing]);

  const save = () => {
    const parsed = type === "number" ? parseFloat(draft) : draft;
    if (type === "number" && (isNaN(parsed) || parsed < 0)) {
      toast.error(`${label} must be a valid number`);
      setDraft(value);
      setEditing(false);
      return;
    }
    if (parsed === value) {
      setEditing(false);
      return;
    }
    updateMutation.mutate(
      { id: productId, data: { [field]: parsed } },
      {
        onSuccess: () => {
          toast.success(`${label} updated`);
          setEditing(false);
        },
        onError: (err) => {
          toast.error(getErrorMessage(err));
          setDraft(value);
          setEditing(false);
        },
      },
    );
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") save();
    if (e.key === "Escape") {
      setDraft(value);
      setEditing(false);
    }
  };

  if (editing) {
    return (
      <div>
        <p className="text-xs text-muted-foreground mb-1">{label}</p>
        <div className="flex items-center gap-1">
          {prefix && <span className="text-sm text-muted-foreground">{prefix}</span>}
          <Input
            ref={inputRef}
            type={type}
            step={type === "number" ? "0.01" : undefined}
            value={draft ?? ""}
            onChange={(e) => setDraft(e.target.value)}
            onBlur={save}
            onKeyDown={handleKeyDown}
            className="h-7 text-sm font-mono w-20"
            disabled={updateMutation.isPending}
          />
          {suffix && <span className="text-xs text-muted-foreground">{suffix}</span>}
          <button
            onClick={save}
            className="p-0.5 rounded text-success hover:bg-success/10 transition-colors shrink-0"
          >
            <Check className="w-3 h-3" />
          </button>
        </div>
      </div>
    );
  }

  const display =
    type === "number" && value != null
      ? `${prefix || ""}${Number(value).toFixed(field === "min_stock" ? 0 : 2)}`
      : value || "—";

  return (
    <div
      className="group cursor-pointer rounded-md px-1 -mx-1 py-0.5 hover:bg-muted/60 transition-colors"
      onClick={() => setEditing(true)}
    >
      <p className="text-xs text-muted-foreground flex items-center gap-1">
        {label}
        <Pencil className="w-2.5 h-2.5 opacity-0 group-hover:opacity-100 transition-opacity" />
      </p>
      <p className="text-sm text-foreground font-mono tabular-nums mt-0.5">
        {display}
        {suffix ? ` ${suffix}` : ""}
      </p>
    </div>
  );
}

function StockGauge({ quantity, minStock }) {
  const max = Math.max(minStock * 3, quantity, 1);
  const pct = Math.min((quantity / max) * 100, 100);
  const minPct = Math.min((minStock / max) * 100, 100);
  const color =
    quantity === 0 ? "bg-destructive" : quantity <= minStock ? "bg-warning" : "bg-success";
  const label = quantity === 0 ? "Out of Stock" : quantity <= minStock ? "Low Stock" : "In Stock";
  const labelColor =
    quantity === 0 ? "text-destructive" : quantity <= minStock ? "text-warning" : "text-success";

  return (
    <div className="space-y-2">
      <div className="flex items-end justify-between">
        <div>
          <p className="text-2xl font-bold font-mono tabular-nums">{quantity}</p>
        </div>
        <span className={`text-xs font-semibold ${labelColor}`}>{label}</span>
      </div>
      <div className="relative h-2.5 bg-muted rounded-full overflow-hidden">
        <div
          className={`h-full ${color} transition-all rounded-full`}
          style={{ width: `${pct}%` }}
        />
        <div
          className="absolute top-0 bottom-0 w-px bg-foreground/20"
          style={{ left: `${minPct}%` }}
        />
      </div>
    </div>
  );
}

function ReadField({ label, value, mono }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className={`text-sm text-foreground mt-0.5 ${mono ? "font-mono tabular-nums" : ""}`}>
        {value || "—"}
      </p>
    </div>
  );
}

const SPRING = { type: "spring", stiffness: 300, damping: 36 };

export function InventoryDetailPanel({ product, open, onClose, onAdjust, onViewHistory }) {
  const [detailsOpen, setDetailsOpen] = useState(false);
  const { data: historyData, isLoading: historyLoading } = useStockHistory(
    open ? product?.id : null,
  );
  const updateMutation = useUpdateProduct();
  const recentHistory = (historyData?.history || []).slice(0, 10);

  useEffect(() => {
    if (open && product) setDetailsOpen(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reset on panel open/product change, not every re-render
  }, [open, product?.id]);

  if (!open || !product) return null;

  const baseUnit = product.base_unit || "each";
  const sellUom = product.sell_uom || baseUnit;

  const handleCategoryChange = (categoryId) => {
    updateMutation.mutate(
      { id: product.id, data: { category_id: categoryId } },
      {
        onSuccess: () => toast.success("Category updated"),
        onError: (err) => toast.error(getErrorMessage(err)),
      },
    );
  };

  const handleUnitChange = (field, value) => {
    updateMutation.mutate(
      { id: product.id, data: { [field]: value } },
      {
        onSuccess: () => toast.success("Unit updated"),
        onError: (err) => toast.error(getErrorMessage(err)),
      },
    );
  };

  return (
    <motion.div
      key="inventory-panel"
      initial={{ width: 0, opacity: 0 }}
      animate={{ width: "42%", opacity: 1 }}
      exit={{ width: 0, opacity: 0 }}
      transition={SPRING}
      className="h-full shrink-0 overflow-hidden"
    >
      <div className="flex flex-col h-full bg-card border-l border-border/60 overflow-hidden shadow-xl">
        {/* Header — stock gauge + actions */}
        <div className="px-5 pt-5 pb-4 border-b border-border/50 shrink-0">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="w-8 h-8 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center shrink-0">
                <Package className="w-4 h-4 text-accent" />
              </div>
              <div className="min-w-0">
                <h2 className="font-semibold text-sm leading-tight truncate">{product.name}</h2>
                <p className="text-xs text-muted-foreground mt-0.5">
                  <span className="font-mono">{product.sku}</span>
                  {" · "}
                  {product.category_name}
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors shrink-0"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="mt-4">
            <StockGauge quantity={product.quantity ?? 0} minStock={product.min_stock ?? 5} />
          </div>

          <div className="flex items-center gap-2 mt-4">
            <Button size="sm" className="gap-1.5 flex-1" onClick={() => onAdjust?.(product)}>
              <SlidersHorizontal className="w-3.5 h-3.5" />
              Adjust Stock
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5"
              onClick={() => onViewHistory?.(product)}
            >
              <History className="w-3.5 h-3.5" />
              Full History
            </Button>
          </div>
        </div>

        {/* Scrollable body */}
        <div className="flex-1 overflow-auto px-5 py-4 space-y-1">
          {/* Product Details — collapsible, editable */}
          <Collapsible open={detailsOpen} onOpenChange={setDetailsOpen}>
            <CollapsibleTrigger asChild>
              <button className="flex items-center gap-2 w-full py-2 text-left group">
                <ChevronRight
                  className={`w-3.5 h-3.5 text-muted-foreground transition-transform ${detailsOpen ? "rotate-90" : ""}`}
                />
                <Settings2 className="w-3.5 h-3.5 text-muted-foreground" />
                <span className="text-[10px] font-bold uppercase tracking-[0.12em] text-muted-foreground flex-1">
                  Product Details
                </span>
              </button>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <div className="pb-4 space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Category</p>
                    <CategoryCombobox
                      value={product.category_id}
                      onValueChange={handleCategoryChange}
                      disabled={updateMutation.isPending}
                      className="h-8 text-sm"
                    />
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Sell Unit</p>
                    <UnitCombobox
                      value={sellUom}
                      onValueChange={(v) => handleUnitChange("sell_uom", v)}
                      disabled={updateMutation.isPending}
                      className="h-8 text-sm"
                    />
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Base Unit</p>
                    <UnitCombobox
                      value={baseUnit}
                      onValueChange={(v) => handleUnitChange("base_unit", v)}
                      disabled={updateMutation.isPending}
                      className="h-8 text-sm"
                    />
                  </div>
                  <ReadField label="Scan Code" value={product.barcode || product.sku} mono />
                  <EditableValue
                    label="Price"
                    value={product.price || 0}
                    field="price"
                    productId={product.id}
                    prefix="$"
                  />
                  <EditableValue
                    label="Cost"
                    value={product.cost || 0}
                    field="cost"
                    productId={product.id}
                    prefix="$"
                  />
                  <EditableValue
                    label="Reorder At"
                    value={product.min_stock ?? 5}
                    field="min_stock"
                    productId={product.id}
                    suffix={baseUnit}
                  />
                </div>
              </div>
            </CollapsibleContent>
          </Collapsible>

          {/* Recent movements — always visible */}
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-muted-foreground mb-3">
              Recent Movements
            </p>
            {historyLoading ? (
              <p className="text-sm text-muted-foreground">Loading...</p>
            ) : recentHistory.length === 0 ? (
              <p className="text-sm text-muted-foreground">No transactions yet</p>
            ) : (
              <div className="rounded-xl border border-border/50 overflow-hidden">
                {recentHistory.map((tx, i) => {
                  const hasOriginal =
                    tx.original_quantity != null &&
                    tx.original_unit &&
                    tx.original_unit !== (tx.unit || "each");
                  return (
                    <div
                      key={tx.id}
                      className={`flex items-center justify-between px-4 py-2.5 text-sm ${i < recentHistory.length - 1 ? "border-b border-border/40" : ""}`}
                    >
                      <span className="text-muted-foreground text-xs">
                        {TX_TYPE_LABELS[tx.transaction_type] || tx.transaction_type}
                      </span>
                      <span className="flex items-center gap-1.5">
                        <DeltaBadge delta={tx.quantity_delta} />
                        {hasOriginal && (
                          <span className="text-[10px] text-muted-foreground">
                            ({tx.original_quantity} {tx.original_unit})
                          </span>
                        )}
                      </span>
                      <span className="text-muted-foreground text-xs">
                        {tx.created_at ? format(new Date(tx.created_at), "MMM d, HH:mm") : "—"}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
