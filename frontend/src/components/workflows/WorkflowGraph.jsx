import { useState, useCallback, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { ReactFlow, Handle, Position } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { ArrowRight, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { useChatPanel } from "@/context/ChatContext";
import WORKFLOWS, { WORKFLOW_KEYS } from "./workflowData";

function WorkflowNode({ data }) {
  const navigate = useNavigate();
  const { sendPrompt } = useChatPanel();
  const [hovered, setHovered] = useState(false);
  const Icon = data.icon;
  const isOutcome = data.nodeType === "outcome";
  const isDecision = data.nodeType === "decision";
  const isAssistant = !!data.prompt;
  const clickable = !!data.route || isAssistant;

  const handleClick = useCallback(() => {
    if (data.prompt) {
      sendPrompt(data.prompt);
    } else if (data.route) {
      navigate(data.route);
    }
  }, [data.route, data.prompt, navigate, sendPrompt]);

  return (
    <>
      <Handle
        type="target"
        position={Position.Left}
        className="!bg-transparent !w-0 !h-0 !border-0 !min-w-0 !min-h-0"
      />
      <div
        className="relative"
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      >
        <button
          onClick={handleClick}
          disabled={!clickable}
          className={cn(
            "group flex items-center gap-2 rounded-xl border px-3 py-2 transition-all",
            "bg-surface shadow-soft",
            isOutcome
              ? "border-accent/30 text-accent"
              : isDecision
                ? "border-warning/30 text-warning"
                : "border-border/60 text-foreground",
            clickable &&
              "cursor-pointer hover:border-accent/50 hover:shadow-md hover:bg-surface-muted",
            !clickable && "cursor-default",
          )}
        >
          <div
            className={cn(
              "w-6 h-6 rounded-md flex items-center justify-center shrink-0 transition-colors",
              isOutcome
                ? "bg-accent/10"
                : isDecision
                  ? "bg-warning/10"
                  : "bg-muted ring-1 ring-border/40",
              clickable && "group-hover:bg-accent/10",
            )}
          >
            {Icon && <Icon className="w-3 h-3 opacity-80" />}
          </div>
          <span className="text-[11px] font-medium whitespace-nowrap">{data.label}</span>
          {isAssistant ? (
            <Sparkles className="w-3 h-3 ml-0.5 opacity-40 group-hover:opacity-80 transition-opacity text-accent shrink-0" />
          ) : clickable ? (
            <ArrowRight className="w-3 h-3 ml-0.5 opacity-0 group-hover:opacity-50 transition-opacity text-accent shrink-0" />
          ) : null}
        </button>

        {hovered && data.hint && (
          <div className="absolute left-1/2 -translate-x-1/2 top-full mt-2 z-50 w-48 pointer-events-none animate-in fade-in duration-150">
            <div className="bg-surface border border-border/80 rounded-lg shadow-soft-lg px-3 py-2 text-[11px] leading-relaxed text-muted-foreground">
              {data.hint}
            </div>
          </div>
        )}
      </div>
      <Handle
        type="source"
        position={Position.Right}
        className="!bg-transparent !w-0 !h-0 !border-0 !min-w-0 !min-h-0"
      />
    </>
  );
}

const nodeTypes = { workflowNode: WorkflowNode };

export default function WorkflowGraph() {
  const [active, setActive] = useState(WORKFLOW_KEYS[0]);
  const workflow = WORKFLOWS[active];

  const defaultEdgeOptions = useMemo(() => ({ type: "default", animated: true }), []);

  return (
    <div>
      <div className="flex items-center gap-1 mb-2 overflow-x-auto scrollbar-none">
        {WORKFLOW_KEYS.map((key) => {
          const w = WORKFLOWS[key];
          const isActive = active === key;
          return (
            <button
              key={key}
              onClick={() => setActive(key)}
              className={cn(
                "flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium transition-all whitespace-nowrap",
                isActive
                  ? "bg-accent/15 text-accent"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted/50",
              )}
            >
              {w.label}
              <span
                className={cn(
                  "text-[9px] tabular-nums px-1.5 py-0.5 rounded-full font-bold leading-none",
                  isActive ? "bg-accent/20 text-accent" : "bg-muted text-muted-foreground/50",
                )}
              >
                {w.nodes.length}
              </span>
            </button>
          );
        })}
        <span className="ml-auto text-[11px] text-muted-foreground/60 hidden md:block whitespace-nowrap">
          {workflow.description}
        </span>
      </div>

      <div className="h-[155px] rounded-xl border border-border/40 bg-background/40 overflow-hidden">
        <ReactFlow
          key={active}
          nodes={workflow.nodes}
          edges={workflow.edges}
          nodeTypes={nodeTypes}
          defaultEdgeOptions={defaultEdgeOptions}
          fitView
          fitViewOptions={{ padding: 0.25 }}
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable={false}
          panOnDrag={false}
          zoomOnScroll={false}
          zoomOnPinch={false}
          zoomOnDoubleClick={false}
          preventScrolling={false}
          proOptions={{ hideAttribution: true }}
        />
      </div>
    </div>
  );
}
