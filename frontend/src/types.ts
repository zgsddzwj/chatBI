export interface QueryResult {
  columns: string[];
  rows: unknown[][];
  row_count: number;
}

export type ChartSpec =
  | { type: "empty" }
  | { type: "table" }
  | { type: "kpi"; label: string; value: number | string }
  | {
      type: "pie";
      data: { name: string; value: number }[];
      label?: string;
    }
  | {
      type: "bar" | "line";
      x: (string | number)[];
      series: { name: string; data: number[] }[];
      x_label?: string;
      y_label?: string;
    };

export interface ChatAnswer {
  type: "answer" | "clarification" | "error";
  conversation_id: number;
  message_id: number;
  sql?: string;
  explanation?: string;
  data?: QueryResult;
  chart?: ChartSpec;
  summary?: string;
  clarification?: string;
  error?: string;
}

export interface Conversation {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface MessageHistory {
  id: number;
  role: "user" | "assistant";
  content: string;
  sql?: string | null;
  result?: QueryResult | null;
  chart?: ChartSpec | null;
  summary?: string | null;
  error?: string | null;
  created_at: string;
}

export interface ConversationDetail extends Conversation {
  messages: MessageHistory[];
}

export interface UIMessage {
  id: number | string;
  role: "user" | "assistant";
  content: string;
  sql?: string | null;
  result?: QueryResult | null;
  chart?: ChartSpec | null;
  summary?: string | null;
  error?: string | null;
  clarification?: string | null;
  pending?: boolean;
  streaming?: boolean;
}

export type StreamEventType =
  | "thinking"
  | "sql"
  | "data"
  | "chart"
  | "summary_chunk"
  | "clarification"
  | "done"
  | "error"
  | "progress"; // 新版 Data Agent 进度事件

export interface ProgressStep {
  step: string;
  status: "running" | "success" | "error";
}

export type StreamEvent =
  | { type: "thinking"; conversation_id?: number }
  | { type: "sql"; conversation_id?: number; sql?: string; explanation?: string }
  | { type: "data"; conversation_id?: number; data?: QueryResult }
  | { type: "chart"; conversation_id?: number; chart?: ChartSpec }
  | { type: "summary_chunk"; conversation_id?: number; chunk?: string; done?: boolean }
  | { type: "clarification"; conversation_id?: number; clarification?: string }
  | { type: "done"; conversation_id?: number; message_id?: number }
  | { type: "error"; conversation_id?: number; error?: string }
  | { type: "progress"; conversation_id?: number; step?: string; status?: "running" | "success" | "error" };
