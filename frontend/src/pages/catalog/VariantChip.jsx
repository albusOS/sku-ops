import { useNavigate } from "react-router-dom";
import { cn } from "@/lib/utils";

function variantLabel(sku) {
  const attrs = sku.variant_attrs;
  if (attrs && Object.keys(attrs).length > 0) {
    return Object.values(attrs).join(" · ");
  }
  if (sku.variant_label) return sku.variant_label;
  return sku.name;
}

function stockDot(quantity) {
  if (quantity == null) return null;
  if (quantity === 0) return "bg-destructive";
  if (quantity <= 5) return "bg-warning";
  return "bg-success";
}

export function VariantChip({ sku, familyId, className }) {
  const navigate = useNavigate();
  const dot = stockDot(sku.quantity);

  return (
    <button
      onClick={(e) => {
        e.stopPropagation();
        navigate(`/products/${familyId}?sku=${sku.id}`);
      }}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-lg border border-border/60 bg-muted/30",
        "px-2.5 py-1.5 text-left transition-all",
        "hover:bg-muted/70 hover:border-border hover:shadow-sm",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/30",
        className,
      )}
    >
      {dot && <span className={cn("w-1.5 h-1.5 rounded-full shrink-0", dot)} />}
      <span className="text-xs font-medium truncate max-w-[120px]">{variantLabel(sku)}</span>
      <span className="text-[11px] font-mono text-muted-foreground">
        ${(sku.price || 0).toFixed(2)}
      </span>
    </button>
  );
}
