import { useState } from "react";
import {
  Layers,
  Database,
  Zap,
  Bot,
  Shield,
  Server,
  ChevronRight,
  GitBranch,
  Search,
  BarChart3,
  Box,
} from "lucide-react";

const SECTIONS = [
  {
    id: "overview",
    label: "Overview",
    icon: Layers,
    color: "text-sky-400",
    bg: "bg-sky-400/10",
    border: "border-sky-400/20",
    activeBorder: "border-sky-400/60",
    title: "Modular Monolith",
    subtitle: "One process. Nine bounded contexts. Strict layer enforcement.",
    content: (
      <div className="space-y-5">
        <p className="text-sm text-sidebar-muted leading-relaxed">
          Supply Yard is built as a{" "}
          <span className="text-sidebar-foreground font-medium">modular monolith</span> — a single
          deployable process with the same bounded-context discipline as microservices, without the
          distributed systems complexity. The codebase is structured so each context could be
          extracted into a service with minimal rework.
        </p>
        <div className="grid grid-cols-3 gap-2">
          {[
            "identity",
            "operations",
            "finance",
            "catalog",
            "inventory",
            "purchasing",
            "jobs",
            "documents",
            "assistant",
          ].map((ctx) => (
            <div
              key={ctx}
              className="bg-sidebar-border/30 rounded-lg px-3 py-2 text-center border border-sidebar-border/40"
            >
              <span className="text-xs font-mono text-sidebar-muted">{ctx}</span>
            </div>
          ))}
        </div>
        <div className="rounded-xl border border-sidebar-border/40 overflow-hidden">
          <div className="bg-sidebar-border/20 px-4 py-2 border-b border-sidebar-border/40">
            <span className="text-xs font-mono text-sidebar-muted">
              Layer dependency graph (strict)
            </span>
          </div>
          <div className="p-4 space-y-1 font-mono text-xs">
            {[
              { layer: "api/", note: "thin HTTP transport", color: "text-violet-400" },
              { layer: "application/", note: "use-case orchestration", color: "text-sky-400" },
              {
                layer: "infrastructure/",
                note: "repos, schema, adapters",
                color: "text-emerald-400",
              },
              { layer: "ports/", note: "protocol interfaces", color: "text-amber-400" },
              { layer: "domain/", note: "pure computation, no IO", color: "text-rose-400" },
            ].map((row, i, arr) => (
              <div key={row.layer} className="flex items-center gap-3">
                <span className={`w-28 shrink-0 ${row.color}`}>{row.layer}</span>
                <span className="text-sidebar-border">←</span>
                <span className="text-sidebar-muted">{row.note}</span>
                {i < arr.length - 1 && <div className="ml-auto text-sidebar-border/50">↓ only</div>}
              </div>
            ))}
          </div>
        </div>
      </div>
    ),
  },
  {
    id: "backend",
    label: "Backend",
    icon: Server,
    color: "text-violet-400",
    bg: "bg-violet-400/10",
    border: "border-violet-400/20",
    activeBorder: "border-violet-400/60",
    title: "FastAPI + asyncpg",
    subtitle: "Python 3.13, async throughout, native Postgres SQL.",
    content: (
      <div className="space-y-5">
        <div className="grid grid-cols-2 gap-3">
          {[
            { label: "Framework", value: "FastAPI" },
            { label: "Python", value: "3.13" },
            { label: "DB Driver", value: "asyncpg" },
            { label: "Validation", value: "Pydantic v2" },
            { label: "SQL", value: "Native Postgres" },
            { label: "ORM", value: "None" },
          ].map((item) => (
            <div
              key={item.label}
              className="bg-sidebar-border/20 rounded-lg px-3 py-2 border border-sidebar-border/30"
            >
              <div className="text-xs text-sidebar-muted">{item.label}</div>
              <div className="text-sm font-medium text-sidebar-foreground font-mono mt-0.5">
                {item.value}
              </div>
            </div>
          ))}
        </div>
        <div className="rounded-xl border border-sidebar-border/40 overflow-hidden">
          <div className="bg-sidebar-border/20 px-4 py-2 border-b border-sidebar-border/40">
            <span className="text-xs font-mono text-sidebar-muted">
              ContextVar Unit of Work — ambient transactions
            </span>
          </div>
          <pre className="p-4 text-xs font-mono text-sidebar-muted leading-relaxed overflow-x-auto">{`async with transaction():
    # connection stored in ContextVar
    # repos call get_connection() — no conn params
    await withdrawal_repo.create(cmd)
    await inventory_repo.decrement(items)
    # auto-commit or rollback`}</pre>
        </div>
        <p className="text-xs text-sidebar-muted leading-relaxed">
          Each asyncio request task gets its own isolated transaction via Python&apos;s{" "}
          <code className="text-violet-300 font-mono">ContextVar</code>. Repos never accept{" "}
          <code className="text-violet-300 font-mono">conn</code> parameters — they join the ambient
          transaction automatically.
        </p>
      </div>
    ),
  },
  {
    id: "database",
    label: "Database",
    icon: Database,
    color: "text-emerald-400",
    bg: "bg-emerald-400/10",
    border: "border-emerald-400/20",
    activeBorder: "border-emerald-400/60",
    title: "PostgreSQL 16",
    subtitle: "Every environment. No SQLite. No ORM. No dialect abstraction.",
    content: (
      <div className="space-y-5">
        <p className="text-sm text-sidebar-muted leading-relaxed">
          Postgres everywhere — dev (Docker), test (
          <code className="text-emerald-300 font-mono">sku_ops_test</code>), staging, production.
          All SQL is native: <code className="text-emerald-300 font-mono">$1/$2</code> placeholders,{" "}
          <code className="text-emerald-300 font-mono">ON CONFLICT</code>, CTEs,{" "}
          <code className="text-emerald-300 font-mono">::date</code> casts.
        </p>
        <div className="rounded-xl border border-sidebar-border/40 overflow-hidden">
          <div className="bg-sidebar-border/20 px-4 py-2 border-b border-sidebar-border/40">
            <span className="text-xs font-mono text-sidebar-muted">
              Org isolation — every table, every query
            </span>
          </div>
          <pre className="p-4 text-xs font-mono text-sidebar-muted leading-relaxed">{`SELECT id, name, quantity
FROM products
WHERE organization_id = $1   -- always
  AND department_id = $2
ORDER BY name;`}</pre>
        </div>
        <div className="space-y-2">
          <div className="text-xs text-sidebar-muted font-medium uppercase tracking-wider">
            Schema ownership
          </div>
          <div className="flex gap-2 flex-wrap">
            {[
              "Each context owns its tables",
              "Cross-context reads via facades",
              "Migrations versioned",
            ].map((t) => (
              <span
                key={t}
                className="text-xs bg-emerald-400/10 text-emerald-300 border border-emerald-400/20 rounded-full px-3 py-1"
              >
                {t}
              </span>
            ))}
          </div>
        </div>
        <div className="rounded-xl border border-sidebar-border/40 overflow-hidden">
          <div className="bg-sidebar-border/20 px-4 py-2 border-b border-sidebar-border/40">
            <span className="text-xs font-mono text-sidebar-muted">Pool configuration</span>
          </div>
          <div className="p-4 font-mono text-xs space-y-1 text-sidebar-muted">
            <div>
              <span className="text-emerald-400">PG_ACQUIRE_TIMEOUT</span>=10s{" "}
              <span className="text-sidebar-border/60">← circuit breaker, not queue</span>
            </div>
            <div>
              <span className="text-emerald-400">PG_COMMAND_TIMEOUT</span>=30s{" "}
              <span className="text-sidebar-border/60">← kills runaway queries</span>
            </div>
            <div>
              <span className="text-emerald-400">PG_POOL_MIN/MAX</span>=2/10{" "}
              <span className="text-sidebar-border/60">← configurable per env</span>
            </div>
          </div>
        </div>
      </div>
    ),
  },
  {
    id: "realtime",
    label: "Real-time",
    icon: Zap,
    color: "text-amber-400",
    bg: "bg-amber-400/10",
    border: "border-amber-400/20",
    activeBorder: "border-amber-400/60",
    title: "Domain Events → WebSocket → Cache Invalidation",
    subtitle: "No polling. Typed events drive live UI updates.",
    content: (
      <div className="space-y-5">
        <div className="rounded-xl border border-amber-400/20 bg-amber-400/5 p-4">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
            <span className="text-xs font-medium text-amber-300">Event flow</span>
          </div>
          <div className="space-y-2">
            {[
              { step: "Use case commits transaction", detail: "e.g. withdrawal created" },
              { step: "dispatch(WithdrawalCreated)", detail: "typed domain event" },
              { step: "ws_bridge serializes + broadcasts", detail: "WebSocket hub" },
              { step: "Redis Pub/Sub (production)", detail: "all workers receive all events" },
              { step: "Browser: useRealtimeSync", detail: "maps event → query key" },
              { step: "queryClient.invalidateQueries()", detail: "TanStack Query refetches" },
            ].map((item, i, arr) => (
              <div key={i} className="flex items-start gap-3">
                <div className="flex flex-col items-center shrink-0 mt-1">
                  <div className="w-5 h-5 rounded-full bg-amber-400/20 border border-amber-400/40 flex items-center justify-center">
                    <span className="text-amber-400 text-xs font-mono">{i + 1}</span>
                  </div>
                  {i < arr.length - 1 && <div className="w-px h-4 bg-amber-400/20 mt-1" />}
                </div>
                <div>
                  <div className="text-xs font-medium text-sidebar-foreground">{item.step}</div>
                  <div className="text-xs text-sidebar-muted">{item.detail}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-lg border border-sidebar-border/40 p-3">
            <div className="text-xs font-medium text-sidebar-foreground mb-1">Domain WS</div>
            <div className="text-xs font-mono text-sidebar-muted">/api/beta/shared/ws</div>
            <div className="text-xs text-sidebar-muted mt-1">Live data sync</div>
          </div>
          <div className="rounded-lg border border-sidebar-border/40 p-3">
            <div className="text-xs font-medium text-sidebar-foreground mb-1">Chat WS</div>
            <div className="text-xs font-mono text-sidebar-muted">/api/beta/assistant/ws</div>
            <div className="text-xs text-sidebar-muted mt-1">AI token streaming</div>
          </div>
        </div>
      </div>
    ),
  },
  {
    id: "auth",
    label: "Auth",
    icon: Shield,
    color: "text-rose-400",
    bg: "bg-rose-400/10",
    border: "border-rose-400/20",
    activeBorder: "border-rose-400/60",
    title: "Stateless JWT",
    subtitle: "Zero DB round-trips per request. Provider-agnostic claim extraction.",
    content: (
      <div className="space-y-5">
        <p className="text-sm text-sidebar-muted leading-relaxed">
          Every request carries a JWT. The token is verified against{" "}
          <code className="text-rose-300 font-mono">JWT_SECRET</code>, claims are extracted by a
          single <code className="text-rose-300 font-mono">resolve_claims()</code> function, and{" "}
          <code className="text-rose-300 font-mono">organization_id</code> is set as a contextvar.
          No DB round-trip — except one soft-delete check on{" "}
          <code className="text-rose-300 font-mono">is_user_active()</code>.
        </p>
        <div className="rounded-xl border border-sidebar-border/40 overflow-hidden">
          <div className="bg-sidebar-border/20 px-4 py-2 border-b border-sidebar-border/40">
            <span className="text-xs font-mono text-sidebar-muted">Provider auto-selection</span>
          </div>
          <pre className="p-4 text-xs font-mono text-sidebar-muted leading-relaxed">{`# auth_provider.py — single source of truth
def resolve_claims(payload):
    if settings.ENV == "production":
        return _supabase_claims(payload)
    return _internal_claims(payload)

# Adding a new provider = one new branch here.
# Zero other files change.`}</pre>
        </div>
        <div className="space-y-2">
          {[
            { label: "No org_id in token", value: "Hard 401 in production" },
            { label: "Role", value: "admin / contractor — drives route visibility" },
            { label: "Contractor data", value: "Resolved from DB record, not token" },
          ].map((row) => (
            <div key={row.label} className="flex items-start justify-between gap-4 text-xs">
              <span className="text-sidebar-muted shrink-0">{row.label}</span>
              <span className="text-rose-300 text-right">{row.value}</span>
            </div>
          ))}
        </div>
      </div>
    ),
  },
  {
    id: "agents",
    label: "AI Agents",
    icon: Bot,
    color: "text-sky-300",
    bg: "bg-sky-300/10",
    border: "border-sky-300/20",
    activeBorder: "border-sky-300/60",
    title: "Multi-Agent System",
    subtitle: "pydantic-ai. One orchestrator. Four specialists. Streaming responses.",
    content: (
      <div className="space-y-5">
        <div className="space-y-2">
          {[
            {
              icon: GitBranch,
              name: "Unified",
              role: "Orchestrator — routes to specialists via tool calls",
              color: "text-sky-300",
            },
            {
              icon: Database,
              name: "Analyst",
              role: "Writes + executes sandboxed SQL against live DB",
              color: "text-emerald-400",
            },
            {
              icon: Box,
              name: "Procurement",
              role: "Reorder optimization, vendor selection",
              color: "text-amber-400",
            },
            {
              icon: BarChart3,
              name: "Trend",
              role: "Time-series, period-over-period, anomaly detection",
              color: "text-violet-400",
            },
            {
              icon: Search,
              name: "Health",
              role: "Holistic business health across all domains",
              color: "text-rose-400",
            },
          ].map(({ icon: Icon, name, role, color }) => (
            <div
              key={name}
              className="flex items-start gap-3 bg-sidebar-border/20 rounded-lg p-3 border border-sidebar-border/30"
            >
              <Icon className={`w-4 h-4 mt-0.5 shrink-0 ${color}`} />
              <div>
                <span className="text-xs font-semibold text-sidebar-foreground">{name}</span>
                <span className="text-xs text-sidebar-muted ml-2">{role}</span>
              </div>
            </div>
          ))}
        </div>
        <div className="rounded-xl border border-sidebar-border/40 overflow-hidden">
          <div className="bg-sidebar-border/20 px-4 py-2 border-b border-sidebar-border/40">
            <span className="text-xs font-mono text-sidebar-muted">
              Context assembly — runs before every call
            </span>
          </div>
          <div className="p-4 space-y-2">
            {[
              { step: "embed(query)", parallel: true },
              { step: "compress_history()", parallel: true },
              { step: "recall_memories(embedding)", parallel: false },
              { step: "entity_graph_neighbors()", parallel: false },
              { step: "agent.run(enriched_context)", parallel: false },
            ].map(({ step, parallel }, i) => (
              <div key={i} className="flex items-center gap-3 text-xs font-mono">
                <span className="text-sky-300">{step}</span>
                {parallel && <span className="text-amber-400/70 text-xs">∥ concurrent</span>}
              </div>
            ))}
          </div>
        </div>
        <div className="flex gap-2 flex-wrap">
          {[
            "Semantic search index",
            "BM25 fallback",
            "Per-user memory",
            "Structured UI blocks",
            "Tool streaming",
          ].map((t) => (
            <span
              key={t}
              className="text-xs bg-sky-400/10 text-sky-300 border border-sky-400/20 rounded-full px-2.5 py-0.5"
            >
              {t}
            </span>
          ))}
        </div>
      </div>
    ),
  },
];

export function ArchExplorer() {
  const [active, setActive] = useState(null);

  const activeSection = SECTIONS.find((s) => s.id === active);

  return (
    <div className="mt-10 w-full">
      <div className="flex items-center gap-2 mb-4">
        <div className="h-px flex-1 bg-sidebar-border/40" />
        <span className="text-xs text-sidebar-muted font-medium tracking-widest uppercase px-3">
          How it&apos;s built
        </span>
        <div className="h-px flex-1 bg-sidebar-border/40" />
      </div>

      {/* Nav pills */}
      <div className="flex flex-wrap gap-2 justify-center mb-4">
        {SECTIONS.map((s) => {
          const Icon = s.icon;
          const isActive = active === s.id;
          return (
            <button
              key={s.id}
              onClick={() => setActive(isActive ? null : s.id)}
              className={`
                flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium
                border transition-all duration-150 cursor-pointer
                ${
                  isActive
                    ? `${s.bg} ${s.color} ${s.activeBorder}`
                    : `bg-sidebar-border/20 text-sidebar-muted border-sidebar-border/40 hover:text-sidebar-foreground hover:border-sidebar-border/70`
                }
              `}
            >
              <Icon className="w-3.5 h-3.5" />
              {s.label}
              {isActive && <ChevronRight className="w-3 h-3 rotate-90" />}
            </button>
          );
        })}
      </div>

      {/* Expanded panel */}
      {activeSection && (
        <div
          className={`rounded-2xl border ${activeSection.border} bg-sidebar/80 backdrop-blur-sm overflow-hidden`}
        >
          <div className={`px-5 py-4 border-b ${activeSection.border} ${activeSection.bg}`}>
            <div className="flex items-center gap-2">
              {(() => {
                const Icon = activeSection.icon;
                return <Icon className={`w-4 h-4 ${activeSection.color}`} />;
              })()}
              <span className={`text-sm font-semibold ${activeSection.color}`}>
                {activeSection.title}
              </span>
            </div>
            <p className="text-xs text-sidebar-muted mt-1">{activeSection.subtitle}</p>
          </div>
          <div className="p-5">{activeSection.content}</div>
        </div>
      )}

      {!activeSection && (
        <p className="text-center text-xs text-sidebar-muted/60 py-2">
          Select a section to explore the architecture
        </p>
      )}
    </div>
  );
}
