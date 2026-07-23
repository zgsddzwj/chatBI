import axios from "axios";
import type {
  ChatAnswer,
  Conversation,
  ConversationDetail,
  StreamEvent,
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

// 统一响应错误拦截：401 跳登录，其他错误格式化消息
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // token 过期，清除并跳转登录
      localStorage.removeItem("chatbi_token");
      localStorage.removeItem("chatbi_user");
      if (window.location.pathname !== "/") {
        window.location.href = "/";
      }
    }
    const detail = error.response?.data?.detail || error.message || "请求失败";
    return Promise.reject(new Error(typeof detail === "string" ? detail : JSON.stringify(detail)));
  },
);

export interface ChatPayload {
  question: string;
  conversation_id?: number | null;
  history?: { role: "user" | "assistant"; content: string }[];
}

export const sendChat = async (payload: ChatPayload): Promise<ChatAnswer> => {
  const { data } = await api.post<ChatAnswer>("/api/chat", payload);
  return data;
};

export const sendChatStream = (
  payload: ChatPayload,
  onEvent: (event: StreamEvent) => void,
  onError?: (err: string) => void,
): (() => void) => {
  const ctrl = new AbortController();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  fetch("/api/query", {
    method: "POST",
    headers,
    body: JSON.stringify({ query: payload.question }),
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
              const raw = JSON.parse(m[1]);
              // 适配新版 Data Agent 事件格式 -> 旧版 StreamEvent
              const evt = adaptDataAgentEvent(raw);
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

/** 将新版 Data Agent 事件适配为前端 StreamEvent */
function adaptDataAgentEvent(raw: any): StreamEvent {
  const type = raw.type;
  if (type === "progress") {
    // 新版进度事件：直接透传给前端展示
    return {
      type: "progress",
      step: raw.step,
      status: raw.status,
    } as StreamEvent;
  }
  if (type === "result") {
    const data = raw.data;
    // 新版 result 是对象数组，需要转成 QueryResult 格式
    if (Array.isArray(data) && data.length > 0) {
      const columns = Object.keys(data[0]);
      const rows = data.map((row: any) => columns.map((c) => row[c]));
      return {
        type: "data",
        data: { columns, rows, row_count: rows.length },
      } as StreamEvent;
    }
    return { type: "data", data: { columns: [], rows: [], row_count: 0 } } as StreamEvent;
  }
  if (type === "sql") {
    return { type: "sql", sql: raw.sql, explanation: raw.explanation } as StreamEvent;
  }
  if (type === "error") {
    return { type: "error", error: raw.message || raw.error || "未知错误" } as StreamEvent;
  }
  if (type === "done") {
    return { type: "done" } as StreamEvent;
  }
  // 其他未知类型，默认透传为 thinking
  return { type: "thinking" } as StreamEvent;
}

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

export const exportConversationMarkdown = async (conversationId: number): Promise<Blob> => {
  const { data } = await api.get<Blob>(`/api/export/conversation/${conversationId}/markdown`, {
    responseType: "blob",
  });
  return data;
};

export const exportConversationJson = async (conversationId: number): Promise<Blob> => {
  const { data } = await api.get<Blob>(`/api/export/conversation/${conversationId}/json`, {
    responseType: "blob",
  });
  return data;
};

export const createShareLink = async (conversationId: number): Promise<{ share_id: string; url: string; expires_in_hours: number }> => {
  const { data } = await api.post<{ share_id: string; url: string; expires_in_hours: number }>(`/api/export/conversation/${conversationId}/share`);
  return data;
};

export interface FeedbackPayload {
  message_id: number;
  rating: number;
  comment?: string;
}

export const submitFeedback = async (payload: FeedbackPayload): Promise<{ id: number }> => {
  const { data } = await api.post<{ id: number }>("/api/feedback", payload);
  return data;
};

// ========== 缓存管理 API ==========

export interface CacheStats {
  total_entries: number;
  active_entries: number;
  expired_entries: number;
  total_hits: number;
  hit_rate: number;
  top_queries: Array<{
    sql: string;
    hits: number;
    last_hit: string | null;
  }>;
}

export const getCacheStats = async (): Promise<CacheStats> => {
  const { data } = await api.get<CacheStats>("/api/meta/cache/stats");
  return data;
};

export const clearCache = async (): Promise<{ cleared: number; message: string }> => {
  const { data } = await api.post<{ cleared: number; message: string }>("/api/meta/cache/clear");
  return data;
};

export const findSimilarCache = async (q: string, limit: number = 3): Promise<{ query: string; similar_queries: any[] }> => {
  const { data } = await api.get("/api/meta/cache/similar", { params: { q, limit } });
  return data;
};

// ========== 查询建议 API ==========

export const getSuggestions = async (
  q: string = "",
  conversationId?: number,
  limit: number = 8
): Promise<{ suggestions: Array<{ text: string; source: string; score: number }> }> => {
  const { data } = await api.get("/api/chat/suggestions", {
    params: { q, conversation_id: conversationId, limit },
  });
  return data;
};

export const getAutocomplete = async (q: string, limit: number = 5): Promise<string[]> => {
  const { data } = await api.get("/api/chat/autocomplete", { params: { q, limit } });
  return data.results;
};

// ========== 查询历史 API ==========

export interface QueryHistoryItem {
  conversation_id: number;
  sql: string;
  intent: string | null;
  success: boolean;
  created_at: string;
}

export interface QueryStats {
  total_queries: number;
  success_rate: number;
  top_intents: Array<{ intent: string; count: number }>;
}

export interface QueryRecommendation {
  sql: string;
  intent: string;
  source: string;
  score: number;
}

export interface QueryPattern {
  pattern: string;
  sql: string;
  count: number;
}

export const getHistory = async (
  userId: number,
  limit: number = 20,
  offset: number = 0,
): Promise<{ history: QueryHistoryItem[] }> => {
  const { data } = await api.get(`/api/chat/history/${userId}`, { params: { limit, offset } });
  return data;
};

export const getHistoryStats = async (userId: number): Promise<QueryStats> => {
  const { data } = await api.get(`/api/chat/history/${userId}/stats`);
  return data;
};

export const getHistoryRecommendations = async (
  userId: number,
  limit: number = 5,
): Promise<{ recommendations: QueryRecommendation[] }> => {
  const { data } = await api.get(`/api/chat/history/${userId}/recommendations`, { params: { limit } });
  return data;
};

export const getHistoryPatterns = async (userId: number): Promise<{ patterns: QueryPattern[] }> => {
  const { data } = await api.get(`/api/chat/history/${userId}/patterns`);
  return data;
};
