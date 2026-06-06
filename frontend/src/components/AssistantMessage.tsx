import { useState } from "react";
import { Tabs, Tag, Tooltip, Button, message as msgApi, Rate, Input } from "antd";
import {
  BarChartOutlined,
  TableOutlined,
  CodeOutlined,
  CopyOutlined,
  StarOutlined,
  BookOutlined,
} from "@ant-design/icons";
import type { ChartSpec, QueryResult } from "../types";
import { ChartView } from "./ChartView";
import { submitFeedback } from "../api";

function normalizeQueryResult(raw: QueryResult | null | undefined): QueryResult | null {
  if (!raw) return null;
  const columns = Array.isArray(raw.columns) ? raw.columns.map(String) : [];
  const rows = Array.isArray(raw.rows) ? raw.rows : [];
  const n = columns.length;
  const safeRows = rows.map((row) => {
    const r = Array.isArray(row) ? row : [];
    if (n <= 0) return r;
    const copy = r.slice(0, n);
    while (copy.length < n) copy.push(null);
    return copy;
  });
  const row_count = typeof raw.row_count === "number" ? raw.row_count : safeRows.length;
  return { columns, rows: safeRows, row_count };
}

interface Props {
  messageId?: number;
  summary?: string | null;
  sql?: string | null;
  data?: QueryResult | null;
  chart?: ChartSpec | null;
  error?: string | null;
  clarification?: string | null;
  streaming?: boolean;
  onPin?: () => void;
  onBookmark?: () => void;
}

const renderTable = (data: QueryResult) => {
  return (
    <div style={{ maxHeight: 360, overflow: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
        <thead>
          <tr>
            {data.columns.map((col) => (
              <th
                key={col}
                style={{
                  border: "1px solid #e8ebf3",
                  padding: "6px 10px",
                  background: "#f6f7fb",
                  textAlign: "left",
                  whiteSpace: "nowrap",
                }}
              >
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.rows.slice(0, 100).map((row, i) => (
            <tr key={i}>
              {data.columns.map((_, j) => {
                const v = row[j];
                return (
                  <td
                    key={j}
                    style={{
                      border: "1px solid #e8ebf3",
                      padding: "5px 10px",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {v === null || v === undefined ? "-" : String(v)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      {data.rows.length > 100 && (
        <div style={{ color: "#9aa0b5", fontSize: 12, marginTop: 8 }}>
          只显示前 100 行，共 {data.row_count} 行
        </div>
      )}
    </div>
  );
};

export const AssistantMessage: React.FC<Props> = ({
  messageId,
  summary,
  sql,
  data,
  chart,
  error,
  clarification,
  streaming,
  onPin,
  onBookmark,
}) => {
  const [tab, setTab] = useState<string>(() => (chart?.type === "table" ? "table" : "chart"));
  const [rating, setRating] = useState<number>(0);
  const [comment, setComment] = useState<string>("");
  const [feedbackSent, setFeedbackSent] = useState(false);
  const safeData = normalizeQueryResult(data);

  const handleRate = async (value: number) => {
    setRating(value);
    if (messageId && value > 0) {
      try {
        await submitFeedback({ message_id: messageId, rating: value, comment: comment || undefined });
        setFeedbackSent(true);
        msgApi.success("感谢反馈！");
      } catch {
        msgApi.error("提交失败");
      }
    }
  };

  if (error) {
    return (
      <div className="assistant-card">
        <Tag color="red">出错</Tag>
        <div style={{ marginTop: 8, color: "#dc2626" }}>{error}</div>
      </div>
    );
  }

  if (clarification) {
    return (
      <div className="assistant-card">
        <Tag color="orange">需要补充</Tag>
        <div style={{ marginTop: 8 }}>{clarification}</div>
      </div>
    );
  }

  const copySQL = async () => {
    if (!sql) return;
    try {
      await navigator.clipboard.writeText(sql);
      msgApi.success("SQL 已复制");
    } catch {
      msgApi.error("复制失败，请检查浏览器权限");
    }
  };

  return (
    <div className="assistant-card">
      {summary && (
        <div className="assistant-summary" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
          <span style={{ flex: 1 }}>{summary}</span>
          <div style={{ display: "flex", gap: 4 }}>
            {onBookmark && (
              <Tooltip title="收藏查询模板">
                <Button size="small" icon={<BookOutlined />} onClick={onBookmark} />
              </Tooltip>
            )}
            {onPin && chart && chart.type !== "empty" && chart.type !== "table" && (
              <Tooltip title="收藏到仪表盘">
                <Button size="small" icon={<StarOutlined />} onClick={onPin} />
              </Tooltip>
            )}
          </div>
          {streaming && <span className="typing-cursor" />}
        </div>
      )}

      {safeData && safeData.row_count > 0 && !safeData.columns.length && (
        <div style={{ color: "#9aa0b5", fontSize: 13 }}>返回数据缺少列信息，无法展示表格。</div>
      )}

      {safeData && safeData.row_count > 0 && safeData.columns.length > 0 && (
        <Tabs
          activeKey={tab}
          onChange={setTab}
          size="small"
          items={[
            {
              key: "chart",
              label: (
                <span>
                  <BarChartOutlined /> 图表
                </span>
              ),
              children: <ChartView chart={chart} data={safeData} />,
            },
            {
              key: "table",
              label: (
                <span>
                  <TableOutlined /> 数据 ({safeData.row_count})
                </span>
              ),
              children: renderTable(safeData),
            },
            {
              key: "sql",
              label: (
                <span>
                  <CodeOutlined /> SQL
                </span>
              ),
              children: (
                <div>
                  <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 4 }}>
                    <Tooltip title="复制 SQL">
                      <Button size="small" icon={<CopyOutlined />} onClick={() => void copySQL()}>
                        复制
                      </Button>
                    </Tooltip>
                  </div>
                  <pre className="sql-block">{sql ?? "（无 SQL）"}</pre>
                </div>
              ),
            },
          ]}
        />
      )}

      {safeData && safeData.row_count === 0 && (
        <div style={{ color: "#9aa0b5", fontSize: 13 }}>未查询到匹配数据。</div>
      )}

      {messageId && !streaming && !error && !clarification && (
        <div style={{ marginTop: 12, paddingTop: 8, borderTop: "1px solid #e8ebf3" }}>
          {feedbackSent ? (
            <span style={{ fontSize: 13, color: "#10b981" }}>✓ 已收到反馈</span>
          ) : (
            <>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: 13, color: "#6b7184" }}>这个回答有帮助吗？</span>
                <Rate value={rating} onChange={handleRate} style={{ fontSize: 16 }} />
              </div>
              {rating > 0 && (
                <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
                  <Input.TextArea
                    placeholder="可选：留下具体建议..."
                    value={comment}
                    onChange={(e) => setComment(e.target.value)}
                    autoSize={{ minRows: 2, maxRows: 4 }}
                    style={{ flex: 1 }}
                  />
                  <Button type="primary" size="small" onClick={() => handleRate(rating)}>
                    提交
                  </Button>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
};
