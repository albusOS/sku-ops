const STORAGE_KEY = "sku-ops:chat:v6";

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

const CHAT_MODES = [
  { id: "general", label: "General" },
  { id: "procurement", label: "Procurement" },
  { id: "trend", label: "Trends" },
  { id: "health", label: "Health Check" },
];

function agentTypeForMode(mode) {
  if (mode === "general") return "general";
  return mode;
}

const AGENT_SUGGESTIONS = {
  general: [
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
  procurement: [
    {
      label: "Reorder plan",
      prompt:
        "Build a reorder plan: what's low on stock and selling fast vs not urgent, group by vendor, and recommend quantities based on past orders",
    },
    {
      label: "Vendor performance",
      prompt:
        "Compare our vendors — who has the best fill rate, lead time, and pricing? Flag any reliability issues",
    },
    {
      label: "What should we order?",
      prompt:
        "What should we order next? Prioritize by stockout risk, group items by vendor, and estimate total spend",
    },
    {
      label: "Purchase history",
      prompt:
        "Show recent purchase orders — what did we order, from which vendors, and at what cost?",
    },
  ],
  trend: [
    {
      label: "Revenue trend",
      prompt: "How has revenue trended over the last 4 weeks? Any anomalies?",
    },
    {
      label: "Period comparison",
      prompt: "Compare this month to last month — revenue, margins, and top products",
    },
    {
      label: "Growth rate",
      prompt: "What's our growth rate? Are sales trending up or down?",
    },
    {
      label: "Seasonal patterns",
      prompt: "Are there any seasonal patterns in our sales data?",
    },
  ],
  health: [
    {
      label: "Full health check",
      prompt: "Run a full business health check — inventory, finance, and operations",
    },
    {
      label: "Quarterly review",
      prompt: "Give me a quarterly business review with key metrics and recommendations",
    },
    {
      label: "What needs attention?",
      prompt: "What areas of the business need the most attention right now?",
    },
    {
      label: "Store assessment",
      prompt: "Complete store assessment with actionable recommendations",
    },
  ],
};

const AGENT_PLACEHOLDER = {
  general: "Ask about inventory, finance, or operations…",
  procurement: "Ask about vendors, reorder plans, purchasing…",
  trend: "Ask about trends, growth, period comparisons…",
  health: "Ask for a business health assessment…",
};

export {
  STORAGE_KEY,
  AGENT_META,
  CHAT_MODES,
  AGENT_SUGGESTIONS,
  AGENT_PLACEHOLDER,
  agentTypeForMode,
};
