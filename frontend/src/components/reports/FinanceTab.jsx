import { useMemo } from "react";
import { Building2, ChevronDown, ChevronRight } from "lucide-react";
import { valueFormatter } from "@/lib/chartConfig";
import { themeColors } from "@/lib/chartTheme";
import { StatCard } from "@/components/StatCard";
import { StackedBarChart } from "@/components/charts/StackedBarChart";
import { ReportPanel, ReportSectionHead } from "@/components/ReportPanel";
import { ARAgingTable } from "./ARAgingTable";

const SectionHead = ({ title, action }) => <ReportSectionHead title={title} action={action} />;

export const FinanceTab = ({ financialSummary, arAging, arAgingOpen, setArAgingOpen }) => {
  const t = themeColors();
  const arAgingByEntity = useMemo(() => {
    if (!arAging) return {};
    const map = {};
    for (const row of arAging) map[row.billing_entity] = row;
    return map;
  }, [arAging]);

  return (
    <div className="space-y-6">
      {financialSummary && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <StatCard
            label="Total Revenue"
            value={valueFormatter(financialSummary.total_revenue || 0)}
            accent="emerald"
          />
          <StatCard
            label="Gross Margin"
            value={valueFormatter(financialSummary.gross_margin || 0)}
            accent="violet"
          />
          <StatCard
            label="Total Cost"
            value={valueFormatter(financialSummary.total_cost || 0)}
            accent="orange"
          />
          <StatCard
            label="Transactions"
            value={financialSummary.transaction_count || 0}
            accent="blue"
          />
        </div>
      )}

      {financialSummary?.by_billing_entity &&
        Object.keys(financialSummary.by_billing_entity).length > 0 && (
          <ReportPanel>
            <SectionHead title="By Billing Entity" />
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {Object.entries(financialSummary.by_billing_entity).map(([entity, data]) => {
                const aging = arAgingByEntity[entity];
                const hasOverdue90 =
                  aging && ((aging.overdue_61_90 || 0) > 0 || (aging.overdue_90_plus || 0) > 0);
                const hasOverdue30 = aging && (aging.overdue_31_60 || 0) > 0;
                const hasOverdue = aging && (aging.overdue_1_30 || 0) > 0;
                const badgeColor = hasOverdue90
                  ? "bg-destructive/15 text-destructive border-destructive/30"
                  : hasOverdue30
                    ? "bg-category-5/15 text-category-5 border-category-5/30"
                    : hasOverdue
                      ? "bg-accent/15 text-accent border-accent/30"
                      : null;
                const badgeLabel = hasOverdue90
                  ? "60d+ overdue"
                  : hasOverdue30
                    ? "31\u201360d overdue"
                    : hasOverdue
                      ? "1\u201330d overdue"
                      : null;
                return (
                  <div key={entity} className="p-3 bg-muted rounded-lg border border-border/50">
                    <div className="flex items-center gap-2 mb-2">
                      <Building2 className="w-3.5 h-3.5 text-muted-foreground" />
                      <span className="text-sm font-semibold text-foreground flex-1 truncate">
                        {entity}
                      </span>
                      {badgeColor && (
                        <span
                          className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full border ${badgeColor}`}
                        >
                          {badgeLabel}
                        </span>
                      )}
                    </div>
                    <div className="space-y-0.5 text-xs">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Revenue</span>
                        <span className="font-mono tabular-nums">
                          ${(data.total ?? 0).toFixed(2)}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">AR Balance</span>
                        <span className="font-mono tabular-nums text-accent">
                          ${(data.ar_balance ?? 0).toFixed(2)}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Txns</span>
                        <span className="font-mono tabular-nums">{data.count}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </ReportPanel>
        )}

      {arAging?.length > 0 && (
        <ReportPanel>
          <SectionHead title="AR Aging by Entity" />
          <StackedBarChart
            data={arAging.map((r) => ({
              name: r.billing_entity,
              current: r.current_not_due || 0,
              "1-30d": r.overdue_1_30 || 0,
              "31-60d": r.overdue_31_60 || 0,
              "61-90d": r.overdue_61_90 || 0,
              "90d+": r.overdue_90_plus || 0,
            }))}
            categoryKey="name"
            series={[
              { key: "current", label: "Current", color: t.success },
              { key: "1-30d", label: "1\u201330d", color: t.warning },
              { key: "31-60d", label: "31\u201360d", color: t.category5 },
              { key: "61-90d", label: "61\u201390d", color: t.destructive },
              { key: "90d+", label: "90d+", color: t.destructive },
            ]}
            valueFormatter={valueFormatter}
            height={Math.max(200, arAging.length * 40)}
          />
        </ReportPanel>
      )}

      {arAging?.length > 0 && (
        <div>
          <button
            onClick={() => setArAgingOpen(!arAgingOpen)}
            className="flex items-center gap-2 text-sm font-semibold text-foreground hover:text-foreground mb-3"
          >
            {arAgingOpen ? (
              <ChevronDown className="w-4 h-4" />
            ) : (
              <ChevronRight className="w-4 h-4" />
            )}
            AR Aging Detail
            <span className="text-xs font-normal text-muted-foreground">
              ({arAging.length} entities)
            </span>
          </button>
          {arAgingOpen && <ARAgingTable data={arAging} />}
        </div>
      )}
    </div>
  );
};
