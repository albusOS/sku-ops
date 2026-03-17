import { useMemo } from "react";
import { valueFormatter } from "@/lib/chartConfig";
import { DataTable } from "@/components/DataTable";

const AR_AGING_COLUMNS = [
  {
    key: "billing_entity",
    label: "Entity",
    render: (row) => <span className="font-medium text-foreground">{row.billing_entity}</span>,
  },
  {
    key: "total_ar",
    label: "Total AR",
    align: "right",
    render: (row) => (
      <span className="tabular-nums font-semibold">{valueFormatter(row.total_ar)}</span>
    ),
  },
  {
    key: "current_not_due",
    label: "Current",
    align: "right",
    render: (row) => (
      <span className="tabular-nums text-muted-foreground">
        {valueFormatter(row.current_not_due)}
      </span>
    ),
  },
  {
    key: "overdue_1_30",
    label: "1\u201330d",
    align: "right",
    render: (row) => (
      <span className="tabular-nums text-accent">{valueFormatter(row.overdue_1_30)}</span>
    ),
  },
  {
    key: "overdue_31_60",
    label: "31\u201360d",
    align: "right",
    render: (row) => (
      <span className="tabular-nums text-accent">{valueFormatter(row.overdue_31_60)}</span>
    ),
  },
  {
    key: "overdue_61_90",
    label: "61\u201390d",
    align: "right",
    render: (row) => (
      <span className="tabular-nums text-category-5">{valueFormatter(row.overdue_61_90)}</span>
    ),
  },
  {
    key: "overdue_90_plus",
    label: "90d+",
    align: "right",
    render: (row) => (
      <span className="tabular-nums text-destructive font-semibold">
        {valueFormatter(row.overdue_90_plus)}
      </span>
    ),
  },
];

export const ARAgingTable = ({ data }) => {
  const dataWithId = useMemo(
    () => data.map((r, i) => ({ ...r, id: r.billing_entity || i })),
    [data],
  );
  return (
    <DataTable
      data={dataWithId}
      columns={AR_AGING_COLUMNS}
      title="Accounts Receivable Aging"
      emptyMessage="No AR data"
      searchable
      exportable
      exportFilename="ar-aging.csv"
    />
  );
};
