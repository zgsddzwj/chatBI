import axios from "axios";
import type {
  ChatAnswer,
  Conversation,
  ConversationDetail,
} from "./types";
import { getToken } from "./auth";

const api = axios.create({
  baseURL: "/",
  timeout: 90000,
});

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
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

export interface LoginPayload {
  username: string;
  password: string;
}

export interface LoginResult {
  access_token: string;
  token_type: string;
  user: {
    id: number;
    username: string;
    display_name: string | null;
    role: string;
  };
}

export const login = async (payload: LoginPayload): Promise<LoginResult> => {
  const { data } = await api.post<LoginResult>("/api/auth/login", payload);
  return data;
};

export const register = async (payload: LoginPayload & { display_name?: string }): Promise<LoginResult["user"]> => {
  const { data } = await api.post<LoginResult["user"]>("/api/auth/register", payload);
  return data;
};

export const getMe = async (): Promise<LoginResult["user"]> => {
  const { data } = await api.get<LoginResult["user"]>("/api/auth/me");
  return data;
};

export interface DataSource {
  id: number;
  name: string;
  db_type: string;
  description?: string;
  is_default: boolean;
  is_active: boolean;
}

export const listDataSources = async (): Promise<DataSource[]> => {
  const { data } = await api.get<DataSource[]>("/api/datasources");
  return data;
};

export interface DashboardCard {
  id: number;
  title: string;
  chart_type: string;
  chart: any;
  data?: any;
  sql?: string;
  created_at?: string;
}

export interface Dashboard {
  id: number;
  user_id: number;
  name: string;
  description?: string;
  cards: DashboardCard[];
  created_at?: string;
  updated_at?: string;
}

export const createCard = async (payload: Omit<DashboardCard, "id" | "created_at">): Promise<DashboardCard> => {
  const { data } = await api.post<DashboardCard>("/api/dashboards/cards", payload);
  return data;
};

export const listCards = async (): Promise<DashboardCard[]> => {
  const { data } = await api.get<DashboardCard[]>("/api/dashboards/cards");
  return data;
};

export const createDashboard = async (payload: { name: string; description?: string }): Promise<Dashboard> => {
  const { data } = await api.post<Dashboard>("/api/dashboards", payload);
  return data;
};

export const listDashboards = async (): Promise<Dashboard[]> => {
  const { data } = await api.get<Dashboard[]>("/api/dashboards");
  return data;
};

export const getDashboard = async (id: number): Promise<Dashboard> => {
  const { data } = await api.get<Dashboard>(`/api/dashboards/${id}`);
  return data;
};
