import { AlertTriangle, Flame } from "lucide-react";

export const LowStockList = ({ items = [] }) => (
  <div className="space-y-1">
    {items.map((item, i) => {
      const pct = item.min_stock > 0 ? Math.min((item.quantity / item.min_stock) * 100, 100) : 0;
      const isEmpty = item.quantity === 0;
      const isCritical = isEmpty || pct < 25;
      return (
        <div
          key={i}
          className={`py-3 px-3 flex items-center gap-3 rounded-lg transition-colors ${
            isEmpty
              ? "bg-destructive/[0.04] border border-destructive/15"
              : isCritical
                ? "bg-warning/[0.03] border border-warning/10"
                : "border border-transparent"
          }`}
        >
          <div className="shrink-0 w-5 flex items-center justify-center">
            {isEmpty ? (
              <span className="relative flex h-2.5 w-2.5">
                <span className="absolute inset-0 rounded-full bg-destructive animate-ping opacity-40" />
                <span className="relative rounded-full h-2.5 w-2.5 bg-destructive" />
              </span>
            ) : isCritical ? (
              <Flame className="w-3.5 h-3.5 text-destructive/70" />
            ) : (
              <AlertTriangle className="w-3.5 h-3.5 text-warning/70" />
            )}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between mb-1">
              <p className="text-sm font-medium text-foreground truncate">{item.name}</p>
              <div className="flex items-center gap-2 ml-3 shrink-0">
                {isEmpty ? (
                  <span className="text-[10px] font-bold text-destructive bg-destructive/10 px-2 py-0.5 rounded-full">
                    Out of stock
                  </span>
                ) : (
                  <span
                    className={`text-sm font-bold tabular-nums ${isCritical ? "text-destructive" : "text-warning"}`}
                  >
                    {item.quantity}
                  </span>
                )}
                <span className="text-[10px] text-muted-foreground/60 tabular-nums">
                  / {item.min_stock}
                </span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${
                    isEmpty ? "bg-destructive" : isCritical ? "bg-destructive/70" : "bg-warning"
                  }`}
                  style={{ width: `${Math.max(pct, isEmpty ? 0 : 2)}%` }}
                />
              </div>
            </div>
          </div>
        </div>
      );
    })}
  </div>
);
