const STORAGE_KEY = "sku-ops:chat:v7";

const AGENT_META = {
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

const AGENT_SUGGESTIONS = [
  {
    label: "Store overview",
    prompt:
      "Give me a full store overview: inventory health, this week's revenue, outstanding balances, and any stockout risks",
  },
  {
    label: "What needs attention?",
    prompt:
      "What needs my attention today? Any critical stock, pending requests, or outstanding invoices?",
  },
  {
    label: "Reorder plan",
    prompt:
      "Build a reorder plan: what's low on stock and selling fast, group by vendor, and recommend quantities",
  },
  {
    label: "Revenue trend",
    prompt: "How has revenue trended over the last 4 weeks? Any anomalies or patterns?",
  },
];

const AGENT_PLACEHOLDER = "Ask about inventory, finance, operations, or anything else…";

export { STORAGE_KEY, AGENT_META, AGENT_SUGGESTIONS, AGENT_PLACEHOLDER };
