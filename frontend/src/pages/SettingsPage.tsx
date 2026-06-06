import { useEffect, useState } from "react";
import { Table, Tag, Typography, message as msgApi, Card, Form, Select, Switch, InputNumber, Button, Space } from "antd";
import { listDataSources } from "../api";
import type { DataSource } from "../api";
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

export function SettingsPage() {
  const { user } = useAuth();
  const [sources, setSources] = useState<DataSource[]>([]);
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const { prefs, setPrefs, resetPrefs } = usePreferences();

  useEffect(() => {
    listDataSources().then(setSources).catch(() => msgApi.error("加载数据源失败"));
    if (user?.role === "admin") {
      // getAuditLogs().then(setLogs).catch(() => undefined);
      setLogs([]);
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
    </div>
  );
}
