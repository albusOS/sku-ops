import { useState, useMemo } from "react";
import { Calendar as CalendarIcon, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { format } from "date-fns";
import { DATE_PRESETS } from "@/lib/constants";
import { dateToISO, endOfDayISO } from "@/lib/utils";
import { valueFormatter } from "@/lib/chartConfig";
import { themeColors } from "@/lib/chartTheme";
import { MultiLineChart } from "@/components/charts/MultiLineChart";
import { HorizontalBarChart } from "@/components/charts/HorizontalBarChart";
import { PLStatement } from "@/components/reports/PLStatement";
import { ARAgingTable } from "@/components/reports/ARAgingTable";
import { ProductDetailModal } from "@/components/ProductDetailModal";
import {
  useReportPL,
  useReportTrends,
  useReportSales,
  useReportMargins,
  useReportArAging,
  useReportInventory,
  useReportKpis,
  useReportReorderUrgency,
} from "@/hooks/useReports";

function KpiCard({ label, value, subtext, trend, warn }) {
  return (
    <div className="rounded-xl border border-border/60 bg-card/70 shadow-sm px-5 py-4">
      <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-muted-foreground">
        {label}
      </p>
      <p className="text-xl font-bold tabular-nums text-foreground mt-1 leading-none">{value}</p>
      {(subtext || trend != null) && (
        <div className="flex items-center gap-1.5 mt-2">
          {trend != null && (
            <span
              className={`inline-flex items-center gap-0.5 text-xs font-medium ${
                warn
                  ? "text-destructive"
                  : trend > 0
                    ? "text-success"
                    : trend < 0
                      ? "text-destructive"
                      : "text-muted-foreground"
              }`}
            >
              {trend > 0 ? (
                <TrendingUp className="w-3 h-3" />
              ) : trend < 0 ? (
                <TrendingDown className="w-3 h-3" />
              ) : (
                <Minus className="w-3 h-3" />
              )}
              {trend > 0 ? "+" : ""}
              {trend.toFixed(1)}%
            </span>
          )}
          {subtext && <span className="text-xs text-muted-foreground">{subtext}</span>}
        </div>
      )}
    </div>
  );
}

function SectionTitle({ children }) {
  return (
    <h2 className="text-[10px] font-bold uppercase tracking-[0.14em] text-muted-foreground border-l-2 border-accent pl-3">
      {children}
    </h2>
  );
}

const Reports = () => {
  const [dateRange, setDateRange] = useState({ from: null, to: null });
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [trendGroupBy, setTrendGroupBy] = useState("week");

  const dateParams = useMemo(
    () => ({
      start_date: dateToISO(dateRange.from),
      end_date: endOfDayISO(dateRange.to),
    }),
    [dateRange],
  );

  const reportFilters = useMemo(() => ({ ...dateParams }), [dateParams]);

  // Data hooks
  const plParams = useMemo(() => ({ ...reportFilters, group_by: "overall" }), [reportFilters]);
  const { data: plData } = useReportPL(plParams);
  const { data: salesReport } = useReportSales(reportFilters);

  const trendParams = useMemo(
    () => ({ ...reportFilters, group_by: trendGroupBy }),
    [reportFilters, trendGroupBy],
  );
  const { data: trendsReport } = useReportTrends(trendParams);

  const { data: marginsReport } = useReportMargins(reportFilters);
  const { data: arData } = useReportArAging(reportFilters);
  const { data: inventoryReport } = useReportInventory();
  const { data: kpis } = useReportKpis(reportFilters);
  const { data: reorderData } = useReportReorderUrgency();

  const t = themeColors();

  // Derived data
  const summary = plData?.summary;
  const revenue = summary?.revenue ?? 0;
  const cogs = summary?.cogs ?? 0;
  const grossProfit = summary?.gross_profit ?? 0;
  const marginPct = summary?.margin_pct ?? 0;

  const trendSeries = useMemo(() => trendsReport?.series || [], [trendsReport]);

  const topProducts = useMemo(
    () =>
      (marginsReport?.products || []).slice(0, 10).map((p) => ({
        name: p.name || p.sku_id,
        revenue: p.revenue ?? 0,
        margin_pct: p.margin_pct ?? 0,
      })),
    [marginsReport],
  );

  const arEntities = useMemo(() => arData?.entities || arData?.data || [], [arData]);
  const totalAR = useMemo(
    () => arEntities.reduce((s, e) => s + (e.total_ar || 0), 0),
    [arEntities],
  );

  const inventoryValue = inventoryReport?.total_retail_value ?? 0;
  const lowStockCount = inventoryReport?.low_stock_count ?? 0;
  const outOfStockCount = inventoryReport?.out_of_stock_count ?? 0;
  const totalProducts = inventoryReport?.total_products ?? 0;
  const criticalCount = useMemo(
    () =>
      (reorderData?.products || []).filter((p) => p.urgency === "critical" || p.urgency === "high")
        .length,
    [reorderData],
  );

  // Period-over-period trend (compare last half of trend to first half)
  const revenueTrend = useMemo(() => {
    if (trendSeries.length < 4) return null;
    const mid = Math.floor(trendSeries.length / 2);
    const first = trendSeries.slice(0, mid);
    const second = trendSeries.slice(mid);
    const avgFirst = first.reduce((s, d) => s + (d.revenue ?? 0), 0) / first.length;
    const avgSecond = second.reduce((s, d) => s + (d.revenue ?? 0), 0) / second.length;
    if (avgFirst === 0) return null;
    return ((avgSecond - avgFirst) / avgFirst) * 100;
  }, [trendSeries]);

  const handleProductClick = (product) => {
    setSelectedProduct({
      id: product.sku_id || product.id,
      name: product.name,
      sku: product.sku,
    });
  };

  return (
    <div className="p-6 md:p-8" data-testid="reports-page">
      <div className="max-w-[1400px] mx-auto space-y-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold text-foreground tracking-tight">Reports</h1>
            <p className="text-muted-foreground mt-1 text-sm">
              Financial performance, inventory health, and product intelligence
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex gap-0.5 bg-muted rounded-lg p-0.5">
              {DATE_PRESETS.map((preset) => (
                <button
                  key={preset.label}
                  onClick={() => setDateRange(preset.getValue())}
                  className="text-xs px-3 py-1.5 rounded-md text-muted-foreground hover:bg-card hover:shadow-sm transition-all font-medium"
                >
                  {preset.label}
                </button>
              ))}
            </div>
            <Popover>
              <PopoverTrigger asChild>
                <Button variant="outline" size="sm" className="gap-2" data-testid="date-range-btn">
                  <CalendarIcon className="w-4 h-4" />
                  {dateRange.from
                    ? dateRange.to
                      ? `${format(dateRange.from, "MMM d")} – ${format(dateRange.to, "MMM d")}`
                      : format(dateRange.from, "MMM d, yyyy")
                    : "Custom"}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0" align="end">
                <Calendar
                  mode="range"
                  selected={dateRange}
                  onSelect={(r) => setDateRange(r || { from: null, to: null })}
                  numberOfMonths={2}
                />
              </PopoverContent>
            </Popover>
            {(dateRange.from || dateRange.to) && (
              <button
                onClick={() => setDateRange({ from: null, to: null })}
                className="text-xs text-muted-foreground hover:text-foreground"
              >
                Clear
              </button>
            )}
          </div>
        </div>

        {/* KPI row */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <KpiCard
            label="Revenue"
            value={summary ? valueFormatter(revenue) : "—"}
            trend={revenueTrend}
          />
          <KpiCard
            label="Gross Profit"
            value={summary ? valueFormatter(grossProfit) : "—"}
            subtext={summary ? `${marginPct}% margin` : undefined}
          />
          <KpiCard
            label="COGS"
            value={summary ? valueFormatter(cogs) : "—"}
            subtext={revenue > 0 ? `${((cogs / revenue) * 100).toFixed(0)}% of revenue` : undefined}
          />
          <KpiCard
            label="Transactions"
            value={salesReport ? (salesReport.total_transactions || 0).toLocaleString() : "—"}
            subtext={
              salesReport?.average_transaction
                ? `avg ${valueFormatter(salesReport.average_transaction)}`
                : undefined
            }
          />
          <KpiCard
            label="AR Outstanding"
            value={arEntities.length > 0 ? valueFormatter(totalAR) : "—"}
            subtext={arEntities.length > 0 ? `${arEntities.length} accounts` : undefined}
            warn={totalAR > 0}
          />
          <KpiCard
            label="Inventory Value"
            value={inventoryValue > 0 ? valueFormatter(inventoryValue) : "—"}
            subtext={`${totalProducts} SKUs`}
          />
        </div>

        {/* Revenue & Profit Trend */}
        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <SectionTitle>Revenue & Profit Trend</SectionTitle>
            <div className="flex gap-0.5 bg-muted rounded-lg p-0.5">
              {["day", "week", "month"].map((g) => (
                <button
                  key={g}
                  onClick={() => setTrendGroupBy(g)}
                  className={`text-xs px-3 py-1.5 rounded-md font-medium transition-all ${
                    trendGroupBy === g
                      ? "bg-card shadow-sm text-foreground"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {g.charAt(0).toUpperCase() + g.slice(1)}
                </button>
              ))}
            </div>
          </div>
          <div className="rounded-xl border border-border/60 bg-card/70 shadow-sm p-5">
            {trendSeries.length > 0 ? (
              <MultiLineChart
                data={trendSeries}
                xKey="date"
                series={[
                  { key: "revenue", label: "Revenue", color: t.info },
                  { key: "cost", label: "COGS", color: t.destructive, width: 1 },
                  { key: "profit", label: "Profit", color: t.success, width: 3 },
                ]}
                valueFormatter={valueFormatter}
                height={320}
                area
                stepped
              />
            ) : (
              <div className="h-[320px] flex items-center justify-center text-sm text-muted-foreground">
                No trend data for selected period
              </div>
            )}
          </div>
        </section>

        {/* P&L + Top Products */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <section className="space-y-3">
            <SectionTitle>Profit & Loss</SectionTitle>
            {summary ? (
              <PLStatement summary={summary} />
            ) : (
              <div className="rounded-xl border border-border/60 bg-card/70 p-6 text-sm text-muted-foreground text-center">
                No P&L data for selected period
              </div>
            )}
          </section>

          <section className="space-y-3">
            <SectionTitle>Top Products by Revenue</SectionTitle>
            <div className="rounded-xl border border-border/60 bg-card/70 shadow-sm p-5">
              {topProducts.length > 0 ? (
                <HorizontalBarChart
                  data={topProducts}
                  categoryKey="name"
                  series={[{ key: "revenue", label: "Revenue", color: t.category1 }]}
                  valueFormatter={valueFormatter}
                  height={Math.max(200, topProducts.length * 32)}
                  onBarClick={handleProductClick}
                />
              ) : (
                <div className="h-[200px] flex items-center justify-center text-sm text-muted-foreground">
                  No product data
                </div>
              )}
            </div>
          </section>
        </div>

        {/* AR Aging */}
        {arEntities.length > 0 && (
          <section className="space-y-3">
            <SectionTitle>Accounts Receivable Aging</SectionTitle>
            <ARAgingTable data={arEntities} />
          </section>
        )}

        {/* Inventory Health */}
        <section className="space-y-3">
          <SectionTitle>Inventory Health</SectionTitle>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            <KpiCard label="Total SKUs" value={totalProducts || "—"} />
            <KpiCard
              label="In Stock"
              value={totalProducts > 0 ? totalProducts - lowStockCount - outOfStockCount : "—"}
            />
            <KpiCard label="Low Stock" value={lowStockCount || "0"} warn={lowStockCount > 0} />
            <KpiCard
              label="Out of Stock"
              value={outOfStockCount || "0"}
              warn={outOfStockCount > 0}
            />
            <KpiCard label="Critical" value={criticalCount || "0"} warn={criticalCount > 0} />
            {kpis && (
              <KpiCard
                label="Turnover"
                value={`${kpis.inventory_turnover}×`}
                subtext={`${kpis.dio}d avg`}
              />
            )}
          </div>
        </section>
      </div>

      <ProductDetailModal
        product={selectedProduct}
        open={!!selectedProduct}
        onOpenChange={(open) => !open && setSelectedProduct(null)}
      />
    </div>
  );
};

export default Reports;
