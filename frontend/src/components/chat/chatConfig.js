const STORAGE_KEY = "sku-ops:chat:v4";

const AGENT_META = {
  inventory: {
    label: "Inventory",
    cls: "bg-info/10 text-info border border-info/30",
  },
  ops: {
    label: "Operations",
    cls: "bg-warning/10 text-category-5 border border-warning/30",
  },
  finance: {
    label: "Finance",
    cls: "bg-success/10 text-success border border-success/30",
  },
  unified: {
    label: "Assistant",
    cls: "bg-accent/10 text-accent border border-accent/30",
  },
  system: {
    label: "Assistant",
    cls: "bg-accent/10 text-accent border border-accent/30",
  },
  lookup: {
    label: "Lookup",
    cls: "bg-muted text-muted-foreground border border-border",
  },
  dag: {
    label: "Report",
    cls: "bg-category-4/10 text-category-4 border border-category-4/30",
  },
  procurement: {
    label: "Procurement",
    cls: "bg-category-2/10 text-category-2 border border-category-2/30",
  },
  trend: {
    label: "Trends",
    cls: "bg-category-3/10 text-category-3 border border-category-3/30",
  },
  health: {
    label: "Health",
    cls: "bg-success/10 text-success border border-success/30",
  },
};

function agentTypeFromPath(pathname) {
  if (["/inventory", "/vendors", "/departments", "/purchasing"].some((p) => pathname.startsWith(p)))
    return "inventory";
  if (
    ["/pos", "/pending-requests", "/contractors", "/billing-entities"].some((p) =>
      pathname.startsWith(p),
    )
  )
    return "ops";
  return "auto";
}

const AGENT_SUGGESTIONS = {
  auto: [
    {
      label: "Store overview",
      prompt:
        "Give me a full store overview: inventory health, this week's revenue, outstanding balances, and stockout risks",
    },
    {
      label: "Weekly summary",
      prompt:
        "Write a weekly summary covering sales, top products, outstanding invoices, and any low stock alerts",
    },
    {
      label: "What needs attention?",
      prompt:
        "What needs my attention today? Any critical stock, pending requests, or outstanding invoices?",
    },
    {
      label: "Stockout forecast",
      prompt: "Which items are at risk of stocking out in the next 2 weeks?",
    },
  ],
  inventory: [
    {
      label: "Low stock alerts",
      prompt: "List all products running low that need to be reordered soon",
    },
    {
      label: "Inventory health",
      prompt:
        "Do a full inventory analysis — stock health by category, slow movers, and reorder suggestions",
    },
    {
      label: "Reorder priority",
      prompt: "What should we reorder urgently? Rank by days until stockout",
    },
    {
      label: "Slow movers",
      prompt: "Which products have stock on hand but haven't moved in 30 days?",
    },
  ],
  ops: [
    {
      label: "Recent activity",
      prompt: "Show me all withdrawals from the last 7 days",
    },
    {
      label: "Pending requests",
      prompt: "List all pending material requests awaiting approval",
    },
    {
      label: "Contractor summary",
      prompt:
        "Give me a summary of contractor activity this week — who's been active and any unpaid jobs",
    },
    {
      label: "Unpaid jobs",
      prompt: "Which jobs have outstanding unpaid balances?",
    },
  ],
  finance: [
    {
      label: "Finance overview",
      prompt:
        "Give me a finance overview: P&L summary, outstanding invoices, and who owes us the most",
    },
    {
      label: "Outstanding balances",
      prompt: "Who has outstanding unpaid balances and how much do they owe?",
    },
    {
      label: "This month's P&L",
      prompt: "Show me the profit and loss for the last 30 days including gross margin",
    },
    {
      label: "Weekly sales report",
      prompt:
        "Write a weekly sales report covering revenue, top-selling products, and outstanding balances",
    },
  ],
};

const AGENT_PLACEHOLDER = {
  auto: "Ask about inventory, finance, or operations…",
  inventory: "Ask about products, stock levels, reorders…",
  ops: "Ask about withdrawals, contractors, requests…",
  finance: "Ask about invoices, revenue, P&L, balances…",
};

export { STORAGE_KEY, AGENT_META, AGENT_SUGGESTIONS, AGENT_PLACEHOLDER, agentTypeFromPath };
