import {
  FileUp,
  PackageCheck,
  Warehouse,
  ClipboardList,
  ScanLine,
  ShoppingCart,
  Receipt,
  FileText,
  RefreshCw,
  CreditCard,
  ListChecks,
  SlidersHorizontal,
  BarChart3,
  Sparkles,
} from "lucide-react";

const GAP = 220;
const X0 = 40;
const Y0 = 50;
const Y1 = 130;

function pos(col, row = 0) {
  return { x: X0 + col * GAP, y: row === 0 ? Y0 : Y1 };
}

function nodes(raw) {
  return raw.map((n, i) => ({
    id: n.id,
    type: "workflowNode",
    position: n.position ?? pos(i),
    data: {
      label: n.label,
      icon: n.icon,
      route: n.route,
      prompt: n.prompt,
      nodeType: n.nodeType ?? "action",
      hint: n.hint,
    },
  }));
}

function edges(raw) {
  return raw.map((e) => ({
    id: `${e.source}-${e.target}`,
    source: e.source,
    target: e.target,
    label: e.label,
    type: "default",
    animated: true,
    style: { stroke: "hsl(var(--muted-foreground))", strokeWidth: 1.5, opacity: 0.4 },
    labelStyle: { fill: "hsl(var(--muted-foreground))", fontSize: 10, fontWeight: 500 },
    labelBgStyle: { fill: "hsl(var(--surface))", fillOpacity: 0.9 },
  }));
}

const WORKFLOWS = {
  restock: {
    label: "Restock",
    description: "Vendor deliveries into inventory.",
    nodes: nodes([
      {
        id: "import",
        label: "Import Invoice",
        icon: FileUp,
        route: "/purchasing",
        hint: "Upload a vendor invoice — AI extracts items into a purchase order.",
      },
      {
        id: "receive",
        label: "Receive Stock",
        icon: PackageCheck,
        route: "/purchasing",
        hint: "Mark items received at the dock. Quantities update automatically.",
      },
      {
        id: "live",
        label: "Inventory Live",
        icon: Warehouse,
        route: "/inventory",
        nodeType: "outcome",
        hint: "Products are in stock and available for issue.",
      },
    ]),
    edges: edges([
      { source: "import", target: "receive" },
      { source: "receive", target: "live" },
    ]),
  },

  issue: {
    label: "Issue Materials",
    description: "Contractors get materials charged to account.",
    nodes: nodes([
      {
        id: "request",
        label: "Request",
        icon: ClipboardList,
        route: "/pos",
        position: pos(0, 0),
        hint: "Contractor submits a material request from the field.",
      },
      {
        id: "walkup",
        label: "Walk-Up",
        icon: ScanLine,
        route: "/pos/scan",
        position: pos(0, 1),
        hint: "Contractor walks in — scan items at the counter.",
      },
      {
        id: "issue",
        label: "Issue",
        icon: ShoppingCart,
        route: "/pos/issue",
        position: pos(1.5),
        hint: "Process and issue materials. Stock is decremented.",
      },
      {
        id: "charged",
        label: "Charged",
        icon: Receipt,
        nodeType: "outcome",
        position: pos(2.5),
        hint: "Withdrawal recorded — ready for invoicing.",
      },
    ]),
    edges: edges([
      { source: "request", target: "issue" },
      { source: "walkup", target: "issue" },
      { source: "issue", target: "charged" },
    ]),
  },

  billing: {
    label: "Billing",
    description: "Withdrawals become invoices synced to Xero.",
    nodes: nodes([
      {
        id: "invoice",
        label: "Create Invoice",
        icon: FileText,
        route: "/pos",
        hint: "Group uninvoiced withdrawals and generate an invoice.",
      },
      {
        id: "sync",
        label: "Sync to Xero",
        icon: RefreshCw,
        route: "/xero-health",
        hint: "Push to Xero for accounting. Status syncs back.",
      },
      {
        id: "paid",
        label: "Paid",
        icon: CreditCard,
        nodeType: "outcome",
        hint: "Payment recorded. Supports partial payments.",
      },
    ]),
    edges: edges([
      { source: "invoice", target: "sync" },
      { source: "sync", target: "paid" },
    ]),
  },

  inventory: {
    label: "Inventory",
    description: "Count, correct, and reorder.",
    nodes: nodes([
      {
        id: "count",
        label: "Cycle Count",
        icon: ListChecks,
        route: "/cycle-counts",
        hint: "Physical count by department — compare against system stock.",
      },
      {
        id: "adjust",
        label: "Adjust",
        icon: SlidersHorizontal,
        route: "/inventory",
        hint: "Commit corrections. Each change is recorded in the ledger.",
      },
      {
        id: "reorder",
        label: "Reorder Plan",
        icon: Sparkles,
        prompt:
          "Build a reorder plan: what's low on stock and selling fast vs not urgent, group by vendor, and recommend quantities based on past orders",
        nodeType: "outcome",
        hint: "AI builds a reorder plan grouped by vendor based on stock levels and velocity.",
      },
    ]),
    edges: edges([
      { source: "count", target: "adjust" },
      { source: "adjust", target: "reorder", label: "low stock" },
    ]),
  },

  reports: {
    label: "Reports",
    description: "Sales, margins, inventory health, job P&L.",
    nodes: nodes([
      {
        id: "reports",
        label: "Reports",
        icon: BarChart3,
        route: "/reports",
        hint: "Sales, margins, inventory, job P&L, KPIs — all in one place.",
      },
      {
        id: "lowstock",
        label: "Low Stock",
        icon: SlidersHorizontal,
        prompt:
          "What should we reorder urgently? Rank by days until stockout and flag critical items",
        nodeType: "decision",
        hint: "AI analyzes low stock items ranked by urgency and stockout risk.",
      },
      {
        id: "reorder",
        label: "Reorder Plan",
        icon: Sparkles,
        prompt:
          "Build a reorder plan: what's low on stock and selling fast vs not urgent, group by vendor, and recommend quantities based on past orders",
        nodeType: "outcome",
        hint: "AI builds a vendor-grouped reorder plan with quantity recommendations.",
      },
    ]),
    edges: edges([
      { source: "reports", target: "lowstock" },
      { source: "lowstock", target: "reorder", label: "low stock" },
    ]),
  },
};

export const WORKFLOW_KEYS = Object.keys(WORKFLOWS);
export default WORKFLOWS;
