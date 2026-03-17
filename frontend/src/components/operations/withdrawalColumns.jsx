import { HardHat } from "lucide-react";
import { StatusBadge } from "@/components/StatusBadge";

export function buildWithdrawalColumns(onViewJob) {
  return [
    {
      key: "created_at",
      label: "Date",
      type: "date",
      render: (row) => (
        <span className="font-mono text-xs text-muted-foreground">
          {new Date(row.created_at).toLocaleDateString()}
        </span>
      ),
      exportValue: (row) => row.created_at,
    },
    {
      key: "contractor_name",
      label: "Contractor",
      type: "text",
      render: (row) => (
        <div className="flex items-center gap-2">
          <HardHat className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
          <div>
            <p className="font-medium text-foreground">{row.contractor_name}</p>
            <p className="text-[10px] text-muted-foreground">{row.contractor_company}</p>
          </div>
        </div>
      ),
      exportValue: (row) => `${row.contractor_name} (${row.contractor_company || ""})`,
    },
    {
      key: "job_id",
      label: "Job",
      type: "text",
      render: (row) =>
        row.job_id ? (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onViewJob(row.job_id);
            }}
            className="font-mono text-xs text-info hover:text-info hover:underline"
          >
            {row.job_id}
          </button>
        ) : (
          <span className="text-xs text-muted-foreground">—</span>
        ),
    },
    { key: "billing_entity", label: "Entity", type: "enum" },
    {
      key: "total",
      label: "Total",
      type: "number",
      align: "right",
      render: (row) => (
        <span className="font-semibold tabular-nums">${(row.total || 0).toFixed(2)}</span>
      ),
      exportValue: (row) => (row.total || 0).toFixed(2),
    },
    {
      key: "cost_total",
      label: "Cost",
      type: "number",
      align: "right",
      render: (row) => (
        <span className="text-muted-foreground tabular-nums">
          ${(row.cost_total || 0).toFixed(2)}
        </span>
      ),
      exportValue: (row) => (row.cost_total || 0).toFixed(2),
    },
    {
      key: "_margin",
      label: "Margin",
      type: "number",
      sortable: false,
      filterable: false,
      searchable: false,
      render: (row) => (
        <span className="text-success tabular-nums">
          ${((row.total || 0) - (row.cost_total || 0)).toFixed(2)}
        </span>
      ),
      exportValue: (row) => ((row.total || 0) - (row.cost_total || 0)).toFixed(2),
    },
    {
      key: "_invoice_status",
      label: "Status",
      type: "enum",
      sortable: false,
      filterable: false,
      render: (row) =>
        row.invoice_id ? (
          <span className="inline-block">
            <StatusBadge status="invoiced" />
          </span>
        ) : (
          <StatusBadge status="uninvoiced" />
        ),
      exportValue: (row) => (row.invoice_id ? "invoiced" : "uninvoiced"),
    },
  ];
}
