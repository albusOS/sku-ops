import { MultiLineChart } from "@/components/charts/MultiLineChart";
import { HorizontalBarChart } from "@/components/charts/HorizontalBarChart";
import { StackedBarChart } from "@/components/charts/StackedBarChart";
import { GaugeRing } from "@/components/charts/GaugeRing";

/**
 * Renders a chart block inline in the chat panel.
 *
 * Schema:
 * {
 *   type: "chart",
 *   chart_type: "line" | "bar" | "stacked_bar" | "gauge",
 *   title?: string,
 *   data: object[],
 *   x_key?: string,
 *   category_key?: string,
 *   series: { key: string, label: string, color?: string }[],
 *   value_format?: "currency" | "percent" | "number",
 *   // gauge-specific:
 *   value?: number,
 *   max?: number,
 *   label?: string,
 *   unit?: string,
 * }
 */

const PALETTE = [
  "var(--category-1)",
  "var(--category-2)",
  "var(--category-3)",
  "var(--category-4)",
  "var(--category-5)",
  "var(--category-6)",
  "var(--category-7)",
  "var(--category-8)",
];

function makeFormatter(format) {
  if (format === "currency") return (v) => `$${Number(v).toLocaleString()}`;
  if (format === "percent") return (v) => `${v}%`;
  return (v) => String(v);
}

function colorize(series) {
  return series.map((s, i) => ({
    ...s,
    color: s.color || PALETTE[i % PALETTE.length],
  }));
}

export function InlineChart({ block }) {
  const {
    chart_type,
    title,
    data = [],
    x_key = "date",
    category_key = "name",
    series = [],
    value_format = "number",
    value,
    max,
    label,
    unit,
  } = block;

  const formatter = makeFormatter(value_format);
  const coloredSeries = colorize(series);

  return (
    <div className="my-2">
      {title && (
        <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-muted-foreground mb-1.5">
          {title}
        </p>
      )}
      <div className="rounded-lg border border-border/40 bg-surface/50 p-2 overflow-hidden">
        {chart_type === "line" && (
          <MultiLineChart
            data={data}
            xKey={x_key}
            series={coloredSeries}
            valueFormatter={formatter}
            height={200}
            area
          />
        )}
        {chart_type === "bar" && (
          <HorizontalBarChart
            data={data}
            categoryKey={category_key}
            series={coloredSeries}
            valueFormatter={formatter}
            height={Math.min(data.length * 32 + 40, 250)}
          />
        )}
        {chart_type === "stacked_bar" && (
          <StackedBarChart
            data={data}
            categoryKey={category_key}
            series={coloredSeries}
            valueFormatter={formatter}
            height={Math.min(data.length * 32 + 60, 250)}
          />
        )}
        {chart_type === "gauge" && (
          <div className="flex justify-center">
            <GaugeRing
              value={value ?? 0}
              max={max ?? 100}
              label={label ?? ""}
              unit={unit ?? ""}
              size={140}
            />
          </div>
        )}
      </div>
    </div>
  );
}
