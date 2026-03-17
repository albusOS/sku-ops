import { createContext, useCallback, useContext, useRef, useState } from "react";

const ChatContext = createContext(null);

export function ChatProvider({ children }) {
  const [open, setOpen] = useState(false);
  const pendingPromptRef = useRef(null);

  const sendPrompt = useCallback(
    (prompt) => {
      pendingPromptRef.current = prompt;
      setOpen(true);
    },
    [setOpen],
  );

  return (
    <ChatContext.Provider value={{ open, setOpen, sendPrompt, pendingPromptRef }}>
      {children}
    </ChatContext.Provider>
  );
}

export function useChatPanel() {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error("useChatPanel must be used within ChatProvider");
  return ctx;
}
