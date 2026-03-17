import { useState, useEffect, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { X, Truck, CheckCircle, BoxIcon, Loader2, Package, ArrowRight } from "lucide-react";
import { StatusBadge } from "@/components/StatusBadge";
import { useMarkDelivery, useReceivePO } from "@/hooks/usePurchaseOrders";
import api, { getErrorMessage } from "@/lib/api-client";
import { ReviewFlow } from "./ReviewFlow";

function StatBox({ label, value, accent }) {
  return (
    <div
      className={`rounded-lg px-3 py-2 text-center ${accent ? "bg-warning/10 border border-warning/20" : "bg-muted/50 border border-border/40"}`}
    >
      <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-0.5">{label}</p>
      <p className={`font-mono font-semibold text-sm ${accent ? "text-warning" : ""}`}>{value}</p>
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
      <motion.div
        key="review-flow"
        initial={{ x: "100%", opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        exit={{ x: "100%", opacity: 0 }}
        transition={{ type: "spring", stiffness: 340, damping: 38 }}
        className="flex flex-col h-full bg-card border-l border-border/60 overflow-hidden shadow-xl"
        style={{ width: "100%" }}
      >
        <ReviewFlow
          items={reviewItems}
          mode="receive"
          onConfirm={handleConfirmReceive}
          onBack={() => setReviewItems(null)}
          submitting={acting === "receive"}
          confirmLabel="Add to Inventory"
        />
      </motion.div>
    );
  }

  return (
    <AnimatePresence>
      {open && po && (
        <motion.div
          key="po-panel"
          initial={{ x: "100%", opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: "100%", opacity: 0 }}
          transition={{ type: "spring", stiffness: 340, damping: 38 }}
          className="flex flex-col h-full bg-card border-l border-border/60 overflow-hidden shadow-xl"
          style={{ width: "100%" }}
        >
          {/* Header */}
          <div className="px-5 pt-5 pb-4 border-b border-border/50 shrink-0">
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-2.5 min-w-0">
                <div className="w-8 h-8 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center shrink-0">
                  <Package className="w-4 h-4 text-accent" />
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

            <div className="grid grid-cols-3 gap-2 mt-4">
              <StatBox
                label="Total"
                value={po.total > 0 ? `$${Number(po.total).toFixed(2)}` : "—"}
              />
              <StatBox
                label="Received"
                value={`${progress.arrived}/${items.length || po.item_count}`}
                accent={progress.arrived < items.length && items.length > 0}
              />
              <StatBox label="Complete" value={`${progress.pct}%`} />
            </div>

            {items.length > 0 && (
              <div className="mt-3 flex items-center gap-1.5">
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
                  label="In Stock"
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

          {/* Tabs */}
          <Tabs defaultValue="items" className="flex-1 flex flex-col min-h-0">
            <TabsList className="grid grid-cols-2 mx-5 mt-3 shrink-0">
              <TabsTrigger value="items" className="text-xs">
                Items ({items.length || po.item_count})
              </TabsTrigger>
              <TabsTrigger value="receive" className="text-xs">
                Receive
                {pendingItems.length > 0 && (
                  <span className="ml-1 bg-info/20 text-info text-[9px] px-1.5 py-0 rounded-full font-bold">
                    {pendingItems.length}
                  </span>
                )}
              </TabsTrigger>
            </TabsList>

            {/* Items tab */}
            <TabsContent value="items" className="flex-1 overflow-auto px-5 mt-3 pb-5">
              {loading ? (
                <div className="flex items-center justify-center py-12 text-muted-foreground">
                  <Loader2 className="w-5 h-5 animate-spin mr-2" />
                  Loading items…
                </div>
              ) : (
                <div className="space-y-4">
                  {orderedItems.length > 0 && (
                    <ItemGroup
                      label="Waiting for delivery"
                      icon={<BoxIcon className="w-3 h-3" />}
                      color="text-muted-foreground"
                      items={orderedItems}
                      selected={selectedOrdered}
                      onToggle={(id) => setSelectedOrdered((p) => ({ ...p, [id]: !p[id] }))}
                      action={
                        <Button
                          onClick={handleMarkDelivery}
                          disabled={acting === "delivery" || selectedOrderedCount === 0}
                          size="sm"
                          className="gap-1.5 w-full"
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
                    <div className="rounded-xl border border-info/30 bg-info/5 px-4 py-3">
                      <p className="text-sm font-medium">Items ready to receive</p>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        Switch to the <strong>Receive</strong> tab to confirm quantities and add to
                        inventory.
                      </p>
                    </div>
                  )}

                  {arrivedItems.length > 0 && (
                    <div className="space-y-1.5">
                      <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-success flex items-center gap-1.5">
                        <CheckCircle className="w-3 h-3" />
                        In Inventory ({arrivedItems.length})
                      </p>
                      {arrivedItems.map((item) => (
                        <div
                          key={item.id}
                          className="flex items-center gap-3 p-3 rounded-lg border border-success/30 bg-success/5"
                        >
                          <CheckCircle className="w-4 h-4 text-success shrink-0" />
                          <div className="min-w-0 flex-1">
                            <p className="text-sm font-medium truncate">{item.name}</p>
                            <p className="text-[10px] text-muted-foreground">
                              {item.suggested_department}
                              {item.original_sku && (
                                <>
                                  {" "}
                                  · <span className="font-mono">{item.original_sku}</span>
                                </>
                              )}
                            </p>
                          </div>
                          <span className="text-xs text-muted-foreground tabular-nums">
                            {item.delivered_qty ?? item.ordered_qty}
                          </span>
                          {item.cost > 0 && (
                            <span className="text-xs text-muted-foreground tabular-nums">
                              ${Number(item.cost).toFixed(2)}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  {items.length === 0 && !loading && (
                    <div className="text-center py-12 text-muted-foreground text-sm">
                      No items found
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
                </div>
              )}
            </TabsContent>

            {/* Receive tab */}
            <TabsContent value="receive" className="flex-1 overflow-auto px-5 mt-3 pb-5">
              {pendingItems.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <Truck className="w-8 h-8 text-muted-foreground/40 mb-3" />
                  <p className="text-sm text-muted-foreground">
                    {orderedItems.length > 0
                      ? "Mark items as delivered first"
                      : "All items have been received"}
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  <p className="text-xs text-muted-foreground">
                    Confirm the received quantities, then add to inventory.
                  </p>

                  {pendingItems.map((item) => {
                    const isSelected = selectedPending[item.id];
                    return (
                      <div
                        key={item.id}
                        className={`rounded-xl border p-3 transition-all ${
                          isSelected
                            ? "border-border bg-card"
                            : "border-border/50 bg-muted/20 opacity-60"
                        }`}
                      >
                        <div className="flex items-center gap-3">
                          <button
                            type="button"
                            onClick={() =>
                              setSelectedPending((p) => ({ ...p, [item.id]: !p[item.id] }))
                            }
                            className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-colors shrink-0 ${
                              isSelected ? "bg-accent border-accent" : "border-border"
                            }`}
                          >
                            {isSelected && (
                              <svg
                                className="w-3 h-3 text-white"
                                fill="currentColor"
                                viewBox="0 0 20 20"
                              >
                                <path
                                  fillRule="evenodd"
                                  d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                                  clipRule="evenodd"
                                />
                              </svg>
                            )}
                          </button>
                          <div className="min-w-0 flex-1">
                            <p className="text-sm font-medium truncate">{item.name}</p>
                            <p className="text-[10px] text-muted-foreground">
                              Ordered: {item.ordered_qty}
                              {item.cost > 0 && ` · $${Number(item.cost).toFixed(2)}`}
                            </p>
                          </div>
                          <div className="flex items-center gap-2 shrink-0">
                            <span className="text-[10px] text-muted-foreground">Qty</span>
                            <Input
                              type="number"
                              min="0"
                              step="any"
                              value={deliveredQtys[item.id] ?? item.ordered_qty ?? 1}
                              onChange={(e) =>
                                setDeliveredQtys((p) => ({ ...p, [item.id]: e.target.value }))
                              }
                              className="h-8 text-sm text-right w-20"
                            />
                          </div>
                        </div>
                      </div>
                    );
                  })}

                  <Button
                    onClick={handleOpenReceive}
                    disabled={acting === "receive" || selectedPendingCount === 0}
                    className="btn-primary gap-1.5 w-full mt-2"
                  >
                    {acting === "receive" ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <CheckCircle className="w-3.5 h-3.5" />
                    )}
                    Add to Inventory ({selectedPendingCount} item
                    {selectedPendingCount !== 1 ? "s" : ""})
                  </Button>
                </div>
              )}
            </TabsContent>
          </Tabs>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function ItemGroup({ label, icon, color, items, selected, onToggle, action }) {
  const selectedCount = items.filter((i) => selected[i.id]).length;

  return (
    <div className="space-y-1.5">
      <p
        className={`text-[10px] font-bold uppercase tracking-[0.12em] ${color} flex items-center gap-1.5`}
      >
        {icon}
        {label} ({items.length})
      </p>
      {items.map((item) => {
        const isSelected = selected[item.id];
        return (
          <div
            key={item.id}
            className={`flex items-center gap-3 p-3 rounded-lg border transition-all ${
              isSelected ? "border-border bg-card" : "border-border/50 bg-muted/20 opacity-60"
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
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium truncate">{item.name}</p>
              <p className="text-[10px] text-muted-foreground">
                {item.suggested_department}
                {item.base_unit && item.base_unit !== "each" && ` · ${item.base_unit}`}
                {item.original_sku && (
                  <>
                    {" "}
                    · <span className="font-mono">{item.original_sku}</span>
                  </>
                )}
              </p>
            </div>
            <span className="text-xs text-muted-foreground tabular-nums shrink-0">
              {item.ordered_qty}
            </span>
            {item.cost > 0 && (
              <span className="text-xs text-muted-foreground tabular-nums shrink-0">
                ${Number(item.cost).toFixed(2)}
              </span>
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
      </div>
      {action}
    </div>
  );
}
