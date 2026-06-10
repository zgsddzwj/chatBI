import { useRef, useState } from "react";
import { message as msgApi } from "antd";
import { sendChatStream } from "../api";
import type { ChartSpec, QueryResult, StreamEvent, UIMessage } from "../types";

interface UseChatOptions {
  activeId: number | null;
  setActiveId: (id: number | null) => void;
  messages: UIMessage[];
  setMessages: React.Dispatch<React.SetStateAction<UIMessage[]>>;
  onConversationUpdated: () => void;
}

export function useChat({
  activeId,
  setActiveId,
  messages,
  setMessages,
  onConversationUpdated,
}: UseChatOptions) {
  const [loading, setLoading] = useState(false);
  const abortRef = useRef<(() => void) | null>(null);

  const sendQuestion = async (question: string) => {
    if (!question.trim() || loading) return;

    const userMsg: UIMessage = {
      id: `u-${Date.now()}`,
      role: "user",
      content: question,
    };
    const placeholder: UIMessage = {
      id: `a-${Date.now()}`,
      role: "assistant",
      content: "",
      pending: true,
      streaming: true,
    };
    setMessages((prev) => [...prev, userMsg, placeholder]);
    setLoading(true);

    const history = messages
      .filter((m) => !m.pending && m.content)
      .map((m) => ({ role: m.role, content: m.content }));

    let currentSql: string | undefined;
    let currentData: QueryResult | undefined;
    let currentChart: ChartSpec | undefined;
    let currentSummary = "";
    let currentMsgId: number | string = placeholder.id;
    let currentProgress: { step: string; status: string } | null = null;

    const handleEvent = (evt: StreamEvent) => {
      if (evt.type === "progress") {
        // 新版 Data Agent 进度事件
        currentProgress = evt.step ? { step: evt.step, status: evt.status || "running" } : null;
        setMessages((prev) => {
          const next = [...prev];
          const idx = next.findIndex((m) => m.id === placeholder.id);
          if (idx >= 0) {
            next[idx] = {
              ...next[idx],
              content: currentProgress ? `正在${currentProgress.step}...` : "",
              pending: true,
              streaming: true,
            };
          }
          return next;
        });
      } else if (evt.type === "thinking" && evt.conversation_id) {
        setActiveId(evt.conversation_id);
      } else if (evt.type === "sql") {
        currentSql = evt.sql;
      } else if (evt.type === "data") {
        currentData = evt.data;
      } else if (evt.type === "chart") {
        currentChart = evt.chart;
      } else if (evt.type === "summary_chunk") {
        currentSummary = evt.chunk || "";
        setMessages((prev) => {
          const next = [...prev];
          const idx = next.findIndex((m) => m.id === placeholder.id);
          if (idx >= 0) {
            next[idx] = {
              ...next[idx],
              id: currentMsgId,
              role: "assistant",
              content: currentSummary,
              summary: currentSummary,
              sql: currentSql,
              result: currentData,
              chart: currentChart,
              pending: false,
              streaming: !evt.done,
            };
          }
          return next;
        });
      } else if (evt.type === "clarification") {
        setMessages((prev) => {
          const next = [...prev];
          const idx = next.findIndex((m) => m.id === placeholder.id);
          if (idx >= 0) {
            next[idx] = {
              ...next[idx],
              role: "assistant",
              content: evt.clarification || "",
              clarification: evt.clarification || null,
              pending: false,
              streaming: false,
            };
          }
          return next;
        });
        setLoading(false);
        onConversationUpdated();
      } else if (evt.type === "done") {
        if (evt.conversation_id) setActiveId(evt.conversation_id);
        if (evt.message_id) currentMsgId = evt.message_id;
        setMessages((prev) => {
          const next = [...prev];
          const idx = next.findIndex((m) => m.id === placeholder.id);
          if (idx >= 0) {
            next[idx] = {
              ...next[idx],
              id: currentMsgId,
              role: "assistant",
              content: currentSummary,
              summary: currentSummary,
              sql: currentSql,
              result: currentData,
              chart: currentChart,
              pending: false,
              streaming: false,
            };
          }
          return next;
        });
        setLoading(false);
        onConversationUpdated();
      } else if (evt.type === "error") {
        setMessages((prev) => {
          const next = [...prev];
          const idx = next.findIndex((m) => m.id === placeholder.id);
          if (idx >= 0) {
            next[idx] = {
              ...next[idx],
              id: `e-${Date.now()}`,
              role: "assistant",
              content: evt.error || "请求失败",
              error: evt.error || "请求失败",
              pending: false,
              streaming: false,
            };
          }
          return next;
        });
        setLoading(false);
        msgApi.error(`请求失败: ${evt.error}`);
      }
    };

    abortRef.current = sendChatStream(
      { question, conversation_id: activeId, history },
      handleEvent,
      (errMsg) => {
        setLoading(false);
        msgApi.error(`请求失败: ${errMsg}`);
      },
    );
  };

  return { loading, sendQuestion, abortRef };
}
