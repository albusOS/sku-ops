import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ChevronDown, ChevronUp } from "lucide-react";
import { AGENT_META } from "./chatConfig";
import { mdComponents } from "./markdownComponents";
import { BlockRenderer } from "./blocks/BlockRenderer";

function AgentBubble({ msg, thinkingOpen, onToggleThinking }) {
  const meta = AGENT_META[msg.agent];
  const toolCalls = msg.tool_calls || [];
  const thinking = msg.thinking || [];
  const blocks = msg.blocks || [];

  return (
    <div className="flex flex-col gap-1 max-w-[94%]">
      <div className="bg-surface border border-border/40 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-foreground shadow-sm">
        <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>
          {msg.content}
        </ReactMarkdown>
        <BlockRenderer blocks={blocks} />
      </div>
      {(meta || toolCalls.length > 0 || thinking.length > 0) && (
        <div className="flex items-center gap-1.5 flex-wrap px-1">
          {meta && (
            <span className={`text-[9px] font-medium px-1.5 py-0.5 rounded ${meta.cls}`}>
              {meta.label}
            </span>
          )}
          {toolCalls.map((t, i) => (
            <span
              key={t.tool || i}
              className="text-[9px] text-muted-foreground bg-muted/50 px-1.5 py-0.5 rounded border border-border/40"
            >
              {t.tool}
            </span>
          ))}
          {thinking.length > 0 && (
            <button
              onClick={onToggleThinking}
              className="flex items-center gap-0.5 text-[9px] text-muted-foreground hover:text-foreground transition-colors ml-auto"
            >
              {thinkingOpen ? (
                <ChevronUp className="w-2.5 h-2.5" />
              ) : (
                <ChevronDown className="w-2.5 h-2.5" />
              )}
              reasoning
            </button>
          )}
        </div>
      )}
      {thinking.length > 0 && thinkingOpen && (
        <div className="mx-1 p-2.5 bg-muted/40 border border-border/30 rounded-lg text-[10px] text-muted-foreground font-mono leading-relaxed max-h-40 overflow-y-auto whitespace-pre-wrap">
          {thinking.join("\n\n---\n\n")}
        </div>
      )}
    </div>
  );
}

function StreamingBubble({ text, tools: _tools }) {
  return (
    <div className="flex flex-col gap-1 max-w-[94%]">
      <div className="bg-surface border border-border/40 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-foreground shadow-sm">
        {text ? (
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>
            {text}
          </ReactMarkdown>
        ) : (
          <span className="inline-flex gap-1 items-center">
            <span
              className="w-1.5 h-1.5 bg-accent rounded-full animate-bounce"
              style={{ animationDelay: "0ms" }}
            />
            <span
              className="w-1.5 h-1.5 bg-accent/70 rounded-full animate-bounce"
              style={{ animationDelay: "150ms" }}
            />
            <span
              className="w-1.5 h-1.5 bg-accent/40 rounded-full animate-bounce"
              style={{ animationDelay: "300ms" }}
            />
          </span>
        )}
      </div>
    </div>
  );
}

export { AgentBubble, StreamingBubble };
