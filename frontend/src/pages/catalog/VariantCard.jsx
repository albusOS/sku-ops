import { Plus } from "lucide-react";
import { cn } from "@/lib/utils";

function stockIndicator(quantity) {
  if (quantity == null) return { dot: "bg-muted-foreground", label: "Unknown" };
  if (quantity === 0) return { dot: "bg-destructive", label: "Out of Stock" };
  if (quantity <= 5) return { dot: "bg-warning", label: `Low (${quantity})` };
  return { dot: "bg-success", label: `In Stock (${quantity})` };
}

export function VariantCard({ sku, isSelected, onClick }) {
  const stock = stockIndicator(sku.quantity);
  const attrs = sku.variant_attrs;
  const hasAttrs = attrs && Object.keys(attrs).length > 0;

  return (
    <button
      onClick={() => onClick?.(sku)}
      className={cn(
        "flex flex-col items-start rounded-xl border p-4 text-left transition-all w-full",
        "hover:shadow-md hover:border-border",
        isSelected
          ? "border-accent bg-accent/5 shadow-sm ring-1 ring-accent/20"
          : "border-border/60 bg-card",
      )}
    >
      <p className="text-sm font-semibold truncate w-full">{sku.name}</p>
      <p className="text-xs font-mono text-muted-foreground mt-0.5">{sku.sku}</p>

      {hasAttrs && (
        <div className="flex flex-wrap gap-1.5 mt-2">
          {Object.entries(attrs).map(([k, v]) => (
            <span
              key={k}
              className="inline-flex items-center gap-1 rounded-md border border-border/50 bg-muted/30 px-1.5 py-0.5 text-[11px]"
            >
              <span className="text-muted-foreground">{k}:</span>
              <span className="font-medium">{v}</span>
            </span>
          ))}
        </div>
      )}

      <div className="flex items-center justify-between w-full mt-3">
        <span className="font-mono text-sm font-medium">${(sku.price || 0).toFixed(2)}</span>
        <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
          <span className={cn("w-2 h-2 rounded-full", stock.dot)} />
          {stock.label}
        </span>
      </div>
    </button>
  );
}

export function AddVariantCard({ onClick }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex flex-col items-center justify-center rounded-xl border border-dashed border-border/60",
        "p-6 text-muted-foreground transition-all min-h-[120px]",
        "hover:border-accent hover:text-accent hover:bg-accent/5",
      )}
    >
      <Plus className="w-5 h-5 mb-1.5" />
      <span className="text-xs font-medium">Add Variant</span>
    </button>
  );
}
