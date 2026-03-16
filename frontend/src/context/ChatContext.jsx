import { createContext, useContext, useState } from "react";

const ChatContext = createContext(null);

export function ChatProvider({ children }) {
  const [open, setOpen] = useState(false);

  return <ChatContext.Provider value={{ open, setOpen }}>{children}</ChatContext.Provider>;
}

export function useChatPanel() {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error("useChatPanel must be used within ChatProvider");
  return ctx;
}
