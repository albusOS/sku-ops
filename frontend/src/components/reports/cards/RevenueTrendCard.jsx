import { useState, useMemo } from "react";
import { valueFormatter } from "@/lib/chartConfig";
import { themeColors } from "@/lib/chartTheme";
import { useReportTrends, useReportSales } from "@/hooks/useReports";
import { BentoCard } from "../BentoCard";
import { ReportDetailModal, Narrative } from "../ReportDetailModal";
import { MultiLineChart } from "@/components/charts/MultiLineChart";

function SpreadChart({ data = [], height = 80 }) {
  const t = themeColors();
  if (data.length < 2) return <div style={{ height }} />;

  const revenues = data.map((d) => d.revenue ?? 0);
  const costs = data.map((d) => d.cost ?? 0);
  const allVals = [...revenues, ...costs];
  const max = Math.max(...allVals, 1);
  const min = Math.min(...allVals, 0);
  const range = max - min || 1;
  const w = 100;
  const pad = 4;

  const toY = (v) => height - ((v - min) / range) * (height - pad * 2) - pad;
  const toX = (i) => (i / (data.length - 1)) * w;

  const revPoints = revenues.map((v, i) => `${toX(i)},${toY(v)}`);
  const costPoints = costs.map((v, i) => `${toX(i)},${toY(v)}`);

  const fillPoints = [...revPoints, ...costPoints.slice().reverse()].join(" ");

  const profitPositive = revenues.every((r, i) => r >= costs[i]);

  return (
    <svg viewBox={`0 0 ${w} ${height}`} className="w-full" preserveAspectRatio="none" aria-hidden>
      <polygon
        points={fillPoints}
        fill={profitPositive ? t.success : t.destructive}
        opacity="0.12"
      />
      <polyline points={revPoints.join(" ")} fill="none" stroke={t.info} strokeWidth="1.5" />
      <polyline
        points={costPoints.join(" ")}
        fill="none"
        stroke={t.destructive}
        strokeWidth="1"
        strokeDasharray="3 2"
      />
    </svg>
  );
}

export function RevenueTrendCard({ reportFilters }) {
  const [open, setOpen] = useState(false);
  const [groupBy, setGroupBy] = useState("day");
  const t = themeColors();

  const { data: salesReport } = useReportSales(reportFilters);
  const sparkParams = useMemo(() => ({ ...reportFilters, group_by: "week" }), [reportFilters]);
  const { data: sparkTrends } = useReportTrends(sparkParams);

  const detailParams = useMemo(
    () => ({ ...reportFilters, group_by: groupBy }),
    [reportFilters, groupBy],
  );
  const { data: detailTrends } = useReportTrends(detailParams);

  const sparkData = useMemo(() => sparkTrends?.series || [], [sparkTrends]);
  const detailData = detailTrends?.series || [];

  const peakDate = useMemo(() => {
    if (!sparkData.length) return null;
    let maxVal = -Infinity;
    let peak = null;
    for (const d of sparkData) {
      if ((d.revenue ?? 0) > maxVal) {
        maxVal = d.revenue;
        peak = d.date;
      }
    }
    return peak;
  }, [sparkData]);

  const spreadHealth = useMemo(() => {
    if (sparkData.length < 2) return null;
    const recent = sparkData.slice(-4);
    const avgSpread =
      recent.reduce((s, d) => s + ((d.revenue ?? 0) - (d.cost ?? 0)), 0) / recent.length;
    const earlier = sparkData.slice(0, 4);
    const avgSpreadEarlier =
      earlier.reduce((s, d) => s + ((d.revenue ?? 0) - (d.cost ?? 0)), 0) / earlier.length;
    if (avgSpreadEarlier === 0) return null;
    return { trend: avgSpread > avgSpreadEarlier ? "widening" : "narrowing", avgSpread };
  }, [sparkData]);

  const narrativeItems = useMemo(() => {
    if (!salesReport) return [];
    const items = [];
    items.push(
      `${salesReport.total_transactions || 0} transactions totaling ${valueFormatter(salesReport.total_revenue || 0)}.`,
    );
    if (salesReport.average_transaction)
      items.push(`Average transaction value: ${valueFormatter(salesReport.average_transaction)}.`);
    if (peakDate) items.push(`Revenue peaked around ${peakDate}.`);
    if (spreadHealth)
      items.push(
        `The revenue-cost spread is ${spreadHealth.trend} — ${spreadHealth.trend === "widening" ? "margins are improving" : "margins are under pressure"}.`,
      );
    if (salesReport.gross_margin_pct != null)
      items.push(`Overall gross margin: ${salesReport.gross_margin_pct}%.`);
    return items;
  }, [salesReport, peakDate, spreadHealth]);

  const revenue = salesReport?.total_revenue ?? 0;
  const spreadLabel = spreadHealth ? `spread ${spreadHealth.trend}` : "";
  const insight = salesReport
    ? `${salesReport.total_transactions || 0} transactions · ${spreadLabel || `avg ${valueFormatter(salesReport.average_transaction || 0)}`}`
    : "Loading...";

  const toggles = (
    <div className="flex gap-0.5 bg-muted rounded-lg p-0.5">
      {["day", "week", "month"].map((g) => (
        <button
          key={g}
          onClick={() => setGroupBy(g)}
          className={`text-xs px-3 py-1.5 rounded-md font-medium transition-all ${groupBy === g ? "bg-card shadow-sm text-foreground" : "text-muted-foreground hover:text-foreground"}`}
        >
          {g.charAt(0).toUpperCase() + g.slice(1)}
        </button>
      ))}
    </div>
  );

  return (
    <>
      <BentoCard
        title="Revenue Trend"
        metric={valueFormatter(revenue)}
        insight={insight}
        size="medium"
        onClick={() => setOpen(true)}
      >
        <SpreadChart data={sparkData} height={80} />
        <div className="flex gap-4 mt-2">
          <span className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
            <span className="w-3 h-0.5 rounded-full" style={{ background: t.info }} /> Revenue
          </span>
          <span className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
            <span className="w-3 h-0.5 rounded-full" style={{ background: t.destructive }} /> Cost
          </span>
          <span className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
            <span className="w-2 h-2 rounded-sm opacity-30" style={{ background: t.success }} />{" "}
            Profit gap
          </span>
        </div>
      </BentoCard>

      <ReportDetailModal
        open={open}
        onClose={() => setOpen(false)}
        title="Revenue, Cost & Profit Over Time"
        subtitle="The shaded gap between revenue and cost lines represents profit — watch it widen or narrow"
        controls={toggles}
      >
        {detailData.length > 0 && (
          <MultiLineChart
            data={detailData}
            xKey="date"
            series={[
              { key: "revenue", label: "Revenue", color: t.info },
              { key: "cost", label: "Cost", color: t.destructive },
              { key: "profit", label: "Profit", color: t.success, width: 3 },
            ]}
            valueFormatter={valueFormatter}
            height={360}
            stepped
          />
        )}
        <Narrative items={narrativeItems} />
      </ReportDetailModal>
    </>
  );
}
