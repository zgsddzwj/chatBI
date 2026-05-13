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

interface Props {
  summary?: string | null;
  sql?: string | null;
  data?: QueryResult | null;
  chart?: ChartSpec | null;
  error?: string | null;
  clarification?: string | null;
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
              {row.map((v, j) => (
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
              ))}
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
}) => {
  const [tab, setTab] = useState<string>("chart");

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

  const copySQL = () => {
    if (sql) {
      navigator.clipboard.writeText(sql);
      msgApi.success("SQL 已复制");
    }
  };

  return (
    <div className="assistant-card">
      {summary && <div className="assistant-summary">{summary}</div>}

      {data && data.row_count > 0 && (
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
              children: <ChartView chart={chart} data={data} />,
            },
            {
              key: "table",
              label: (
                <span>
                  <TableOutlined /> 数据 ({data.row_count})
                </span>
              ),
              children: renderTable(data),
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
                      <Button size="small" icon={<CopyOutlined />} onClick={copySQL}>
                        复制
                      </Button>
                    </Tooltip>
                  </div>
                  <pre className="sql-block">{sql}</pre>
                </div>
              ),
            },
          ]}
        />
      )}

      {data && data.row_count === 0 && (
        <div style={{ color: "#9aa0b5", fontSize: 13 }}>未查询到匹配数据。</div>
      )}
    </div>
  );
};
