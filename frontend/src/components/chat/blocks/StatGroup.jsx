/**
 * Renders a stat_group block as a horizontal KPI strip.
 * Schema: { type: "stat_group", stats: [{ label, value, trend?, status? }] }
 */
export function StatGroup({ block }) {
  const stats = block.stats || [];
  if (!stats.length) return null;

  return (
    <div
      className="grid gap-2 my-2"
      style={{ gridTemplateColumns: `repeat(${Math.min(stats.length, 4)}, 1fr)` }}
    >
      {stats.map((s, i) => (
        <div
          key={i}
          className="rounded-lg px-3 py-2 bg-muted/50 border border-border/40 text-center"
        >
          <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-0.5">
            {s.label}
          </p>
          <p className="font-mono font-semibold text-sm text-foreground">{s.value}</p>
          {s.trend && (
            <p
              className={`text-[10px] mt-0.5 ${s.trend.startsWith("-") ? "text-destructive" : "text-success"}`}
            >
              {s.trend}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}
