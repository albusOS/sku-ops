import { valueFormatter } from "@/lib/chartConfig";

export const PLStatement = ({ summary }) => {
  if (!summary) return null;
  const revenue = summary.revenue || 0;
  const cogs = summary.cogs || 0;
  const grossProfit = summary.gross_profit || revenue - cogs;
  const tax = summary.tax_collected || 0;
  const shrinkage = summary.shrinkage || 0;
  const netProfit = grossProfit - tax - shrinkage;
  const marginPct =
    summary.margin_pct || (revenue > 0 ? ((grossProfit / revenue) * 100).toFixed(1) : 0);

  const Line = ({ label, value, bold, indent, muted }) => (
    <div className={`flex items-center justify-between py-2 ${indent ? "pl-6" : ""}`}>
      <span
        className={`text-sm ${bold ? "font-semibold text-foreground" : muted ? "text-muted-foreground" : "text-muted-foreground"}`}
      >
        {label}
      </span>
      <span
        className={`text-sm tabular-nums font-mono ${bold ? "font-bold text-foreground" : muted ? "text-muted-foreground" : "text-foreground"}`}
      >
        {valueFormatter(value)}
      </span>
    </div>
  );

  return (
    <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
      <Line label="REVENUE" value={revenue} bold />
      <Line label="Cost of Goods Sold" value={cogs} indent />
      <div className="border-t border-border my-1" />
      <div className="flex items-center justify-between py-2">
        <span className="text-sm font-semibold text-foreground">GROSS PROFIT</span>
        <div className="flex items-center gap-3">
          <span className="text-sm tabular-nums font-mono font-bold text-foreground">
            {valueFormatter(grossProfit)}
          </span>
          <span
            className={`text-xs font-bold px-2 py-0.5 rounded-full ${parseFloat(marginPct) >= 40 ? "bg-success/10 text-success" : parseFloat(marginPct) < 30 ? "bg-category-5/10 text-category-5" : "bg-info/10 text-info"}`}
          >
            {marginPct}%
          </span>
        </div>
      </div>
      {tax > 0 && <Line label="Tax Collected" value={tax} indent muted />}
      {shrinkage > 0 && <Line label="Shrinkage" value={shrinkage} indent muted />}
      {(tax > 0 || shrinkage > 0) && (
        <>
          <div className="border-t border-border my-1" />
          <Line label="NET OPERATING PROFIT" value={netProfit} bold />
        </>
      )}
    </div>
  );
};
