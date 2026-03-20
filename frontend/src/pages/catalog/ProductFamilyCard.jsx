import { useNavigate } from "react-router-dom";
import { Plus, Clock } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { VariantChip } from "./VariantChip";

function timeAgo(iso) {
  if (!iso) return null;
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  const months = Math.floor(days / 30);
  return `${months}mo ago`;
}

function priceRange(skus) {
  const prices = skus.map((s) => s.price).filter((p) => p != null && p > 0);
  if (prices.length === 0) return null;
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  if (min === max) return `$${min.toFixed(2)}`;
  return `$${min.toFixed(2)} – $${max.toFixed(2)}`;
}

const MAX_VISIBLE_CHIPS = 5;

export function ProductFamilyCard({ group, onAddVariant }) {
  const navigate = useNavigate();
  const { familyId, name, category, skus, isMulti } = group;

  const mostRecent = skus.reduce((latest, s) => {
    if (!s.updated_at) return latest;
    return !latest || new Date(s.updated_at) > new Date(latest) ? s.updated_at : latest;
  }, null);

  const handleCardClick = () => {
    if (isMulti) {
      navigate(`/products/${familyId}`);
    } else {
      navigate(`/products/${familyId}?sku=${skus[0].id}`);
    }
  };

  const handleAddVariant = (e) => {
    e.stopPropagation();
    onAddVariant?.(familyId, skus[0]?.category_id);
  };

  if (!isMulti) {
    const sku = skus[0];
    return (
      <div
        onClick={handleCardClick}
        className={cn(
          "group rounded-xl border border-border/60 bg-card p-4 cursor-pointer transition-all",
          "hover:border-border hover:shadow-md hover:bg-card/80",
        )}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <p className="text-xs font-mono text-muted-foreground">{sku.sku}</p>
            <p className="font-semibold text-sm mt-0.5 truncate">{sku.name}</p>
          </div>
          {category && (
            <Badge variant="outline" className="text-[10px] font-mono shrink-0">
              {category}
            </Badge>
          )}
        </div>

        <div className="flex items-center justify-between mt-3">
          <span className="font-mono text-sm">${(sku.price || 0).toFixed(2)}</span>
          {mostRecent && (
            <span className="inline-flex items-center gap-1 text-[11px] text-muted-foreground">
              <Clock className="w-3 h-3" />
              {timeAgo(mostRecent)}
            </span>
          )}
        </div>
      </div>
    );
  }

  const visibleSkus = skus.slice(0, MAX_VISIBLE_CHIPS);
  const hiddenCount = skus.length - MAX_VISIBLE_CHIPS;

  return (
    <div
      onClick={handleCardClick}
      className={cn(
        "group rounded-xl border border-border/60 bg-card p-4 cursor-pointer transition-all",
        "hover:border-border hover:shadow-md hover:bg-card/80",
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <p className="font-semibold text-sm truncate">{name}</p>
            <Badge variant="secondary" className="text-[10px] font-medium px-1.5 py-0 shrink-0">
              {skus.length} variants
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground mt-0.5">{priceRange(skus)}</p>
        </div>
        {category && (
          <Badge variant="outline" className="text-[10px] font-mono shrink-0">
            {category}
          </Badge>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-1.5 mt-3">
        {visibleSkus.map((sku) => (
          <VariantChip key={sku.id} sku={sku} familyId={familyId} />
        ))}
        {hiddenCount > 0 && (
          <span className="text-[11px] text-muted-foreground px-1.5">+{hiddenCount} more</span>
        )}
        <button
          onClick={handleAddVariant}
          className={cn(
            "inline-flex items-center gap-1 rounded-lg border border-dashed border-border/60",
            "px-2 py-1.5 text-xs text-muted-foreground transition-all",
            "opacity-0 group-hover:opacity-100",
            "hover:border-accent hover:text-accent hover:bg-accent/5",
          )}
        >
          <Plus className="w-3 h-3" />
          Add variant
        </button>
      </div>

      <div className="flex items-center justify-between mt-3">
        <div />
        {mostRecent && (
          <span className="inline-flex items-center gap-1 text-[11px] text-muted-foreground">
            <Clock className="w-3 h-3" />
            {timeAgo(mostRecent)}
          </span>
        )}
      </div>
    </div>
  );
}
