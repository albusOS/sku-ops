import { useState, useMemo } from "react";
import { useAuth } from "@/context/AuthContext";
import {
  Package,
  MapPin,
  ChevronDown,
  Send,
  Clock,
  FileText,
  X,
  RotateCcw,
  Search,
  ShoppingCart,
  TrendingUp,
} from "lucide-react";
import { format } from "date-fns";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PageSkeleton } from "@/components/LoadingSkeleton";
import { QueryError } from "@/components/QueryError";
import { StatCard } from "@/components/StatCard";
import { StatusBadge } from "@/components/StatusBadge";
import { DateRangeFilter } from "@/components/DateRangeFilter";
import { CreateReturnModal } from "@/components/operations/CreateReturnModal";
import { useWithdrawals } from "@/hooks/useWithdrawals";
import { useReturns } from "@/hooks/useReturns";
import { useMaterialRequests } from "@/hooks/useMaterialRequests";
import { dateToISO, endOfDayISO } from "@/lib/utils";

const PAYMENT_FILTERS = [
  { value: "", label: "All" },
  { value: "unpaid", label: "Uninvoiced" },
  { value: "invoiced", label: "Invoiced" },
];

const MyHistory = () => {
  const { user } = useAuth();
  const [dateRange, setDateRange] = useState({ from: null, to: null });
  const [paymentStatus, setPaymentStatus] = useState("");
  const [expandedId, setExpandedId] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");

  const params = useMemo(
    () => ({
      start_date: dateToISO(dateRange.from),
      end_date: endOfDayISO(dateRange.to),
      payment_status: paymentStatus || undefined,
    }),
    [dateRange, paymentStatus],
  );

  const [returnWithdrawalId, setReturnWithdrawalId] = useState(null);

  const {
    data: withdrawals = [],
    isLoading: wdLoading,
    isError: wdError,
    error: wdErr,
    refetch: wdRefetch,
  } = useWithdrawals(params);
  const { data: allRequests = [], isLoading: reqLoading } = useMaterialRequests();
  const { data: returns = [] } = useReturns(params);

  const returnsByWithdrawal = useMemo(() => {
    const map = {};
    for (const r of returns) {
      if (!map[r.withdrawal_id]) map[r.withdrawal_id] = [];
      map[r.withdrawal_id].push(r);
    }
    return map;
  }, [returns]);

  const filteredWithdrawals = useMemo(() => {
    if (!searchQuery.trim()) return withdrawals;
    const q = searchQuery.toLowerCase();
    return withdrawals.filter(
      (w) =>
        w.id?.toLowerCase().includes(q) ||
        w.job_id?.toLowerCase().includes(q) ||
        w.service_address?.toLowerCase().includes(q) ||
        w.items?.some((i) => i.name?.toLowerCase().includes(q) || i.sku?.toLowerCase().includes(q)),
    );
  }, [withdrawals, searchQuery]);

  const requests = allRequests.filter?.((r) => r.status === "pending") || [];
  const totalSpent = withdrawals.reduce((sum, w) => sum + (w.total || 0), 0);
  const totalReturned = returns.reduce((sum, r) => sum + (r.total || 0), 0);
  const totalUninvoiced = withdrawals
    .filter((w) => !w.invoice_id)
    .reduce((sum, w) => sum + (w.total || 0), 0);

  const hasFilters = dateRange.from || dateRange.to || paymentStatus || searchQuery;

  if (wdLoading || reqLoading) return <PageSkeleton />;
  if (wdError) return <QueryError error={wdErr} onRetry={wdRefetch} />;

  return (
    <div className="p-6 lg:p-8 max-w-5xl mx-auto" data-testid="my-history-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">My History</h1>
          <p className="text-muted-foreground mt-1 text-sm">
            {user?.name} · {user?.company || "Independent"}
          </p>
        </div>
        <DateRangeFilter value={dateRange} onChange={setDateRange} />
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
        <StatCard label="Total Orders" value={withdrawals.length} icon={ShoppingCart} />
        <StatCard
          label="Total Value"
          value={`$${totalSpent.toLocaleString("en-US", { minimumFractionDigits: 2 })}`}
          accent="emerald"
          icon={TrendingUp}
        />
        <StatCard
          label="Uninvoiced"
          value={`$${totalUninvoiced.toLocaleString("en-US", { minimumFractionDigits: 2 })}`}
          accent="amber"
          icon={Clock}
        />
        <StatCard
          label="Returns"
          value={
            returns.length > 0
              ? `-$${totalReturned.toLocaleString("en-US", { minimumFractionDigits: 2 })}`
              : "$0.00"
          }
          accent="rose"
          icon={RotateCcw}
        />
      </div>

      {/* Pending requests */}
      {requests.length > 0 && (
        <div className="mb-8">
          <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-muted-foreground mb-3">
            Pending Requests
          </p>
          <div className="space-y-2">
            {requests.map((r) => {
              const itemCount = (r.items || []).reduce((s, i) => s + (i.quantity || 0), 0);
              return (
                <div
                  key={r.id}
                  className="bg-card border border-warning/20 rounded-xl p-4 flex items-center justify-between shadow-soft"
                  data-testid={`pending-request-${r.id}`}
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-warning/10 flex items-center justify-center ring-1 ring-warning/20">
                      <Send className="w-4 h-4 text-warning" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-foreground">
                        Pickup order — awaiting fulfillment
                      </p>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {itemCount} items · {new Date(r.created_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  <StatusBadge status="pending" />
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Orders section */}
      <div data-testid="withdrawals-list">
        {/* Filter bar */}
        <div className="flex flex-col sm:flex-row sm:items-center gap-3 mb-4">
          <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-muted-foreground shrink-0">
            Orders
          </p>
          <div className="flex flex-1 flex-wrap items-center gap-2">
            {/* Payment status chips */}
            <div className="flex items-center gap-1 bg-muted rounded-lg p-0.5">
              {PAYMENT_FILTERS.map((f) => (
                <button
                  key={f.value}
                  onClick={() => setPaymentStatus(f.value)}
                  className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                    paymentStatus === f.value
                      ? "bg-card text-foreground shadow-sm"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>

            {/* Search within orders */}
            <div className="relative flex-1 min-w-[180px]">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground pointer-events-none" />
              <Input
                type="text"
                placeholder="Search orders…"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 h-8 text-xs bg-muted/50"
              />
            </div>

            {hasFilters && (
              <button
                type="button"
                onClick={() => {
                  setDateRange({ from: null, to: null });
                  setPaymentStatus("");
                  setSearchQuery("");
                }}
                className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors shrink-0"
              >
                <X className="w-3 h-3" /> Clear
              </button>
            )}
          </div>
        </div>

        {/* Orders list */}
        {filteredWithdrawals.length === 0 ? (
          <div className="bg-card border border-border rounded-xl p-16 text-center shadow-soft">
            <div className="w-14 h-14 rounded-2xl bg-muted flex items-center justify-center mx-auto mb-4">
              <Package className="w-7 h-7 text-muted-foreground" />
            </div>
            <p className="font-medium text-foreground">
              {hasFilters ? "No orders match these filters" : "No orders yet"}
            </p>
            {!hasFilters && (
              <p className="text-sm text-muted-foreground mt-1.5">
                Submit a pickup order or visit the yard to check out materials
              </p>
            )}
            {hasFilters && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setDateRange({ from: null, to: null });
                  setPaymentStatus("");
                  setSearchQuery("");
                }}
                className="mt-4"
              >
                Clear filters
              </Button>
            )}
          </div>
        ) : (
          <div className="space-y-2">
            {filteredWithdrawals.map((w) => {
              const isExpanded = expandedId === w.id;
              const wReturns = returnsByWithdrawal[w.id];
              return (
                <div
                  key={w.id}
                  className={`bg-card border rounded-xl shadow-soft overflow-hidden transition-all ${
                    isExpanded ? "border-border ring-1 ring-border/50" : "border-border/80"
                  }`}
                  data-testid={`withdrawal-${w.id}`}
                >
                  <button
                    className="w-full p-4 flex items-center justify-between text-left hover:bg-muted/40 transition-colors"
                    onClick={() => setExpandedId(isExpanded ? null : w.id)}
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <StatusIcon status={w.invoice_id ? "invoiced" : "uninvoiced"} />
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs text-muted-foreground">
                            {w.id.slice(0, 8).toUpperCase()}
                          </span>
                          <StatusBadge status={w.invoice_id ? "invoiced" : "uninvoiced"} />
                          {wReturns?.length > 0 && (
                            <span className="inline-flex items-center gap-1 text-[10px] text-destructive bg-destructive/10 px-1.5 py-0.5 rounded-full">
                              <RotateCcw className="w-2.5 h-2.5" />
                              {wReturns.length}
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          {format(new Date(w.created_at), "MMM d, yyyy")}
                          {w.job_id ? ` · Job: ${w.job_id}` : ""}
                          {w.items?.length
                            ? ` · ${w.items.length} item${w.items.length !== 1 ? "s" : ""}`
                            : ""}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3 shrink-0">
                      <span className="font-semibold text-foreground tabular-nums">
                        ${(w.total || 0).toFixed(2)}
                      </span>
                      <ChevronDown
                        className={`w-4 h-4 text-muted-foreground transition-transform duration-200 ${isExpanded ? "rotate-180" : ""}`}
                      />
                    </div>
                  </button>

                  {isExpanded && (
                    <div className="border-t border-border/50 p-4 bg-muted/30">
                      {w.service_address && (
                        <div className="flex items-center gap-2 text-xs text-muted-foreground mb-3 bg-card rounded-lg px-3 py-2 border border-border/50">
                          <MapPin className="w-3.5 h-3.5 shrink-0" />
                          {w.service_address}
                        </div>
                      )}

                      {/* Line items */}
                      <div className="space-y-1.5 mb-4">
                        {w.items?.map((item, idx) => (
                          <div
                            key={idx}
                            className="flex items-center justify-between p-3 bg-card rounded-lg border border-border/50"
                          >
                            <div className="min-w-0">
                              <p className="font-mono text-[10px] text-muted-foreground">
                                {item.sku}
                              </p>
                              <p className="text-sm text-foreground">{item.name}</p>
                            </div>
                            <div className="text-right text-sm shrink-0 ml-3">
                              <p className="text-muted-foreground tabular-nums">
                                {item.quantity}
                                {item.unit && item.unit !== "each" ? ` ${item.unit}` : ""} × $
                                {(item.price || 0).toFixed(2)}
                              </p>
                              <p className="font-semibold text-foreground tabular-nums">
                                ${(item.subtotal || 0).toFixed(2)}
                              </p>
                            </div>
                          </div>
                        ))}
                      </div>

                      {/* Totals */}
                      <div className="bg-card rounded-lg border border-border/50 p-3 space-y-1 text-sm">
                        <div className="flex justify-between text-muted-foreground">
                          <span>Subtotal</span>
                          <span className="tabular-nums">${(w.subtotal || 0).toFixed(2)}</span>
                        </div>
                        <div className="flex justify-between text-muted-foreground">
                          <span>Tax</span>
                          <span className="tabular-nums">${(w.tax || 0).toFixed(2)}</span>
                        </div>
                        <div className="flex justify-between font-semibold text-foreground pt-1 border-t border-border/50">
                          <span>Total</span>
                          <span className="tabular-nums">${(w.total || 0).toFixed(2)}</span>
                        </div>
                      </div>

                      {w.notes && (
                        <div className="mt-3 p-3 bg-warning/5 rounded-lg border border-warning/20 text-xs text-foreground">
                          <span className="font-medium text-warning">Note:</span> {w.notes}
                        </div>
                      )}

                      {/* Returns */}
                      {wReturns?.length > 0 && (
                        <div className="mt-4 pt-3 border-t border-border/50">
                          <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-muted-foreground mb-2">
                            Returns
                          </p>
                          <div className="space-y-2">
                            {wReturns.map((ret) => (
                              <div
                                key={ret.id}
                                className="flex items-center justify-between p-3 bg-destructive/5 rounded-lg border border-destructive/15"
                              >
                                <div className="flex items-center gap-2.5">
                                  <div className="w-8 h-8 rounded-lg bg-destructive/10 flex items-center justify-center">
                                    <RotateCcw className="w-3.5 h-3.5 text-destructive" />
                                  </div>
                                  <div>
                                    <p className="text-xs font-medium text-foreground capitalize">
                                      {(ret.reason || "other").replace(/_/g, " ")}
                                    </p>
                                    <p className="text-[10px] text-muted-foreground">
                                      {format(new Date(ret.created_at), "MMM d, yyyy")} ·{" "}
                                      {ret.items?.length || 0} items
                                    </p>
                                  </div>
                                </div>
                                <span className="font-semibold tabular-nums text-destructive text-sm">
                                  -${(ret.total || 0).toFixed(2)}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Actions */}
                      <div className="mt-4 pt-3 border-t border-border/50 flex justify-end">
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            setReturnWithdrawalId(w.id);
                          }}
                          className="inline-flex items-center gap-1.5 text-xs font-medium text-destructive/80 hover:text-destructive transition-colors px-3 py-1.5 rounded-lg hover:bg-destructive/5"
                        >
                          <RotateCcw className="w-3.5 h-3.5" />
                          Return items
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      <CreateReturnModal
        open={!!returnWithdrawalId}
        onOpenChange={(open) => !open && setReturnWithdrawalId(null)}
        prefillWithdrawalId={returnWithdrawalId}
      />
    </div>
  );
};

function StatusIcon({ status }) {
  const styles = {
    invoiced: "bg-info/10 text-info ring-info/20",
    uninvoiced: "bg-warning/10 text-warning ring-warning/20",
  };
  const Icon = status === "invoiced" ? FileText : Clock;
  return (
    <div
      className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ring-1 ${styles[status] || styles.uninvoiced}`}
    >
      <Icon className="w-4 h-4" />
    </div>
  );
}

export default MyHistory;
