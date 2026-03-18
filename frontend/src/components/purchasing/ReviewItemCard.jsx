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

const spring = { type: "spring", stiffness: 400, damping: 40 };

const REC_STYLES = {
  link_existing: {
    label: "Exact Match",
    cls: "bg-info/12 text-info border border-info/25",
    Icon: Link,
  },
  add_variant: {
    label: "Add to Family",
    cls: "bg-purple-500/12 text-purple-500 border border-purple-500/25",
    Icon: GitBranch,
  },
  create_new: {
    label: "New Product",
    cls: "bg-warning/12 text-warning border border-warning/25",
    Icon: Sparkles,
  },
};

function ConfidenceDot({ confidence }) {
  if (confidence == null) return null;
  const color =
    confidence >= 0.8 ? "bg-success" : confidence >= 0.5 ? "bg-amber-500" : "bg-destructive";
  return (
    <span
      className={`w-1.5 h-1.5 rounded-full shrink-0 ${color}`}
      title={`Confidence: ${(confidence * 100).toFixed(0)}%`}
    />
  );
}

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
  const recStyle = REC_STYLES[rec];
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

  const statusIcon = matched ? (
    <CheckCircle className="w-3.5 h-3.5 text-success shrink-0" />
  ) : rec === "add_variant" ? (
    <GitBranch className="w-3.5 h-3.5 text-purple-500 shrink-0" />
  ) : (
    <PackagePlus className="w-3.5 h-3.5 text-warning shrink-0" />
  );

  return (
    <motion.div
      layout
      transition={spring}
      className={`rounded-lg border transition-colors ${
        expanded
          ? isNew
            ? rec === "add_variant"
              ? "border-purple-500/25 bg-purple-500/[0.03]"
              : "border-warning/25 bg-warning/[0.03]"
            : "border-success/25 bg-success/[0.03]"
          : "border-border/50 bg-card hover:border-border"
      }`}
    >
      {/* Collapsed row */}
      <button
        type="button"
        onClick={onToggleExpand}
        className="w-full flex items-center gap-2.5 px-3 py-2.5 text-left"
      >
        <ChevronRight
          className={`w-3.5 h-3.5 text-muted-foreground shrink-0 transition-transform duration-200 ${
            expanded ? "rotate-90" : ""
          }`}
        />

        {statusIcon}

        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-foreground truncate leading-tight">
            {item.name || "Unnamed item"}
          </p>
          {matched && !expanded && (
            <p className="text-[10px] text-success font-mono leading-tight mt-0.5">{matched.sku}</p>
          )}
          {!matched && item.brand && !expanded && (
            <p className="text-[10px] text-muted-foreground leading-tight mt-0.5">{item.brand}</p>
          )}
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <ConfidenceDot confidence={item._confidence} />
          <span className="text-xs text-muted-foreground tabular-nums">
            &times;{item.delivered_qty ?? item.quantity ?? 1}
          </span>
          {item.cost != null && item.cost !== "" && (
            <span className="text-xs text-muted-foreground tabular-nums font-mono">
              ${Number(item.cost).toFixed(2)}
            </span>
          )}
        </div>

        {recStyle ? (
          <span
            className={`px-1.5 py-0.5 rounded text-[10px] font-semibold shrink-0 flex items-center gap-1 ${recStyle.cls}`}
          >
            <recStyle.Icon className="w-2.5 h-2.5" />
            {recStyle.label}
          </span>
        ) : matched ? (
          <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-success/12 text-success border border-success/25 shrink-0">
            Found
          </span>
        ) : (
          <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-warning/12 text-warning border border-warning/25 shrink-0">
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
            transition={spring}
            className="overflow-hidden"
          >
            <div className="px-3 pb-3 pt-1 space-y-3 border-t border-border/30">
              {/* AI reasoning */}
              {reason && (
                <div className="rounded-lg bg-muted/40 border border-border/30 px-3 py-2 text-xs text-muted-foreground">
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

              {/* Family candidates */}
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

              {/* Fields */}
              {matched ? (
                <MatchedFields item={item} matched={matched} onChange={onFieldChange} mode={mode} />
              ) : (
                <NewItemFields item={item} onChange={onFieldChange} departments={departments} />
              )}

              {/* Actions */}
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
                  Remove
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

function MatchedFields({ item, matched, onChange, mode }) {
  const currentQty = matched?.quantity ?? 0;
  const deliveredQty = parseFloat(item.delivered_qty ?? item.quantity ?? 1) || 0;
  const newQty = currentQty + deliveredQty;

  return (
    <div className="space-y-3">
      {mode === "receive" && (
        <div className="flex items-center gap-3 text-sm">
          <div className="flex-1 bg-card rounded-lg border border-border px-3 py-2">
            <p className="text-[10px] font-medium text-muted-foreground uppercase">Current</p>
            <p className="font-mono font-semibold tabular-nums">{currentQty}</p>
          </div>
          <ArrowRight className="w-4 h-4 text-muted-foreground/40 shrink-0" />
          <div className="flex-1 bg-card rounded-lg border border-success/30 px-3 py-2">
            <p className="text-[10px] font-medium text-success uppercase">After</p>
            <p className="font-mono font-semibold text-success tabular-nums">{newQty}</p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-2">
        <div>
          <Label className="text-muted-foreground text-xs">Qty received</Label>
          <Input
            type="number"
            min="0"
            step="any"
            value={item.delivered_qty ?? item.quantity ?? 1}
            onChange={(e) => onChange("delivered_qty", e.target.value)}
            className="input-field h-8 text-sm mt-1"
          />
        </div>
        <div>
          <Label className="text-muted-foreground text-xs">Cost</Label>
          <Input
            type="number"
            step="0.01"
            value={item.cost ?? ""}
            onChange={(e) => onChange("cost", e.target.value ? parseFloat(e.target.value) : null)}
            className="input-field h-8 text-sm mt-1"
          />
        </div>
      </div>

      {item.original_sku && (
        <p className="text-[10px] text-muted-foreground font-mono">
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
