import { valueFormatter } from "@/lib/chartConfig";
import { themeColors } from "@/lib/chartTheme";

export const PaymentStrip = ({ data = [] }) => {
  const total = data.reduce((s, d) => s + d.value, 0) || 1;
  const t = themeColors();
  const palette = {
    Paid: t.success,
    Invoiced: t.info,
    Unpaid: t.category5,
    Unknown: t.mutedForeground,
  };
  return (
    <div>
      <div className="flex h-3 rounded-full overflow-hidden gap-px mb-3">
        {data.map((d) => (
          <div
            key={d.name}
            style={{
              width: `${(d.value / total) * 100}%`,
              backgroundColor: palette[d.name] || t.mutedForeground,
            }}
            title={`${d.name}: ${valueFormatter(d.value)}`}
          />
        ))}
      </div>
      <div className="flex flex-wrap gap-x-5 gap-y-1.5">
        {data.map((d) => (
          <div key={d.name} className="flex items-center gap-1.5">
            <div
              className="w-2 h-2 rounded-full shrink-0"
              style={{ backgroundColor: palette[d.name] || t.mutedForeground }}
            />
            <span className="text-xs text-muted-foreground">{d.name}</span>
            <span className="text-xs font-bold text-foreground tabular-nums">
              {valueFormatter(d.value)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};
