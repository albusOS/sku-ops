import { useState, useEffect, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { X, Truck, CheckCircle, BoxIcon, Loader2, Package } from "lucide-react";
import { StatusBadge } from "@/components/StatusBadge";
import { useMarkDelivery, useReceivePO } from "@/hooks/usePurchaseOrders";
import api, { getErrorMessage } from "@/lib/api-client";
import { ReviewFlow } from "./ReviewFlow";

const spring = { type: "spring", stiffness: 300, damping: 34 };
const stagger = {
  hidden: {},
  show: { transition: { staggerChildren: 0.04 } },
};
const fadeUp = {
  hidden: { opacity: 0, y: 8 },
  show: { opacity: 1, y: 0, transition: spring },
};

export function PODetailPanel({ po, open, onClose, onUpdated }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [deliveredQtys, setDeliveredQtys] = useState({});
  const [selectedOrdered, setSelectedOrdered] = useState({});
  const [selectedPending, setSelectedPending] = useState({});
  const [acting, setActing] = useState(null);
  const [reviewItems, setReviewItems] = useState(null);

  const markDelivery = useMarkDelivery();
  const receivePO = useReceivePO();

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
    if (open && po?.id) {
      loadItems();
      setReviewItems(null);
    }
  }, [open, po?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const orderedItems = items.filter((i) => i.status === "ordered");
  const pendingItems = items.filter((i) => i.status === "pending");
  const arrivedItems = items.filter((i) => i.status === "arrived");
  const selectedOrderedCount = orderedItems.filter((i) => selectedOrdered[i.id]).length;
  const selectedPendingCount = pendingItems.filter((i) => selectedPending[i.id]).length;

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

  if (reviewItems) {
    return (
      <div className="flex flex-col h-full bg-card border-l border-border/60 overflow-hidden">
        <ReviewFlow
          items={reviewItems}
          mode="receive"
          onConfirm={handleConfirmReceive}
          onBack={() => setReviewItems(null)}
          submitting={acting === "receive"}
          confirmLabel="Add to Inventory"
        />
      </div>
    );
  }

  return (
    <AnimatePresence mode="wait">
      {open && po && (
        <motion.div
          key="po-panel"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
          className="flex flex-col h-full bg-card border-l border-border/60 overflow-hidden"
        >
          {/* Header */}
          <div className="px-5 pt-5 pb-4 border-b border-border/50 shrink-0">
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-9 h-9 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center shrink-0">
                  <Package className="w-4.5 h-4.5 text-accent" />
                </div>
                <div className="min-w-0">
                  <h2 className="font-semibold text-sm leading-tight truncate">{po.vendor_name}</h2>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {po.item_count} item{po.item_count !== 1 ? "s" : ""}
                    {" · "}
                    {new Date(po.created_at).toLocaleDateString()}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <StatusBadge status={po.status} />
                <button
                  onClick={onClose}
                  className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Progress bar */}
            {items.length > 0 && (
              <div className="mt-4 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">
                    {progress.arrived} of {items.length} in stock
                  </span>
                  <span className="font-mono text-muted-foreground tabular-nums">
                    {progress.pct}%
                  </span>
                </div>
                <div className="h-1.5 bg-muted rounded-full overflow-hidden flex">
                  {progress.arrived > 0 && (
                    <motion.div
                      className="h-full bg-success"
                      initial={{ width: 0 }}
                      animate={{ width: `${(progress.arrived / items.length) * 100}%` }}
                      transition={spring}
                    />
                  )}
                  {progress.pending > 0 && (
                    <motion.div
                      className="h-full bg-info"
                      initial={{ width: 0 }}
                      animate={{ width: `${(progress.pending / items.length) * 100}%` }}
                      transition={spring}
                    />
                  )}
                </div>
                <div className="flex items-center gap-4 text-[10px] text-muted-foreground">
                  {progress.ordered > 0 && (
                    <span className="flex items-center gap-1">
                      <span className="w-2 h-2 rounded-full bg-muted-foreground/30" />
                      {progress.ordered} ordered
                    </span>
                  )}
                  {progress.pending > 0 && (
                    <span className="flex items-center gap-1">
                      <span className="w-2 h-2 rounded-full bg-info" />
                      {progress.pending} delivered
                    </span>
                  )}
                  {progress.arrived > 0 && (
                    <span className="flex items-center gap-1">
                      <span className="w-2 h-2 rounded-full bg-success" />
                      {progress.arrived} in stock
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Content */}
          <div className="flex-1 overflow-auto">
            {loading ? (
              <div className="flex items-center justify-center py-16 text-muted-foreground">
                <Loader2 className="w-5 h-5 animate-spin" />
              </div>
            ) : (
              <motion.div
                className="px-5 py-4 space-y-6"
                variants={stagger}
                initial="hidden"
                animate="show"
              >
                {/* Ordered */}
                {orderedItems.length > 0 && (
                  <motion.section variants={fadeUp} className="space-y-2">
                    <SectionHeader
                      icon={<BoxIcon className="w-3 h-3" />}
                      label="Waiting for delivery"
                      count={orderedItems.length}
                      onToggleAll={() => {
                        const allSelected = orderedItems.every((i) => selectedOrdered[i.id]);
                        const next = {};
                        if (!allSelected) orderedItems.forEach((i) => (next[i.id] = true));
                        setSelectedOrdered(next);
                      }}
                      allSelected={orderedItems.every((i) => selectedOrdered[i.id])}
                    />
                    <div className="space-y-1.5">
                      {orderedItems.map((item) => (
                        <ItemRow
                          key={item.id}
                          item={item}
                          selected={!!selectedOrdered[item.id]}
                          onToggle={() =>
                            setSelectedOrdered((p) => ({ ...p, [item.id]: !p[item.id] }))
                          }
                          trailing={
                            <span className="text-xs text-muted-foreground tabular-nums">
                              ×{item.ordered_qty}
                            </span>
                          }
                        />
                      ))}
                    </div>
                    <Button
                      onClick={handleMarkDelivery}
                      disabled={acting === "delivery" || selectedOrderedCount === 0}
                      size="sm"
                      variant="outline"
                      className="w-full gap-1.5"
                    >
                      {acting === "delivery" ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <Truck className="w-3.5 h-3.5" />
                      )}
                      Mark Delivered ({selectedOrderedCount})
                    </Button>
                  </motion.section>
                )}

                {/* Pending */}
                {pendingItems.length > 0 && (
                  <motion.section variants={fadeUp} className="space-y-2">
                    <SectionHeader
                      icon={<Truck className="w-3 h-3" />}
                      label="Confirm quantities"
                      count={pendingItems.length}
                      color="text-info"
                      onToggleAll={() => {
                        const allSelected = pendingItems.every((i) => selectedPending[i.id]);
                        const next = {};
                        if (!allSelected) pendingItems.forEach((i) => (next[i.id] = true));
                        setSelectedPending(next);
                      }}
                      allSelected={pendingItems.every((i) => selectedPending[i.id])}
                    />
                    <div className="space-y-1.5">
                      {pendingItems.map((item) => (
                        <ItemRow
                          key={item.id}
                          item={item}
                          selected={!!selectedPending[item.id]}
                          onToggle={() =>
                            setSelectedPending((p) => ({ ...p, [item.id]: !p[item.id] }))
                          }
                          trailing={
                            <div className="flex items-center gap-2 shrink-0">
                              <span className="text-[10px] text-muted-foreground tabular-nums">
                                ord {item.ordered_qty}
                              </span>
                              <Input
                                type="number"
                                min="0"
                                step="any"
                                value={deliveredQtys[item.id] ?? item.ordered_qty ?? 1}
                                onChange={(e) =>
                                  setDeliveredQtys((p) => ({ ...p, [item.id]: e.target.value }))
                                }
                                className="h-7 text-xs text-right w-14 font-mono rounded-md"
                              />
                            </div>
                          }
                        />
                      ))}
                    </div>
                    <Button
                      onClick={handleOpenReceive}
                      disabled={acting === "receive" || selectedPendingCount === 0}
                      className="btn-primary w-full gap-1.5"
                    >
                      {acting === "receive" ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <CheckCircle className="w-3.5 h-3.5" />
                      )}
                      Add to Inventory ({selectedPendingCount})
                    </Button>
                  </motion.section>
                )}

                {/* Arrived */}
                {arrivedItems.length > 0 && (
                  <motion.section variants={fadeUp} className="space-y-1.5">
                    <SectionHeader
                      icon={<CheckCircle className="w-3 h-3" />}
                      label="In stock"
                      count={arrivedItems.length}
                      color="text-success"
                    />
                    <div className="space-y-1">
                      {arrivedItems.map((item) => (
                        <div
                          key={item.id}
                          className="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-success/5 border border-success/15"
                        >
                          <CheckCircle className="w-3.5 h-3.5 text-success shrink-0" />
                          <ItemInfo item={item} />
                          <span className="text-xs text-muted-foreground tabular-nums shrink-0">
                            ×{item.delivered_qty ?? item.ordered_qty}
                          </span>
                          {item.cost > 0 && (
                            <span className="text-xs text-muted-foreground tabular-nums shrink-0">
                              ${Number(item.cost).toFixed(2)}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  </motion.section>
                )}

                {/* Completion */}
                {po.status === "received" && (
                  <motion.div
                    variants={fadeUp}
                    className="flex items-center gap-2 text-xs text-success pt-2 border-t border-border/50"
                  >
                    <CheckCircle className="w-3.5 h-3.5 shrink-0" />
                    <span>
                      All items received
                      {po.received_by_name && ` by ${po.received_by_name}`}
                      {po.received_at && ` on ${new Date(po.received_at).toLocaleDateString()}`}
                    </span>
                  </motion.div>
                )}

                {items.length === 0 && !loading && (
                  <div className="text-center py-16 text-muted-foreground text-sm">
                    No items found
                  </div>
                )}
              </motion.div>
            )}
          </div>

          {/* Footer — total if available */}
          {po.total > 0 && (
            <div className="px-5 py-3 border-t border-border/50 shrink-0 flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Order total</span>
              <span className="font-mono font-semibold">${Number(po.total).toFixed(2)}</span>
            </div>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function SectionHeader({
  icon,
  label,
  count,
  color = "text-muted-foreground",
  onToggleAll,
  allSelected,
}) {
  return (
    <div className="flex items-center justify-between">
      <p
        className={`text-[10px] font-bold uppercase tracking-[0.12em] flex items-center gap-1.5 ${color}`}
      >
        {icon}
        {label} ({count})
      </p>
      {onToggleAll && (
        <button
          type="button"
          onClick={onToggleAll}
          className="text-[10px] text-muted-foreground hover:text-foreground transition-colors"
        >
          {allSelected ? "Deselect all" : "Select all"}
        </button>
      )}
    </div>
  );
}

function ItemRow({ item, selected, onToggle, trailing }) {
  return (
    <div
      className={`flex items-center gap-3 px-3 py-2.5 rounded-lg border transition-colors ${
        selected ? "border-border bg-card" : "border-transparent bg-muted/30 opacity-50"
      }`}
    >
      <Checkbox checked={selected} onCheckedChange={onToggle} className="shrink-0" />
      <ItemInfo item={item} />
      {trailing}
    </div>
  );
}

function ItemInfo({ item }) {
  return (
    <div className="min-w-0 flex-1">
      <p className="text-sm font-medium truncate">{item.name}</p>
      <p className="text-[10px] text-muted-foreground truncate">
        {item.suggested_department}
        {item.base_unit && item.base_unit !== "each" && ` · ${item.base_unit}`}
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
