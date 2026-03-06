import * as echarts from "echarts/core";

const PALETTE = [
  "#f59e0b", // amber
  "#10b981", // emerald
  "#3b82f6", // blue
  "#fb923c", // orange
  "#8b5cf6", // violet
  "#ec4899", // pink
  "#06b6d4", // cyan
  "#84cc16", // lime
];

echarts.registerTheme("skuops", {
  color: PALETTE,
  backgroundColor: "transparent",
  textStyle: { fontFamily: "Inter, system-ui, sans-serif" },
  title: {
    textStyle: { fontSize: 14, fontWeight: 600, color: "#1e293b" },
    subtextStyle: { fontSize: 11, color: "#94a3b8" },
  },
  legend: {
    bottom: 0,
    icon: "circle",
    itemWidth: 8,
    itemHeight: 8,
    itemGap: 16,
    textStyle: { fontSize: 11, color: "#94a3b8" },
  },
  tooltip: {
    backgroundColor: "#1e293b",
    borderColor: "#334155",
    borderWidth: 1,
    textStyle: { fontSize: 12, color: "#f1f5f9" },
    extraCssText:
      "border-radius:8px;box-shadow:0 4px 20px rgba(0,0,0,.18);padding:10px 14px;",
  },
  grid: {
    left: 12,
    right: 12,
    top: 12,
    bottom: 36,
    containLabel: true,
  },
  categoryAxis: {
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: { fontSize: 11, color: "#94a3b8" },
    splitLine: { show: false },
  },
  valueAxis: {
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: { fontSize: 11, color: "#94a3b8" },
    splitLine: { lineStyle: { color: "#f1f5f9" } },
  },
  line: {
    smooth: false,
    symbolSize: 4,
    lineStyle: { width: 2 },
  },
  bar: {
    barMaxWidth: 20,
    itemStyle: { borderRadius: [0, 3, 3, 0] },
  },
});

export { PALETTE };
