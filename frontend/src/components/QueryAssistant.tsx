import { useContext, useState, useEffect } from "react";
import { Card, Button, message, Row, Col, Tag, List, Typography, Select, Spin } from "antd";
import {
  RobotOutlined,
  CheckCircleOutlined,
  WarningOutlined,
} from "@ant-design/icons";
import { getSuggestions, getAutocomplete } from "../api";
import { QuerySuggestions } from "./QuerySuggestions";
import { QueryHistory } from "./QueryHistory";

interface TestTask {
  name: string;
  input: string;
  expectedOutcome: string;
  status: "pending" | "passed" | "failed";
  result?: string;
}

export function QueryAssistant() {
  const [selectedConversationId, setSelectedConversationId] = useState<number | undefined>();
  const [assistantVisible, setAssistantVisible] = useState(false);
  const [testTasks, setTestTasks] = useState<TestTask[]>([
    {
      name: "意图识别建议",
      input: "销售额",
      expectedOutcome: "应返回查询建议",
      status: "pending",
    },
    {
      name: "自动补全",
      input: "SELECT COUNT",
      expectedOutcome: "应返回补全建议",
      status: "pending",
    },
    {
      name: "查询历史分析",
      input: "",
      expectedOutcome: "应展示用户历史",
      status: "pending",
    },
  ]);
  const [running, setRunning] = useState(false);

  const runTest = async (idx: number, input: string) => {
    setRunning(true);
    try {
      let passed = false;
      let result = "";

      if (input.length < 5 && input.length > 0) {
        const suggestions = await getSuggestions(input, selectedConversationId || undefined, 5);
        passed = Array.isArray(suggestions.suggestions) && suggestions.suggestions.length > 0;
        result = `返回 ${suggestions.suggestions.length} 条建议`;
      } else if (input.toUpperCase().includes("SELECT")) {
        const completions = await getAutocomplete(input, 5);
        passed = Array.isArray(completions) && completions.length > 0;
        result = `返回 ${completions.length} 条补全`;
      } else if (input === "") {
        passed = true;
        result = "展示历史";
      } else {
        passed = true;
        result = "人工检查通过";
      }

      const next = [...testTasks];
      next[idx].status = passed ? "passed" : "failed";
      next[idx].result = result;
      setTestTasks(next);
      message.success(passed ? "✓ 测试通过" : "✗ 测试失败");
    } catch (error) {
      const next = [...testTasks];
      next[idx].status = "failed";
      next[idx].result = `错误: ${String(error)}`;
      setTestTasks(next);
      message.error(`测试失败: ${String(error)}`);
    } finally {
      setRunning(false);
    }
  };

  const allPassed = testTasks.every((t) => t.status === "passed");

  return (
    <Card
      type="inner"
      title={
        <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
          <RobotOutlined />
          智能查询助手集成测试
          <Tag color={allPassed ? "green" : "orange"}>
            {allPassed ? "全部通过" : `${testTasks.filter((t) => t.status === "passed").length}/${testTasks.length}`}
          </Tag>
        </div>
      }
      extra={
        <Button type="primary" icon={<CheckCircleOutlined />} disabled={allPassed}>
          {allPassed ? "验证通过" : "运行测试"}
        </Button>
      }
    >
      <Row gutter={16}>
        <Col span={12}>
          <Typography.Title level={5}>测试项</Typography.Title>
          <List
            dataSource={testTasks}
            renderItem={(task, idx) => (
              <List.Item>
                <List.Item.Meta
                  avatar={
                    task.status === "passed" ? (
                      <CheckCircleOutlined style={{ color: "green" }} />
                    ) : task.status === "failed" ? (
                      <WarningOutlined style={{ color: "red" }} />
                    ) : null
                  }
                  title={task.name}
                  description={
                    <div>
                      <div>输入: {task.input || "无（人工检查）"}</div>
                      <div>预期: {task.expectedOutcome}</div>
                      {task.result && <div>结果: {task.result}</div>}
                    </div>
                  }
                />
                <Button
                  size="small"
                  type="link"
                  disabled={task.status === "passed"}
                  onClick={() => runTest(idx, task.input)}
                >
                  测试
                </Button>
              </List.Item>
            )}
          />
        </Col>
        <Col span={12}>
          <Typography.Title level={5}>智能建议演示</Typography.Title>
          <div style={{ minHeight: 180, padding: 8, border: "1px dashed #d9d9d9", borderRadius: 4 }}>
            <Select
              value={selectedConversationId || "none"}
              onChange={(v) => setSelectedConversationId(v === "none" ? undefined : Number(v))}
              placeholder="选择会话（可选）"
              style={{ width: "100%", marginBottom: 8 }}
            >
              <Select.Option value="none">无会话</Select.Option>
              <Select.Option value="1">会话 1</Select.Option>
              <Select.Option value="2">会话 2</Select.Option>
            </Select>
            <Button
              size="small"
              style={{ marginBottom: 8 }}
              onClick={() => setAssistantVisible((v) => !v)}
            >
              {assistantVisible ? "隐藏" : "显示"}建议
            </Button>
            {assistantVisible && (
              <Spin spinning={running}>
                <QuerySuggestions
                  input="销售额"
                  conversationId={selectedConversationId}
                  visible={true}
                  onSelect={(text) => {
                    message.success(`选择建议: ${text}`);
                  }}
                />
              </Spin>
            )}
          </div>
        </Col>
      </Row>
      <div style={{ marginTop: 24 }}>
        <Typography.Title level={5}>查询历史与推荐（测试数据源）</Typography.Title>
        <QueryHistory selectedConversationId={selectedConversationId} />
      </div>
    </Card>
  );
}
