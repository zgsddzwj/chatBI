import { useEffect, useState } from "react";
import { Card, Col, Empty, Row, Spin, Typography } from "antd";
import { listCards } from "../api";
import type { DashboardCard } from "../api";
import { ChartView } from "../components/ChartView";
import type { ChartSpec } from "../types";

export function DashboardsPage() {
  const [cards, setCards] = useState<DashboardCard[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listCards()
      .then(setCards)
      .catch(() => setCards([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spin style={{ margin: 40 }} />;

  return (
    <div className="page-content">
      <Typography.Title level={3}>我的仪表盘</Typography.Title>
      {cards.length === 0 ? (
        <Empty description="暂无收藏图表，在对话中点击 Pin 收藏" />
      ) : (
        <Row gutter={[16, 16]}>
          {cards.map((c) => (
            <Col key={c.id} xs={24} sm={12} lg={8}>
              <Card title={c.title} size="small">
                <ChartView chart={(c.chart || { type: "empty" }) as ChartSpec} data={c.data} />
              </Card>
            </Col>
          ))}
        </Row>
      )}
    </div>
  );
}
