export interface QueryResult {
  columns: string[];
  rows: any[][];
  row_count: number;
}

export type ChartSpec =
  | { type: "empty" }
  | { type: "table" }
  | { type: "kpi"; label: string; value: any }
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
