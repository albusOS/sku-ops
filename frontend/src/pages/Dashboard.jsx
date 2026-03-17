import { useState, useMemo, useContext } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { RealtimeSyncContext } from "@/context/RealtimeSyncContext";
import { Truck, ShoppingCart, AlertTriangle, Flame } from "lucide-react";
import { format } from "date-fns";
import { valueFormatter } from "@/lib/chartConfig";
import { ROLES, DATE_PRESETS } from "@/lib/constants";
import { PageSkeleton } from "@/components/LoadingSkeleton";
import { QueryError } from "@/components/QueryError";
import { StatCard } from "@/components/StatCard";
import { StatusBadge } from "@/components/StatusBadge";
import { DateRangeFilter } from "@/components/DateRangeFilter";
import { ActionTile } from "@/components/ActionTile";
import { useDashboardStats } from "@/hooks/useDashboard";
import { dateToISO, endOfDayISO } from "@/lib/utils";
import { Panel, SectionHead } from "@/components/Panel";
import WorkflowGraph from "@/components/workflows/WorkflowGraph";

function getGreeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

function LivePulse({ connected }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
      <span className="relative flex h-2 w-2">
        <span
          className={`absolute inset-0 rounded-full ${connected ? "bg-success animate-live-pulse" : "bg-warning animate-pulse"}`}
        />
        <span
          className={`relative rounded-full h-2 w-2 ${connected ? "bg-success" : "bg-warning"}`}
        />
      </span>
      {connected ? "Live" : "Reconnecting"}
    </span>
  );
}

const POSummaryStrip = ({ summary = {} }) => {
  const statuses = [
    { key: "ordered", label: "On Order", bar: "bg-info", dot: "bg-info" },
    { key: "partial", label: "At Dock", bar: "bg-warning", dot: "bg-warning" },
    { key: "received", label: "Received", bar: "bg-success", dot: "bg-success" },
  ];
  const total = Object.values(summary).reduce((s, v) => s + (v?.total || 0), 0) || 1;
  return (
    <div>
      <div className="flex h-3 rounded-full overflow-hidden gap-0.5 mb-3 bg-muted">
        {statuses.map((s) => {
          const val = summary[s.key]?.total || 0;
          if (!val) return null;
          return (
            <div
              key={s.key}
              className={`${s.bar} transition-all`}
              style={{ width: `${(val / total) * 100}%` }}
              title={`${s.label}: ${valueFormatter(val)}`}
            />
          );
        })}
      </div>
      <div className="flex flex-wrap gap-x-5 gap-y-1.5">
        {statuses.map((s) => {
          const v = summary[s.key];
          if (!v) return null;
          return (
            <div key={s.key} className="flex items-center gap-1.5">
              <div className={`w-2 h-2 rounded-full ${s.dot}`} />
              <span className="text-xs text-muted-foreground">{s.label}</span>
              <span className="text-xs font-bold text-foreground tabular-nums">{v.count}</span>
              <span className="text-[10px] text-muted-foreground tabular-nums">
                ({valueFormatter(v.total)})
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

const Dashboard = () => {
  const { user } = useAuth();
  const { connected } = useContext(RealtimeSyncContext);

  const defaultRange = DATE_PRESETS[1].getValue();
  const [dateRange, setDateRange] = useState(defaultRange);

  const statsParams = useMemo(() => {
    const p = {};
    if (dateRange.from) p.start_date = dateToISO(dateRange.from);
    if (dateRange.to) p.end_date = endOfDayISO(dateRange.to);
    return p;
  }, [dateRange]);

  const { data: stats, isLoading, isError, error, refetch } = useDashboardStats(statsParams);

  const isContractor = user?.role === ROLES.CONTRACTOR;

  const rangeLabel = dateRange.from
    ? dateRange.to
      ? `${format(dateRange.from, "MMM d")} – ${format(dateRange.to, "MMM d")}`
      : format(dateRange.from, "MMM d, yyyy")
    : "All time";

  if (isLoading) return <PageSkeleton />;
  if (isError) return <QueryError error={error} onRetry={refetch} />;

  if (isContractor) {
    return (
      <div className="p-8" data-testid="dashboard-page">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-semibold text-foreground tracking-tight">
                {getGreeting()}, {user?.name?.split(" ")[0] || "there"}
              </h1>
              <LivePulse connected={connected} />
            </div>
            <p className="text-muted-foreground mt-1 text-sm">
              {user?.company || "Independent"} · {format(new Date(), "EEEE, MMM d")}
            </p>
          </div>
          <DateRangeFilter value={dateRange} onChange={setDateRange} />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <StatCard label="Total Orders" value={stats?.total_withdrawals || 0} />
          <StatCard
            label="Total Value"
            value={valueFormatter(stats?.total_spent || 0)}
            accent="emerald"
          />
          <StatCard
            label="Uninvoiced"
            value={valueFormatter(stats?.unpaid_balance || 0)}
            accent="amber"
          />
        </div>

        <Panel>
          <h2 className="text-base font-semibold text-foreground mb-4">Recent Orders</h2>
          {stats?.recent_withdrawals?.length > 0 ? (
            <div className="space-y-2">
              {stats.recent_withdrawals.map((w, i) => (
                <div key={w.id || i} className="p-4 bg-muted/80 rounded-lg border border-border/50">
                  <div className="flex items-center justify-between mb-2">
                    <p className="font-mono text-xs text-muted-foreground">Job: {w.job_id}</p>
                    <div className="flex items-center gap-3">
                      <span className="font-semibold text-foreground tabular-nums">
                        ${w.total?.toFixed(2)}
                      </span>
                      <StatusBadge status={w.invoice_id ? "invoiced" : "uninvoiced"} />
                    </div>
                  </div>
                  {w.items?.length > 0 && (
                    <div className="space-y-1 mt-2 border-t border-border/50 pt-2">
                      {w.items.map((item, j) => (
                        <div
                          key={j}
                          className="flex items-center justify-between text-xs text-muted-foreground"
                        >
                          <span className="truncate max-w-[200px]">
                            {item.name || item.product_name || "Item"}
                          </span>
                          <span className="tabular-nums text-muted-foreground">
                            {item.quantity} × ${(item.unit_price ?? 0).toFixed(2)}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12 text-muted-foreground">
              <ShoppingCart className="w-10 h-10 mx-auto mb-2 opacity-40" />
              <p className="text-sm">No orders in this range</p>
            </div>
          )}
        </Panel>
      </div>
    );
  }

  const hasPOs = stats?.po_summary && Object.keys(stats.po_summary).length > 0;
  const orderedPOCount = stats?.po_summary?.ordered?.count || 0;
  const partialPOCount = stats?.po_summary?.partial?.count || 0;
  const receivedPOCount = stats?.po_summary?.received?.count || 0;
  const openPOCount = orderedPOCount + partialPOCount;

  return (
    <div className="p-8" data-testid="dashboard-page">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold text-foreground tracking-tight">
              {getGreeting()}, {user?.name?.split(" ")[0] || "there"}
            </h1>
            <LivePulse connected={connected} />
          </div>
          <p className="text-muted-foreground mt-1 text-sm">
            {format(new Date(), "EEEE, MMM d")} · {rangeLabel}
          </p>
        </div>
        <DateRangeFilter value={dateRange} onChange={setDateRange} />
      </div>

      <div className="mb-8">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-base font-semibold text-foreground">Quick actions</h2>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          <ActionTile
            to="/pos"
            icon={ShoppingCart}
            title="Point of Sale"
            description="Process requests, issue materials, and track invoices."
          />
          <ActionTile
            to="/purchasing"
            icon={Truck}
            title="Purchasing"
            description="Import documents, track deliveries, and receive inventory."
          />
        </div>
      </div>

      <Panel className="mb-8">
        <SectionHead title="Workflows" />
        <WorkflowGraph />
      </Panel>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {hasPOs && (
          <Panel>
            <SectionHead
              title="Inbound delivery status"
              action={
                <Link
                  to="/purchasing"
                  className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1"
                >
                  All POs <Truck className="w-3 h-3" />
                </Link>
              }
            />
            <div className="mb-4 flex flex-wrap items-end gap-4">
              <div>
                <span className="text-lg font-bold text-foreground tabular-nums">
                  {openPOCount}
                </span>
                <span className="text-xs text-muted-foreground ml-2">still inbound</span>
              </div>
              <div className="text-xs text-muted-foreground">
                {orderedPOCount} on order · {partialPOCount} at dock · {receivedPOCount} received
              </div>
            </div>
            <POSummaryStrip summary={stats.po_summary} />
          </Panel>
        )}

        {stats?.low_stock_alerts?.length > 0 &&
          (() => {
            const hasOutOfStock = stats.low_stock_alerts.some((p) => p.quantity === 0);
            return (
              <Panel severity={hasOutOfStock ? "danger" : "warn"}>
                <SectionHead
                  title="Low stock items"
                  icon={hasOutOfStock ? Flame : AlertTriangle}
                  action={
                    <Link
                      to="/inventory?low_stock=1"
                      className="text-xs text-muted-foreground hover:text-foreground"
                    >
                      {stats.low_stock_count} items →
                    </Link>
                  }
                />
                <div className="space-y-1.5 max-h-[260px] overflow-auto -mx-6 px-6">
                  {stats.low_stock_alerts.map((product, i) => {
                    const isEmpty = product.quantity === 0;
                    const pct =
                      product.min_stock > 0
                        ? Math.min((product.quantity / product.min_stock) * 100, 100)
                        : 0;
                    return (
                      <Link
                        key={product.id || i}
                        to="/inventory"
                        className={`flex items-center gap-3 p-3 rounded-lg border transition-colors hover:bg-muted/60 ${
                          isEmpty
                            ? "border-destructive/25 bg-destructive/[0.04]"
                            : "border-warning/20 bg-warning/[0.02]"
                        }`}
                      >
                        <div
                          className={`w-1 h-9 rounded-full shrink-0 ${isEmpty ? "bg-destructive" : "bg-warning"}`}
                        />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between gap-2">
                            <div className="min-w-0">
                              <p className="text-sm text-foreground truncate">{product.name}</p>
                              <p className="font-mono text-[10px] text-muted-foreground">
                                {product.sku}
                              </p>
                            </div>
                            <div className="flex items-center gap-2 shrink-0">
                              {isEmpty ? (
                                <span className="inline-flex items-center gap-1 text-[10px] font-bold text-destructive bg-destructive/10 px-2 py-0.5 rounded-full">
                                  <span className="w-1.5 h-1.5 rounded-full bg-destructive animate-pulse" />
                                  Out
                                </span>
                              ) : (
                                <span className="text-xs font-bold tabular-nums text-warning">
                                  {product.quantity}
                                </span>
                              )}
                              <span className="text-[10px] text-muted-foreground/60 tabular-nums">
                                / {product.min_stock}
                              </span>
                            </div>
                          </div>
                          <div className="mt-1.5 h-1 bg-muted rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full transition-all ${isEmpty ? "bg-destructive" : "bg-warning"}`}
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                        </div>
                      </Link>
                    );
                  })}
                </div>
              </Panel>
            );
          })()}
      </div>
    </div>
  );
};

export default Dashboard;
