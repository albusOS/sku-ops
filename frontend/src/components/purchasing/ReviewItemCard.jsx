import { motion, AnimatePresence } from "framer-motion";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  ChevronRight,
  CheckCircle,
  PackagePlus,
  Trash2,
  ArrowRight,
  Link,
  GitBranch,
  Sparkles,
  AlertTriangle,
  MessageCircle,
} from "lucide-react";
import { ProductMatchPicker } from "@/components/ProductMatchPicker";
import { ProductFields } from "@/components/ProductFields";
const HIDDEN_FOR_NEW = new Set(["description", "vendor_id", "min_stock", "quantity"]);

const RECOMMENDATION_BADGES = {
  link_existing: { label: "Exact Match", className: "bg-blue-500/15 text-blue-600", icon: Link },
  add_variant: {
    label: "Add to Family",
    className: "bg-purple-500/15 text-purple-600",
    icon: GitBranch,
  },
  create_new: { label: "New Product", className: "bg-amber-500/15 text-amber-600", icon: Sparkles },
};

function ConfidenceDot({ confidence }) {
  if (confidence == null) return null;
  const color =
    confidence >= 0.8 ? "bg-success" : confidence >= 0.5 ? "bg-amber-500" : "bg-destructive";
  return (
    <span
      className={`w-2 h-2 rounded-full shrink-0 ${color}`}
      title={`Confidence: ${(confidence * 100).toFixed(0)}%`}
    />
  );
}

/**
 * Single item card used in ReviewFlow.
 * Collapsed: one-line summary showing name + match status + qty + cost.
 * Expanded: full match picker + editable fields + agent reasoning.
 */
export function ReviewItemCard({
  item,
  matchState = {},
  expanded = false,
  onToggleExpand,
  onFieldChange,
  onConfirmMatch,
  onClearMatch,
  onSearchMatch,
  onRemove,
  onAskAssistant,
  departments = [],
  mode = "import",
}) {
  const matched = matchState.matched || item.matched_product || null;
  const isNew = !matched;
  const rec = item._recommendation;
  const badge = RECOMMENDATION_BADGES[rec];
  const BadgeIcon = badge?.icon;
  const familyCandidates = item._family_candidates || [];
  const warnings = item._warnings || [];
  const reason = item._recommendation_reason;

  const handleAskAssistant = (e) => {
    e.stopPropagation();
    if (!onAskAssistant) return;
    const context = reason
      ? `I'm reviewing a PO item: "${item.name}". The AI suggests: ${reason}. Is this right?`
      : `I'm reviewing a PO item: "${item.name}". Can you help me classify this product?`;
    onAskAssistant(context);
  };

  return (
    <div
      className={`rounded-xl border transition-all ${
        expanded
          ? isNew
            ? rec === "add_variant"
              ? "border-purple-500/30 bg-purple-500/5 shadow-sm"
              : "border-warning/30 bg-warning/5 shadow-sm"
            : "border-success/30 bg-success/5 shadow-sm"
          : "border-border/60 bg-card hover:border-border hover:shadow-sm"
      }`}
    >
      {/* Collapsed header — always visible */}
      <button
        type="button"
        onClick={onToggleExpand}
        className="w-full flex items-center gap-3 p-3.5 text-left"
      >
        <ChevronRight
          className={`w-4 h-4 text-muted-foreground shrink-0 transition-transform ${
            expanded ? "rotate-90" : ""
          }`}
        />

        {matched ? (
          <CheckCircle className="w-4 h-4 text-success shrink-0" />
        ) : rec === "add_variant" ? (
          <GitBranch className="w-4 h-4 text-purple-500 shrink-0" />
        ) : (
          <PackagePlus className="w-4 h-4 text-warning shrink-0" />
        )}

        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-foreground truncate">
            {item.name || "Unnamed item"}
          </p>
          {matched && !expanded && (
            <p className="text-[10px] text-success mt-0.5 font-mono">{matched.sku}</p>
          )}
          {!matched && item.brand && !expanded && (
            <p className="text-[10px] text-muted-foreground mt-0.5">{item.brand}</p>
          )}
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <ConfidenceDot confidence={item._confidence} />
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <span className="tabular-nums">&times;{item.delivered_qty ?? item.quantity ?? 1}</span>
            {item.cost != null && item.cost !== "" && (
              <span className="tabular-nums">${Number(item.cost).toFixed(2)}</span>
            )}
          </div>
        </div>

        {badge ? (
          <span
            className={`px-2 py-0.5 rounded-md text-[10px] font-semibold shrink-0 flex items-center gap-1 ${badge.className}`}
          >
            {BadgeIcon && <BadgeIcon className="w-3 h-3" />}
            {badge.label}
          </span>
        ) : matched ? (
          <span className="px-2 py-0.5 rounded-md text-[10px] font-semibold bg-success/15 text-success shrink-0">
            Found
          </span>
        ) : (
          <span className="px-2 py-0.5 rounded-md text-[10px] font-semibold bg-warning/15 text-warning shrink-0">
            New
          </span>
        )}
      </button>

      {/* Expanded detail */}
      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ type: "spring", stiffness: 400, damping: 40 }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4 pt-1 space-y-3 border-t border-border/30">
              {/* Agent reasoning */}
              {reason && (
                <div className="rounded-lg bg-muted/50 border border-border/40 px-3 py-2 text-xs text-muted-foreground">
                  <span className="font-medium text-foreground">AI reasoning:</span> {reason}
                </div>
              )}

              {/* Warnings */}
              {warnings.length > 0 && (
                <div className="space-y-1">
                  {warnings.map((w, i) => (
                    <div key={i} className="flex items-start gap-1.5 text-xs text-amber-600">
                      <AlertTriangle className="w-3 h-3 mt-0.5 shrink-0" />
                      <span>{w}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Family candidates for add_variant */}
              {rec === "add_variant" && familyCandidates.length > 0 && !matched && (
                <div className="rounded-lg border border-purple-500/20 bg-purple-500/5 px-3 py-2 space-y-1.5">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-purple-600">
                    Suggested family
                  </p>
                  {familyCandidates.map((fc) => (
                    <div key={fc.family_id} className="flex items-center justify-between">
                      <span className="text-xs font-medium text-foreground">{fc.family_name}</span>
                      <span className="text-[10px] text-muted-foreground font-mono">
                        {(fc.similarity * 100).toFixed(0)}% match
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {/* Match picker */}
              <ProductMatchPicker
                matched={matched}
                options={matchState.options || []}
                searching={matchState.searching || false}
                onSearch={onSearchMatch}
                onConfirm={onConfirmMatch}
                onClear={onClearMatch}
              />

              {/* Matched item: qty + cost + stock preview */}
              {matched ? (
                <MatchedFields item={item} matched={matched} onChange={onFieldChange} mode={mode} />
              ) : (
                <NewItemFields item={item} onChange={onFieldChange} departments={departments} />
              )}

              {/* Actions row */}
              <div className="flex items-center justify-between pt-1">
                {onAskAssistant ? (
                  <button
                    type="button"
                    onClick={handleAskAssistant}
                    className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-accent transition-colors"
                  >
                    <MessageCircle className="w-3.5 h-3.5" />
                    Ask assistant
                  </button>
                ) : (
                  <span />
                )}
                <button
                  type="button"
                  onClick={onRemove}
                  className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-destructive transition-colors"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  Remove item
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function MatchedFields({ item, matched, onChange, mode }) {
  const currentQty = matched?.quantity ?? 0;
  const deliveredQty = parseFloat(item.delivered_qty ?? item.quantity ?? 1) || 0;
  const newQty = currentQty + deliveredQty;

  return (
    <div className="space-y-3">
      {mode === "receive" && (
        <div className="grid grid-cols-3 gap-3 text-sm">
          <div className="bg-card rounded-lg border border-border px-3 py-2">
            <p className="text-[10px] font-medium text-muted-foreground uppercase">In stock now</p>
            <p className="font-mono font-semibold text-foreground">{currentQty}</p>
          </div>
          <div className="flex items-center justify-center">
            <ArrowRight className="w-4 h-4 text-muted-foreground/50" />
          </div>
          <div className="bg-card rounded-lg border border-success/30 px-3 py-2">
            <p className="text-[10px] font-medium text-success uppercase">After receiving</p>
            <p className="font-mono font-semibold text-success">{newQty}</p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label className="text-muted-foreground text-xs">Quantity received</Label>
          <Input
            type="number"
            min="0"
            step="any"
            value={item.delivered_qty ?? item.quantity ?? 1}
            onChange={(e) => onChange("delivered_qty", e.target.value)}
            className="input-field h-9 text-sm mt-1"
          />
        </div>
        <div>
          <Label className="text-muted-foreground text-xs">Cost</Label>
          <Input
            type="number"
            step="0.01"
            value={item.cost ?? ""}
            onChange={(e) => onChange("cost", e.target.value ? parseFloat(e.target.value) : null)}
            className="input-field h-9 text-sm mt-1"
          />
        </div>
      </div>

      {item.original_sku && (
        <p className="text-xs text-muted-foreground font-mono">
          Supplier code: {item.original_sku}
        </p>
      )}
    </div>
  );
}

function NewItemFields({ item, onChange, departments }) {
  return (
    <ProductFields
      compact
      fields={{
        name: item.name || "",
        price: item.price ?? "",
        cost: item.cost ?? "",
        base_unit: item.base_unit || "each",
        sell_uom: item.sell_uom || item.base_unit || "each",
        pack_qty: item.pack_qty ?? 1,
        barcode: item.barcode || "",
        category_id: item.suggested_department || "",
        quantity: item.delivered_qty ?? item.quantity ?? 1,
      }}
      onChange={(field, value) => {
        const mapped =
          field === "category_id"
            ? "suggested_department"
            : field === "quantity"
              ? "delivered_qty"
              : field;
        onChange(mapped, value);
      }}
      departments={departments}
      hiddenFields={HIDDEN_FOR_NEW}
    />
  );
}
