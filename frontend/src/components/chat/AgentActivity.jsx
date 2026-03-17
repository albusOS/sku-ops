import { Activity, Wrench } from "lucide-react";
import { AGENT_META } from "./chatConfig";

function AgentActivity({ tools, agentType }) {
  const meta = AGENT_META[agentType] || AGENT_META.unified;
  return (
    <div className="flex items-center gap-2 px-4 py-2 bg-muted/30 border-b border-border/40">
      <Activity className="w-3 h-3 text-accent animate-pulse" />
      <span className={`text-[9px] font-medium px-1.5 py-0.5 rounded ${meta.cls}`}>
        {meta.label}
      </span>
      {tools.length > 0 && (
        <div className="flex items-center gap-1 flex-wrap">
          <Wrench
            className="w-2.5 h-2.5 text-muted-foreground animate-spin"
            style={{ animationDuration: "3s" }}
          />
          {tools.map((tool, i) => (
            <span
              key={`${tool}-${i}`}
              className="text-[9px] text-muted-foreground bg-muted/60 px-1.5 py-0.5 rounded border border-border/40"
            >
              {tool}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

export { AgentActivity };
