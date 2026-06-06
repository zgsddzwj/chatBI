import { useEffect, useState } from "react";
import { Table, Tag, Typography, message as msgApi } from "antd";
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

export function SettingsPage() {
  const { user } = useAuth();
  const [sources, setSources] = useState<DataSource[]>([]);
  const [logs, setLogs] = useState<AuditLog[]>([]);

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
