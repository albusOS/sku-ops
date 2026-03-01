import { useState, useEffect, useRef, useCallback } from "react";
import { Link } from "react-router-dom";
import { useVirtualizer } from "@tanstack/react-virtual";
import axios from "axios";
import { toast } from "sonner";
import { useAuth } from "../context/AuthContext";
import {
  DollarSign,
  ShoppingCart,
  Package,
  AlertTriangle,
  Users,
  TrendingUp,
  Clock,
  ArrowRight,
  BarChart3,
} from "lucide-react";
import { Card, Metric, SparkAreaChart, AreaChart, Tracker } from "@tremor/react";
import { format } from "date-fns";
import { Button } from "@/components/ui/button";
import { API } from "@/lib/api";
import { valueFormatter } from "@/lib/chartConfig";
import { StockHistoryModal } from "@/components/StockHistoryModal";

function TransactionsVirtualList({ rows, parentRef, setStockHistoryProduct }) {
  const rowVirtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: (i) => (rows[i]?.type === "header" ? 44 : 36),
    overscan: 5,
  });
  return (
    <div
      style={{
        height: `${rowVirtualizer.getTotalSize()}px`,
        width: "100%",
        position: "relative",
      }}
    >
      {rowVirtualizer.getVirtualItems().map((virtualRow) => {
        const row = rows[virtualRow.index];
        if (!row) return null;
        if (row.type === "header") {
          const w = row.withdrawal;
          return (
            <div
              key={row.key}
              style={{
                position: "absolute",
                top: 0,
                left: 0,
                width: "100%",
                transform: `translateY(${virtualRow.start}px)`,
              }}
              className="flex items-center justify-between px-4 py-2 hover:bg-slate-100/80 border-b border-slate-100"
            >
              <div className="flex items-center gap-3 min-w-0">
                <span className="text-slate-500 shrink-0 text-xs">
                  {format(new Date(w.created_at), "MMM d HH:mm")}
                </span>
                <span className="text-slate-700 truncate">{w.contractor_name || "—"}</span>
                <span className="text-slate-500 text-xs">Job: {w.job_id || "—"}</span>
              </div>
              <div className="flex items-center gap-3 shrink-0">
                <span className="text-slate-900 font-semibold">${(w.total || 0).toFixed(2)}</span>
                <span
                  className={`text-xs px-2 py-0.5 rounded ${
                    w.payment_status === "paid"
                      ? "bg-emerald-500/15 text-emerald-700"
                      : w.payment_status === "invoiced"
                      ? "bg-blue-500/15 text-blue-700"
                      : "bg-amber-500/15 text-amber-700"
                  }`}
                >
                  {w.payment_status}
                </span>
              </div>
            </div>
          );
        }
        const { item } = row;
        return (
          <div
            key={row.key}
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              width: "100%",
              transform: `translateY(${virtualRow.start}px)`,
            }}
            className="flex items-center justify-between px-4 py-1.5 pl-8 text-xs text-slate-600 bg-slate-50/60 group"
          >
            <button
              type="button"
              onClick={() => item.product_id && setStockHistoryProduct({ id: item.product_id, sku: item.sku, name: item.name })}
              className="truncate text-left hover:text-emerald-600 transition-colors flex-1 min-w-0"
              title="View stock history"
            >
              {item.name || item.sku}
            </button>
            <span className="shrink-0 flex items-center gap-2">
              <span>
                {item.quantity} × ${(item.price || 0).toFixed(2)} = ${(item.subtotal || 0).toFixed(2)}
              </span>
              {item.product_id && (
                <Link
                  to={`/inventory?search=${encodeURIComponent(item.sku || "")}`}
                  className="text-slate-500 hover:text-amber-600 opacity-0 group-hover:opacity-100 transition-opacity"
                  title="View in Inventory"
                >
                  ↗
                </Link>
              )}
            </span>
          </div>
        );
      })}
    </div>
  );
}

const Dashboard = () => {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  const isContractor = user?.role === "contractor";
  const isAdmin = user?.role === "admin";
  const showTransactionsTerminal = isAdmin || user?.role === "warehouse_manager";
  const [stockHistoryProduct, setStockHistoryProduct] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [transactionsLoading, setTransactionsLoading] = useState(false);
  const [transactionsOffset, setTransactionsOffset] = useState(0);
  const [timeRange, setTimeRange] = useState("24h");
  const [hasMore, setHasMore] = useState(false);
  const transactionsScrollRef = useRef(null);
  const transactionsRef = useRef([]);
  transactionsRef.current = transactions;

  useEffect(() => {
    fetchStats();
    if (!isContractor) {
      seedDepartments();
    }
  }, []);

  const fetchTransactions = useCallback(
    async (reset = true) => {
      if (!showTransactionsTerminal) return;
      setTransactionsLoading(true);
      try {
        const offset = reset ? 0 : transactionsRef.current.length;
        const res = await axios.get(
          `${API}/dashboard/transactions?limit=20&offset=${offset}&time_range=${timeRange}`
        );
        const next = res.data.withdrawals || [];
        setHasMore(res.data.has_more ?? false);
        setTransactions((prev) => (reset ? next : [...prev, ...next]));
      } catch (err) {
        toast.error("Failed to load transactions");
      } finally {
        setTransactionsLoading(false);
      }
    },
    [showTransactionsTerminal, timeRange]
  );

  useEffect(() => {
    if (showTransactionsTerminal) fetchTransactions(true);
  }, [showTransactionsTerminal, timeRange]);

  const seedDepartments = async () => {
    try {
      await axios.post(`${API}/seed/departments`);
    } catch (error) {
      // Ignore - may already be seeded
    }
  };

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API}/dashboard/stats`);
      setStats(response.data);
    } catch (error) {
      console.error("Error fetching stats:", error);
      toast.error("Failed to load dashboard data");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[50vh]">
        <div className="flex items-center gap-3 text-slate-500">
          <div className="w-5 h-5 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
          <span className="font-medium">Loading dashboard…</span>
        </div>
      </div>
    );
  }

  // Contractor Dashboard
  if (isContractor) {
    return (
      <div className="p-8" data-testid="dashboard-page">
        <div className="mb-8">
          <h1 className="text-2xl font-semibold text-slate-900 tracking-tight">
            Dashboard
          </h1>
          <p className="text-slate-500 mt-1 text-sm">
            Welcome back, {user?.name} · {user?.company || "Independent"}
          </p>
        </div>

        {/* Contractor Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <Card className="card-workshop">
            <Metric>{stats?.total_withdrawals || 0}</Metric>
            <p className="text-sm text-slate-500 font-medium mt-1">Total Withdrawals</p>
          </Card>
          <Card className="card-workshop">
            <Metric color="emerald">{valueFormatter(stats?.total_spent || 0)}</Metric>
            <p className="text-sm text-slate-500 font-medium mt-1">Total Value</p>
          </Card>
          <Card className="card-workshop">
            <Metric color="amber">{valueFormatter(stats?.unpaid_balance || 0)}</Metric>
            <p className="text-sm text-slate-500 font-medium mt-1">Unpaid Balance</p>
          </Card>
        </div>

        {/* Recent Withdrawals */}
        <Card className="card-elevated p-6">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">
            Recent Withdrawals
          </h2>
          {stats?.recent_withdrawals?.length > 0 ? (
            <div className="space-y-3">
              {stats.recent_withdrawals.map((w, index) => (
                <div
                  key={w.id || index}
                  className="flex items-center justify-between p-4 bg-slate-50/80 rounded-xl border border-slate-100"
                >
                  <div>
                    <p className="font-mono text-xs text-slate-500">
                      Job: {w.job_id}
                    </p>
                    <p className="text-sm text-slate-600 mt-0.5">
                      {w.items?.length || 0} items ·{" "}
                      {w.service_address?.slice(0, 30)}...
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="font-semibold text-slate-900">
                      ${w.total?.toFixed(2)}
                    </p>
                    <span
                      className={
                        w.payment_status === "paid"
                          ? "badge-success"
                          : "badge-warning"
                      }
                    >
                      {w.payment_status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12 text-slate-400">
              <ShoppingCart className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p className="font-medium">No withdrawals yet</p>
            </div>
          )}
        </Card>
      </div>
    );
  }

  // Warehouse Manager / Admin Dashboard
  const revenueChartData = stats?.revenue_by_day?.length
    ? stats.revenue_by_day.map((d) => ({
        date: format(new Date(d.date), "MMM d"),
        Revenue: d.revenue,
      }))
    : [];

  const displayCards = [
    {
      label: "Today's Activity",
      value: valueFormatter(stats?.today_revenue || 0),
      subtext: `${stats?.today_transactions || 0} withdrawals`,
      color: "emerald",
      hasSpark: true,
    },
    {
      label: "This Week",
      value: valueFormatter(stats?.week_revenue || 0),
      subtext: "Last 7 days",
      color: "blue",
      hasSpark: true,
    },
    {
      label: "Total Products",
      value: stats?.total_products || 0,
      color: "slate",
      adminOnly: false,
    },
    {
      label: "Low Stock Items",
      value: stats?.low_stock_count || 0,
      color: "amber",
      adminOnly: false,
    },
    {
      label: "Contractors",
      value: stats?.total_contractors || 0,
      color: "violet",
      adminOnly: true,
    },
    {
      label: "Total Vendors",
      value: stats?.total_vendors || 0,
      color: "slate",
      adminOnly: false,
    },
  ].filter((card) => !card.adminOnly || isAdmin);

  const transactionRows = transactions.flatMap((w) => [
    { type: "header", withdrawal: w, key: w.id },
    ...(w.items || []).map((item, j) => ({ type: "item", withdrawal: w, item, key: `${w.id}-${j}` })),
  ]);

  const trackerData =
    stats?.recent_withdrawals?.map((w, i) => ({
      key: w.id || i,
      color: w.payment_status === "paid" ? "emerald" : "amber",
      tooltip: `${w.contractor_name || "Unknown"} · ${valueFormatter(w.total)} · ${w.payment_status}`,
    })) || [];

  return (
    <div className="p-8" data-testid="dashboard-page">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-slate-900 tracking-tight">
          Dashboard
        </h1>
        <p className="text-slate-500 mt-1 text-sm">
          Welcome back, {user?.name}
        </p>
      </div>

      {isAdmin && stats?.unpaid_total > 0 && (
        <Link to="/financials">
          <div className="card-workshop p-5 mb-6 border-rose-200 bg-rose-50/50 hover:border-rose-300 cursor-pointer transition-colors">
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-rose-100 rounded-xl flex items-center justify-center">
                  <AlertTriangle className="w-5 h-5 text-rose-600" />
                </div>
                <div>
                  <p className="font-semibold text-rose-800">Outstanding Balance</p>
                  <p className="text-sm text-rose-600">Unpaid contractor withdrawals — View all</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <p className="text-xl font-semibold text-rose-600">
                  ${(stats?.unpaid_total || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}
                </p>
                <ArrowRight className="w-5 h-5 text-rose-500" />
              </div>
            </div>
          </div>
        </Link>
      )}

      <div
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-6 mb-8"
        data-testid="stats-grid"
      >
        {displayCards.map((stat, index) => (
          <Card
            key={index}
            className="card-workshop animate-slide-in"
            style={{ animationDelay: `${index * 50}ms` }}
          >
            {stat.hasSpark && revenueChartData.length > 0 ? (
              <>
                <Metric color={stat.color}>{stat.value}</Metric>
                <p className="text-sm text-slate-500 font-medium mt-1">{stat.label}</p>
                {stat.subtext && <p className="text-xs text-slate-400 mt-2">{stat.subtext}</p>}
                <SparkAreaChart
                  data={revenueChartData}
                  index="date"
                  categories={["Revenue"]}
                  colors={[stat.color]}
                  className="mt-4 h-12"
                />
              </>
            ) : (
              <>
                <Metric color={stat.color}>{stat.value}</Metric>
                <p className="text-sm text-slate-500 font-medium mt-1">{stat.label}</p>
                {stat.subtext && <p className="text-xs text-slate-400 mt-2">{stat.subtext}</p>}
              </>
            )}
          </Card>
        ))}
      </div>

      {/* Revenue chart */}
      {revenueChartData.length > 0 && (
        <Card className="card-workshop p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-slate-900">Revenue — Last 7 Days</h2>
            <Link to="/reports" className="text-sm text-slate-500 hover:text-orange-600 flex items-center gap-1">
              View reports <BarChart3 className="w-4 h-4" />
            </Link>
          </div>
          <AreaChart
            data={revenueChartData}
            index="date"
            categories={["Revenue"]}
            colors={["orange"]}
            valueFormatter={valueFormatter}
            showLegend={false}
            className="h-48"
          />
        </Card>
      )}

      {showTransactionsTerminal && (
        <Card className="card-workshop p-6 mb-6" data-testid="recent-transactions-terminal">
          <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-200">
            <h2 className="text-lg font-semibold text-slate-900">Recent Transactions</h2>
            <Link to="/financials" className="text-sm text-slate-500 hover:text-orange-600 flex items-center gap-1">
              View all <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
          <div className="flex items-center gap-2 mb-3">
            {["today", "24h", "7d", "all"].map((r) => (
              <button
                key={r}
                type="button"
                onClick={() => setTimeRange(r)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  timeRange === r
                    ? "bg-slate-900 text-white shadow-sm"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                {r === "today" ? "Today" : r === "24h" ? "24h" : r === "7d" ? "7 days" : "All"}
              </button>
            ))}
          </div>
          {transactionsLoading && transactions.length === 0 ? (
            <div className="rounded-xl bg-slate-50/80 border border-slate-200 p-8 text-center text-slate-500 text-sm">
              Loading…
            </div>
          ) : transactions.length === 0 ? (
            <div className="rounded-xl bg-slate-50/80 border border-slate-200 p-8 text-center text-slate-500 text-sm">
              No transactions
            </div>
          ) : (
            <>
              <div
                ref={transactionsScrollRef}
                className="rounded-xl bg-slate-50/80 border border-slate-200 text-sm overflow-y-auto"
                style={{ height: 320 }}
              >
                <div className="p-3 text-slate-500 text-xs border-b border-slate-200">
                  # withdrawals (itemized) · Click item for stock history · ↗ = Inventory
                </div>
                <TransactionsVirtualList
                  rows={transactionRows}
                  parentRef={transactionsScrollRef}
                  setStockHistoryProduct={setStockHistoryProduct}
                />
              </div>
              {hasMore && (
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-3 w-full"
                  onClick={() => fetchTransactions(false)}
                  disabled={transactionsLoading}
                >
                  {transactionsLoading ? "Loading…" : "Load more"}
                </Button>
              )}
            </>
          )}
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="card-workshop p-6" data-testid="recent-sales-card">
          <div className="flex items-center justify-between mb-5 pb-4 border-b border-slate-200">
            <h2 className="text-lg font-semibold text-slate-900">Recent Withdrawals</h2>
            <Link to="/financials" className="text-sm text-slate-500 hover:text-orange-600 flex items-center gap-1">
              View all <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
          {trackerData.length > 0 ? (
            <div className="space-y-4">
              <Tracker data={trackerData} className="mt-2" />
              <div className="text-xs text-slate-500 mt-3">
                Hover over blocks for details · Green = paid, Amber = unpaid
              </div>
            </div>
          ) : (
            <div className="text-center py-12 text-slate-400">
              <ShoppingCart className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p className="font-medium">No withdrawals yet</p>
            </div>
          )}
        </Card>

        <Card className="card-workshop p-6" data-testid="low-stock-card">
          <div className="flex items-center justify-between mb-5 pb-4 border-b border-slate-200">
            <h2 className="text-lg font-semibold text-slate-900">Low Stock Alerts</h2>
            <Link to="/inventory?low_stock=1" className="text-sm text-slate-500 hover:text-orange-600 flex items-center gap-1">
              View in Inventory <ArrowRight className="w-4 h-4" />
            </Link>
          </div>

          {stats?.low_stock_alerts?.length > 0 ? (
            <div className="space-y-3">
              {stats.low_stock_alerts.map((product, index) => (
                <Link key={product.id || index} to="/inventory" className="block">
                  <div className="flex items-center justify-between p-4 bg-amber-50/80 rounded-xl border border-amber-200/80 hover:border-amber-300 transition-colors">
                    <div>
                      <p className="font-mono text-xs text-amber-700">{product.sku}</p>
                      <p className="font-medium text-slate-800">{product.name}</p>
                    </div>
                    <div className="text-right flex items-center gap-2">
                      <span className="badge-warning">{product.quantity} left</span>
                      <p className="text-xs text-slate-500">Min: {product.min_stock}</p>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <div className="text-center py-12 text-slate-400">
              <Package className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p className="font-medium">All products well stocked</p>
            </div>
          )}
        </Card>
      </div>

      {(isAdmin || user?.role === "warehouse_manager") && (
        <StockHistoryModal
          product={stockHistoryProduct}
          open={!!stockHistoryProduct}
          onOpenChange={(open) => !open && setStockHistoryProduct(null)}
        />
      )}
    </div>
  );
};

export default Dashboard;
