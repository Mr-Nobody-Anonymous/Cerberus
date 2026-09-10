/**
 * Chat sidebar — conversation list with search, new chat, delete.
 */

import { useState } from "react";
import { chatsApi } from "@/lib/api";
import type { ChatSummary } from "@/lib/api";
import { useFetch, useToast } from "@/hooks";
import { useApp } from "@/stores/app";
import { IconButton } from "@/components/common/Basics";

export function ChatList() {
  const { state, dispatch } = useApp();
  const toast = useToast();
  const [q, setQ] = useState("");
  const [creating, setCreating] = useState(false);

  const { data, refresh } = useFetch(
    () => chatsApi.list(q), [q]);

  const newChat = async () => {
    setCreating(true);
    try {
      const { chat } = await chatsApi.create("New conversation");
      dispatch({ type: "SET_ACTIVE_CHAT", id: chat.id });
      await refresh();
    } catch (e) {
      toast("error", e instanceof Error ? e.message : "failed to create chat");
    } finally {
      setCreating(false);
    }
  };

  const remove = async (id: string) => {
    try {
      await chatsApi.remove(id);
      if (state.activeChatId === id) dispatch({ type: "SET_ACTIVE_CHAT", id: null });
      await refresh();
      toast("success", "conversation deleted");
    } catch (e) {
      toast("error", e instanceof Error ? e.message : "delete failed");
    }
  };

  const chats = data?.chats ?? [];

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div style={{ padding: "10px 10px 6px", display: "flex", gap: 6 }}>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search conversations…"
          style={{ flex: 1, fontSize: 12 }}
        />
        <button onClick={newChat} disabled={creating}
                title="New conversation"
                style={{
                  padding: "4px 10px", borderRadius: "var(--cb-radius-sm)",
                  border: "1px solid var(--cb-cyan)55", color: "var(--cb-cyan)",
                  fontSize: 12, fontWeight: 600,
                }}>
          + New
        </button>
      </div>
      <div style={{ flex: 1, overflowY: "auto", padding: "4px 6px" }}>
        {chats.length === 0 && (
          <div className="faint" style={{ padding: "18px 10px", fontSize: 12,
                                          textAlign: "center" }}>
            No conversations yet.<br />Start one to talk to CERBERUS.
          </div>
        )}
        {chats.map((c: ChatSummary) => {
          const active = state.activeChatId === c.id;
          return (
            <div key={c.id}
                 onClick={() => dispatch({ type: "SET_ACTIVE_CHAT", id: c.id })}
                 style={{
                   display: "flex", alignItems: "center", gap: 8,
                   padding: "7px 9px", marginBottom: 2,
                   borderRadius: "var(--cb-radius-sm)", cursor: "pointer",
                   background: active ? "var(--cb-bg3)" : "transparent",
                   borderLeft: `2px solid ${active ? "var(--cb-cyan)" : "transparent"}`,
                 }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{
                  fontSize: 12.5, overflow: "hidden", textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                  color: active ? "var(--cb-text)" : "var(--cb-text-dim)",
                }}>
                  {c.title || "Untitled"}
                </div>
                <div className="faint" style={{ fontSize: 10.5 }}>
                  {c.message_count} msg{c.message_count === 1 ? "" : "s"}
                  {c.mode ? ` · ${c.mode}` : ""}
                </div>
              </div>
              <IconButton title="Delete" danger
                          onClick={() => {
                            void remove(c.id);
                          }}>
                ✕
              </IconButton>
            </div>
          );
        })}
      </div>
    </div>
  );
}
