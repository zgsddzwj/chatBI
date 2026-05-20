import { useRef, useMemo } from "react";
import { useVirtualList } from "../hooks/useVirtualList";
import { AssistantMessage } from "./AssistantMessage";
import type { QueryResult, ChartSpec } from "../types";

interface MessageItem {
  id: number | string;
  role: "user" | "assistant";
  content: string;
  sql?: string | null;
  result?: QueryResult | null;
  chart?: ChartSpec | null;
  summary?: string | null;
  error?: string | null;
  clarification?: string | null;
  streaming?: boolean;
}

interface Props {
  messages: MessageItem[];
  onPin?: (message: MessageItem) => void;
}

const ITEM_HEIGHT_ESTIMATE = 120;

export const VirtualMessageList: React.FC<Props> = ({ messages, onPin }) => {
  const containerRef = useRef<HTMLDivElement>(null);

  const { virtualItems, totalHeight } = useVirtualList(
    messages,
    containerRef,
    { itemHeight: ITEM_HEIGHT_ESTIMATE, overscan: 2 }
  );

  return (
    <div
      ref={containerRef}
      style={{ flex: 1, overflowY: "auto", position: "relative" }}
    >
      <div style={{ height: totalHeight, position: "relative" }}>
        {virtualItems.map(({ index, style }) => {
          const m = messages[index];
          if (!m) return null;
          return (
            <div key={m.id} style={style} className={`message ${m.role}`}>
              {m.role === "user" ? (
                <div className="bubble">{m.content}</div>
              ) : (
                <AssistantMessage
                  summary={m.summary || m.content}
                  sql={m.sql}
                  data={m.result as any}
                  chart={m.chart as any}
                  error={m.error}
                  clarification={m.clarification}
                  streaming={m.streaming}
                  onPin={
                    onPin && m.chart && m.chart.type !== "empty" && m.chart.type !== "table"
                      ? () => onPin(m)
                      : undefined
                  }
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
