/**
 * Chat view — the centerpiece. Conversation pane + input.
 * Slash commands dispatch through the shared command bus (same as CLI);
 * natural language goes to the LLM gateway.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { chatsApi } from "@/lib/api";
import type { ChatMessage } from "@/lib/api";
import { useApp } from "@/stores/app";
import { useToast } from "@/hooks";
import { ChatInput } from "./ChatInput";
import { MessageBubble } from "./MessageBubble";
import { EmptyState, ErrorBox, Spinner } from "@/components/common/Basics";
import { IconButton } from "@/components/common/Basics";

export function ChatView() {
  const { state, dispatch } = useApp();
  const toast = useToast();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  const chatId = state.activeChatId;

  // Load messages when the active chat changes.
  useEffect(() => {
    if (!chatId) { setMessages([]); setError(null); return; }
    let cancelled = false;
    setLoading(true);
    chatsApi.get(chatId)
      .then(({ chat, messages: msgs }) => {
        if (cancelled) return;
        setMessages(msgs);
        setTitle(chat.title);
        setError(null);
      })
      .catch((e) => !cancelled && setError(e.message))
      .finally(() => !cancelled && setLoading(false));
    return () => { cancelled = true; };
  }, [chatId]);

  // Auto-scroll to the newest message.
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, sending]);

  const send = useCallback(async (text: string) => {
    if (!chatId) {
      // No active chat: create one implicitly, then send.
      try {
        const { chat } = await chatsApi.create();
        dispatch({ type: "SET_ACTIVE_CHAT", id: chat.id });
        const res = await chatsApi.send(chat.id, text);
        setMessages([res.user_message, res.assistant_message]);
      } catch (e) {
        toast("error", e instanceof Error ? e.message : "send failed");
      }
      return;
    }
    setSending(true);
    // Optimistic user message.
    const optimistic: ChatMessage = {
      id: `tmp-${Date.now()}`, session_id: chatId, role: "user", content: text,
      model: null, mode: null, created_at: new Date().toISOString(),
    };
    setMessages((m) => [...m, optimistic]);
    try {
      const res = await chatsApi.send(chatId, text);
      setMessages((m) => [...m.filter((x) => x.id !== optimistic.id),
                           res.user_message, res.assistant_message]);
    } catch (e) {
      setMessages((m) => m.filter((x) => x.id !== optimistic.id));
      toast("error", e instanceof Error ? e.message : "send failed");
    } finally {
      setSending(false);
    }
  }, [chatId, dispatch, toast]);

  const fork = async () => {
    if (!chatId) return;
    try {
      const { chat } = await chatsApi.fork(chatId);
      dispatch({ type: "SET_ACTIVE_CHAT", id: chat.id });
      toast("success", "conversation forked");
    } catch (e) {
      toast("error", e instanceof Error ? e.message : "fork failed");
    }
  };

  const rename = async () => {
    if (!chatId) return;
    const next = window.prompt("Rename conversation", title);
    if (!next || next === title) return;
    try {
      await chatsApi.patch(chatId, { title: next });
      setTitle(next);
    } catch (e) {
      toast("error", e instanceof Error ? e.message : "rename failed");
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", minWidth: 0 }}>
      {/* Header */}
      <div style={{
        display: "flex", alignItems: "center", gap: 8,
        padding: "10px 16px", borderBottom: "1px solid var(--cb-border)",
        flexShrink: 0,
      }}>
        <span style={{ fontSize: 13.5, fontWeight: 600,
                       overflow: "hidden", textOverflow: "ellipsis",
                       whiteSpace: "nowrap", maxWidth: 340 }}>
          {title || "New conversation"}
        </span>
        <div style={{ flex: 1 }} />
        <IconButton title="Rename" onClick={() => void rename()}>✎</IconButton>
        <IconButton title="Fork conversation" onClick={() => void fork()}>⑂</IconButton>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: "auto", padding: "12px 0", minHeight: 0 }}>
        {error && <ErrorBox error={error} />}
        {loading && (
          <div style={{ display: "flex", justifyContent: "center", padding: 30 }}>
            <Spinner />
          </div>
        )}
        {!loading && !error && messages.length === 0 && (
          <EmptyState
            icon="Ω"
            title="Talk to CERBERUS"
            hint="Ask about targets, findings, or past missions — or type / to run a command. Natural language goes to the local model; slash commands run instantly." />
        )}
        {messages.map((m) => <MessageBubble key={m.id} msg={m} />)}
        {sending && (
          <div style={{ display: "flex", gap: 10, padding: "3px 16px" }}>
            <div style={{
              width: 30, height: 30, borderRadius: "50%", flexShrink: 0,
              display: "flex", alignItems: "center", justifyContent: "center",
              background: "var(--cb-bg3)", color: "var(--cb-cyan)",
              border: "1px solid var(--cb-cyan)44", fontSize: 11,
            }}>Ω</div>
            <div style={{
              display: "flex", alignItems: "center", padding: "8px 14px",
              border: "1px solid var(--cb-border)", borderRadius: "4px 12px 12px 12px",
              background: "var(--cb-bg1)",
            }}>
              <Spinner size={13} />
              <span className="dim" style={{ marginLeft: 8, fontSize: 12 }}>
                thinking…
              </span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <ChatInput onSend={(t) => void send(t)} disabled={sending} />
    </div>
  );
}
