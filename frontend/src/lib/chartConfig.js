/**
 * Shared chart configuration for Tremor components.
 * Aligns with design tokens in index.css (--chart-1 through --chart-5).
 */
export const CHART_COLORS = ["orange", "slate", "emerald", "blue", "violet", "amber"];

export const valueFormatter = (v) =>
  `$${Number(v).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export const numberFormatter = (v) =>
  Number(v).toLocaleString("en-US");
