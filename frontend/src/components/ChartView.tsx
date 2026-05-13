import ReactECharts from "echarts-for-react";
import { Empty, Table } from "antd";
import type { ChartSpec, QueryResult } from "../types";

interface Props {
  chart?: ChartSpec | null;
  data?: QueryResult | null;
}

const PALETTE = ["#5b8def", "#8b5cf6", "#06b6d4", "#10b981", "#f59e0b", "#ef4444", "#ec4899"];

const formatValue = (v: any): string => {
  if (v === null || v === undefined) return "-";
  if (typeof v === "number") {
    if (Number.isInteger(v)) return v.toLocaleString();
    return v.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }
  return String(v);
};

const renderTable = (data: QueryResult) => {
  const columns = data.columns.map((col) => ({
    title: col,
    dataIndex: col,
    key: col,
    render: (v: any) => formatValue(v),
  }));
  const rows = data.rows.map((row, idx) => {
    const obj: Record<string, any> = { __key: idx };
    data.columns.forEach((col, ci) => {
      obj[col] = row[ci];
    });
    return obj;
  });
  return (
    <Table
      size="small"
      rowKey="__key"
      columns={columns}
      dataSource={rows}
      pagination={rows.length > 10 ? { pageSize: 10, size: "small" } : false}
      scroll={{ x: "max-content" }}
    />
  );
};

export const ChartView: React.FC<Props> = ({ chart, data }) => {
  if (!chart || chart.type === "empty" || !data || data.row_count === 0) {
    return <Empty description="没有查询到匹配的数据" />;
  }

  if (chart.type === "table") {
    return renderTable(data);
  }

  if (chart.type === "kpi") {
    return (
      <div className="kpi-card">
        <div className="kpi-label">{chart.label}</div>
        <div className="kpi-value">{formatValue(chart.value)}</div>
      </div>
    );
  }

  if (chart.type === "pie") {
    const option = {
      tooltip: { trigger: "item" },
      legend: { orient: "vertical", left: "left", textStyle: { fontSize: 12 } },
      color: PALETTE,
      series: [
        {
          name: chart.label || "",
          type: "pie",
          radius: ["35%", "65%"],
          avoidLabelOverlap: true,
          label: { show: true, formatter: "{b}: {d}%" },
          data: chart.data,
        },
      ],
    };
    return <ReactECharts option={option} style={{ height: 360 }} />;
  }

  if (chart.type === "bar" || chart.type === "line") {
    const option = {
      tooltip: { trigger: "axis" },
      legend: { top: 0, textStyle: { fontSize: 12 } },
      grid: { left: 50, right: 20, top: 40, bottom: 60 },
      color: PALETTE,
      xAxis: {
        type: "category",
        data: chart.x,
        name: chart.x_label,
        axisLabel: {
          rotate: chart.x.length > 6 ? 30 : 0,
          fontSize: 11,
        },
      },
      yAxis: {
        type: "value",
        name: chart.y_label,
      },
      series: chart.series.map((s) => ({
        name: s.name,
        type: chart.type,
        data: s.data,
        smooth: chart.type === "line",
        barMaxWidth: 36,
        emphasis: { focus: "series" },
      })),
    };
    return <ReactECharts option={option} style={{ height: 360 }} />;
  }

  return renderTable(data);
};
