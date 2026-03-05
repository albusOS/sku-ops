import { useState, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import {
  ArrowLeft, CheckCircle2, AlertTriangle, Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { StatusBadge } from "@/components/StatusBadge";
import { Panel } from "@/components/Panel";
import { cn } from "@/lib/utils";
import { getErrorMessage } from "@/lib/api-client";
import {
  useCycleCount,
  useUpdateCountItem,
  useCommitCycleCount,
} from "@/hooks/useCycleCounts";

function formatDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined, {
    month: "short", day: "numeric", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

function VarianceCell({ variance }) {
  if (variance == null) return <span className="text-slate-300">—</span>;
  if (variance === 0) return <span className="text-slate-400 tabular-nums">0</span>;
  const positive = variance > 0;
  return (
    <span className={cn(
      "tabular-nums font-semibold",
      positive ? "text-emerald-600" : "text-red-600"
    )}>
      {positive ? "+" : ""}{variance}
    </span>
  );
}

function CountInput({ item, countId, disabled }) {
  const [value, setValue] = useState(
    item.counted_qty != null ? String(item.counted_qty) : ""
  );
  const [saving, setSaving] = useState(false);
  const updateMutation = useUpdateCountItem(countId);

  const handleBlur = () => {
    const parsed = parseFloat(value);
    if (isNaN(parsed) || parsed < 0) return;
    if (parsed === item.counted_qty) return;
    setSaving(true);
    updateMutation.mutate(
      { itemId: item.id, data: { counted_qty: parsed } },
      {
        onSuccess: () => setSaving(false),
        onError: (err) => {
          toast.error(getErrorMessage(err));
          setSaving(false);
        },
      }
    );
  };

  if (disabled) {
    return (
      <span className="text-sm tabular-nums text-slate-700">
        {item.counted_qty != null ? item.counted_qty : <span className="text-slate-300">—</span>}
      </span>
    );
  }

  return (
    <div className="relative w-24">
      <Input
        type="number"
        min="0"
        step="any"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onBlur={handleBlur}
        placeholder="Enter qty"
        className="h-8 text-sm tabular-nums pr-7"
      />
      {saving && (
        <Loader2 className="absolute right-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400 animate-spin" />
      )}
    </div>
  );
}

function VarianceSummary({ items }) {
  const stats = useMemo(() => {
    const counted = items.filter((i) => i.counted_qty != null);
    const withVariance = counted.filter((i) => i.variance && i.variance !== 0);
    const shortages = withVariance.filter((i) => i.variance < 0);
    const overages = withVariance.filter((i) => i.variance > 0);
    return {
      total: items.length,
      counted: counted.length,
      withVariance: withVariance.length,
      shortages: shortages.length,
      overages: overages.length,
    };
  }, [items]);

  return (
    <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
      {[
        { label: "Total lines",   value: stats.total },
        { label: "Counted",       value: stats.counted },
        { label: "Variances",     value: stats.withVariance },
        { label: "Shortages",     value: stats.shortages,  color: stats.shortages > 0 ? "text-red-600" : undefined },
        { label: "Overages",      value: stats.overages,   color: stats.overages > 0  ? "text-emerald-600" : undefined },
      ].map(({ label, value, color }) => (
        <div key={label} className="bg-slate-50 rounded-lg px-4 py-3">
          <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1">{label}</p>
          <p className={cn("text-2xl font-semibold tabular-nums text-slate-800", color)}>{value}</p>
        </div>
      ))}
    </div>
  );
}

export default function CycleCountDetailPage() {
  const { countId } = useParams();
  const navigate = useNavigate();
  const { data: count, isLoading, error } = useCycleCount(countId);
  const commitMutation = useCommitCycleCount();

  const isOpen = count?.status === "open";
  const items = count?.items ?? [];

  const canCommit = useMemo(
    () => items.some((i) => i.counted_qty != null),
    [items]
  );

  const handleCommit = () => {
    if (!window.confirm(
      "Apply all variances as stock adjustments? This cannot be undone."
    )) return;

    commitMutation.mutate(countId, {
      onSuccess: (result) => {
        toast.success(
          `Count committed — ${result.items_adjusted} adjustment${result.items_adjusted !== 1 ? "s" : ""} applied`
        );
      },
      onError: (err) => toast.error(getErrorMessage(err)),
    });
  };

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
      </div>
    );
  }

  if (error || !count) {
    return (
      <div className="flex-1 p-6">
        <p className="text-slate-500">Count not found.</p>
      </div>
    );
  }

  return (
    <div className="flex-1 p-6 space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate("/cycle-counts")}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-xl font-semibold text-slate-900">
                Cycle Count
              </h1>
              <StatusBadge status={count.status} />
            </div>
            <p className="text-sm text-slate-500 mt-0.5">
              {count.scope
                ? <><span className="font-medium">{count.scope}</span> department</>
                : "Full warehouse"
              }
              {" · "}Opened {formatDate(count.created_at)} by {count.created_by_name || "—"}
              {count.committed_at && (
                <> · Committed {formatDate(count.committed_at)}</>
              )}
            </p>
          </div>
        </div>

        {isOpen && (
          <Button
            onClick={handleCommit}
            disabled={!canCommit || commitMutation.isPending}
            className="gap-2 shrink-0"
          >
            {commitMutation.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <CheckCircle2 className="w-4 h-4" />
            )}
            Commit Count
          </Button>
        )}
      </div>

      {/* Variance summary */}
      <VarianceSummary items={items} />

      {isOpen && (
        <div className="flex items-center gap-2 text-xs text-slate-500 bg-amber-50 border border-amber-200 rounded-lg px-4 py-2.5">
          <AlertTriangle className="w-3.5 h-3.5 text-amber-500 shrink-0" />
          Enter the physical count for each line. Changes save automatically on blur.
          Committing will apply all non-zero variances as stock adjustments.
        </div>
      )}

      {/* Count sheet table */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="bg-slate-50/80 hover:bg-slate-50/80">
                <TableHead className="text-[10px] font-bold uppercase tracking-[0.1em] text-slate-400 px-4 py-2.5">SKU</TableHead>
                <TableHead className="text-[10px] font-bold uppercase tracking-[0.1em] text-slate-400 px-4 py-2.5">Product</TableHead>
                <TableHead className="text-[10px] font-bold uppercase tracking-[0.1em] text-slate-400 px-4 py-2.5 text-right">On Hand (snapshot)</TableHead>
                <TableHead className="text-[10px] font-bold uppercase tracking-[0.1em] text-slate-400 px-4 py-2.5 text-right">Counted</TableHead>
                <TableHead className="text-[10px] font-bold uppercase tracking-[0.1em] text-slate-400 px-4 py-2.5 text-right">Variance</TableHead>
                <TableHead className="text-[10px] font-bold uppercase tracking-[0.1em] text-slate-400 px-4 py-2.5">Unit</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-12 text-slate-400 text-sm">
                    No items in this count
                  </TableCell>
                </TableRow>
              ) : (
                items.map((item) => (
                  <TableRow
                    key={item.id}
                    className={cn(
                      "hover:bg-slate-50/60 transition-colors",
                      item.variance != null && item.variance !== 0 && "bg-amber-50/30"
                    )}
                  >
                    <TableCell className="px-4 py-2.5">
                      <span className="font-mono text-xs text-slate-600">{item.sku}</span>
                    </TableCell>
                    <TableCell className="px-4 py-2.5 text-sm text-slate-700 max-w-xs truncate">
                      {item.product_name}
                    </TableCell>
                    <TableCell className="px-4 py-2.5 text-right tabular-nums text-sm text-slate-600">
                      {item.snapshot_qty}
                    </TableCell>
                    <TableCell className="px-4 py-2.5 text-right">
                      <div className="flex justify-end">
                        <CountInput item={item} countId={countId} disabled={!isOpen} />
                      </div>
                    </TableCell>
                    <TableCell className="px-4 py-2.5 text-right">
                      <VarianceCell variance={item.variance} />
                    </TableCell>
                    <TableCell className="px-4 py-2.5 text-sm text-slate-400">
                      {item.unit}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </div>
    </div>
  );
}
