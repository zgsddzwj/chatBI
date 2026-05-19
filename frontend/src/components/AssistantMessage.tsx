import { useState } from "react";
import { Tabs, Tag, Tooltip, Button, message as msgApi } from "antd";
import {
  BarChartOutlined,
  TableOutlined,
  CodeOutlined,
  CopyOutlined,
} from "@ant-design/icons";
import type { ChartSpec, QueryResult } from "../types";
import { ChartView } from "./ChartView";

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
  summary?: string | null;
  sql?: string | null;
  data?: QueryResult | null;
  chart?: ChartSpec | null;
  error?: string | null;
  clarification?: string | null;
  streaming?: boolean;
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
  summary,
  sql,
  data,
  chart,
  error,
  clarification,
  streaming,
}) => {
  const [tab, setTab] = useState<string>(() => (chart?.type === "table" ? "table" : "chart"));
  const safeData = normalizeQueryResult(data);

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
        <div className="assistant-summary">
          {summary}
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
    </div>
  );
};
