import { useState, useEffect, useMemo } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loader2, Truck, CheckCircle, BoxIcon, ArrowLeft, ArrowRight } from "lucide-react";
import { StatusBadge } from "@/components/StatusBadge";
import { useMarkDelivery, useReceivePO } from "@/hooks/usePurchaseOrders";
import { useDepartments } from "@/hooks/useDepartments";
import api, { getErrorMessage } from "@/lib/api-client";
import { ReviewFlow } from "./ReviewFlow";

/**
 * Right-column detail view for an existing purchase order.
 * Shows items grouped by status with inline actions.
 * When user clicks "Receive into Inventory", transitions to ReviewFlow.
 *
 * @param {object}   po         Purchase order summary (from list)
 * @param {function} onBack     Deselect this PO
 * @param {function} onUpdated  Called after a successful mutation to refresh list
 */
export function PurchaseOrderDetail({ po, onBack, onUpdated }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [deliveredQtys, setDeliveredQtys] = useState({});
  const [selectedOrdered, setSelectedOrdered] = useState({});
  const [selectedPending, setSelectedPending] = useState({});
  const [acting, setActing] = useState(null);
  const [reviewItems, setReviewItems] = useState(null);

  const markDelivery = useMarkDelivery();
  const receivePO = useReceivePO();
  useDepartments(); // departments available for ProductFields if needed

  const loadItems = async () => {
    setLoading(true);
    try {
      const res = await api.purchaseOrders.get(po.id);
      const fetched = res.items || [];
      setItems(fetched);

      const qtys = {};
      const selO = {};
      const selP = {};
      for (const item of fetched) {
        if (item.status === "ordered") selO[item.id] = true;
        if (item.status === "pending") {
          qtys[item.id] = item.delivered_qty ?? item.ordered_qty ?? 1;
          selP[item.id] = true;
        }
      }
      setDeliveredQtys(qtys);
      setSelectedOrdered(selO);
      setSelectedPending(selP);
    } catch {
      toast.error("Failed to load items");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (po?.id) {
      loadItems();
      setReviewItems(null);
    }
  }, [po?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const orderedItems = items.filter((i) => i.status === "ordered");
  const pendingItems = items.filter((i) => i.status === "pending");
  const arrivedItems = items.filter((i) => i.status === "arrived");

  const selectedOrderedCount = orderedItems.filter((i) => selectedOrdered[i.id]).length;
  const selectedPendingCount = pendingItems.filter((i) => selectedPending[i.id]).length;

  const handleMarkDelivery = async () => {
    const ids = orderedItems.filter((i) => selectedOrdered[i.id]).map((i) => i.id);
    if (ids.length === 0) return;
    setActing("delivery");
    try {
      await markDelivery.mutateAsync({ id: po.id, data: { item_ids: ids } });
      toast.success(`${ids.length} item(s) marked as delivered`);
      await loadItems();
      onUpdated?.();
    } catch (e) {
      toast.error(getErrorMessage(e));
    } finally {
      setActing(null);
    }
  };

  const handleOpenReceive = () => {
    const pending = pendingItems.filter((i) => selectedPending[i.id]);
    if (pending.length === 0) {
      toast.error("No items selected");
      return;
    }
    const withQtys = pending.map((i) => ({
      ...i,
      delivered_qty: deliveredQtys[i.id] ?? i.delivered_qty ?? i.ordered_qty ?? 1,
    }));
    setReviewItems(withQtys);
  };

  const handleConfirmReceive = async (payload) => {
    setActing("receive");
    try {
      const res = await receivePO.mutateAsync({ id: po.id, data: { items: payload } });
      const total = (res.received || 0) + (res.matched || 0);
      toast.success(
        `${total} item(s) added to inventory${res.errors > 0 ? ` (${res.errors} failed)` : ""}`,
      );
      res.error_details?.forEach((e) => toast.error(`${e.item || e.item_id}: ${e.error}`));
      setReviewItems(null);
      await loadItems();
      onUpdated?.();
    } catch (e) {
      toast.error(getErrorMessage(e));
    } finally {
      setActing(null);
    }
  };

  const progress = useMemo(() => {
    const total = items.length;
    if (total === 0) return { ordered: 0, pending: 0, arrived: 0, pct: 0 };
    return {
      ordered: orderedItems.length,
      pending: pendingItems.length,
      arrived: arrivedItems.length,
      pct: Math.round((arrivedItems.length / total) * 100),
    };
  }, [items, orderedItems, pendingItems, arrivedItems]);

  if (reviewItems) {
    return (
      <ReviewFlow
        items={reviewItems}
        mode="receive"
        onConfirm={handleConfirmReceive}
        onBack={() => setReviewItems(null)}
        submitting={acting === "receive"}
        confirmLabel="Add to Inventory"
      />
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-5 pt-5 pb-4 border-b border-border/50 shrink-0">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onBack}
            className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h2 className="text-base font-semibold truncate">{po.vendor_name}</h2>
              <StatusBadge status={po.status} />
            </div>
            <p className="text-xs text-muted-foreground mt-0.5">
              {po.item_count} item{po.item_count !== 1 ? "s" : ""}
              {po.total > 0 && ` · $${Number(po.total).toFixed(2)}`}
              {" · "}
              {new Date(po.created_at).toLocaleDateString()}
            </p>
          </div>
        </div>

        {/* Progress stepper */}
        {items.length > 0 && (
          <div className="mt-4 flex items-center gap-1.5">
            <StepIndicator
              label="Ordered"
              count={progress.ordered}
              active={progress.ordered > 0 && progress.pending === 0 && progress.arrived === 0}
              done={progress.ordered === 0}
              icon={<BoxIcon className="w-3 h-3" />}
            />
            <ArrowRight className="w-3 h-3 text-muted-foreground/40 shrink-0" />
            <StepIndicator
              label="Delivered"
              count={progress.pending}
              active={progress.pending > 0}
              done={progress.pending === 0 && progress.arrived > 0}
              icon={<Truck className="w-3 h-3" />}
            />
            <ArrowRight className="w-3 h-3 text-muted-foreground/40 shrink-0" />
            <StepIndicator
              label="Received"
              count={progress.arrived}
              active={progress.arrived > 0 && progress.arrived === items.length}
              done={progress.arrived === items.length}
              icon={<CheckCircle className="w-3 h-3" />}
            />
            <span className="ml-auto text-[10px] font-mono text-muted-foreground tabular-nums">
              {progress.pct}%
            </span>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto px-5 py-4 space-y-5">
        {loading ? (
          <div className="text-center text-muted-foreground py-12">
            <Loader2 className="w-5 h-5 animate-spin mx-auto mb-2" />
            Loading items…
          </div>
        ) : (
          <>
            {/* Contextual guidance banner */}
            {orderedItems.length > 0 && pendingItems.length === 0 && arrivedItems.length === 0 && (
              <div className="rounded-xl border border-info/30 bg-info/5 px-4 py-3 text-sm text-foreground">
                <p className="font-medium">Has the order arrived?</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Select the items that have been delivered, then tap &ldquo;Mark Delivered&rdquo;
                  to start counting.
                </p>
              </div>
            )}
            {pendingItems.length > 0 && arrivedItems.length === 0 && (
              <div className="rounded-xl border border-accent/30 bg-accent/5 px-4 py-3 text-sm text-foreground">
                <p className="font-medium">Ready to add to inventory?</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Check the quantities are correct, then tap &ldquo;Add to Inventory&rdquo; to
                  update your stock.
                </p>
              </div>
            )}

            {orderedItems.length > 0 && (
              <ItemSection
                label="Waiting for delivery"
                icon={<BoxIcon className="w-3 h-3" />}
                color="muted-foreground"
                items={orderedItems}
                selected={selectedOrdered}
                onToggle={(id) => setSelectedOrdered((p) => ({ ...p, [id]: !p[id] }))}
                orderedLabel="Qty"
                action={
                  <Button
                    onClick={handleMarkDelivery}
                    disabled={acting === "delivery" || selectedOrderedCount === 0}
                    size="sm"
                    className="gap-1.5"
                  >
                    {acting === "delivery" ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Truck className="w-3.5 h-3.5" />
                    )}
                    Mark Delivered ({selectedOrderedCount})
                  </Button>
                }
              />
            )}

            {pendingItems.length > 0 && (
              <ItemSection
                label="Delivered — check quantities"
                icon={<Truck className="w-3 h-3" />}
                color="accent"
                items={pendingItems}
                selected={selectedPending}
                onToggle={(id) => setSelectedPending((p) => ({ ...p, [id]: !p[id] }))}
                showQtyInput
                deliveredQtys={deliveredQtys}
                onQtyChange={(id, val) => setDeliveredQtys((p) => ({ ...p, [id]: val }))}
                orderedLabel="Ordered"
                receivedLabel="Received"
                action={
                  <Button
                    onClick={handleOpenReceive}
                    disabled={acting === "receive" || selectedPendingCount === 0}
                    size="sm"
                    className="gap-1.5 btn-primary"
                  >
                    {acting === "receive" ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <CheckCircle className="w-3.5 h-3.5" />
                    )}
                    Add to Inventory ({selectedPendingCount})
                  </Button>
                }
              />
            )}

            {arrivedItems.length > 0 && (
              <div className="space-y-2">
                <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-success flex items-center gap-1.5">
                  <CheckCircle className="w-3 h-3" />
                  Added to inventory ({arrivedItems.length})
                </p>
                {arrivedItems.map((item) => (
                  <div
                    key={item.id}
                    className="flex items-center gap-3 p-3 rounded-lg border border-success/30 bg-success/5"
                  >
                    <CheckCircle className="w-4 h-4 text-success shrink-0" />
                    <ItemInfo item={item} />
                    <span className="text-xs text-muted-foreground tabular-nums shrink-0">
                      {item.delivered_qty ?? item.ordered_qty}
                    </span>
                    {item.cost > 0 && (
                      <span className="text-xs text-muted-foreground tabular-nums shrink-0">
                        ${Number(item.cost).toFixed(2)}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}

            {po.status === "received" && (
              <div className="flex items-center gap-2 text-xs text-success pt-3 border-t border-border/50">
                <CheckCircle className="w-3.5 h-3.5" />
                <span>
                  All items added to inventory
                  {po.received_by_name && ` by ${po.received_by_name}`}
                  {po.received_at && ` on ${new Date(po.received_at).toLocaleDateString()}`}
                </span>
              </div>
            )}

            {items.length === 0 && !loading && (
              <div className="text-center py-12 text-muted-foreground text-sm">No items found</div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function StepIndicator({ label, count, active, done, icon }) {
  const base = done
    ? "border-success/40 bg-success/10 text-success"
    : active
      ? "border-accent/40 bg-accent/10 text-accent"
      : "border-border/50 bg-muted/30 text-muted-foreground";

  return (
    <div
      className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-[10px] font-medium transition-colors ${base}`}
    >
      {icon}
      <span>{label}</span>
      {count > 0 && (
        <span className="rounded-full bg-current/10 px-1.5 py-0 text-[9px] tabular-nums">
          {count}
        </span>
      )}
    </div>
  );
}

function ItemSection({
  label,
  icon,
  color,
  items,
  selected,
  onToggle,
  showQtyInput,
  deliveredQtys,
  onQtyChange,
  orderedLabel = "Qty",
  receivedLabel,
  action,
}) {
  const selectedCount = items.filter((i) => selected[i.id]).length;

  return (
    <div className="space-y-2">
      <p
        className={`text-[10px] font-bold uppercase tracking-[0.12em] text-${color} flex items-center gap-1.5`}
      >
        {icon}
        {label}
      </p>

      {/* Column headers */}
      <div className="flex items-center gap-3 px-3 pb-0.5">
        <span className="w-5 shrink-0" />
        <span className="flex-1 text-[10px] text-muted-foreground/60 uppercase tracking-wider">
          Item
        </span>
        <span className="text-[10px] text-muted-foreground/60 uppercase tracking-wider w-14 text-right">
          {orderedLabel}
        </span>
        {showQtyInput ? (
          <span className="text-[10px] text-muted-foreground/60 uppercase tracking-wider w-20 text-right">
            {receivedLabel || "Received"}
          </span>
        ) : (
          <span className="w-20" />
        )}
        <span className="text-[10px] text-muted-foreground/60 uppercase tracking-wider w-16 text-right">
          Cost
        </span>
      </div>

      {items.map((item) => {
        const isSelected = selected[item.id];
        return (
          <div
            key={item.id}
            className={`flex items-center gap-3 p-3 rounded-lg border transition-all ${
              isSelected ? "border-border bg-muted/80" : "border-border/50 bg-muted/30 opacity-60"
            }`}
          >
            <button
              type="button"
              onClick={() => onToggle(item.id)}
              className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-colors shrink-0 ${
                isSelected ? "bg-accent border-accent" : "border-border"
              }`}
            >
              {isSelected && (
                <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                    clipRule="evenodd"
                  />
                </svg>
              )}
            </button>
            <ItemInfo item={item} />
            <span className="text-xs text-muted-foreground tabular-nums shrink-0 w-14 text-right">
              {item.ordered_qty}
            </span>
            {showQtyInput ? (
              <Input
                type="number"
                min="0"
                step="any"
                value={deliveredQtys?.[item.id] ?? item.ordered_qty ?? 1}
                onChange={(e) => onQtyChange?.(item.id, e.target.value)}
                className="h-8 text-sm text-right w-20"
              />
            ) : (
              <span className="text-xs text-muted-foreground w-20 text-right">—</span>
            )}
            {item.cost > 0 ? (
              <span className="text-xs text-muted-foreground tabular-nums shrink-0 w-16 text-right">
                ${Number(item.cost).toFixed(2)}
              </span>
            ) : (
              <span className="w-16" />
            )}
          </div>
        );
      })}
      <div className="flex items-center justify-between pt-1">
        <p className="text-xs text-muted-foreground">
          {selectedCount === items.length ? (
            "All selected"
          ) : (
            <>
              <strong>{selectedCount}</strong> of {items.length} selected
            </>
          )}
        </p>
        {action}
      </div>
    </div>
  );
}

function ItemInfo({ item }) {
  return (
    <div className="min-w-0 flex-1">
      <p className="text-sm font-medium text-foreground truncate">{item.name}</p>
      <p className="text-[10px] text-muted-foreground mt-0.5">
        {item.suggested_department && `${item.suggested_department}`}
        {item.base_unit && item.base_unit !== "each" && (
          <>
            {" · "}
            {item.pack_qty > 1 ? `${item.pack_qty} ` : ""}
            {item.base_unit}
          </>
        )}
        {item.original_sku && (
          <>
            {" · "}
            <span className="font-mono">{item.original_sku}</span>
          </>
        )}
      </p>
    </div>
  );
}
