import { useMemo } from "react";
import { valueFormatter } from "@/lib/chartConfig";
import { DataTable } from "@/components/DataTable";

export const PL_DIMENSIONS = [
  { value: "overall", label: "Overall" },
  { value: "job", label: "By Job" },
  { value: "department", label: "By Category" },
  { value: "entity", label: "By Entity" },
  { value: "product", label: "By Product" },
];

const PL_COLUMNS = {
  job: { label: "Job ID", key: "job_id", secondary: "billing_entity" },
  department: { label: "Category", key: "department" },
  entity: { label: "Billing Entity", key: "billing_entity" },
  product: { label: "Product", key: "name" },
};

export const PLBreakdownTable = ({ plDimension, rows, onRowClick, selectedId, totalRows }) => {
  const colCfg = PL_COLUMNS[plDimension];
  const columns = useMemo(() => {
    const cols = [
      {
        key: colCfg?.key || "name",
        label: colCfg?.label || "Name",
        render: (row) => (
          <span className="font-medium text-foreground truncate max-w-[200px] block">
            {onRowClick && <span className="text-accent mr-1">&#x25B8;</span>}
            {row[colCfg?.key] || "\u2014"}
          </span>
        ),
      },
    ];
    if (plDimension === "job") {
      cols.push(
        {
          key: "billing_entity",
          label: "Customer",
          render: (row) => (
            <span className="text-muted-foreground truncate max-w-[160px] block">
              {row.billing_entity || "\u2014"}
            </span>
          ),
        },
        {
          key: "withdrawal_count",
          label: "Orders",
          align: "right",
          render: (row) => (
            <span className="tabular-nums text-muted-foreground">
              {row.withdrawal_count || row.transaction_count}
            </span>
          ),
        },
      );
    }
    cols.push(
      {
        key: "revenue",
        label: "Revenue",
        align: "right",
        render: (row) => (
          <span className="tabular-nums font-semibold text-foreground">
            {valueFormatter(row.revenue)}
          </span>
        ),
      },
      {
        key: "cost",
        label: "COGS",
        align: "right",
        render: (row) => (
          <span className="tabular-nums text-muted-foreground">{valueFormatter(row.cost)}</span>
        ),
      },
      {
        key: "profit",
        label: "Profit",
        align: "right",
        render: (row) => (
          <span className="tabular-nums font-semibold text-foreground">
            {valueFormatter(row.profit)}
          </span>
        ),
      },
      {
        key: "margin_pct",
        label: "Margin",
        align: "right",
        render: (row) => {
          const isHigh = (row.margin_pct || 0) >= 40;
          const isLow = (row.margin_pct || 0) < 30;
          return (
            <span
              className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold tabular-nums ${isHigh ? "bg-success/10 text-success" : isLow ? "bg-category-5/10 text-category-5" : "bg-info/10 text-info"}`}
            >
              {row.margin_pct}%
            </span>
          );
        },
      },
    );
    return cols;
  }, [plDimension, colCfg, onRowClick]);

  const dataWithId = useMemo(
    () => rows.map((r, i) => ({ ...r, id: r[colCfg?.key] || i })),
    [rows, colCfg],
  );
  const selectedSet = useMemo(() => (selectedId ? new Set([selectedId]) : new Set()), [selectedId]);

  return (
    <DataTable
      data={dataWithId}
      columns={columns}
      title={`${PL_DIMENSIONS.find((d) => d.value === plDimension)?.label || plDimension}${totalRows != null ? ` \u2014 ${totalRows} total` : ""}`}
      emptyMessage="No P&L data"
      searchable
      exportable
      exportFilename={`pl-${plDimension}.csv`}
      pageSize={20}
      onRowClick={onRowClick}
      selectedIds={selectedSet}
    />
  );
};
