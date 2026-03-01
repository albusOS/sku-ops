import { useState, useEffect, useCallback, useRef } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { toast } from "sonner";
import { ArrowRight, ExternalLink } from "lucide-react";
import { Card } from "@tremor/react";
import { format } from "date-fns";
import { Button } from "@/components/ui/button";
import { API } from "@/lib/api";

/**
 * RecentTransactions — self-contained card that fetches and displays
 * recent withdrawals with itemized line items. Structure: withdrawal (parent) → items (children).
 */
export function RecentTransactions({ onProductStockHistory }) {
  const [withdrawals, setWithdrawals] = useState([]);
  const [loading, setLoading] = useState(false);
  const [timeRange, setTimeRange] = useState("24h");
  const [hasMore, setHasMore] = useState(false);
  const withdrawalsRef = useRef([]);
  withdrawalsRef.current = withdrawals;

  const fetchTransactions = useCallback(
    async (reset = true) => {
      setLoading(true);
      try {
        const offset = reset ? 0 : withdrawalsRef.current.length;
        const res = await axios.get(
          `${API}/dashboard/transactions?limit=20&offset=${offset}&time_range=${timeRange}`
        );
        const next = res.data.withdrawals || [];
        setHasMore(res.data.has_more ?? false);
        setWithdrawals((prev) => (reset ? next : [...prev, ...next]));
      } catch (err) {
        toast.error("Failed to load transactions");
      } finally {
        setLoading(false);
      }
    },
    [timeRange]
  );

  useEffect(() => {
    fetchTransactions(true);
  }, [fetchTransactions]);

  const handleLoadMore = () => fetchTransactions(false);

  return (
    <Card className="card-workshop p-6 mb-6" data-testid="recent-transactions-terminal">
      <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-200">
        <h2 className="text-lg font-semibold text-slate-900">Recent Transactions</h2>
        <Link
          to="/financials"
          className="text-sm text-slate-500 hover:text-orange-600 flex items-center gap-1"
        >
          View all <ArrowRight className="w-4 h-4" />
        </Link>
      </div>

      <div className="flex items-center gap-2 mb-4">
        {[
          { value: "today", label: "Today" },
          { value: "24h", label: "24h" },
          { value: "7d", label: "7 days" },
          { value: "all", label: "All" },
        ].map(({ value, label }) => (
          <button
            key={value}
            type="button"
            onClick={() => setTimeRange(value)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              timeRange === value
                ? "bg-slate-900 text-white shadow-sm"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {loading && withdrawals.length === 0 ? (
        <div className="rounded-xl bg-slate-50/80 border border-slate-200 p-8 text-center text-slate-500 text-sm">
          Loading…
        </div>
      ) : withdrawals.length === 0 ? (
        <div className="rounded-xl bg-slate-50/80 border border-slate-200 p-8 text-center text-slate-500 text-sm">
          No transactions
        </div>
      ) : (
        <>
          <div
            className="rounded-xl border border-slate-200 overflow-y-auto overflow-x-hidden bg-slate-50/50 p-2 space-y-3"
            style={{ maxHeight: 360 }}
          >
            {withdrawals.map((w) => (
              <WithdrawalBlock
                key={w.id}
                withdrawal={w}
                onProductStockHistory={onProductStockHistory}
              />
            ))}
          </div>
          {hasMore && (
            <Button
              variant="outline"
              size="sm"
              className="mt-3 w-full"
              onClick={handleLoadMore}
              disabled={loading}
            >
              {loading ? "Loading…" : "Load more"}
            </Button>
          )}
        </>
      )}
    </Card>
  );
}

function WithdrawalBlock({ withdrawal: w, onProductStockHistory }) {
  const statusClasses = {
    paid: "bg-emerald-100 text-emerald-700",
    invoiced: "bg-blue-100 text-blue-700",
    unpaid: "bg-amber-100 text-amber-700",
  };

  return (
    <div className="rounded-lg border border-slate-200 overflow-hidden bg-white">
      {/* Header: withdrawal summary */}
      <div className="flex items-center justify-between px-4 py-3 bg-slate-50 border-b border-slate-100">
        <div className="flex flex-col gap-0.5 min-w-0">
          <span className="text-slate-800 font-semibold truncate">
            {w.contractor_name || "—"}
          </span>
          <span className="text-slate-500 text-xs">
            {format(new Date(w.created_at), "MMM d, h:mm a")} · Job {w.job_id || "—"}
          </span>
        </div>
        <div className="flex flex-col items-end gap-1 shrink-0">
          <span className="text-lg font-bold text-slate-900 tabular-nums">
            ${(w.total || 0).toFixed(2)}
          </span>
          <span
            className={`text-xs px-2 py-0.5 rounded font-medium ${
              statusClasses[w.payment_status] || statusClasses.unpaid
            }`}
          >
            {w.payment_status}
          </span>
        </div>
      </div>

      {/* Items: nested under withdrawal */}
      <ul className="divide-y divide-slate-100">
        {(w.items || []).map((item, j) => (
          <WithdrawalItem
            key={`${w.id}-${j}`}
            item={item}
            onProductStockHistory={onProductStockHistory}
          />
        ))}
      </ul>
    </div>
  );
}

function WithdrawalItem({ item, onProductStockHistory }) {
  const priceStr =
    item.quantity === 1
      ? `$${(item.subtotal || 0).toFixed(2)}`
      : `${item.quantity} @ $${(item.price || 0).toFixed(2)}`;

  return (
    <li className="flex items-center justify-between gap-4 px-4 py-2 pl-6 group">
      <button
        type="button"
        onClick={() =>
          item.product_id &&
          onProductStockHistory?.({ id: item.product_id, sku: item.sku, name: item.name })
        }
        className="truncate text-left text-slate-700 hover:text-slate-900 text-sm flex-1 min-w-0"
        title="View stock history"
      >
        {item.name || item.sku}
      </button>
      <span className="shrink-0 flex items-center gap-2">
        <span className="text-slate-500 text-sm tabular-nums">{priceStr}</span>
        {item.product_id && (
          <Link
            to={`/inventory?search=${encodeURIComponent(item.sku || "")}`}
            className="p-1 rounded text-slate-400 hover:text-amber-600 hover:bg-amber-50 transition-colors opacity-60 hover:opacity-100"
            title="Inventory"
          >
            <ExternalLink className="w-3 h-3" />
          </Link>
        )}
      </span>
    </li>
  );
}
