import { useMemo } from "react";
import { TrendingUp, DollarSign } from "lucide-react";
import { valueFormatter } from "@/lib/chartConfig";
import { themeColors } from "@/lib/chartTheme";
import { StatCard } from "@/components/StatCard";
import { useReportTrends, useReportMargins, useReportProductPerformance } from "@/hooks/useReports";
import { HorizontalBarChart } from "@/components/charts/HorizontalBarChart";
import { MultiLineChart } from "@/components/charts/MultiLineChart";
import { ProductBubblePlot } from "@/components/charts/ProductBubblePlot";
import { ActivityHeatmap } from "@/components/charts/ActivityHeatmap";
import { ChartExplainer } from "@/components/charts/ChartExplainer";
import { Panel, SectionHead as SectionHeadBase } from "@/components/Panel";

const Stat = StatCard;
const SectionHead = ({ title, action }) => <SectionHeadBase title={title} action={action} variant="report" />;

export function TrendsTab({ reportFilters, dateParams, trendsGroupBy, setTrendsGroupBy, onProductClick }) {
  const t = themeColors();

  // Always fetch day-level data for the heatmap (independent of the grouped chart)
  const trailing365 = useMemo(() => {
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - 365);
    return { start_date: start.toISOString(), end_date: end.toISOString(), group_by: "day" };
  }, []);
  const { data: heatmapTrends } = useReportTrends(trailing365);
  const heatmapData = useMemo(() => {
    if (!heatmapTrends?.series) return [];
    return heatmapTrends.series.map((d) => ({
      date: d.date,
      value: d.transaction_count || 0,
      revenue: d.revenue || 0,
    }));
  }, [heatmapTrends]);

  const { data: trendsReport } = useReportTrends({ ...reportFilters, group_by: trendsGroupBy });
  const { data: marginsReport } = useReportMargins(reportFilters);
  const { data: perfData } = useReportProductPerformance(dateParams);

  const margins = marginsReport?.products || [];
  const productPerf = perfData?.products || [];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <Stat label="Total Revenue" value={valueFormatter(trendsReport?.totals?.revenue || 0)} icon={DollarSign} accent="blue" />
        <Stat label="Total COGS" value={valueFormatter(trendsReport?.totals?.cost || 0)} icon={DollarSign} accent="orange" />
        <Stat label="Gross Profit" value={valueFormatter(trendsReport?.totals?.profit || 0)} icon={TrendingUp} accent="emerald" />
      </div>

      {heatmapData.length > 0 && (
        <Panel>
          <SectionHead title="Transaction Activity — Last 12 Months" action={
            <span className="text-xs text-muted-foreground tabular-nums">
              {heatmapData.reduce((s, d) => s + d.value, 0).toLocaleString()} transactions
            </span>
          } />
          <ChartExplainer
            title="Activity Heatmap"
            bullets={[
              "Each square is one day — brighter = more transactions",
              "Rows are days of the week (Mon–Sun), columns are weeks",
              "Hover over any square to see the exact count and revenue",
              "Look for busy periods, quiet weeks, or seasonal patterns",
            ]}
          >
            <ActivityHeatmap
              data={heatmapData}
              label="transactions"
              tooltipExtra={(d) =>
                d?.revenue
                  ? `Revenue: $${d.revenue.toLocaleString("en-US", { minimumFractionDigits: 2 })}`
                  : ""
              }
            />
          </ChartExplainer>
        </Panel>
      )}

      <Panel>
        <SectionHead title="Revenue, Cost & Profit Over Time" action={
          <div className="flex gap-0.5 bg-muted rounded-lg p-0.5">
            {["day", "week", "month"].map((g) => (
              <button key={g} onClick={() => setTrendsGroupBy(g)} className={`text-xs px-3 py-1.5 rounded-md font-medium transition-all ${trendsGroupBy === g ? "bg-card shadow-sm text-foreground" : "text-muted-foreground hover:text-foreground"}`}>{g.charAt(0).toUpperCase() + g.slice(1)}</button>
            ))}
          </div>
        } />
        {trendsReport?.series?.length > 0 ? (
          <MultiLineChart
            data={trendsReport.series}
            xKey="date"
            series={[
              { key: "revenue", label: "Revenue", color: t.info },
              { key: "cost", label: "Cost", color: t.destructive },
              { key: "profit", label: "Profit", color: t.success, width: 3 },
            ]}
            valueFormatter={valueFormatter}
            height={300}
            stepped
          />
        ) : <div className="h-[300px] flex items-center justify-center"><p className="text-sm text-muted-foreground">No trend data</p></div>}
      </Panel>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Panel>
          <SectionHead title="Top Products by Revenue" />
          {margins.length > 0 ? (
            <HorizontalBarChart data={margins.slice(0, 10).map((p) => ({ name: p.name || p.product_id, revenue: p.revenue }))} categoryKey="name" series={[{ key: "revenue", label: "Revenue", color: t.category1 }]} valueFormatter={valueFormatter} height={Math.max(200, Math.min(margins.length, 10) * 36)} />
          ) : <p className="text-sm text-muted-foreground py-8 text-center">No data</p>}
        </Panel>
        <Panel>
          <SectionHead title="Product Performance — Revenue vs Margin" />
          {productPerf.length > 0 ? (
            <ChartExplainer title="Product Scatter" bullets={["Each bubble is a product — bigger = more revenue", "Right = high sell-through, Top = high margin", "Click any bubble to see full product details"]}>
              <ProductBubblePlot products={productPerf} onBubbleClick={onProductClick} height={Math.max(300, 340)} />
            </ChartExplainer>
          ) : <p className="text-sm text-muted-foreground py-8 text-center">No data</p>}
        </Panel>
      </div>
    </div>
  );
}
