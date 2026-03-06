import "./chartTheme";

export const valueFormatter = (v) =>
  `$${Number(v).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export const pctFormatter = (v) => `${Number(v).toFixed(1)}%`;
export const intFormatter = (v) => Number(v).toLocaleString("en-US");
