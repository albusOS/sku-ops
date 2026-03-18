import "./chartTheme";

export const valueFormatter = (v) =>
  `$${Number(v).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
