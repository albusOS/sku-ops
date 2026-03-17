import { useState, useMemo } from "react";
import ReactEChartsCore from "echarts-for-react/lib/core";
import echarts from "@/lib/echarts";
import { valueFormatter } from "@/lib/chartConfig";
import { themeColors } from "@/lib/chartTheme";
import { useReportMargins } from "@/hooks/useReports";
import { BentoCard } from "../BentoCard";
import { ReportDetailModal, Narrative } from "../ReportDetailModal";

function ParetoChart({ data = [], height = 320 }) {
  const option = useMemo(() => {
    const t = themeColors();
    if (!data.length) return {};

    const names = data.map((d) => {
      const n = d.name || "Unknown";
      return n.length > 20 ? n.slice(0, 18) + "…" : n;
    });
    const revenues = data.map((d) => d.revenue ?? 0);
    const totalRev = revenues.reduce((s, v) => s + v, 0) || 1;

    let cumPct = 0;
    const cumulative = revenues.map((r) => {
      cumPct += (r / totalRev) * 100;
      return Math.round(cumPct * 10) / 10;
    });

    return {
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "cross" },
        formatter: (params) => {
          const idx = params[0]?.dataIndex;
          if (idx == null) return "";
          const name = data[idx]?.name || "";
          const rev = revenues[idx];
          const cum = cumulative[idx];
          const margin = data[idx]?.margin_pct ?? 0;
          return `<div style="font-size:12px">
            <b>${name}</b><br/>
            Revenue: <b>${valueFormatter(rev)}</b> (${((rev / totalRev) * 100).toFixed(1)}%)<br/>
            Cumulative: <b>${cum}%</b><br/>
            Margin: <b>${margin}%</b>
          </div>`;
        },
      },
      grid: { left: 8, right: 40, top: 24, bottom: 64, containLabel: true },
      xAxis: {
        type: "category",
        data: names,
        axisLabel: { fontSize: 10, color: t.mutedForeground, rotate: 35, interval: 0 },
        axisLine: { show: false },
        axisTick: { show: false },
      },
      yAxis: [
        {
          type: "value",
          splitLine: { lineStyle: { color: t.border } },
          axisLine: { show: false },
          axisTick: { show: false },
          axisLabel: {
            fontSize: 10,
            color: t.mutedForeground,
            formatter: (v) => valueFormatter(v),
          },
        },
        {
          type: "value",
          min: 0,
          max: 100,
          axisLine: { show: false },
          axisTick: { show: false },
          axisLabel: { fontSize: 10, color: t.mutedForeground, formatter: "{value}%" },
          splitLine: { show: false },
        },
      ],
      series: [
        {
          name: "Revenue",
          type: "bar",
          data: revenues,
          barMaxWidth: 24,
          itemStyle: {
            color: (params) => {
              const cum = cumulative[params.dataIndex];
              if (cum <= 80) return t.category1;
              if (cum <= 95) return t.category5;
              return t.mutedForeground;
            },
            borderRadius: [3, 3, 0, 0],
          },
          emphasis: { itemStyle: { shadowBlur: 6, shadowColor: "rgba(0,0,0,.1)" } },
        },
        {
          name: "Cumulative %",
          type: "line",
          yAxisIndex: 1,
          data: cumulative,
          symbol: "circle",
          symbolSize: 5,
          showSymbol: data.length <= 20,
          lineStyle: { width: 2, color: t.accent },
          itemStyle: { color: t.accent },
          emphasis: { itemStyle: { borderWidth: 2, borderColor: t.card } },
        },
      ],
      graphic: [
        {
          type: "line",
          shape: { x1: 0, y1: 0, x2: "100%", y2: 0 },
          top: "20%",
          left: 0,
          style: { stroke: t.destructive, lineWidth: 1, lineDash: [4, 4], opacity: 0.4 },
          silent: true,
          ignore: false,
        },
      ],
    };
  }, [data]);

  if (!data.length) return null;

  return (
    <ReactEChartsCore
      echarts={echarts}
      option={option}
      style={{ height, width: "100%" }}
      theme="skuops"
      opts={{ renderer: "svg" }}
      notMerge
    />
  );
}

function MiniPareto({ data = [], height = 100 }) {
  const t = themeColors();
  if (!data.length) return <div style={{ height }} />;

  const revenues = data.map((d) => d.revenue ?? 0);
  const totalRev = revenues.reduce((s, v) => s + v, 0) || 1;
  const maxRev = Math.max(...revenues, 1);
  const w = 100;
  const barWidth = w / (data.length * 1.8);

  let cumPct = 0;
  const cumPoints = revenues.map((r, i) => {
    cumPct += (r / totalRev) * 100;
    const x = (i / Math.max(data.length - 1, 1)) * (w - barWidth) + barWidth / 2;
    const y = height - 14 - (cumPct / 100) * (height - 24);
    return `${x},${y}`;
  });

  return (
    <svg viewBox={`0 0 ${w} ${height}`} className="w-full" preserveAspectRatio="none" aria-hidden>
      {revenues.map((r, i) => {
        const barH = Math.max((r / maxRev) * (height - 24), 1);
        const x = (i / Math.max(data.length - 1, 1)) * (w - barWidth);
        const y = height - 14 - barH;
        cumPct = (revenues.slice(0, i + 1).reduce((s, v) => s + v, 0) / totalRev) * 100;
        const fill = cumPct <= 80 ? t.category1 : t.mutedForeground;
        return (
          <rect
            key={i}
            x={x}
            y={y}
            width={barWidth * 0.85}
            height={barH}
            rx="1"
            fill={fill}
            opacity="0.7"
          />
        );
      })}
      <polyline points={cumPoints.join(" ")} fill="none" stroke={t.accent} strokeWidth="1.5" />
    </svg>
  );
}

export function TopPerformersCard({ dateParams }) {
  const [open, setOpen] = useState(false);
  const { data: marginsReport } = useReportMargins(dateParams);
  const margins = useMemo(() => marginsReport?.products || [], [marginsReport]);

  const top10 = useMemo(() => margins.slice(0, 10), [margins]);
  const top20 = useMemo(
    () =>
      margins.slice(0, 20).map((p) => ({
        name: p.name || p.product_id,
        revenue: p.revenue,
        margin_pct: p.margin_pct,
      })),
    [margins],
  );

  const totalRevenue = useMemo(() => margins.reduce((s, p) => s + (p.revenue || 0), 0), [margins]);

  const concentrationRisk = useMemo(() => {
    if (!margins.length || totalRevenue === 0) return null;
    let cum = 0;
    let count80 = 0;
    for (const p of margins) {
      cum += p.revenue || 0;
      count80++;
      if ((cum / totalRevenue) * 100 >= 80) break;
    }
    return {
      count80,
      totalCount: margins.length,
      pct: Math.round((count80 / margins.length) * 100),
    };
  }, [margins, totalRevenue]);

  const narrativeItems = useMemo(() => {
    if (!margins.length) return [];
    const items = [];
    if (concentrationRisk)
      items.push(
        `${concentrationRisk.count80} of ${concentrationRisk.totalCount} products (${concentrationRisk.pct}%) generate 80% of revenue — ${concentrationRisk.pct <= 20 ? "high concentration risk" : "healthy distribution"}.`,
      );
    if (top10[0])
      items.push(
        `#1 is ${top10[0].name} with ${valueFormatter(top10[0].revenue)} (${totalRevenue > 0 ? ((top10[0].revenue / totalRevenue) * 100).toFixed(0) : 0}% of total).`,
      );
    const highMargin = margins.filter((p) => (p.margin_pct ?? 0) >= 40).length;
    items.push(`${highMargin} of ${margins.length} products have margins above 40%.`);
    return items;
  }, [margins, top10, totalRevenue, concentrationRisk]);

  const insight = concentrationRisk
    ? `${concentrationRisk.count80} products make 80% of revenue`
    : margins.length > 0
      ? `${margins.length} products tracked`
      : "Loading...";

  return (
    <>
      <BentoCard
        title="Top Performers"
        metric={margins.length > 0 ? `${margins.length} products` : "—"}
        insight={insight}
        size="medium"
        onClick={() => setOpen(true)}
      >
        <MiniPareto data={top10} height={100} />
      </BentoCard>

      <ReportDetailModal
        open={open}
        onClose={() => setOpen(false)}
        title="Revenue Concentration (Pareto)"
        subtitle="Bars show individual product revenue, the line shows cumulative % — watch where it crosses 80%"
      >
        <ParetoChart data={top20} height={360} />

        {concentrationRisk && (
          <div
            className={`flex items-center gap-3 rounded-xl border p-4 ${
              concentrationRisk.pct <= 20
                ? "bg-destructive/5 border-destructive/20"
                : concentrationRisk.pct <= 40
                  ? "bg-category-5/5 border-category-5/20"
                  : "bg-success/5 border-success/20"
            }`}
          >
            <span
              className={`text-2xl font-bold tabular-nums ${
                concentrationRisk.pct <= 20
                  ? "text-destructive"
                  : concentrationRisk.pct <= 40
                    ? "text-category-5"
                    : "text-success"
              }`}
            >
              {concentrationRisk.count80}
            </span>
            <div>
              <p className="text-sm font-medium text-foreground">
                {concentrationRisk.count80} of {concentrationRisk.totalCount} products generate 80%
                of revenue
              </p>
              <p className="text-xs text-muted-foreground mt-0.5">
                {concentrationRisk.pct <= 20
                  ? "High concentration risk — a supply disruption on key SKUs could significantly impact revenue"
                  : concentrationRisk.pct <= 40
                    ? "Moderate concentration — consider growing sales of mid-tier products"
                    : "Revenue is well-distributed across the product range"}
              </p>
            </div>
          </div>
        )}

        {top20.length > 0 && (
          <div>
            <h4 className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground mb-3">
              Product Breakdown
            </h4>
            <div className="overflow-auto max-h-[300px]">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left">
                    <th className="py-2 text-xs font-bold text-muted-foreground uppercase tracking-wide">
                      #
                    </th>
                    <th className="py-2 text-xs font-bold text-muted-foreground uppercase tracking-wide">
                      Product
                    </th>
                    <th className="py-2 text-xs font-bold text-muted-foreground uppercase tracking-wide text-right">
                      Revenue
                    </th>
                    <th className="py-2 text-xs font-bold text-muted-foreground uppercase tracking-wide text-right">
                      Share
                    </th>
                    <th className="py-2 text-xs font-bold text-muted-foreground uppercase tracking-wide text-right">
                      Margin
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {margins.slice(0, 30).map((p, i) => {
                    const share =
                      totalRevenue > 0 ? ((p.revenue / totalRevenue) * 100).toFixed(1) : 0;
                    return (
                      <tr key={i} className="border-b border-border/50">
                        <td className="py-2 text-xs text-muted-foreground tabular-nums">{i + 1}</td>
                        <td className="py-2 text-foreground truncate max-w-[200px]">
                          {p.name || p.product_id}
                        </td>
                        <td className="py-2 text-right tabular-nums font-medium text-foreground">
                          {valueFormatter(p.revenue)}
                        </td>
                        <td className="py-2 text-right tabular-nums text-muted-foreground">
                          {share}%
                        </td>
                        <td className="py-2 text-right">
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold tabular-nums ${(p.margin_pct ?? 0) >= 40 ? "bg-success/10 text-success" : (p.margin_pct ?? 0) < 30 ? "bg-category-5/10 text-category-5" : "bg-info/10 text-info"}`}
                          >
                            {p.margin_pct ?? 0}%
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        <Narrative items={narrativeItems} />
      </ReportDetailModal>
    </>
  );
}
