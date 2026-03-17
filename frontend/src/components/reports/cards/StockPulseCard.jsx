import { useState, useMemo, useCallback } from "react";
import { valueFormatter } from "@/lib/chartConfig";
import { useReportTrends, useReportProductActivity } from "@/hooks/useReports";
import { useProducts } from "@/hooks/useProducts";
import { ActivityHeatmap } from "@/components/charts/ActivityHeatmap";
import { BentoCard } from "../BentoCard";
import { ReportDetailModal, Narrative } from "../ReportDetailModal";

const METRICS = [
  { id: "transactions", label: "Transactions", valueKey: "transaction_count", unit: "txns" },
  {
    id: "revenue",
    label: "Revenue",
    valueKey: "revenue",
    unit: "$",
    format: (v) => valueFormatter(v),
  },
  { id: "volume", label: "Volume", valueKey: "profit", unit: "units" },
];

function MetricToggle({ active, onChange }) {
  return (
    <div className="flex gap-0.5 bg-muted rounded-lg p-0.5">
      {METRICS.map((m) => (
        <button
          key={m.id}
          onClick={() => onChange(m.id)}
          className={`text-xs px-3 py-1.5 rounded-md font-medium transition-all ${active === m.id ? "bg-card shadow-sm text-foreground" : "text-muted-foreground hover:text-foreground"}`}
        >
          {m.label}
        </button>
      ))}
    </div>
  );
}

function buildHeatmapData(series, metricId) {
  if (!series?.length) return [];
  const metric = METRICS.find((m) => m.id === metricId) || METRICS[0];
  return series.map((d) => ({
    date: d.date || d.day,
    value: d[metric.valueKey] || 0,
    revenue: d.revenue || 0,
    transaction_count: d.transaction_count || 0,
  }));
}

function computeDeviationInsight(data) {
  if (data.length < 14) return null;
  const values = data.map((d) => d.value).filter((v) => v > 0);
  if (!values.length) return null;
  const mean = values.reduce((s, v) => s + v, 0) / values.length;
  const recentDays = data.slice(-14);
  const recentActive = recentDays.filter((d) => d.value > 0);
  if (!recentActive.length) return { label: "No recent activity", direction: "down" };
  const recentMean = recentActive.reduce((s, d) => s + d.value, 0) / recentActive.length;
  const pctDiff = ((recentMean - mean) / mean) * 100;
  if (Math.abs(pctDiff) < 10) return { label: "Activity is steady", direction: "flat" };
  return {
    label: `Recent activity ${pctDiff > 0 ? "up" : "down"} ${Math.abs(pctDiff).toFixed(0)}% vs average`,
    direction: pctDiff > 0 ? "up" : "down",
  };
}

export function StockPulseCard() {
  const [open, setOpen] = useState(false);
  const [metricId, setMetricId] = useState("transactions");
  const [heatmapProductId, setHeatmapProductId] = useState(null);

  const trailing365 = useMemo(() => {
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - 365);
    return {
      start_date: start.toISOString(),
      end_date: end.toISOString(),
      group_by: "day",
    };
  }, []);

  const { data: heatmapTrends } = useReportTrends(trailing365);
  const { data: productsList } = useProducts();

  const activityParams = useMemo(
    () => ({ product_id: heatmapProductId || undefined }),
    [heatmapProductId],
  );
  const { data: productActivityData } = useReportProductActivity(activityParams);

  const rawSeries = useMemo(() => {
    if (heatmapProductId && productActivityData?.series) {
      return productActivityData.series.map((d) => ({
        date: d.day,
        transaction_count: d.transaction_count || 0,
        revenue: 0,
        profit: d.units_moved || 0,
      }));
    }
    return heatmapTrends?.series || [];
  }, [heatmapProductId, productActivityData, heatmapTrends]);

  const heatmapData = useMemo(() => buildHeatmapData(rawSeries, metricId), [rawSeries, metricId]);

  const activeDays = useMemo(() => heatmapData.filter((d) => d.value > 0).length, [heatmapData]);

  const totalValue = useMemo(() => heatmapData.reduce((s, d) => s + d.value, 0), [heatmapData]);

  const deviation = useMemo(() => computeDeviationInsight(heatmapData), [heatmapData]);

  const metric = METRICS.find((m) => m.id === metricId) || METRICS[0];
  const displayTotal = metric.format ? metric.format(totalValue) : totalValue.toLocaleString();

  const narrativeItems = useMemo(() => {
    const items = [];
    items.push(`${displayTotal} total ${metric.unit} over the past 12 months.`);
    items.push(`${activeDays} active days out of ~365.`);
    if (deviation) items.push(deviation.label + ".");
    if (heatmapData.length > 0) {
      const peak = heatmapData.reduce(
        (best, d) => (d.value > best.value ? d : best),
        heatmapData[0],
      );
      if (peak.value > 0) {
        const peakLabel = metric.format ? metric.format(peak.value) : peak.value.toLocaleString();
        items.push(`Peak day: ${peak.date} with ${peakLabel} ${metric.unit}.`);
      }
    }
    return items;
  }, [displayTotal, metric, activeDays, deviation, heatmapData]);

  const insight =
    heatmapData.length > 0
      ? deviation?.label || `${activeDays} active days · ${displayTotal} ${metric.unit}`
      : "Loading...";

  const heatmapLabel =
    metricId === "revenue" ? "revenue" : metricId === "volume" ? "units" : "transactions";
  const tooltipExtra = useCallback(
    (d) => {
      if (!d) return "";
      const parts = [];
      if (metricId !== "transactions" && d.transaction_count)
        parts.push(`${d.transaction_count} txns`);
      if (metricId !== "revenue" && d.revenue) parts.push(`Rev: ${valueFormatter(d.revenue)}`);
      return parts.join(" · ");
    },
    [metricId],
  );

  const controls = (
    <div className="flex flex-wrap items-center gap-3">
      <MetricToggle active={metricId} onChange={setMetricId} />
      <select
        value={heatmapProductId || ""}
        onChange={(e) => setHeatmapProductId(e.target.value || null)}
        className="text-xs border border-border rounded-lg px-2.5 py-1.5 text-muted-foreground bg-card focus:outline-none focus:ring-1 focus:ring-accent/30 max-w-[200px] truncate"
      >
        <option value="">All products</option>
        {(productsList || []).map((p) => (
          <option key={p.id} value={p.id}>
            {p.name} ({p.sku})
          </option>
        ))}
      </select>
    </div>
  );

  return (
    <>
      <BentoCard
        title="Stock Pulse"
        metric={heatmapData.length > 0 ? displayTotal : "—"}
        insight={insight}
        size="medium"
        onClick={() => setOpen(true)}
      >
        {heatmapData.length > 0 ? (
          <ActivityHeatmap data={heatmapData} label={heatmapLabel} height={100} />
        ) : (
          <div className="h-[100px]" />
        )}
      </BentoCard>

      <ReportDetailModal
        open={open}
        onClose={() => setOpen(false)}
        title="Stock Pulse — Activity Heatmap"
        subtitle="Switch metrics and filter by product to understand demand patterns"
        controls={controls}
      >
        {heatmapData.length > 0 && (
          <ActivityHeatmap
            data={heatmapData}
            label={heatmapLabel}
            tooltipExtra={tooltipExtra}
            height={180}
          />
        )}

        {deviation && (
          <div
            className={`flex items-center gap-3 rounded-xl border p-4 ${
              deviation.direction === "up"
                ? "bg-success/[0.06] border-success/25 shadow-[inset_0_1px_0_0_rgb(16_185_129/0.1)]"
                : deviation.direction === "down"
                  ? "bg-destructive/[0.06] border-destructive/25 shadow-[inset_0_1px_0_0_rgb(220_38_38/0.1)]"
                  : "bg-muted/40 border-border/50"
            }`}
          >
            <div
              className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
                deviation.direction === "up"
                  ? "bg-success/15 text-success"
                  : deviation.direction === "down"
                    ? "bg-destructive/15 text-destructive"
                    : "bg-muted text-muted-foreground"
              }`}
            >
              <span className="text-lg font-bold leading-none">
                {deviation.direction === "up" ? "↑" : deviation.direction === "down" ? "↓" : "→"}
              </span>
            </div>
            <div>
              <p className="text-sm font-medium text-foreground">{deviation.label}</p>
              <p className="text-[10px] text-muted-foreground">
                {deviation.direction === "up"
                  ? "Demand is increasing"
                  : deviation.direction === "down"
                    ? "Demand is declining"
                    : "Holding steady"}
              </p>
            </div>
          </div>
        )}

        <Narrative items={narrativeItems} />
      </ReportDetailModal>
    </>
  );
}
