import { useState, useMemo, useContext } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { RealtimeSyncContext } from "@/context/RealtimeSyncContext";
import {
  Truck,
  ShoppingCart,
  AlertTriangle,
  Flame,
  Package,
  FileText,
  Clock,
  ScanBarcode,
  History,
  Send,
  DollarSign,
  TrendingUp,
  Activity,
  ClipboardList,
} from "lucide-react";
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
import { PortfolioCard } from "@/components/reports/cards/PortfolioCard";
import { ProductDetailModal } from "@/components/ProductDetailModal";

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
  const [selectedProduct, setSelectedProduct] = useState(null);

  const isContractor = user?.role === ROLES.CONTRACTOR;

  const rangeLabel = dateRange.from
    ? dateRange.to
      ? `${format(dateRange.from, "MMM d")} – ${format(dateRange.to, "MMM d")}`
      : format(dateRange.from, "MMM d, yyyy")
    : "All time";

  if (isLoading) return <PageSkeleton />;
  if (isError) return <QueryError error={error} onRetry={refetch} />;

  if (isContractor) {
    const pendingCount = stats?.pending_requests || 0;
    return (
      <div className="p-6 lg:p-8 max-w-6xl mx-auto" data-testid="dashboard-page">
        {/* Hero greeting */}
        <div className="relative rounded-2xl bg-gradient-to-br from-accent/10 via-surface to-surface border border-accent/20 p-6 lg:p-8 mb-8 overflow-hidden">
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_60%_50%_at_70%_-20%,hsl(var(--accent)/0.12),transparent)]" />
          <div className="relative flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-2xl lg:text-3xl font-bold text-foreground tracking-tight">
                {getGreeting()}, {user?.name?.split(" ")[0] || "there"}
              </h1>
              <p className="text-muted-foreground mt-1.5 text-sm flex items-center gap-2">
                <span>{user?.company || "Independent"}</span>
                <span className="text-border">·</span>
                <span>{format(new Date(), "EEEE, MMM d")}</span>
                <LivePulse connected={connected} />
              </p>
            </div>
            <DateRangeFilter value={dateRange} onChange={setDateRange} />
          </div>
        </div>

        {/* Quick actions */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-8">
          <Link
            to="/request-materials"
            className="group relative rounded-xl border border-border/80 bg-surface p-4 shadow-soft hover:border-accent/40 hover:shadow-md transition-all"
          >
            <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center mb-3 ring-1 ring-accent/20 group-hover:ring-accent/40 transition-colors">
              <ShoppingCart className="w-5 h-5 text-accent" />
            </div>
            <p className="font-semibold text-sm text-foreground">Request Materials</p>
            <p className="text-xs text-muted-foreground mt-0.5">Browse & order</p>
          </Link>
          <Link
            to="/scan"
            className="group relative rounded-xl border border-border/80 bg-surface p-4 shadow-soft hover:border-accent/40 hover:shadow-md transition-all"
          >
            <div className="w-10 h-10 rounded-xl bg-info/10 flex items-center justify-center mb-3 ring-1 ring-info/20 group-hover:ring-info/40 transition-colors">
              <ScanBarcode className="w-5 h-5 text-info" />
            </div>
            <p className="font-semibold text-sm text-foreground">Scan & Checkout</p>
            <p className="text-xs text-muted-foreground mt-0.5">Quick pickup</p>
          </Link>
          <Link
            to="/my-history"
            className="group relative rounded-xl border border-border/80 bg-surface p-4 shadow-soft hover:border-accent/40 hover:shadow-md transition-all"
          >
            <div className="w-10 h-10 rounded-xl bg-category-4/10 flex items-center justify-center mb-3 ring-1 ring-category-4/20 group-hover:ring-category-4/40 transition-colors">
              <History className="w-5 h-5 text-category-4" />
            </div>
            <p className="font-semibold text-sm text-foreground">My History</p>
            <p className="text-xs text-muted-foreground mt-0.5">Orders & returns</p>
          </Link>
          <Link
            to="/my-history"
            className="group relative rounded-xl border border-border/80 bg-surface p-4 shadow-soft hover:border-accent/40 hover:shadow-md transition-all"
          >
            <div className="w-10 h-10 rounded-xl bg-warning/10 flex items-center justify-center mb-3 ring-1 ring-warning/20 group-hover:ring-warning/40 transition-colors">
              <Send className="w-5 h-5 text-warning" />
            </div>
            <p className="font-semibold text-sm text-foreground">Pending</p>
            <p className="text-xs text-muted-foreground mt-0.5">
              {pendingCount > 0 ? `${pendingCount} awaiting` : "None right now"}
            </p>
          </Link>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <StatCard
            label="Total Orders"
            value={stats?.total_withdrawals || 0}
            icon={ShoppingCart}
          />
          <StatCard
            label="Total Value"
            value={valueFormatter(stats?.total_spent || 0)}
            accent="emerald"
            icon={Package}
          />
          <StatCard
            label="Uninvoiced"
            value={valueFormatter(stats?.unpaid_balance || 0)}
            accent="amber"
            icon={FileText}
          />
        </div>

        {/* Recent orders */}
        <Panel>
          <SectionHead
            title="Recent Orders"
            action={
              stats?.recent_withdrawals?.length > 0 ? (
                <Link
                  to="/my-history"
                  className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                >
                  View all →
                </Link>
              ) : null
            }
          />
          {stats?.recent_withdrawals?.length > 0 ? (
            <div className="space-y-3">
              {stats.recent_withdrawals.map((w, i) => (
                <Link
                  key={w.id || i}
                  to="/my-history"
                  className="block p-4 bg-muted/60 rounded-xl border border-border/50 hover:border-border hover:bg-muted/80 transition-all group"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2.5">
                      <div
                        className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
                          w.invoice_id ? "bg-info/10 text-info" : "bg-warning/10 text-warning"
                        }`}
                      >
                        {w.invoice_id ? (
                          <FileText className="w-4 h-4" />
                        ) : (
                          <Clock className="w-4 h-4" />
                        )}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs text-muted-foreground">
                            {(w.id || "").slice(0, 8).toUpperCase()}
                          </span>
                          <StatusBadge status={w.invoice_id ? "invoiced" : "uninvoiced"} />
                        </div>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          {w.created_at ? format(new Date(w.created_at), "MMM d") : ""}
                          {w.job_id ? ` · Job: ${w.job_id}` : ""}
                          {w.items?.length
                            ? ` · ${w.items.length} item${w.items.length !== 1 ? "s" : ""}`
                            : ""}
                        </p>
                      </div>
                    </div>
                    <span className="font-semibold text-foreground tabular-nums text-sm">
                      ${(w.total ?? 0).toFixed(2)}
                    </span>
                  </div>
                  {w.items?.length > 0 && (
                    <div className="ml-[42px] flex flex-wrap gap-1.5 mt-1">
                      {w.items.slice(0, 4).map((item, j) => (
                        <span
                          key={j}
                          className="inline-flex items-center text-[10px] text-muted-foreground bg-muted rounded-md px-2 py-0.5 border border-border/50"
                        >
                          {item.quantity}× {(item.name || item.product_name || "Item").slice(0, 20)}
                        </span>
                      ))}
                      {w.items.length > 4 && (
                        <span className="text-[10px] text-muted-foreground/60">
                          +{w.items.length - 4} more
                        </span>
                      )}
                    </div>
                  )}
                </Link>
              ))}
            </div>
          ) : (
            <div className="text-center py-12 text-muted-foreground">
              <ShoppingCart className="w-10 h-10 mx-auto mb-2 opacity-30" />
              <p className="text-sm font-medium">No orders in this period</p>
              <p className="text-xs mt-1">
                Head to{" "}
                <Link to="/request-materials" className="text-accent hover:underline">
                  Request Materials
                </Link>{" "}
                to get started
              </p>
            </div>
          )}
        </Panel>
      </div>
    );
  }

  const handleProductClick = (product) => {
    setSelectedProduct({
      id: product.sku_id || product.id,
      name: product.name,
      sku: product.sku,
    });
  };

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

      <div className="flex flex-col sm:flex-row sm:items-start gap-6 mb-8">
        <div className="shrink-0">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-base font-semibold text-foreground">Quick actions</h2>
          </div>
          <div className="flex gap-3">
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
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
        <StatCard
          label="Revenue"
          value={valueFormatter(stats?.range_revenue || 0)}
          icon={DollarSign}
          accent="emerald"
          href="/reports"
        />
        <StatCard
          label="Gross Profit"
          value={valueFormatter(stats?.range_gross_profit || 0)}
          note={stats?.range_margin_pct ? `${stats.range_margin_pct}% margin` : undefined}
          icon={TrendingUp}
          accent="blue"
          href="/reports"
        />
        <StatCard
          label="Transactions"
          value={stats?.range_transactions || 0}
          icon={ShoppingCart}
          accent="violet"
          href="/pos"
        />
        <StatCard
          label="Receivables"
          value={valueFormatter(stats?.unpaid_total || 0)}
          note="uninvoiced"
          icon={FileText}
          accent="amber"
          href="/pos"
        />
        <StatCard
          label="Days in Inventory"
          value={stats?.avg_days_in_inventory || 0}
          note="avg turnover"
          icon={Package}
          accent="orange"
          href="/inventory"
        />
      </div>

      <div className="mb-8">
        <WorkflowGraph stats={stats} />
      </div>

      {stats?.pending_requests?.length > 0 && (
        <Panel severity="warn" className="mb-8">
          <SectionHead
            title="Requests to fulfill"
            icon={ClipboardList}
            action={
              <Link
                to="/pos"
                className="text-xs text-muted-foreground hover:text-foreground transition-colors"
              >
                Process in POS →
              </Link>
            }
          />
          <div className="space-y-2">
            {stats.pending_requests.map((r, i) => {
              const itemCount = r.items?.length || 0;
              const totalQty = r.items?.reduce((sum, it) => sum + (it.quantity || 0), 0) || 0;
              return (
                <Link
                  key={r.id || i}
                  to="/pos"
                  className="flex items-center gap-3 p-3 rounded-lg border border-warning/20 bg-warning/[0.03] hover:bg-warning/[0.07] hover:border-warning/40 transition-all"
                >
                  <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 bg-warning/10 text-warning">
                    <ClipboardList className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-foreground truncate">
                      {r.contractor_name || "Unknown contractor"}
                    </p>
                    <p className="text-xs text-muted-foreground truncate">
                      {r.created_at ? format(new Date(r.created_at), "MMM d, h:mm a") : ""}
                      {` · ${itemCount} item${itemCount !== 1 ? "s" : ""}`}
                      {totalQty > 0 ? ` · ${totalQty} units` : ""}
                      {r.job_id ? ` · Job: ${r.job_id}` : ""}
                    </p>
                  </div>
                  {r.items?.length > 0 && (
                    <div className="hidden sm:flex flex-wrap gap-1 max-w-[200px] justify-end">
                      {r.items.slice(0, 3).map((item, j) => (
                        <span
                          key={j}
                          className="inline-flex items-center text-[10px] text-muted-foreground bg-muted rounded-md px-2 py-0.5 border border-border/50"
                        >
                          {item.quantity}× {(item.name || "Item").slice(0, 16)}
                        </span>
                      ))}
                      {r.items.length > 3 && (
                        <span className="text-[10px] text-muted-foreground/60">
                          +{r.items.length - 3} more
                        </span>
                      )}
                    </div>
                  )}
                </Link>
              );
            })}
          </div>
        </Panel>
      )}

      {stats?.recent_withdrawals?.length > 0 && (
        <Panel className="mb-8">
          <SectionHead
            title="Recent Activity"
            icon={Activity}
            action={
              <Link
                to="/pos"
                className="text-xs text-muted-foreground hover:text-foreground transition-colors"
              >
                View all →
              </Link>
            }
          />
          <div className="space-y-2">
            {stats.recent_withdrawals.map((w, i) => (
              <Link
                key={w.id || i}
                to="/pos"
                className="flex items-center gap-3 p-3 rounded-lg border border-border/50 bg-muted/40 hover:bg-muted/70 hover:border-border transition-all"
              >
                <div
                  className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
                    w.payment_status === "paid"
                      ? "bg-success/10 text-success"
                      : w.invoice_id
                        ? "bg-info/10 text-info"
                        : "bg-warning/10 text-warning"
                  }`}
                >
                  {w.payment_status === "paid" ? (
                    <DollarSign className="w-4 h-4" />
                  ) : w.invoice_id ? (
                    <FileText className="w-4 h-4" />
                  ) : (
                    <Clock className="w-4 h-4" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-foreground truncate">
                    {w.contractor_name || "Walk-in"}
                  </p>
                  <p className="text-xs text-muted-foreground truncate">
                    {w.created_at ? format(new Date(w.created_at), "MMM d, h:mm a") : ""}
                    {w.items?.length
                      ? ` · ${w.items.length} item${w.items.length !== 1 ? "s" : ""}`
                      : ""}
                  </p>
                </div>
                <div className="text-right shrink-0">
                  <p className="text-sm font-semibold text-foreground tabular-nums">
                    {valueFormatter(w.total ?? 0)}
                  </p>
                  <StatusBadge
                    status={
                      w.payment_status === "paid"
                        ? "paid"
                        : w.invoice_id
                          ? "invoiced"
                          : "uninvoiced"
                    }
                  />
                </div>
              </Link>
            ))}
          </div>
        </Panel>
      )}

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

      <div className="mb-6">
        <PortfolioCard dateParams={statsParams} onProductClick={handleProductClick} />
      </div>

      <ProductDetailModal
        product={selectedProduct}
        open={!!selectedProduct}
        onOpenChange={(open) => !open && setSelectedProduct(null)}
      />
    </div>
  );
};

export default Dashboard;
