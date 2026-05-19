import axios from "axios";
import type {
  ChatAnswer,
  Conversation,
  ConversationDetail,
} from "./types";

const api = axios.create({
  baseURL: "/",
  timeout: 90000,
});

export interface ChatPayload {
  question: string;
  conversation_id?: number | null;
  history?: { role: "user" | "assistant"; content: string }[];
}

export const sendChat = async (payload: ChatPayload): Promise<ChatAnswer> => {
  const { data } = await api.post<ChatAnswer>("/api/chat", payload);
  return data;
};

export interface StreamEvent {
  type: string;
  conversation_id?: number;
  message_id?: number;
  sql?: string;
  explanation?: string;
  data?: any;
  chart?: any;
  chunk?: string;
  done?: boolean;
  clarification?: string;
  error?: string;
}

export const sendChatStream = (
  payload: ChatPayload,
  onEvent: (event: StreamEvent) => void,
  onError?: (err: string) => void,
): (() => void) => {
  const ctrl = new AbortController();
  fetch("/api/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal: ctrl.signal,
  })
    .then(async (res) => {
      if (!res.ok) {
        const text = await res.text();
        throw new Error(`HTTP ${res.status}: ${text}`);
      }
      const reader = res.body?.getReader();
      if (!reader) throw new Error("无法读取响应流");
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";
        for (const line of lines) {
          const m = line.trim().match(/^data: (.+)$/);
          if (m) {
            try {
              const evt: StreamEvent = JSON.parse(m[1]);
              onEvent(evt);
            } catch {
              // ignore malformed
            }
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== "AbortError" && onError) {
        onError(err.message || "流式请求失败");
      }
    });
  return () => ctrl.abort();
};

export const listConversations = async (): Promise<Conversation[]> => {
  const { data } = await api.get<Conversation[]>("/api/conversations");
  return data;
};

export const getConversation = async (
  id: number,
): Promise<ConversationDetail> => {
  const { data } = await api.get<ConversationDetail>(`/api/conversations/${id}`);
  return data;
};

export const deleteConversation = async (id: number): Promise<void> => {
  await api.delete(`/api/conversations/${id}`);
};

export const getSamples = async (): Promise<string[]> => {
  const { data } = await api.get<{ questions: string[] }>("/api/meta/samples");
  return data.questions;
};
