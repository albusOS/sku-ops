import { useMemo } from "react";
import ReactECharts from "echarts-for-react";
import "../../lib/chartTheme";

const DEPT_COLORS = {
  Lumber: "#f59e0b",
  Plumbing: "#3b82f6",
  Electrical: "#8b5cf6",
  Paint: "#ec4899",
  Hardware: "#94a3b8",
  Tools: "#06b6d4",
  Garden: "#10b981",
  Appliances: "#fb923c",
};
const FALLBACK_COLOR = "#94a3b8";

/**
 * Bubble scatter plot: sell-through vs margin, sized by revenue, colored by department.
 * Includes quadrant labels for portfolio analysis.
 *
 * @param {object[]} products - from /reports/product-performance
 * @param {function} [onBubbleClick] - callback(product) when bubble clicked
 * @param {number} [height=420]
 */
export function ProductBubblePlot({
  products = [],
  onBubbleClick,
  height = 420,
}) {
  const option = useMemo(() => {
    if (!products.length) return {};

    const departments = [...new Set(products.map((p) => p.department || "Other"))];
    const maxRevenue = Math.max(...products.map((p) => p.revenue || 0), 1);

    const seriesList = departments.map((dept) => ({
      name: dept,
      type: "scatter",
      data: products
        .filter((p) => (p.department || "Other") === dept)
        .map((p) => ({
          value: [
            p.sell_through_pct || 0,
            p.margin_pct || 0,
            p.revenue || 0,
            p.name,
            p.sku,
            p.units_sold || 0,
            p.current_stock || 0,
            p.product_id,
          ],
          symbolSize: Math.max(8, Math.sqrt(p.revenue / maxRevenue) * 40),
        })),
      itemStyle: { color: DEPT_COLORS[dept] || FALLBACK_COLOR, opacity: 0.78 },
      emphasis: {
        itemStyle: {
          opacity: 1,
          borderColor: "#1e293b",
          borderWidth: 2,
          shadowBlur: 8,
          shadowColor: "rgba(0,0,0,.15)",
        },
      },
    }));

    const medianSellThrough =
      products.length > 0
        ? products
            .map((p) => p.sell_through_pct || 0)
            .sort((a, b) => a - b)[Math.floor(products.length / 2)]
        : 50;
    const medianMargin =
      products.length > 0
        ? products
            .map((p) => p.margin_pct || 0)
            .sort((a, b) => a - b)[Math.floor(products.length / 2)]
        : 40;

    return {
      tooltip: {
        formatter: (params) => {
          const [sellThrough, margin, revenue, name, sku, units, stock] =
            params.value;
          return `<div style="font-size:12px">
            <b>${name}</b> <span style="color:#94a3b8">${sku}</span><br/>
            Margin: <b>${margin.toFixed(1)}%</b><br/>
            Sell-through: <b>${sellThrough.toFixed(1)}%</b><br/>
            Revenue: <b>$${revenue.toLocaleString("en-US", { minimumFractionDigits: 2 })}</b><br/>
            ${units} sold · ${stock} in stock
          </div>`;
        },
      },
      legend: {
        bottom: 0,
        textStyle: { fontSize: 11, color: "#94a3b8" },
      },
      grid: { left: 48, right: 24, top: 32, bottom: 52, containLabel: false },
      xAxis: {
        name: "Sell-through %",
        nameLocation: "center",
        nameGap: 28,
        nameTextStyle: { fontSize: 11, color: "#94a3b8" },
        type: "value",
        min: 0,
        splitLine: { lineStyle: { color: "#f1f5f9" } },
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { fontSize: 11, color: "#94a3b8", formatter: "{value}%" },
      },
      yAxis: {
        name: "Margin %",
        nameLocation: "center",
        nameGap: 36,
        nameTextStyle: { fontSize: 11, color: "#94a3b8" },
        type: "value",
        splitLine: { lineStyle: { color: "#f1f5f9" } },
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { fontSize: 11, color: "#94a3b8", formatter: "{value}%" },
      },
      graphic: [
        {
          type: "text",
          left: 60,
          top: 36,
          style: { text: "Slow Movers", fontSize: 10, fill: "#cbd5e1" },
        },
        {
          type: "text",
          right: 36,
          top: 36,
          style: { text: "Stars", fontSize: 10, fill: "#86efac", fontWeight: 600 },
        },
        {
          type: "text",
          left: 60,
          bottom: 56,
          style: { text: "Review", fontSize: 10, fill: "#fca5a5" },
        },
        {
          type: "text",
          right: 36,
          bottom: 56,
          style: { text: "Volume Drivers", fontSize: 10, fill: "#cbd5e1" },
        },
      ],
      series: seriesList,
    };
  }, [products]);

  if (!products.length) return null;

  const handleEvents = onBubbleClick
    ? {
        click: (params) => {
          const productId = params.value?.[7];
          const product = products.find((p) => p.product_id === productId);
          if (product) onBubbleClick(product);
        },
      }
    : undefined;

  return (
    <ReactECharts
      option={option}
      style={{ height, width: "100%" }}
      theme="skuops"
      opts={{ renderer: "svg" }}
      onEvents={handleEvents}
      notMerge
    />
  );
}
