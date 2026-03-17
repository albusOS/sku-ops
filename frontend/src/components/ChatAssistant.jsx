import { useState, useRef, useEffect, useCallback } from "react";
import { useLocation } from "react-router-dom";
import { X, Send, Plus, Sparkles, Square, Wifi, WifiOff, Bot } from "lucide-react";
import api from "@/lib/api-client";
import { useChatSocket } from "@/hooks/useChatSocket";
import { useChatPanel } from "@/context/ChatContext";
import {
  STORAGE_KEY,
  agentTypeFromPath,
  AGENT_SUGGESTIONS,
  AGENT_PLACEHOLDER,
} from "./chat/chatConfig";
import { AgentActivity } from "./chat/AgentActivity";
import { AgentBubble, StreamingBubble } from "./chat/MessageBubbles";

export default function ChatAssistant() {
  const location = useLocation();
  const agentType = agentTypeFromPath(location.pathname);
  const { open, setOpen } = useChatPanel();

  const [messages, setMessages] = useState(() => {
    try {
      return JSON.parse(sessionStorage.getItem(STORAGE_KEY) || "null")?.messages ?? [];
    } catch {
      return [];
    }
  });
  const [sessionId, setSessionId] = useState(() => {
    try {
      return JSON.parse(sessionStorage.getItem(STORAGE_KEY) || "null")?.sessionId ?? null;
    } catch {
      return null;
    }
  });
  const [input, setInput] = useState("");
  const [aiAvailable, setAiAvailable] = useState(null);
  const [setupUrl, setSetupUrl] = useState(null);
  const [openThinking, setOpenThinking] = useState(new Set());
  const [sessionCost, setSessionCost] = useState(0);
  const scrollRef = useRef(null);
  const inputRef = useRef(null);
  const prevAgentType = useRef(agentType);
  const sessionIdRef = useRef(sessionId);

  useEffect(() => {
    sessionIdRef.current = sessionId;
  }, [sessionId]);

  const handleDone = useCallback((result) => {
    if (result.session_id) setSessionId(result.session_id);
    if (result.usage?.session_cost_usd != null) setSessionCost(result.usage.session_cost_usd);
    setMessages((m) => [
      ...m,
      {
        role: "model",
        content: result.response || "No response.",
        agent: result.agent,
        tool_calls: result.tool_calls || [],
        thinking: result.thinking || [],
        blocks: result.blocks || [],
      },
    ]);
  }, []);

  const handleError = useCallback((detail) => {
    setMessages((m) => [...m, { role: "model", content: detail || "Failed to get response." }]);
  }, []);

  const {
    send: wsSend,
    cancel: wsCancel,
    connected,
    streaming,
    streamText,
    activeTools,
  } = useChatSocket({
    onDone: handleDone,
    onError: handleError,
    enabled: open,
  });

  const clearSession = (sid) => {
    if (sid) api.chat.deleteSession(sid).catch(() => {});
  };

  useEffect(() => {
    if (prevAgentType.current !== agentType) {
      clearSession(sessionId);
      setMessages([]);
      setSessionId(null);
      setSessionCost(0);
      prevAgentType.current = agentType;
    }
  }, [agentType, sessionId]);

  const startNewChat = () => {
    if (streaming) wsCancel();
    clearSession(sessionId);
    setMessages([]);
    setSessionId(null);
    setSessionCost(0);
  };

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streaming, streamText]);

  useEffect(() => {
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ messages, sessionId }));
    } catch {
      /* sessionStorage may be full or disabled */
    }
  }, [messages, sessionId]);

  useEffect(() => {
    if (open && aiAvailable === null) {
      api.chat
        .status()
        .then((data) => {
          setAiAvailable(data.available);
          setSetupUrl(data.setup_url);
        })
        .catch(() => setAiAvailable(false));
    }
    if (open) setTimeout(() => inputRef.current?.focus(), 150);
  }, [open, aiAvailable]);

  const sendMessage = useCallback(
    async (text) => {
      text = (text || input).trim();
      if (!text || streaming) return;
      setMessages((m) => [...m, { role: "user", content: text }]);
      setInput("");

      const sid = sessionIdRef.current;

      if (connected) {
        wsSend(text, sid, agentType);
      } else {
        try {
          const data = await api.chat.send({
            message: text,
            session_id: sid,
            agent_type: agentType,
          });
          handleDone(data);
        } catch (err) {
          handleError(err.response?.data?.detail || err.message || "Failed to get response.");
        }
      }
    },
    [input, streaming, connected, wsSend, agentType, handleDone, handleError],
  );

  const toggleThinking = (idx) => {
    setOpenThinking((prev) => {
      const next = new Set(prev);
      next.has(idx) ? next.delete(idx) : next.add(idx);
      return next;
    });
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const suggestions = AGENT_SUGGESTIONS[agentType] || AGENT_SUGGESTIONS.auto;

  return (
    <div className="contents">
      {/* FAB trigger */}
      <button
        onClick={() => setOpen(true)}
        className={`fixed bottom-6 right-6 w-12 h-12 bg-accent hover:bg-accent/90 text-accent-foreground rounded-full shadow-lg shadow-accent/20 flex items-center justify-center transition-all z-40 hover:scale-105 ${open ? "scale-0 pointer-events-none" : "scale-100"}`}
        aria-label="Open AI assistant"
      >
        <Sparkles className="w-5 h-5" />
      </button>

      {/* Panel content - width controlled by ResizablePanel in Layout */}
      <div className="flex flex-col h-full min-w-0 bg-surface border-l border-border/80 shadow-soft">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-2.5 border-b border-border/60 bg-surface shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 bg-accent/15 border border-accent/30 rounded-lg flex items-center justify-center">
              <Bot className="w-4 h-4 text-accent" />
            </div>
            <div>
              <h2 className="font-semibold text-foreground text-sm leading-none">Assistant</h2>
              <div className="flex items-center gap-1.5 mt-0.5">
                {connected ? (
                  <Wifi className="w-2.5 h-2.5 text-success" />
                ) : (
                  <WifiOff className="w-2.5 h-2.5 text-muted-foreground" />
                )}
                <span className="text-[9px] text-muted-foreground">
                  {connected ? "Connected" : "Offline"}
                </span>
                {sessionCost > 0 && (
                  <span className="text-[9px] text-muted-foreground ml-1">
                    · ${sessionCost.toFixed(4)}
                  </span>
                )}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-0.5">
            {messages.length > 0 && (
              <button
                type="button"
                onClick={startNewChat}
                title="New chat"
                className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition-colors"
              >
                <Plus className="w-4 h-4" />
              </button>
            )}
            <button
              onClick={() => setOpen(false)}
              className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Agent activity bar */}
        {streaming && <AgentActivity tools={activeTools} agentType={agentType} />}

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
          {aiAvailable === false && (
            <div className="rounded-lg bg-warning/10 border border-warning/30 p-3">
              <p className="font-medium text-xs text-foreground mb-1">
                AI assistant not configured
              </p>
              <p className="text-[11px] text-muted-foreground mb-2">
                Add{" "}
                <code className="px-1 bg-muted rounded font-mono text-[10px]">
                  ANTHROPIC_API_KEY
                </code>{" "}
                or{" "}
                <code className="px-1 bg-muted rounded font-mono text-[10px]">
                  OPENROUTER_API_KEY
                </code>{" "}
                to <code className="px-1 bg-muted rounded font-mono text-[10px]">backend/.env</code>
              </p>
              {setupUrl && (
                <a
                  href={setupUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[11px] text-accent underline hover:text-foreground"
                >
                  Get an API key
                </a>
              )}
            </div>
          )}

          {messages.length === 0 && aiAvailable !== false && (
            <div className="flex flex-col py-10 gap-5">
              <div className="text-center">
                <div className="w-12 h-12 bg-accent/10 border border-accent/20 rounded-xl flex items-center justify-center mx-auto mb-3">
                  <Sparkles className="w-6 h-6 text-accent" />
                </div>
                <p className="text-sm font-medium text-foreground mb-1">What can I help with?</p>
                <p className="text-xs text-muted-foreground">{AGENT_PLACEHOLDER[agentType]}</p>
              </div>
              <div className="grid grid-cols-2 gap-2">
                {suggestions.map((s) => (
                  <button
                    key={s.label}
                    onClick={() => sendMessage(s.prompt)}
                    disabled={streaming || aiAvailable === false}
                    className="text-xs text-left px-3 py-2.5 rounded-xl border border-border/50 bg-surface hover:bg-accent/5 hover:border-accent/30 text-muted-foreground hover:text-foreground transition-all leading-snug disabled:opacity-50"
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              {m.role === "user" ? (
                <div className="max-w-[85%] bg-accent text-accent-foreground rounded-2xl rounded-tr-sm px-3.5 py-2 text-[13px] leading-relaxed">
                  {m.content}
                </div>
              ) : (
                <AgentBubble
                  msg={m}
                  thinkingOpen={openThinking.has(i)}
                  onToggleThinking={() => toggleThinking(i)}
                />
              )}
            </div>
          ))}

          {streaming && (
            <div className="flex justify-start">
              <StreamingBubble text={streamText} tools={activeTools} />
            </div>
          )}

          <div ref={scrollRef} />
        </div>

        {/* Input */}
        <div className="px-4 py-3 border-t border-border/60 bg-surface shrink-0">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              sendMessage(input);
            }}
            className="flex gap-2"
          >
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                aiAvailable === false ? "Configure API key to enable" : AGENT_PLACEHOLDER[agentType]
              }
              rows={1}
              className="flex-1 px-3 py-2.5 bg-background border border-border/60 rounded-xl text-sm text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:ring-1 focus:ring-accent/40 focus:border-accent/50 disabled:opacity-50 transition-colors resize-none min-h-[40px] max-h-[120px]"
              disabled={aiAvailable === false}
              style={{ fieldSizing: "content" }}
            />
            {streaming ? (
              <button
                type="button"
                onClick={wsCancel}
                className="px-3 py-2.5 bg-destructive/90 hover:bg-destructive text-destructive-foreground rounded-xl transition-colors self-end"
                title="Stop generating"
              >
                <Square className="w-4 h-4" />
              </button>
            ) : (
              <button
                type="submit"
                disabled={!input.trim() || aiAvailable === false}
                className="px-3 py-2.5 bg-accent hover:bg-accent/90 disabled:opacity-30 disabled:cursor-not-allowed text-accent-foreground rounded-xl transition-colors self-end"
              >
                <Send className="w-4 h-4" />
              </button>
            )}
          </form>
          <p className="text-[9px] text-muted-foreground/50 mt-1.5 text-center">⌘+Enter to send</p>
        </div>
      </div>
    </div>
  );
}
