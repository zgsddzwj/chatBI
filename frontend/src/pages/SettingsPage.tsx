import { useEffect, useState } from "react";
import { Table, Tag, Typography, message as msgApi, Card, Form, Select, Switch, InputNumber, Button, Space, Statistic, Row, Col, Popconfirm } from "antd";
import { listDataSources, getCacheStats, clearCache } from "../api";
import type { DataSource, CacheStats } from "../api";
// import { getAuditLogs, type AuditLog } from "../api";

interface AuditLog {
  id: number;
  action: string;
  user_id?: number;
  created_at: string;
  detail?: string;
}

import { useAuth } from "../contexts/AuthContext";
import { usePreferences } from "../hooks/usePreferences";
import { QueryAssistant } from "../components/QueryAssistant";

export function SettingsPage() {
  const { user } = useAuth();
  const [sources, setSources] = useState<DataSource[]>([]);
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [cacheStats, setCacheStats] = useState<CacheStats | null>(null);
  const { prefs, setPrefs, resetPrefs } = usePreferences();

  const loadCacheStats = () => {
    getCacheStats().then(setCacheStats).catch(() => msgApi.error("加载缓存统计失败"));
  };

  const handleClearCache = async () => {
    try {
      const res = await clearCache();
      msgApi.success(res.message);
      loadCacheStats();
    } catch {
      msgApi.error("清空缓存失败");
    }
  };

  useEffect(() => {
    listDataSources().then(setSources).catch(() => msgApi.error("加载数据源失败"));
    if (user?.role === "admin") {
      // getAuditLogs().then(setLogs).catch(() => undefined);
      setLogs([]);
      loadCacheStats();
    }
  }, [user]);

  return (
    <div className="page-content">
      <Typography.Title level={3}>设置</Typography.Title>

      <Card title="偏好设置" style={{ marginBottom: 24 }}>
        <Form layout="vertical">
          <Form.Item label="默认图表类型">
            <Select
              value={prefs.defaultChartType}
              onChange={(v) => setPrefs({ defaultChartType: v })}
              options={[
                { value: "auto", label: "自动（跟随后端推荐）" },
                { value: "bar", label: "柱状图" },
                { value: "line", label: "折线图" },
                { value: "pie", label: "饼图" },
                { value: "table", label: "表格" },
              ]}
              style={{ width: 240 }}
            />
          </Form.Item>
          <Form.Item label="表格每页行数">
            <InputNumber
              min={5}
              max={100}
              value={prefs.tablePageSize}
              onChange={(v) => setPrefs({ tablePageSize: v || 10 })}
            />
          </Form.Item>
          <Form.Item label="深色模式">
            <Switch checked={prefs.darkMode} onChange={(v) => setPrefs({ darkMode: v })} />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button onClick={resetPrefs}>恢复默认</Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>

      <Typography.Title level={5}>数据源</Typography.Title>
      <Table
        rowKey="id"
        dataSource={sources}
        pagination={false}
        columns={[
          { title: "名称", dataIndex: "name" },
          { title: "类型", dataIndex: "db_type" },
          {
            title: "状态",
            render: (_, r) => (
              <Tag color={r.is_active ? "green" : "default"}>{r.is_active ? "启用" : "禁用"}</Tag>
            ),
          },
          {
            title: "默认",
            render: (_, r) => (r.is_default ? <Tag color="blue">默认</Tag> : null),
          },
        ]}
      />

      {user?.role === "admin" && (
        <>
          <Typography.Title level={5} style={{ marginTop: 24 }}>查询缓存管理</Typography.Title>
          <Card style={{ marginBottom: 24 }}>
            <Row gutter={16}>
              <Col span={6}>
                <Statistic title="总条目" value={cacheStats?.total_entries ?? 0} />
              </Col>
              <Col span={6}>
                <Statistic title="活跃缓存" value={cacheStats?.active_entries ?? 0} />
              </Col>
              <Col span={6}>
                <Statistic title="总命中" value={cacheStats?.total_hits ?? 0} />
              </Col>
              <Col span={6}>
                <Statistic title="命中率" value={cacheStats?.hit_rate ?? 0} suffix="%" />
              </Col>
            </Row>
            <div style={{ marginTop: 16 }}>
              <Popconfirm
                title="确认清空所有缓存？"
                onConfirm={handleClearCache}
                okText="确认"
                cancelText="取消"
              >
                <Button danger>清空缓存</Button>
              </Popconfirm>
              <Button style={{ marginLeft: 8 }} onClick={loadCacheStats}>刷新</Button>
            </div>
            {cacheStats && cacheStats.top_queries.length > 0 && (
              <div style={{ marginTop: 16 }}>
                <Typography.Text strong>热门查询 Top 5</Typography.Text>
                <Table
                  rowKey={(r) => r.sql}
                  dataSource={cacheStats.top_queries}
                  size="small"
                  pagination={false}
                  columns={[
                    { title: "SQL", dataIndex: "sql", ellipsis: true },
                    { title: "命中次数", dataIndex: "hits", width: 100 },
                    { title: "最后命中", dataIndex: "last_hit", width: 180 },
                  ]}
                />
              </div>
            )}
          </Card>

          <Typography.Title level={5} style={{ marginTop: 24 }}>审计日志</Typography.Title>
          <Table
            rowKey="id"
            dataSource={logs}
            size="small"
            columns={[
              { title: "用户", dataIndex: "username" },
              { title: "操作", dataIndex: "action" },
              { title: "资源", dataIndex: "resource" },
              { title: "时间", dataIndex: "created_at" },
            ]}
          />
        </>
      )}
      <div style={{ marginTop: 32 }}>
        <QueryAssistant />
      </div>
    </div>
  );
}
