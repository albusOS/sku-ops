export const LowStockList = ({ items = [] }) => (
  <div className="divide-y divide-border/50">
    {items.map((item, i) => {
      const pct = item.min_stock > 0 ? Math.min((item.quantity / item.min_stock) * 100, 100) : 0;
      const isEmpty = item.quantity === 0;
      return (
        <div key={i} className="py-3 flex items-center gap-3">
          <div
            className={`w-1.5 h-8 rounded-full shrink-0 ${isEmpty ? "bg-destructive" : "bg-category-5"}`}
          />
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between mb-1">
              <p className="text-sm font-medium text-foreground truncate">{item.name}</p>
              <span
                className={`text-sm font-bold tabular-nums ml-3 shrink-0 ${isEmpty ? "text-destructive" : "text-category-5"}`}
              >
                {item.quantity} left
              </span>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${isEmpty ? "bg-destructive" : "bg-category-5"}`}
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="text-[10px] text-muted-foreground w-16 text-right shrink-0 tabular-nums">
                min {item.min_stock}
              </span>
            </div>
          </div>
        </div>
      );
    })}
  </div>
);
