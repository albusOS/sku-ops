import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import {
  FileUp,
  Truck,
  Warehouse,
  ShoppingCart,
  FileText,
  CreditCard,
  ArrowRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { valueFormatter } from "@/lib/chartConfig";

/**
 * Live pipeline overview on the Dashboard.
 * Takes real stats from the dashboard endpoint and shows actual counts
 * flowing through the three main business pipelines.
 */
export default function WorkflowGraph({ stats = {} }) {
  const navigate = useNavigate();

  const pipelines = useMemo(() => {
    const po = stats.po_summary || {};
    const ordered = po.ordered || {};
    const partial = po.partial || {};
    const received = po.received || {};

    return [
      {
        label: "Purchasing Pipeline",
        stages: [
          {
            label: "On Order",
            count: ordered.count || 0,
            value: ordered.total,
            icon: FileUp,
            color: "text-muted-foreground",
            bg: "bg-muted",
            route: "/purchasing",
          },
          {
            label: "In Transit",
            count: partial.count || 0,
            value: partial.total,
            icon: Truck,
            color: "text-info",
            bg: "bg-info/10",
            route: "/purchasing",
            pulse: (partial.count || 0) > 0,
          },
          {
            label: "Received",
            count: received.count || 0,
            value: received.total,
            icon: Warehouse,
            color: "text-success",
            bg: "bg-success/10",
            route: "/inventory",
          },
        ],
      },
      {
        label: "Operations Pipeline",
        stages: [
          {
            label: "Withdrawals",
            count: stats.total_withdrawals || 0,
            value: stats.total_spent,
            icon: ShoppingCart,
            color: "text-foreground",
            bg: "bg-muted",
            route: "/pos",
          },
          {
            label: "Uninvoiced",
            count: stats.uninvoiced_count || 0,
            value: stats.unpaid_balance,
            icon: FileText,
            color: stats.uninvoiced_count > 0 ? "text-warning" : "text-muted-foreground",
            bg: stats.uninvoiced_count > 0 ? "bg-warning/10" : "bg-muted",
            route: "/pos",
            pulse: (stats.uninvoiced_count || 0) > 0,
          },
          {
            label: "Paid",
            count: stats.paid_count || 0,
            value: stats.paid_total,
            icon: CreditCard,
            color: "text-success",
            bg: "bg-success/10",
            route: "/xero-health",
          },
        ],
      },
    ];
  }, [stats]);

  return (
    <div className="space-y-4">
      {pipelines.map((pipeline) => {
        const hasActivity = pipeline.stages.some((s) => s.count > 0);
        if (!hasActivity) return null;

        return (
          <div key={pipeline.label}>
            <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-muted-foreground mb-2">
              {pipeline.label}
            </p>
            <div className="flex items-stretch gap-2">
              {pipeline.stages.map((stage, i) => (
                <div key={stage.label} className="contents">
                  {i > 0 && (
                    <div className="flex items-center shrink-0">
                      <ArrowRight className="w-3.5 h-3.5 text-border" />
                    </div>
                  )}
                  <button
                    type="button"
                    onClick={() => navigate(stage.route)}
                    className={cn(
                      "flex-1 flex items-center gap-3 rounded-xl border border-border/60 px-4 py-3 transition-all text-left",
                      "hover:border-accent/40 hover:shadow-sm hover:bg-surface-muted",
                      stage.pulse && "ring-1 ring-info/20",
                    )}
                  >
                    <div
                      className={cn(
                        "w-8 h-8 rounded-lg flex items-center justify-center shrink-0",
                        stage.bg,
                        stage.color,
                      )}
                    >
                      <stage.icon className="w-4 h-4" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-bold tabular-nums leading-none">{stage.count}</p>
                      <p className="text-[10px] text-muted-foreground mt-0.5 truncate">
                        {stage.label}
                        {stage.value > 0 && (
                          <span className="ml-1 tabular-nums">· {valueFormatter(stage.value)}</span>
                        )}
                      </p>
                    </div>
                  </button>
                </div>
              ))}
            </div>
          </div>
        );
      })}

      {!pipelines.some((p) => p.stages.some((s) => s.count > 0)) && (
        <p className="text-sm text-muted-foreground text-center py-4">
          No active pipeline data for this period
        </p>
      )}
    </div>
  );
}
