import { motion, AnimatePresence } from "framer-motion";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ChevronRight, CheckCircle, PackagePlus, Trash2, ArrowRight } from "lucide-react";
import { ProductMatchPicker } from "@/components/ProductMatchPicker";
import { ProductFields } from "@/components/ProductFields";

const HIDDEN_FOR_NEW = new Set(["description", "vendor_id", "min_stock", "quantity"]);

/**
 * Single item card used in ReviewFlow.
 * Collapsed: one-line summary showing name + match status + qty + cost.
 * Expanded: full match picker + editable fields.
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
  departments = [],
  mode = "import",
}) {
  const matched = matchState.matched || item.matched_product || null;
  const isNew = !matched;

  return (
    <div
      className={`rounded-xl border transition-all ${
        expanded
          ? isNew
            ? "border-warning/30 bg-warning/5 shadow-sm"
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
        </div>

        <div className="flex items-center gap-3 text-xs text-muted-foreground shrink-0">
          <span className="tabular-nums">qty: {item.delivered_qty ?? item.quantity ?? 1}</span>
          {item.cost != null && item.cost !== "" && (
            <span className="tabular-nums">${Number(item.cost).toFixed(2)}</span>
          )}
        </div>

        {matched ? (
          <span className="px-2 py-0.5 rounded-md text-[10px] font-semibold bg-success/15 text-success shrink-0">
            Matched
          </span>
        ) : (
          <span className="px-2 py-0.5 rounded-md text-[10px] font-semibold bg-warning/15 text-warning shrink-0">
            New SKU
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

              {/* Remove button */}
              <div className="flex justify-end pt-1">
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
            <p className="text-[10px] font-medium text-muted-foreground uppercase">Current</p>
            <p className="font-mono font-semibold text-foreground">{currentQty}</p>
          </div>
          <div className="flex items-center justify-center">
            <ArrowRight className="w-4 h-4 text-muted-foreground/50" />
          </div>
          <div className="bg-card rounded-lg border border-success/30 px-3 py-2">
            <p className="text-[10px] font-medium text-success uppercase">After</p>
            <p className="font-mono font-semibold text-success">{newQty}</p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label className="text-muted-foreground text-xs">Delivered qty</Label>
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
        <p className="text-xs text-muted-foreground font-mono">Vendor SKU: {item.original_sku}</p>
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
