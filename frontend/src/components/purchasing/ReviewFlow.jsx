import { useState, useMemo, useCallback, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  CheckCircle,
  AlertTriangle,
  Loader2,
  ArrowLeft,
  ClipboardList,
  PackagePlus,
  GitBranch,
} from "lucide-react";
import { useProductMatch } from "@/hooks/useProductMatch";
import { useDepartments } from "@/hooks/useDepartments";
import { useChatPanel } from "@/context/ChatContext";
import { ReviewItemCard } from "./ReviewItemCard";
import api from "@/lib/api-client";

/**
 * Unified review flow for both document import and PO receiving.
 *
 * @param {array}    items           Extracted or PO items to review
 * @param {string}   mode            "import" | "receive"
 * @param {string}   vendorName      Vendor name (import mode)
 * @param {function} onVendorChange  (name: string) => void (import mode)
 * @param {boolean}  createVendor    Create vendor if missing flag
 * @param {function} onCreateVendorChange (bool) => void
 * @param {function} onConfirm       (payload) => void — submit action
 * @param {function} onBack          () => void — go back to previous step
 * @param {boolean}  submitting      Whether the submit is in progress
 * @param {string}   confirmLabel    Label for the confirm button
 */
export function ReviewFlow({
  items: rawItems,
  mode = "import",
  vendorName = "",
  onVendorChange,
  createVendor = true,
  onCreateVendorChange,
  onConfirm,
  onBack,
  submitting = false,
  confirmLabel = "Confirm",
}) {
  const { data: departments = [] } = useDepartments();
  const { sendPrompt } = useChatPanel();
  const [selectedDept, setSelectedDept] = useState("");
  const [expandedId, setExpandedId] = useState(null);
  const [items, setItems] = useState([]);
  const {
    matches,
    autoMatch,
    searchMatch,
    confirmMatch,
    clearMatch,
    reset: resetMatches,
  } = useProductMatch();

  useEffect(() => {
    if (!rawItems?.length) {
      setItems([]);
      resetMatches();
      return;
    }

    const seeded = rawItems.map((item, idx) => ({
      ...item,
      _rid: item.id ?? item._rid ?? idx,
      delivered_qty: item.delivered_qty ?? item.quantity ?? 1,
    }));
    setItems(seeded);

    const preMatched = [];
    const agentMatched = [];
    const needMatch = [];
    for (const item of seeded) {
      if (item.sku_id && item.matched_sku) {
        preMatched.push(item);
      } else if (item.sku_id && !item.matched_sku) {
        agentMatched.push(item);
      } else {
        needMatch.push({ ...item, id: item._rid });
      }
    }

    for (const item of preMatched) {
      confirmMatch(item._rid, {
        id: item.sku_id,
        sku: item.matched_sku,
        name: item.matched_name || item.name,
        quantity: item.matched_quantity ?? 0,
        cost: item.matched_cost ?? item.cost,
      });
    }

    if (agentMatched.length > 0) {
      Promise.all(
        agentMatched.map(async (item) => {
          try {
            const sku = await api.products.get(item.sku_id);
            if (sku) {
              confirmMatch(item._rid, {
                id: sku.id,
                sku: sku.sku,
                name: sku.name,
                quantity: sku.quantity ?? 0,
                cost: sku.cost ?? item.cost,
              });
            }
          } catch {
            needMatch.push({ ...item, id: item._rid });
          }
        }),
      ).then(() => {
        if (needMatch.length > 0) autoMatch(needMatch);
      });
    } else if (needMatch.length > 0) {
      autoMatch(needMatch);
    }
  }, [rawItems]); // eslint-disable-line react-hooks/exhaustive-deps

  const updateItem = useCallback((rid, field, value) => {
    setItems((prev) => {
      const next = prev.map((it) => (it._rid === rid ? { ...it, [field]: value } : it));
      return next;
    });
  }, []);

  const removeItem = useCallback((rid) => {
    setItems((prev) => prev.filter((it) => it._rid !== rid));
  }, []);

  const handleConfirmMatch = useCallback(
    (rid, product) => {
      setItems((prev) =>
        prev.map((it) => (it._rid === rid ? { ...it, matched_product: product } : it)),
      );
      confirmMatch(rid, product);
    },
    [confirmMatch],
  );

  const handleClearMatch = useCallback(
    (rid) => {
      setItems((prev) =>
        prev.map((it) => (it._rid === rid ? { ...it, matched_product: null } : it)),
      );
      clearMatch(rid);
    },
    [clearMatch],
  );

  const resolvedItems = useMemo(() => {
    return items.map((item) => {
      const m = matches[item._rid];
      const matched = m?.matched || item.matched_product || null;
      return { ...item, _resolved_match: matched };
    });
  }, [items, matches]);

  const matchedCount = resolvedItems.filter((i) => i._resolved_match).length;
  const newCount = resolvedItems.filter((i) => !i._resolved_match).length;
  const totalCost = resolvedItems.reduce((sum, it) => {
    const qty = parseFloat(it.delivered_qty ?? it.quantity) || 0;
    const cost = parseFloat(it.cost) || 0;
    return sum + qty * cost;
  }, 0);

  const exactMatches = resolvedItems.filter(
    (i) => i._resolved_match && i._recommendation === "link_existing",
  );
  const familyMatches = resolvedItems.filter(
    (i) => i._recommendation === "add_variant" && !i._resolved_match,
  );
  const readyOther = resolvedItems.filter(
    (i) => i._resolved_match && i._recommendation !== "link_existing",
  );
  const needsAttention = resolvedItems.filter(
    (i) => !i._resolved_match && i._recommendation !== "add_variant",
  );
  const ready = [...exactMatches, ...readyOther];

  const handleAcceptAll = () => {
    for (const item of resolvedItems) {
      const m = matches[item._rid];
      if (m?.options?.length > 0 && !m.matched) {
        handleConfirmMatch(item._rid, m.options[0]);
      }
    }
  };

  const handleSubmit = () => {
    const payload = resolvedItems.map((it) => {
      const entry = {
        id: it.id ?? it._rid,
        delivered_qty: parseFloat(it.delivered_qty) || 1,
        name: it.name,
      };

      if (it.cost != null && it.cost !== "") entry.cost = parseFloat(it.cost);

      const matched = it._resolved_match;
      if (matched) {
        entry.sku_id = matched.id;
      } else {
        entry.price = parseFloat(it.price) || 0;
        entry.original_sku = it.original_sku;
        entry.base_unit = it.base_unit || undefined;
        entry.sell_uom = it.sell_uom || it.base_unit || undefined;
        entry.pack_qty = it.pack_qty != null ? parseInt(it.pack_qty) : undefined;
        entry.suggested_department = it.suggested_department || undefined;
        entry.barcode = it.barcode || undefined;
        entry.min_stock = it.min_stock != null ? parseInt(it.min_stock) : 5;
        entry.ai_parsed = it._ai_parsed || it.ai_parsed || false;
      }

      if (mode === "import") {
        entry.ordered_qty =
          it.ordered_qty != null ? parseFloat(it.ordered_qty) : parseFloat(it.delivered_qty) || 1;
        entry.quantity = parseFloat(it.delivered_qty) || 1;
        entry.selected = true;
        if (selectedDept) entry.suggested_department = selectedDept;
      }

      return entry;
    });

    onConfirm?.(payload);
  };

  const hasUnresolvedSuggestions = resolvedItems.some((item) => {
    const m = matches[item._rid];
    return m?.options?.length > 0 && !m.matched && !item.matched_product;
  });

  const renderItemCard = (item) => (
    <ReviewItemCard
      key={item._rid}
      item={item}
      matchState={matches[item._rid] || {}}
      expanded={expandedId === item._rid}
      onToggleExpand={() => setExpandedId((prev) => (prev === item._rid ? null : item._rid))}
      onFieldChange={(field, value) => updateItem(item._rid, field, value)}
      onConfirmMatch={(product) => handleConfirmMatch(item._rid, product)}
      onClearMatch={() => handleClearMatch(item._rid)}
      onSearchMatch={(q) => searchMatch(item._rid, q)}
      onRemove={() => removeItem(item._rid)}
      onAskAssistant={sendPrompt}
      departments={departments}
      mode={mode}
    />
  );

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-5 pt-5 pb-4 border-b border-border/50 shrink-0">
        <div className="flex items-center gap-3 mb-4">
          {onBack && (
            <button
              type="button"
              onClick={onBack}
              className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
            </button>
          )}
          <h2 className="text-base font-semibold">
            {mode === "import" ? "Review Items" : "Review & Add to Inventory"}
          </h2>
        </div>

        {/* Summary strip */}
        <div className="grid grid-cols-3 gap-2">
          <SummaryChip
            icon={<CheckCircle className="w-3.5 h-3.5 text-success" />}
            label="Recognized"
            value={matchedCount}
            color="success"
          />
          <SummaryChip
            icon={<PackagePlus className="w-3.5 h-3.5 text-warning" />}
            label="New items"
            value={newCount}
            color="warning"
          />
          <SummaryChip
            label="Total cost"
            value={totalCost > 0 ? `$${totalCost.toFixed(2)}` : "—"}
          />
        </div>

        {hasUnresolvedSuggestions && (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleAcceptAll}
            className="mt-3 w-full text-xs h-8"
          >
            <CheckCircle className="w-3.5 h-3.5 mr-1.5 text-success" />
            Accept all suggestions
          </Button>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto px-5 py-4 space-y-5">
        {/* Import-specific: vendor & category */}
        {mode === "import" && (
          <div className="space-y-3">
            <div>
              <Label className="text-muted-foreground font-medium text-sm">Supplier name</Label>
              <Input
                value={vendorName}
                onChange={(e) => onVendorChange?.(e.target.value)}
                className="input-field mt-1.5"
                placeholder="e.g. Builders Warehouse"
              />
            </div>

            <div className="flex items-center gap-2">
              <Checkbox
                id="create-vendor-review"
                checked={createVendor}
                onCheckedChange={(c) => onCreateVendorChange?.(c === true)}
              />
              <Label
                htmlFor="create-vendor-review"
                className="text-sm text-muted-foreground cursor-pointer"
              >
                Add as new supplier if not found
              </Label>
            </div>

            <div>
              <Label className="text-muted-foreground font-medium text-sm">Department</Label>
              <p className="text-[10px] text-muted-foreground/70 mt-0.5 mb-1.5">
                Assign all items to a department, or leave blank to use per-item suggestions
              </p>
              <Select
                value={selectedDept || "none"}
                onValueChange={(v) => setSelectedDept(v === "none" ? "" : v)}
              >
                <SelectTrigger className="input-field">
                  <SelectValue placeholder="Auto-detect per item" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">Auto-detect per item</SelectItem>
                  {departments.map((dept) => (
                    <SelectItem key={dept.id} value={dept.id}>
                      {dept.name} ({dept.code})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        )}

        {/* Needs attention section */}
        {needsAttention.length > 0 && (
          <div className="space-y-2">
            <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-warning flex items-center gap-1.5">
              <AlertTriangle className="w-3 h-3" />
              Needs your attention ({needsAttention.length})
            </p>
            {needsAttention.map(renderItemCard)}
          </div>
        )}

        {/* Family matches section */}
        {familyMatches.length > 0 && (
          <div className="space-y-2">
            <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-purple-500 flex items-center gap-1.5">
              <GitBranch className="w-3 h-3" />
              Family matches ({familyMatches.length})
            </p>
            {familyMatches.map(renderItemCard)}
          </div>
        )}

        {/* Ready section */}
        {ready.length > 0 && (
          <div className="space-y-2">
            <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-success flex items-center gap-1.5">
              <CheckCircle className="w-3 h-3" />
              Good to go ({ready.length})
            </p>
            {ready.map(renderItemCard)}
          </div>
        )}

        {resolvedItems.length === 0 && (
          <div className="text-center py-12 text-muted-foreground text-sm">No items to review</div>
        )}
      </div>

      {/* Sticky footer */}
      <div className="px-5 py-4 border-t border-border bg-muted/50 shrink-0 space-y-3">
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>
            {resolvedItems.length} item{resolvedItems.length !== 1 ? "s" : ""}
            {matchedCount > 0 && newCount > 0 && ` (${matchedCount} existing, ${newCount} new)`}
          </span>
          {totalCost > 0 && (
            <span className="font-mono text-foreground">${totalCost.toFixed(2)}</span>
          )}
        </div>
        <Button
          onClick={handleSubmit}
          disabled={
            submitting ||
            resolvedItems.length === 0 ||
            (mode === "import" && !(vendorName || "").trim())
          }
          className="w-full btn-primary h-11"
        >
          {submitting ? (
            <>
              <Loader2 className="w-5 h-5 mr-2 animate-spin" />
              Processing…
            </>
          ) : (
            <>
              <ClipboardList className="w-5 h-5 mr-2" />
              {confirmLabel}
            </>
          )}
        </Button>
      </div>
    </div>
  );
}

function SummaryChip({ icon, label, value, color }) {
  return (
    <div className="rounded-lg px-3 py-2 text-center bg-muted/50 border border-border/40">
      <div className="flex items-center justify-center gap-1.5 mb-0.5">
        {icon}
        <p className="text-[10px] text-muted-foreground uppercase tracking-wider">{label}</p>
      </div>
      <p className={`font-mono font-semibold text-sm ${color ? `text-${color}` : ""}`}>{value}</p>
    </div>
  );
}
