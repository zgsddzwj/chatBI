import { useCallback, useEffect, useState } from "react";
import { deleteConversation, getConversation, listConversations } from "../api";
import type { Conversation, UIMessage } from "../types";

export function useConversations() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [messages, setMessages] = useState<UIMessage[]>([]);

  const loadConversations = useCallback(async () => {
    try {
      const list = await listConversations();
      setConversations(list);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  const openConversation = async (id: number) => {
    setActiveId(id);
    const detail = await getConversation(id);
    setMessages(
      detail.messages.map((m) => ({
        id: m.id,
        role: m.role,
        content: m.content,
        sql: m.sql,
        result: m.result,
        chart: m.chart,
        summary: m.summary,
        error: m.error,
      })),
    );
  };

  const newConversation = () => {
    setActiveId(null);
    setMessages([]);
  };

  const removeConversation = async (id: number) => {
    await deleteConversation(id);
    if (activeId === id) newConversation();
    await loadConversations();
  };

  return {
    conversations,
    activeId,
    setActiveId,
    messages,
    setMessages,
    loadConversations,
    openConversation,
    newConversation,
    removeConversation,
  };
}
