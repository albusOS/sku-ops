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
  const { open, setOpen, pendingPromptRef } = useChatPanel();

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

  useEffect(() => {
    if (!open || streaming) return;
    const prompt = pendingPromptRef.current;
    if (!prompt) return;
    pendingPromptRef.current = null;
    const timer = setTimeout(() => sendMessage(prompt), 200);
    return () => clearTimeout(timer);
  }, [open, streaming, pendingPromptRef, sendMessage]);

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
    <>
      {/* FAB trigger */}
      <button
        onClick={() => setOpen(true)}
        className={`fixed bottom-6 right-6 w-12 h-12 bg-accent hover:bg-accent/90 text-accent-foreground rounded-full shadow-lg shadow-accent/20 flex items-center justify-center transition-all z-40 hover:scale-105 ${open ? "scale-0 pointer-events-none" : "scale-100"}`}
        aria-label="Open AI assistant"
      >
        <Sparkles className="w-5 h-5" />
      </button>

      <div
        className={`fixed inset-0 z-50 transition-all duration-200 ${
          open ? "pointer-events-auto" : "pointer-events-none"
        }`}
        aria-hidden={!open}
      >
        <div
          className={`absolute inset-0 bg-background/55 backdrop-blur-sm transition-opacity duration-200 ${
            open ? "opacity-100" : "opacity-0"
          }`}
          onClick={() => setOpen(false)}
        />

        <div className="absolute inset-0 flex items-center justify-center p-4 md:p-8">
          <div
            className={`relative flex h-[min(88vh,900px)] w-full max-w-5xl flex-col overflow-hidden rounded-[28px] border border-border/70 bg-background shadow-2xl transition-all duration-200 ${
              open ? "scale-100 opacity-100 translate-y-0" : "scale-95 opacity-0 translate-y-4"
            }`}
          >
            <div className="border-b border-border/60 bg-gradient-to-b from-accent/5 to-background px-6 py-5 shrink-0">
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-accent/20 bg-accent/10">
                    <Bot className="w-5 h-5 text-accent" />
                  </div>
                  <div>
                    <h2 className="text-xl font-semibold text-foreground leading-none">
                      Assistant
                    </h2>
                    <div className="mt-1.5 flex items-center gap-2 text-xs text-muted-foreground">
                      <span className="inline-flex items-center gap-1.5">
                        {connected ? (
                          <Wifi className="w-3 h-3 text-success" />
                        ) : (
                          <WifiOff className="w-3 h-3 text-muted-foreground" />
                        )}
                        {connected ? "Connected" : "Offline"}
                      </span>
                      {sessionCost > 0 && <span>Session ${sessionCost.toFixed(4)}</span>}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {messages.length > 0 && (
                    <button
                      type="button"
                      onClick={startNewChat}
                      title="New chat"
                      className="inline-flex items-center gap-2 rounded-xl border border-border/60 bg-background px-3 py-2 text-sm text-muted-foreground hover:text-foreground hover:border-border transition-colors"
                    >
                      <Plus className="w-4 h-4" />
                      New chat
                    </button>
                  )}
                  <button
                    onClick={() => setOpen(false)}
                    className="rounded-xl border border-border/60 bg-background p-2 text-muted-foreground hover:text-foreground hover:border-border transition-colors"
                    aria-label="Close assistant"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>

            {streaming && <AgentActivity tools={activeTools} agentType={agentType} />}

            <div className="flex-1 overflow-y-auto px-6 py-6 md:px-8">
              <div className="mx-auto flex h-full w-full max-w-3xl flex-col space-y-4">
                {aiAvailable === false && (
                  <div className="rounded-2xl bg-warning/10 border border-warning/30 p-4">
                    <p className="font-medium text-sm text-foreground mb-1.5">
                      AI assistant not configured
                    </p>
                    <p className="text-sm text-muted-foreground mb-2">
                      Add{" "}
                      <code className="px-1.5 py-0.5 bg-muted rounded font-mono text-xs">
                        ANTHROPIC_API_KEY
                      </code>{" "}
                      or{" "}
                      <code className="px-1.5 py-0.5 bg-muted rounded font-mono text-xs">
                        OPENROUTER_API_KEY
                      </code>{" "}
                      to{" "}
                      <code className="px-1.5 py-0.5 bg-muted rounded font-mono text-xs">
                        backend/.env
                      </code>
                    </p>
                    {setupUrl && (
                      <a
                        href={setupUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-accent underline hover:text-foreground"
                      >
                        Get an API key
                      </a>
                    )}
                  </div>
                )}

                {messages.length === 0 && aiAvailable !== false ? (
                  <div className="flex flex-1 flex-col items-center justify-center py-10">
                    <div className="w-full max-w-2xl text-center">
                      <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-3xl border border-accent/20 bg-accent/10">
                        <Sparkles className="w-8 h-8 text-accent" />
                      </div>
                      <p className="text-2xl font-semibold text-foreground mb-2">
                        What can I help with?
                      </p>
                      <p className="text-sm text-muted-foreground mb-8">
                        {AGENT_PLACEHOLDER[agentType]}
                      </p>
                      <div className="grid grid-cols-1 gap-3 text-left sm:grid-cols-2">
                        {suggestions.map((s) => (
                          <button
                            key={s.label}
                            onClick={() => sendMessage(s.prompt)}
                            disabled={streaming || aiAvailable === false}
                            className="rounded-2xl border border-border/60 bg-card px-4 py-4 text-sm text-muted-foreground shadow-sm transition-all hover:border-accent/30 hover:bg-accent/5 hover:text-foreground disabled:opacity-50"
                          >
                            {s.label}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                ) : (
                  <>
                    {messages.map((m, i) => (
                      <div
                        key={i}
                        className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
                      >
                        {m.role === "user" ? (
                          <div className="max-w-[85%] rounded-3xl rounded-br-md bg-accent px-4 py-3 text-sm leading-relaxed text-accent-foreground shadow-sm">
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
                  </>
                )}

                <div ref={scrollRef} />
              </div>
            </div>

            <div className="border-t border-border/60 bg-card/70 px-6 py-5 backdrop-blur-sm shrink-0 md:px-8">
              <div className="mx-auto w-full max-w-3xl">
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    sendMessage(input);
                  }}
                  className="rounded-3xl border border-border/70 bg-background p-3 shadow-sm"
                >
                  <div className="flex items-end gap-3">
                    <textarea
                      ref={inputRef}
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      onKeyDown={handleKeyDown}
                      placeholder={
                        aiAvailable === false
                          ? "Configure API key to enable"
                          : AGENT_PLACEHOLDER[agentType]
                      }
                      rows={1}
                      className="min-h-[52px] max-h-[180px] flex-1 resize-none bg-transparent px-2 py-2 text-sm text-foreground placeholder:text-muted-foreground/60 focus:outline-none disabled:opacity-50"
                      disabled={aiAvailable === false}
                      style={{ fieldSizing: "content" }}
                    />
                    {streaming ? (
                      <button
                        type="button"
                        onClick={wsCancel}
                        className="rounded-2xl bg-destructive/90 px-4 py-3 text-destructive-foreground transition-colors hover:bg-destructive"
                        title="Stop generating"
                      >
                        <Square className="w-4 h-4" />
                      </button>
                    ) : (
                      <button
                        type="submit"
                        disabled={!input.trim() || aiAvailable === false}
                        className="rounded-2xl bg-accent px-4 py-3 text-accent-foreground transition-colors hover:bg-accent/90 disabled:cursor-not-allowed disabled:opacity-30"
                      >
                        <Send className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </form>
                <p className="mt-2 text-center text-[10px] text-muted-foreground/60">
                  ⌘+Enter to send
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
