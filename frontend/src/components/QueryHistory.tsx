import { useContext, useEffect, useState } from "react";
import {
  Card,
  List,
  Tag,
  Tooltip,
  Row,
  Col,
  Statistic,
  Spin,
  Empty,
  Button,
  message,
  Select,
} from "antd";
import {
  UserOutlined,
  ClockCircleOutlined,
  ThunderboltOutlined,
  BarChartOutlined,
  BulbOutlined,
} from "@ant-design/icons";
import {
  getHistory,
  getHistoryStats,
  getHistoryRecommendations,
  getHistoryPatterns,
} from "../api";

interface Props {
  selectedConversationId?: number;
}

export function QueryHistory({ selectedConversationId }: Props) {
  const mockUserId = 999;
  const [activeTab, setActiveTab] = useState("history");
  const [history, setHistory] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [recommendations, setRecommendations] = useState<any[]>([]);
  const [patterns, setPatterns] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadData();
  }, [activeTab]);

  const loadData = async () => {
    setLoading(true);
    try {
      switch (activeTab) {
        case "history": {
          const data = await getHistory(mockUserId);
          setHistory(data.history || []);
          break;
        }
        case "stats": {
          const data = await getHistoryStats(mockUserId);
          setStats(data);
          break;
        }
        case "recommendations": {
          const data = await getHistoryRecommendations(mockUserId);
          setRecommendations(data.recommendations || []);
          break;
        }
        case "patterns": {
          const data = await getHistoryPatterns(mockUserId);
          setPatterns(data.patterns || []);
          break;
        }
      }
    } catch (err) {
      message.error("获取数据失败");
    } finally {
      setLoading(false);
    }
  };

  const renderHistoryTab = () => (
    <List
      itemLayout="horizontal"
      dataSource={history}
      loading={loading}
      renderItem={(item) => (
        <List.Item>
          <List.Item.Meta
            avatar={<UserOutlined style={{ color: "#1890ff" }} />}
            title={
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                {item.intent && <Tag color="blue">{item.intent}</Tag>}
                <Tag color={item.success ? "green" : "red"}>
                  {item.success ? "成功" : "失败"}
                </Tag>
              </div>
            }
            description={
              <>
                <div style={{ fontFamily: "monospace", background: "#f5f5f5", padding: 8, borderRadius: 4, maxWidth: 400, wordBreak: "break-all" }}>
                  {item.sql}
                </div>
                <small style={{ color: "#888" }}>
                  <ClockCircleOutlined /> {new Date(item.created_at).toLocaleString()}
                </small>
              </>
            }
          />
        </List.Item>
      )}
    />
  );

  const renderStatsTab = () => (
    <div>
      {stats ? (
        <Row gutter={16}>
          <Col span={8}>
            <Statistic
              title="总查询次数"
              value={stats.total_queries}
              prefix={<ThunderboltOutlined />}
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="成功率"
              value={stats.success_rate}
              precision={2}
              suffix="%"
              prefix={<BarChartOutlined />}
            />
          </Col>
          <Col span={24} style={{ marginTop: 16 }}>
            <h4>Top 意图</h4>
            {stats.top_intents.map((item: any) => (
              <div key={item.intent} style={{ marginBottom: 8 }}>
                <Tag color="blue">{item.intent}</Tag> ×{item.count}
              </div>
            ))}
          </Col>
        </Row>
      ) : (
        <Empty description="暂无统计信息" />
      )}
    </div>
  );

  const renderRecommendationsTab = () => (
    <List
      itemLayout="horizontal"
      dataSource={recommendations}
      loading={loading}
      renderItem={(item) => (
        <List.Item>
          <List.Item.Meta
            avatar={<BulbOutlined style={{ color: "#52c41a" }} />}
            title={<Tag color="green">{item.source}</Tag>}
            description={
              <div style={{ fontFamily: "monospace", background: "#f0f9f0", padding: 8, borderRadius: 4, maxWidth: 400, wordBreak: "break-all" }}>
                {item.sql}
                <br />
                <small style={{ color: "#888" }}>
                  意图: {item.intent} • 得分: {item.score.toFixed(2)}
                </small>
              </div>
            }
          />
        </List.Item>
      )}
    />
  );

  const renderPatternsTab = () => (
    <List
      itemLayout="horizontal"
      dataSource={patterns}
      loading={loading}
      renderItem={(item) => (
        <List.Item>
          <List.Item.Meta
            title={
              <Tag color="blue" style={{ fontFamily: "monospace" }}>
                ×{item.count}
              </Tag>
            }
            description={
              <>
                <div style={{ fontFamily: "monospace", background: "#f5f5f5", padding: 8, borderRadius: 4, maxWidth: 400, wordBreak: "break-all" }}>
                  {item.sql}
                </div>
                <small style={{ color: "#888" }}>模板: {item.pattern}</small>
              </>
            }
          />
        </List.Item>
      )}
    />
  );

  return (
    <Card
      type="inner"
      title={
        <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
          <UserOutlined />
          查询历史与推荐
          <Select
            value={activeTab}
            onChange={setActiveTab}
            labelInValue={false}
            size="small"
          >
            <Select.Option value="history">历史记录</Select.Option>
            <Select.Option value="stats">统计</Select.Option>
            <Select.Option value="recommendations">推荐</Select.Option>
            <Select.Option value="patterns">模式</Select.Option>
          </Select>
        </div>
      }
      extra={
        <Button type="link" size="small" onClick={loadData} disabled={loading}>
          刷新
        </Button>
      }
      style={{ minHeight: 400 }}
    >
      <Spin spinning={loading}>
        {activeTab === "history" && renderHistoryTab()}
        {activeTab === "stats" && renderStatsTab()}
        {activeTab === "recommendations" && renderRecommendationsTab()}
        {activeTab === "patterns" && renderPatternsTab()}
      </Spin>
    </Card>
  );
}
