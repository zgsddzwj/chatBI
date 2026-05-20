import { useEffect, useMemo, useRef, useState } from "react";
import {
  Button,
  Input,
  Spin,
  Popconfirm,
  message as msgApi,
  Tooltip,
  Dropdown,
  Modal,
} from "antd";
import {
  PlusOutlined,
  SendOutlined,
  DeleteOutlined,
  BarChartOutlined,
  ExportOutlined,
  ShareAltOutlined,
} from "@ant-design/icons";
import {
  deleteConversation,
  getConversation,
  getSamples,
  listConversations,
  sendChatStream,
  type StreamEvent,
  createCard,
  exportConversationMarkdown,
  exportConversationJson,
  createShareLink,
} from "./api";
import type {
  Conversation,
  MessageHistory,
  QueryResult,
  ChartSpec,
} from "./types";
import { AssistantMessage } from "./components/AssistantMessage";
import { LoginModal } from "./components/LoginModal";
import { getAuth, clearAuth, type AuthUser } from "./auth";
import { getMe } from "./api";

function formatApiErrorDetail(detail: unknown): string {
  if (detail == null) return "";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item: { msg?: string; loc?: unknown } | string) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object" && typeof item.msg === "string") return item.msg;
        try {
          return JSON.stringify(item);
        } catch {
          return String(item);
        }
      })
      .join("；");
  }
  if (typeof detail === "object") {
    try {
      return JSON.stringify(detail);
    } catch {
      return String(detail);
    }
  }
  return String(detail);
}

interface UIMessage extends Omit<Partial<MessageHistory>, "id"> {
  id: number | string;
  role: "user" | "assistant";
  content: string;
  pending?: boolean;
  clarification?: string | null;
  streaming?: boolean;
}

export default function App() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [messages, setMessages] = useState<UIMessage[]>([]);
  const [samples, setSamples] = useState<string[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [user, setUser] = useState<AuthUser | null>(getAuth().user);
  const [loginOpen, setLoginOpen] = useState(false);
  const [shareModalOpen, setShareModalOpen] = useState(false);
  const [shareUrl, setShareUrl] = useState("");
  const chatRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const auth = getAuth();
    if (auth.token) {
      getMe()
        .then((u) => setUser(u))
        .catch(() => {
          clearAuth();
          setUser(null);
        });
    }
  }, []);

  const loadConversations = async () => {
    try {
      const list = await listConversations();
      setConversations(list);
    } catch {
      // 忽略列表加载失败
    }
  };

  useEffect(() => {
    loadConversations();
    getSamples().then(setSamples).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight;
    }
  }, [messages, loading]);

  const openConversation = async (id: number) => {
    setActiveId(id);
    try {
      const detail = await getConversation(id);
      setMessages(
        detail.messages.map((m) => ({
          id: m.id,
          role: m.role,
          content: m.content,
          sql: m.sql,
          result: m.result,
          chart: m.chart,
          summary: m.summary,
          error: m.error,
        })),
      );
    } catch {
      msgApi.error("会话加载失败");
    }
  };

  const newConversation = () => {
    setActiveId(null);
    setMessages([]);
  };

  const handleExportMarkdown = async () => {
    if (!activeId) {
      msgApi.warning("请先选择一个对话");
      return;
    }
    try {
      const blob = await exportConversationMarkdown(activeId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `chatbi-conversation-${activeId}.md`;
      a.click();
      URL.revokeObjectURL(url);
      msgApi.success("Markdown 导出成功");
    } catch {
      msgApi.error("导出失败");
    }
  };

  const handleExportJson = async () => {
    if (!activeId) {
      msgApi.warning("请先选择一个对话");
      return;
    }
    try {
      const blob = await exportConversationJson(activeId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `chatbi-conversation-${activeId}.json`;
      a.click();
      URL.revokeObjectURL(url);
      msgApi.success("JSON 导出成功");
    } catch {
      msgApi.error("导出失败");
    }
  };

  const handleShare = async () => {
    if (!activeId) {
      msgApi.warning("请先选择一个对话");
      return;
    }
    try {
      const res = await createShareLink(activeId);
      const fullUrl = `${window.location.origin}${res.url}`;
      setShareUrl(fullUrl);
      setShareModalOpen(true);
    } catch (err: any) {
      msgApi.error(err?.response?.data?.detail || "创建分享链接失败");
    }
  };

  const removeConversation = async (id: number) => {
    try {
      await deleteConversation(id);
      msgApi.success("已删除");
      if (activeId === id) {
        newConversation();
      }
      loadConversations();
    } catch (err: unknown) {
      const ax = err as { response?: { data?: { detail?: unknown } }; message?: string };
      const detail =
        formatApiErrorDetail(ax?.response?.data?.detail) || ax?.message || "删除失败";
      msgApi.error(detail);
    }
  };

  const abortRef = useRef<(() => void) | null>(null);

  const sendQuestion = async (question: string) => {
    if (!question.trim() || loading) return;

    const userMsg: UIMessage = {
      id: `u-${Date.now()}`,
      role: "user",
      content: question,
    };
    const placeholder: UIMessage = {
      id: `a-${Date.now()}`,
      role: "assistant",
      content: "",
      pending: true,
      streaming: true,
    };
    setMessages((prev) => [...prev, userMsg, placeholder]);
    setInput("");
    setLoading(true);

    const history = messages
      .filter((m) => !m.pending && m.content)
      .map((m) => ({ role: m.role, content: m.content }));

    let currentSql: string | undefined;
    let currentExplanation: string | undefined;
    let currentData: QueryResult | undefined;
    let currentChart: ChartSpec | undefined;
    let currentSummary = "";
    let currentConvId: number | null = activeId;
    let currentMsgId: number | string = placeholder.id;

    abortRef.current = sendChatStream(
      {
        question,
        conversation_id: activeId,
        history,
      },
      (evt: StreamEvent) => {
        if (evt.type === "thinking") {
          setMessages((prev) => {
            const next = [...prev];
            const idx = next.findIndex((m) => m.id === placeholder.id);
            if (idx >= 0) {
              next[idx] = { ...next[idx], pending: true, streaming: true };
            }
            return next;
          });
          if (evt.conversation_id) {
            currentConvId = evt.conversation_id;
            setActiveId(evt.conversation_id);
          }
        } else if (evt.type === "sql") {
          currentSql = evt.sql;
          currentExplanation = evt.explanation;
        } else if (evt.type === "data") {
          currentData = evt.data as QueryResult;
        } else if (evt.type === "chart") {
          currentChart = evt.chart as ChartSpec;
        } else if (evt.type === "summary_chunk") {
          currentSummary = evt.chunk || "";
          setMessages((prev) => {
            const next = [...prev];
            const idx = next.findIndex((m) => m.id === placeholder.id);
            if (idx >= 0) {
              next[idx] = {
                ...next[idx],
                id: currentMsgId,
                role: "assistant",
                content: currentSummary,
                summary: currentSummary,
                sql: currentSql,
                result: currentData,
                chart: currentChart,
                pending: false,
                streaming: !evt.done,
              };
            }
            return next;
          });
        } else if (evt.type === "clarification") {
          setMessages((prev) => {
            const next = [...prev];
            const idx = next.findIndex((m) => m.id === placeholder.id);
            if (idx >= 0) {
              next[idx] = {
                ...next[idx],
                id: currentMsgId,
                role: "assistant",
                content: evt.clarification || "",
                clarification: evt.clarification || null,
                pending: false,
                streaming: false,
              };
            }
            return next;
          });
          setLoading(false);
          loadConversations();
        } else if (evt.type === "done") {
          if (evt.conversation_id) {
            currentConvId = evt.conversation_id;
            setActiveId(evt.conversation_id);
          }
          if (evt.message_id) {
            currentMsgId = evt.message_id;
          }
          setMessages((prev) => {
            const next = [...prev];
            const idx = next.findIndex((m) => m.id === placeholder.id);
            if (idx >= 0) {
              next[idx] = {
                ...next[idx],
                id: currentMsgId,
                role: "assistant",
                content: currentSummary,
                summary: currentSummary,
                sql: currentSql,
                result: currentData,
                chart: currentChart,
                pending: false,
                streaming: false,
              };
            }
            return next;
          });
          setLoading(false);
          loadConversations();
        } else if (evt.type === "error") {
          setMessages((prev) => {
            const next = [...prev];
            const idx = next.findIndex((m) => m.id === placeholder.id);
            if (idx >= 0) {
              next[idx] = {
                ...next[idx],
                id: `e-${Date.now()}`,
                role: "assistant",
                content: evt.error || "请求失败",
                error: evt.error || "请求失败",
                pending: false,
                streaming: false,
              };
            }
            return next;
          });
          setLoading(false);
          msgApi.error(`请求失败: ${evt.error}`);
        }
      },
      (errMsg: string) => {
        setMessages((prev) => {
          const next = [...prev];
          const idx = next.findIndex((m) => m.id === placeholder.id);
          if (idx >= 0) {
            next[idx] = {
              ...next[idx],
              id: `e-${Date.now()}`,
              role: "assistant",
              content: errMsg,
              error: errMsg,
              pending: false,
              streaming: false,
            };
          }
          return next;
        });
        setLoading(false);
        msgApi.error(`请求失败: ${errMsg}`);
      },
    );
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendQuestion(input);
    }
  };

  const showWelcome = useMemo(() => messages.length === 0, [messages]);

  return (
    <div className="layout-root">
      <aside className="sidebar">
        <div className="sidebar-title">
          <BarChartOutlined /> ChatBI
        </div>
        <Button
          className="sidebar-new-btn"
          icon={<PlusOutlined />}
          type="primary"
          block
          onClick={newConversation}
        >
          新对话
        </Button>
        <div className="conv-list">
          {conversations.map((c) => (
            <div
              key={c.id}
              className={`conv-item ${activeId === c.id ? "active" : ""}`}
              onClick={() => openConversation(c.id)}
            >
              <span style={{ overflow: "hidden", textOverflow: "ellipsis" }}>
                {c.title}
              </span>
              <Popconfirm
                title="删除该会话？"
                onConfirm={(e) => {
                  e?.stopPropagation();
                  removeConversation(c.id);
                }}
                onCancel={(e) => e?.stopPropagation()}
              >
                <DeleteOutlined
                  className="conv-delete"
                  onClick={(e) => e.stopPropagation()}
                />
              </Popconfirm>
            </div>
          ))}
          {conversations.length === 0 && (
            <div style={{ color: "#7a809a", fontSize: 12, padding: "8px 10px" }}>
              暂无历史会话
            </div>
          )}
        </div>
      </aside>

      <main className="main">
        <header className="main-header">
          <h2>对话式数据分析</h2>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            {activeId && (
              <>
                <Dropdown
                  menu={{
                    items: [
                      { key: "md", label: "导出 Markdown", onClick: handleExportMarkdown },
                      { key: "json", label: "导出 JSON", onClick: handleExportJson },
                      { key: "share", label: "生成分享链接", onClick: handleShare },
                    ],
                  }}
                >
                  <Button size="small" icon={<ExportOutlined />}>导出</Button>
                </Dropdown>
                <Tooltip title="生成分享链接">
                  <Button size="small" icon={<ShareAltOutlined />} onClick={handleShare} />
                </Tooltip>
              </>
            )}
            {user ? (
              <>
                <span style={{ fontSize: 13, color: "#6b7184" }}>
                  {user.display_name || user.username}
                </span>
                <Button size="small" onClick={() => { clearAuth(); setUser(null); }}>
                  退出
                </Button>
              </>
            ) : (
              <Button size="small" type="primary" onClick={() => setLoginOpen(true)}>
                登录
              </Button>
            )}
            <Tooltip title="后端: FastAPI + DeepSeek · 前端: React + AntD + ECharts">
              <span className="message-meta">v0.3 · 产品级原型</span>
            </Tooltip>
          </div>
        </header>

        <div className="chat-area" ref={chatRef}>
          {showWelcome ? (
            <div className="welcome">
              <div className="welcome-title">你好，我是 ChatBI 助手</div>
              <div className="welcome-sub">
                问我任何关于业务数据的问题，我会自动生成 SQL、查询并可视化。
              </div>
              <div className="sample-grid">
                {samples.map((q) => (
                  <div key={q} className="sample-card" onClick={() => sendQuestion(q)}>
                    {q}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <>
              {messages.map((m) => (
                <div key={m.id} className={`message ${m.role}`}>
                  {m.role === "user" ? (
                    <div className="bubble">{m.content}</div>
                  ) : m.pending ? (
                    <div className="assistant-card">
                      <Spin /> <span style={{ marginLeft: 8, color: "#6b7184" }}>正在分析数据…</span>
                    </div>
                  ) : (
                    <AssistantMessage
                      summary={m.summary || m.content}
                      sql={m.sql}
                      data={m.result as any}
                      chart={m.chart as any}
                      error={m.error}
                      clarification={(m as any).clarification}
                      streaming={m.streaming}
                      onPin={
                        m.chart && m.chart.type !== "empty" && m.chart.type !== "table"
                          ? () => {
                              const chart = m.chart!;
                              createCard({
                                title: m.summary?.slice(0, 30) || "未命名图表",
                                chart_type: chart.type,
                                chart: chart,
                                data: m.result,
                                sql: m.sql || undefined,
                              })
                                .then(() => msgApi.success("已收藏到仪表盘"))
                                .catch(() => msgApi.error("收藏失败，请登录"));
                            }
                          : undefined
                      }
                    />
                  )}
                </div>
              ))}
            </>
          )}
        </div>

        <div className="input-area">
          <div className="input-wrap">
            <Input.TextArea
              autoSize={{ minRows: 1, maxRows: 5 }}
              placeholder="问我：例如 '2024 年每个月的销售额？'（Enter 发送，Shift+Enter 换行）"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              disabled={loading}
            />
            <Button
              type="primary"
              icon={<SendOutlined />}
              loading={loading}
              onClick={() => sendQuestion(input)}
              disabled={!input.trim()}
            >
              发送
            </Button>
          </div>
          <div className="tip">仅支持只读 SELECT 查询 · LLM 生成的结果请人工核对</div>
        </div>
      </main>
      <LoginModal
        open={loginOpen}
        onClose={() => setLoginOpen(false)}
        onSuccess={() => {
          const auth = getAuth();
          if (auth.user) setUser(auth.user);
        }}
      />
      <Modal
        title="分享链接"
        open={shareModalOpen}
        onCancel={() => setShareModalOpen(false)}
        footer={[
          <Button key="close" onClick={() => setShareModalOpen(false)}>
            关闭
          </Button>,
          <Button
            key="copy"
            type="primary"
            onClick={() => {
              navigator.clipboard.writeText(shareUrl).then(() => msgApi.success("链接已复制"));
            }}
          >
            复制链接
          </Button>,
        ]}
      >
        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 13, color: "#6b7184", marginBottom: 8 }}>
            链接有效期 7 天，任何人可通过此链接查看对话内容：
          </div>
          <Input value={shareUrl} readOnly onFocus={(e) => e.target.select()} />
        </div>
      </Modal>
    </div>
  );
}
