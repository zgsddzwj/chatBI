import ReactECharts from "echarts-for-react";
import { Empty, Table, Button, Space, Modal, InputNumber, message } from "antd";
import type { ChartSpec, QueryResult } from "../types";
import { useRef, useState } from "react";
import { DownloadOutlined } from "@ant-design/icons";
import { usePreferences } from "../hooks/usePreferences";

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

const renderTable = (data: QueryResult, pageSize: number) => {
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
      pagination={rows.length > pageSize ? { pageSize, size: "small" } : false}
      scroll={{ x: "max-content" }}
    />
  );
};

const isNumericKpiValue = (v: unknown): boolean =>
  typeof v === "number" && Number.isFinite(v);

export const ChartView: React.FC<Props> = ({ chart, data }) => {
  const { prefs } = usePreferences();
  const echartsRef = useRef<ReactECharts>(null);
  const [exportModalOpen, setExportModalOpen] = useState(false);
  const [exportWidth, setExportWidth] = useState(1280);
  const [exportHeight, setExportHeight] = useState(720);
  const [exportLoading, setExportLoading] = useState(false);

  const handleExportPng = async () => {
    setExportLoading(true);
    try {
      const instance = echartsRef.current?.getEchartsInstance();
      if (instance) {
        const canvas = (instance.getZr()?.dom as any)
        if (canvas && typeof canvas.toDataURL === 'function') {
          const pngUrl = canvas.toDataURL('image/png', { backgroundColor: '#fff' })
          const link = document.createElement('a')
          link.download = `chart-${new Date().toISOString().slice(0,19).replace(/[:-]/g,'')}.png`
          link.href = pngUrl
          document.body.appendChild(link)
          link.click()
          document.body.removeChild(link)
        } else {
          message.error('Canvas 未准备就绪')
        }
      } else {
        message.error('图表实例未准备好')
      }
    } catch (error: unknown) {
      message.error('导出失败')
      console.error(error)
    }
    setExportLoading(false);
  };

  if (!chart || chart.type === "empty" || !data || data.row_count === 0) {
    return <Empty description="没有查询到匹配的数据" />;
  }

  // 用户偏好：如果设置了默认图表类型，且后端推荐 table，则尝试用偏好类型
  let effectiveChart: ChartSpec = chart;
  if (prefs.defaultChartType && prefs.defaultChartType !== "auto" && chart.type === "table") {
    // 这里只做简单映射，实际转换需要数据结构支持，暂时仅标记意图
    // 未来可实现：根据 data 重新生成对应 chart spec
  }

  if (effectiveChart.type === "table") {
    return renderTable(data, prefs.tablePageSize || 10);
  }
  if ((effectiveChart as any).type === "heatmap") {
    const cm = effectiveChart as unknown as { x?: any; y?: any; data?: any; x_label?: string; y_label?: string; value_label?: string };
    const x = Array.isArray(cm.x) ? cm.x : [];
    const y = Array.isArray(cm.y) ? cm.y : [];
    const dataGrid = Array.isArray(cm.data) ? cm.data : [];
    if (!x.length || !y.length || !dataGrid.length) {
      return <Empty description="热力图数据不完整" />;
    }
    const option = {
      tooltip: { trigger: "item", formatter: cm.x_label && cm.y_label && cm.value_label ? `{a}: {c}<br/>${cm.x_label}: {b}<br/>${cm.y_label}: {a}` : "" },
      xAxis: { type: "category", data: x, name: cm.x_label },
      yAxis: { type: "category", data: y, name: cm.y_label },
      visualMap: {
        min: Math.min(...(dataGrid.flat().filter((v: any) => v !== null).map(Number))),
        max: Math.max(...(dataGrid.flat().filter((v: any) => v !== null).map(Number))),
        calculable: true,
        orient: "horizontal",
        left: "center",
        bottom: 10,
      },
      series: [
        {
          name: cm.value_label || "值",
          type: "heatmap",
          data: dataGrid.map((item: any, yi: number) => {
            return item.map((value: any, xi: number) => {
              return [xi, yi, value === null ? 0 : value]
            })
          }).flat(),
          label: { show: true, fontSize: 10 },
          emphasis: { itemStyle: { shadowBlur: 10, shadowColor: "rgba(0, 0, 0, 0.5)" } },
        },
      ],
    }
    return (
      <div style={{ position: "relative" }}>
        <div style={{ position: "absolute", top: 8, right: 12, zIndex: 10 }}>
          <Button type="text" icon={<DownloadOutlined />} size="small" onClick={() => setExportModalOpen(true)} title="导出图片" />
        </div>
        <ReactECharts
          ref={echartsRef}
          option={option}
          style={{ height: 360 }}
        />
      </div>
    );
  }
  if ((effectiveChart as any).type === "correlation") {
    const cm = effectiveChart as unknown as { variables?: any; matrix?: any };
    const variables = Array.isArray(cm.variables) ? cm.variables : [];
    const matrix = Array.isArray(cm.matrix) ? cm.matrix : [];
    if (!variables.length || !matrix.length) {
      return <Empty description="相关性矩阵数据不完整" />;
    }
    const option = {
      tooltip: {
        trigger: "item",
        formatter: `{b}: <br/>${"相关性"}: {c}`,
      },
      xAxis: { type: "category", data: variables, name: "变量" },
      yAxis: { type: "category", data: variables, name: "变量" },
      visualMap: {
        min: -1,
        max: 1,
        calculable: true,
        orient: "horizontal",
        left: "center",
        bottom: 10,
        inRange: { color: ["#d73027", "#f46d43", "#fdae61", "#fee08b", "#d9ef8b", "#a6d96a", "#66bd63", "#1a9850"] },
      },
      series: [
        {
          name: "相关性",
          type: "heatmap",
          data: variables.map((varNameX: string, xi: number) => {
            return variables.map((varNameY: string, yi: number) => {
              return [xi, yi, matrix[yi][xi]]
            })
          }).flat(),
          label: { show: true, fontSize: 10, formatter: `{c}` },
          emphasis: { itemStyle: { shadowBlur: 10, shadowColor: "rgba(0, 0, 0, 0.5)" } },
        },
      ],
    }
    return (
      <div style={{ position: "relative" }}>
        <div style={{ position: "absolute", top: 8, right: 12, zIndex: 10 }}>
          <Button type="text" icon={<DownloadOutlined />} size="small" onClick={() => setExportModalOpen(true)} title="导出图片" />
        </div>
        <ReactECharts
          ref={echartsRef}
          option={option}
          style={{ height: 360 }}
        />
      </div>
    );
  }
  if (effectiveChart.type === "kpi") {
    const label = effectiveChart.label ?? "";
    const value = effectiveChart.value;
    const useProse = !isNumericKpiValue(value);
    return (
      <div className="kpi-card">
        <div className="kpi-label">{label}</div>
        <div className={useProse ? "kpi-value-prose" : "kpi-value"}>{formatValue(value)}</div>
      </div>
    );
  }

  if (effectiveChart.type === "pie") {
    const raw = Array.isArray(effectiveChart.data) ? effectiveChart.data : [];
    const pieData = raw.filter(
      (d) =>
        d &&
        typeof d.name === "string" &&
        typeof d.value === "number" &&
        Number.isFinite(d.value),
    );
    if (!pieData.length) {
      return <Empty description="当前结果无法绘制成饼图，已改为表格展示。" />;
    }
    const option = {
      tooltip: { trigger: "item" },
      legend: { orient: "vertical", left: "left", textStyle: { fontSize: 12 } },
      color: PALETTE,
      series: [
        {
          name: effectiveChart.label || "",
          type: "pie",
          radius: ["35%", "65%"],
          avoidLabelOverlap: true,
          label: { show: true, fontSize: 11, formatter: "{b}: {d}%" },
          data: pieData,
        },
      ],
    };
    return (
      <div style={{ position: "relative" }}>
        <div style={{ position: "absolute", top: 8, right: 12, zIndex: 10 }}>
          <Button type="text" icon={<DownloadOutlined />} size="small" onClick={() => setExportModalOpen(true)} title="导出图片" />
        </div>
        <ReactECharts
          ref={echartsRef}
          option={option}
          style={{ height: 360 }}
        />
      </div>
    );
  }

  if (effectiveChart.type === "bar" || effectiveChart.type === "line") {
    const x = Array.isArray(effectiveChart.x) ? effectiveChart.x : [];
    const seriesList = Array.isArray(effectiveChart.series) ? effectiveChart.series : [];
    if (!x.length || !seriesList.length) {
      return <Empty description="图表数据不完整，已改为表格展示。" />;
    }
    const badSeries = seriesList.some(
      (s) => !s || !Array.isArray(s.data) || s.data.length !== x.length,
    );
    if (badSeries) {
      return renderTable(data, prefs.tablePageSize || 10);
    }
    const option = {
      tooltip: { trigger: "axis" },
      legend: { top: 0, textStyle: { fontSize: 12 } },
      grid: { left: 50, right: 20, top: 40, bottom: 60 },
      color: PALETTE,
      xAxis: {
        type: "category",
        data: x,
        name: effectiveChart.x_label,
        axisLabel: {
          rotate: x.length > 6 ? 30 : 0,
          fontSize: 11,
        },
      },
      yAxis: {
        type: "value",
        name: effectiveChart.y_label,
      },
      series: seriesList.map((s) => ({
        name: s.name,
        type: effectiveChart.type,
        data: s.data,
        smooth: effectiveChart.type === "line",
        barMaxWidth: 36,
        emphasis: { focus: "series" },
      })),
    };
    return (
      <div style={{ position: "relative" }}>
        <div style={{ position: "absolute", top: 8, right: 12, zIndex: 10 }}>
          <Button type="text" icon={<DownloadOutlined />} size="small" onClick={() => setExportModalOpen(true)} title="导出图片" />
        </div>
        <ReactECharts
          ref={echartsRef}
          option={option}
          style={{ height: 360 }}
        />
      </div>
    );
  }

  return (
    <>
      {renderTable(data, prefs.tablePageSize || 10)}
      <Modal
        open={exportModalOpen}
        onCancel={() => setExportModalOpen(false)}
        onOk={handleExportPng}
        confirmLoading={exportLoading}
        title="导出图片"
        okText="导出"
        width={400}
      >
        <Space direction="vertical" style={{ width: "100%" }}>
          <div>
            <span style={{ display: "inline-block", width: 60 }}>宽度:</span>
            <InputNumber
              min={400}
              max={4096}
              value={exportWidth}
              onChange={(v) => setExportWidth(v || 1280)}
              style={{ width: "100%" }}
            />
          </div>
          <div>
            <span style={{ display: "inline-block", width: 60 }}>高度:</span>
            <InputNumber
              min={300}
              max={4096}
              value={exportHeight}
              onChange={(v) => setExportHeight(v || 720)}
              style={{ width: "100%" }}
            />
          </div>
        </Space>
      </Modal>
    </>
  );
};
