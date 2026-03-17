import { useState, useMemo } from "react";
import { valueFormatter } from "@/lib/chartConfig";
import { themeColors } from "@/lib/chartTheme";
import { useReportInventory, useReportKpis, useReportReorderUrgency } from "@/hooks/useReports";
import { LollipopChart } from "@/components/charts/LollipopChart";
import { LowStockList } from "../LowStockList";
import { BentoCard } from "../BentoCard";
import { ReportDetailModal, Narrative } from "../ReportDetailModal";

function CoverageRunway({ reorderProducts = [], inventoryReport }) {
  const t = themeColors();

  const categoryRunway = useMemo(() => {
    const byDept = {};
    for (const p of reorderProducts) {
      const dept = p.department || "Other";
      if (!byDept[dept]) byDept[dept] = { minDays: Infinity, count: 0, critical: 0 };
      byDept[dept].count++;
      if (p.days_until_stockout != null) {
        byDept[dept].minDays = Math.min(byDept[dept].minDays, p.days_until_stockout);
      }
      if (p.urgency === "critical" || p.urgency === "high") byDept[dept].critical++;
    }

    if (inventoryReport?.by_department) {
      for (const dept of Object.keys(inventoryReport.by_department)) {
        if (!byDept[dept]) byDept[dept] = { minDays: Infinity, count: 0, critical: 0 };
      }
    }

    return Object.entries(byDept)
      .map(([name, data]) => ({
        name,
        days: data.minDays === Infinity ? null : data.minDays,
        count: data.count,
        critical: data.critical,
      }))
      .sort((a, b) => {
        if (a.days == null && b.days == null) return 0;
        if (a.days == null) return 1;
        if (b.days == null) return -1;
        return a.days - b.days;
      });
  }, [reorderProducts, inventoryReport]);

  if (!categoryRunway.length) {
    return (
      <div className="text-sm text-muted-foreground text-center py-4">All stock levels healthy</div>
    );
  }

  const maxDays = Math.max(...categoryRunway.map((c) => c.days ?? 0), 30);

  return (
    <div className="space-y-2">
      {categoryRunway.slice(0, 8).map((cat) => {
        const pct = cat.days != null ? Math.min((cat.days / maxDays) * 100, 100) : 100;
        const color =
          cat.days != null && cat.days <= 3
            ? t.destructive
            : cat.days != null && cat.days <= 7
              ? t.warning
              : cat.days != null && cat.days <= 30
                ? t.category5
                : t.success;
        const label = cat.days != null ? `${cat.days}d` : "OK";

        return (
          <div key={cat.name} className="flex items-center gap-3">
            <span className="text-xs text-muted-foreground truncate w-20 shrink-0 text-right">
              {cat.name.length > 12 ? cat.name.slice(0, 10) + "…" : cat.name}
            </span>
            <div className="flex-1 h-4 bg-muted rounded-full overflow-hidden relative">
              <div
                className="h-full rounded-full transition-all"
                style={{ width: `${pct}%`, background: color }}
              />
            </div>
            <span
              className="text-xs font-bold tabular-nums w-10 text-right shrink-0"
              style={{ color }}
            >
              {label}
            </span>
            {cat.critical > 0 && (
              <span className="text-[10px] font-bold text-destructive bg-destructive/10 px-1.5 py-0.5 rounded-full shrink-0">
                {cat.critical}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}

export function InventoryHealthCard({ dateParams, onProductClick }) {
  const [open, setOpen] = useState(false);
  const { data: inventoryReport } = useReportInventory();
  const { data: kpis } = useReportKpis(dateParams);
  const { data: reorderData } = useReportReorderUrgency();

  const reorderProducts = useMemo(() => reorderData?.products || [], [reorderData]);
  const lollipopData = useMemo(
    () =>
      reorderProducts.map((p) => ({
        name: p.name,
        value: p.days_until_stockout,
        urgency: p.urgency,
        id: p.sku_id,
        ...p,
      })),
    [reorderProducts],
  );

  const totalProducts = inventoryReport?.total_products || 0;
  const lowCount = inventoryReport?.low_stock_count || 0;
  const outCount = inventoryReport?.out_of_stock_count || 0;
  const inStock = totalProducts - lowCount - outCount;
  const criticalCount = reorderProducts.filter(
    (p) => p.urgency === "critical" || p.urgency === "high",
  ).length;

  const lowestDays = useMemo(() => {
    const withDays = reorderProducts.filter((p) => p.days_until_stockout != null);
    if (!withDays.length) return null;
    return Math.min(...withDays.map((p) => p.days_until_stockout));
  }, [reorderProducts]);

  const narrativeItems = useMemo(() => {
    const items = [];
    items.push(
      `${totalProducts} total products: ${inStock} in stock, ${lowCount} low, ${outCount} out of stock.`,
    );
    if (criticalCount > 0)
      items.push(`${criticalCount} items critically low — reorder immediately.`);
    if (lowestDays != null) items.push(`Shortest runway: ${lowestDays} days until stockout.`);
    if (kpis) {
      items.push(`Inventory turnover: ${kpis.inventory_turnover}× over ${kpis.period_days} days.`);
      items.push(`Days in inventory: ${kpis.dio} days average.`);
      if (kpis.sell_through_pct != null)
        items.push(`Sell-through rate: ${kpis.sell_through_pct}%.`);
    }
    if (inventoryReport?.total_retail_value)
      items.push(`Total retail value: ${valueFormatter(inventoryReport.total_retail_value)}.`);
    return items;
  }, [
    totalProducts,
    inStock,
    lowCount,
    outCount,
    criticalCount,
    lowestDays,
    kpis,
    inventoryReport,
  ]);

  const insight = inventoryReport
    ? criticalCount > 0
      ? `${criticalCount} items critical · shortest runway ${lowestDays ?? "—"}d`
      : "All stock levels healthy"
    : "Loading...";

  const cardStatus =
    outCount > 0 ? "danger" : criticalCount > 0 ? "warn" : lowCount > 0 ? "warn" : "healthy";

  return (
    <>
      <BentoCard
        title="Inventory Health"
        metric={totalProducts > 0 ? `${totalProducts} SKUs` : "—"}
        insight={insight}
        status={cardStatus}
        size="medium"
        onClick={() => setOpen(true)}
      >
        <CoverageRunway reorderProducts={reorderProducts} inventoryReport={inventoryReport} />
      </BentoCard>

      <ReportDetailModal
        open={open}
        onClose={() => setOpen(false)}
        title="Inventory Health"
        subtitle="Stock coverage runway by category — shorter bars need attention first"
      >
        <CoverageRunway reorderProducts={reorderProducts} inventoryReport={inventoryReport} />

        {kpis && (
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-muted/40 rounded-xl p-4 text-center">
              <p className="text-xl font-bold text-foreground tabular-nums">
                {kpis.inventory_turnover}×
              </p>
              <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-wide mt-1">
                Turnover
              </p>
            </div>
            <div className="bg-muted/40 rounded-xl p-4 text-center">
              <p className="text-xl font-bold text-foreground tabular-nums">{kpis.dio} days</p>
              <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-wide mt-1">
                Days in Inventory
              </p>
            </div>
            <div className="bg-muted/40 rounded-xl p-4 text-center">
              <p className="text-xl font-bold text-foreground tabular-nums">
                {kpis.sell_through_pct ?? "—"}%
              </p>
              <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-wide mt-1">
                Sell-Through
              </p>
            </div>
          </div>
        )}

        <div className="grid grid-cols-3 gap-3 text-center">
          <div className="rounded-xl border border-success/30 bg-success/5 p-4 shadow-[inset_0_1px_0_0_rgb(16_185_129/0.1)]">
            <p className="text-xl font-bold text-success tabular-nums">{inStock}</p>
            <p className="text-[10px] text-muted-foreground font-medium uppercase mt-1">In Stock</p>
          </div>
          <div className="rounded-xl border border-warning/30 bg-warning/5 p-4 shadow-[inset_0_1px_0_0_rgb(245_158_11/0.1)]">
            <p className="text-xl font-bold text-warning tabular-nums">{lowCount}</p>
            <p className="text-[10px] text-muted-foreground font-medium uppercase mt-1">Low</p>
          </div>
          <div
            className={`rounded-xl border p-4 ${outCount > 0 ? "border-destructive/40 bg-destructive/[0.07] shadow-[0_0_12px_-3px_rgb(220_38_38/0.2),inset_0_1px_0_0_rgb(220_38_38/0.1)]" : "border-destructive/20 bg-destructive/5"}`}
          >
            <div className="flex items-center justify-center gap-1.5">
              <p className="text-xl font-bold text-destructive tabular-nums">{outCount}</p>
              {outCount > 0 && (
                <span className="relative flex h-2 w-2">
                  <span className="absolute inset-0 rounded-full bg-destructive animate-ping opacity-50" />
                  <span className="relative rounded-full h-2 w-2 bg-destructive" />
                </span>
              )}
            </div>
            <p className="text-[10px] text-muted-foreground font-medium uppercase mt-1">
              Out of Stock
            </p>
          </div>
        </div>

        {lollipopData.length > 0 && (
          <div>
            <h4 className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground mb-3">
              Reorder Urgency — Days to Stockout
            </h4>
            <LollipopChart
              data={lollipopData.slice(0, 15)}
              valueLabel="days"
              onDotClick={onProductClick}
              height={Math.max(200, Math.min(lollipopData.length, 15) * 28)}
            />
          </div>
        )}

        {inventoryReport?.low_stock_items?.length > 0 && (
          <div>
            <h4 className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground mb-3">
              Low Stock Items
            </h4>
            <div className="max-h-[300px] overflow-auto">
              <LowStockList items={inventoryReport.low_stock_items} />
            </div>
          </div>
        )}

        <Narrative items={narrativeItems} />
      </ReportDetailModal>
    </>
  );
}
