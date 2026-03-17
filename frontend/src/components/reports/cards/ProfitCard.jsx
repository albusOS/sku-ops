import { useMemo, useState } from "react";
import { valueFormatter } from "@/lib/chartConfig";
import { themeColors } from "@/lib/chartTheme";
import { useReportPL, useReportTrends } from "@/hooks/useReports";
import { BentoCard } from "../BentoCard";
import { ReportDetailModal, Narrative } from "../ReportDetailModal";
import { WaterfallChart } from "@/components/charts/WaterfallChart";
import { PLStatement } from "../PLStatement";

function MarginBridge({ items = [], height = 90 }) {
  const t = themeColors();
  if (items.length < 2) return <div style={{ height }} />;

  const maxAbs = Math.max(...items.map((i) => Math.abs(i.value)), 1);
  const barW = 100 / (items.length * 2 + 1);

  return (
    <svg viewBox="0 0 100 90" className="w-full" preserveAspectRatio="none" aria-hidden>
      {items.map((item, i) => {
        const x = barW * (i * 2 + 1);
        const barH = Math.max((Math.abs(item.value) / maxAbs) * 60, 2);
        const isTotal = item.type === "total";
        const isNeg = item.type === "decrease" || item.value < 0;
        const y = isNeg ? 44 : 44 - barH;
        const fill = isTotal ? t.success : isNeg ? t.destructive : t.info;
        const opacity = isTotal ? 0.9 : 0.65;

        return (
          <g key={i}>
            <rect
              x={x}
              y={y}
              width={barW * 1.5}
              height={barH}
              rx="1.5"
              fill={fill}
              opacity={opacity}
            />
            <text
              x={x + barW * 0.75}
              y={height - 2}
              textAnchor="middle"
              className="fill-muted-foreground"
              style={{ fontSize: "5px" }}
            >
              {item.label.length > 6 ? item.label.slice(0, 5) + "…" : item.label}
            </text>
          </g>
        );
      })}
      <line
        x1="0"
        y1="44"
        x2="100"
        y2="44"
        stroke={t.border}
        strokeWidth="0.3"
        strokeDasharray="2 2"
      />
    </svg>
  );
}

export function ProfitCard({ dateParams: _dateParams, reportFilters }) {
  const [open, setOpen] = useState(false);
  const plParams = useMemo(() => ({ ...reportFilters, group_by: "overall" }), [reportFilters]);
  const { data: plData } = useReportPL(plParams);
  const { data: trendsReport } = useReportTrends({ ...reportFilters, group_by: "week" });

  const summary = plData?.summary;
  const grossProfit = summary?.gross_profit ?? 0;
  const revenue = summary?.revenue ?? 0;
  const cogs = summary?.cogs ?? 0;
  const marginPct = summary?.margin_pct ?? 0;

  const waterfallItems = useMemo(() => {
    if (!summary) return [];
    const items = [{ label: "Revenue", value: revenue, type: "total" }];
    if (cogs) items.push({ label: "COGS", value: -cogs, type: "decrease" });
    if (summary.shrinkage)
      items.push({ label: "Shrinkage", value: -summary.shrinkage, type: "decrease" });
    if (summary.tax_collected)
      items.push({ label: "Tax", value: -summary.tax_collected, type: "decrease" });
    const net = revenue - cogs - (summary.shrinkage || 0) - (summary.tax_collected || 0);
    items.push({ label: "Net", value: net, type: "total" });
    return items;
  }, [summary, revenue, cogs]);

  const sparkData = useMemo(() => trendsReport?.series || [], [trendsReport]);

  const narrativeItems = useMemo(() => {
    if (!summary) return [];
    const items = [];
    items.push(
      `Total revenue of ${valueFormatter(revenue)} with ${valueFormatter(cogs)} in cost of goods sold.`,
    );
    const marginQuality =
      marginPct >= 40 ? "healthy" : marginPct >= 30 ? "moderate" : "below target — needs attention";
    items.push(`Gross margin is ${marginPct}% — ${marginQuality}.`);
    if (summary.shrinkage > 0)
      items.push(
        `Shrinkage of ${valueFormatter(summary.shrinkage)} eroded ${revenue > 0 ? ((summary.shrinkage / revenue) * 100).toFixed(1) : 0}% of revenue.`,
      );
    if (sparkData.length > 2) {
      const recent = sparkData[sparkData.length - 1]?.profit ?? 0;
      const prior = sparkData[sparkData.length - 2]?.profit ?? 0;
      if (prior > 0) {
        const delta = (((recent - prior) / prior) * 100).toFixed(1);
        items.push(
          `Most recent period profit ${Number(delta) >= 0 ? "up" : "down"} ${Math.abs(Number(delta))}% vs prior.`,
        );
      }
    }
    return items;
  }, [summary, revenue, cogs, marginPct, sparkData]);

  const insight = summary
    ? `${marginPct}% margin · ${valueFormatter(revenue)} revenue`
    : "Loading...";

  const profitStatus = summary
    ? marginPct >= 40
      ? "healthy"
      : marginPct >= 25
        ? undefined
        : "warn"
    : undefined;

  return (
    <>
      <BentoCard
        title="Profit Snapshot"
        metric={summary ? valueFormatter(grossProfit) : "—"}
        insight={insight}
        status={profitStatus}
        size="large"
        onClick={() => setOpen(true)}
      >
        <MarginBridge items={waterfallItems} height={90} />
      </BentoCard>

      <ReportDetailModal
        open={open}
        onClose={() => setOpen(false)}
        title="Profit & Loss"
        subtitle="Formal P&L breakdown for the selected period"
      >
        {summary && <PLStatement summary={summary} />}
        {waterfallItems.length > 0 && (
          <div>
            <h4 className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground mb-3">
              P&L Waterfall
            </h4>
            <WaterfallChart items={waterfallItems} height={300} />
          </div>
        )}
        <Narrative items={narrativeItems} />
      </ReportDetailModal>
    </>
  );
}
