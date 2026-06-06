import { useEffect, useMemo, useRef, useState } from "react";
import { Button, Dropdown, Modal, Input, Spin, Tooltip, message as msgApi } from "antd";
import { ExportOutlined, ShareAltOutlined, BookOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import {
  createCard,
  createShareLink,
  exportConversationJson,
  exportConversationMarkdown,
  getSamples,
} from "../api";
import { getAuth } from "../auth";
import { LoginModal } from "../components/LoginModal";
import { ChatInput } from "../components/ChatInput";
import { VirtualMessageList } from "../components/VirtualMessageList";
import { AssistantMessage } from "../components/AssistantMessage";
import { TemplateDrawer } from "../components/TemplateDrawer";
import { useAuth } from "../contexts/AuthContext";
import { useConversationsContext } from "../contexts/ConversationsContext";
import { useChat } from "../hooks/useChat";
import { useTemplates } from "../hooks/useTemplates";

export function ChatPage() {
  const navigate = useNavigate();
  const { user, setUser, logout } = useAuth();
  const [input, setInput] = useState("");
  const [samples, setSamples] = useState<string[]>([]);
  const [loginOpen, setLoginOpen] = useState(false);
  const [shareModalOpen, setShareModalOpen] = useState(false);
  const [shareUrl, setShareUrl] = useState("");
  const [templateDrawerOpen, setTemplateDrawerOpen] = useState(false);
  const chatRef = useRef<HTMLDivElement>(null);

  const {
    activeId,
    setActiveId,
    messages,
    setMessages,
    loadConversations,
  } = useConversationsContext();

  const { addTemplate } = useTemplates();

  const { loading, sendQuestion } = useChat({
    activeId,
    setActiveId,
    messages,
    setMessages,
    onConversationUpdated: loadConversations,
  });

  useEffect(() => {
    getSamples().then(setSamples).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight;
    }
  }, [messages, loading]);

  const showWelcome = useMemo(() => messages.length === 0, [messages]);
  const useVirtual = messages.length > 50;

  const handleExportMarkdown = async () => {
    if (!activeId) return msgApi.warning("请先选择一个对话");
    const blob = await exportConversationMarkdown(activeId);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `chatbi-conversation-${activeId}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleExportJson = async () => {
    if (!activeId) return msgApi.warning("请先选择一个对话");
    const blob = await exportConversationJson(activeId);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `chatbi-conversation-${activeId}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleShare = async () => {
    if (!activeId) return msgApi.warning("请先选择一个对话");
    try {
      const res = await createShareLink(activeId);
      setShareUrl(`${window.location.origin}${res.url}`);
      setShareModalOpen(true);
    } catch (err: unknown) {
      const ax = err as { response?: { data?: { detail?: string } } };
      msgApi.error(ax?.response?.data?.detail || "创建分享链接失败");
    }
  };

  const handleBookmark = (m: (typeof messages)[0]) => {
    try {
      const question = m.summary || m.content;
      addTemplate({
        question,
        summary: m.summary || undefined,
        sql: m.sql || null,
        data: m.result || null,
        chart: m.chart || null,
      });
      msgApi.success("已收藏");
    } catch (err) {
      msgApi.error("收藏失败");
    }
  };

  const handlePin = (m: (typeof messages)[0]) => {
    if (!m.chart || m.chart.type === "empty" || m.chart.type === "table") return;
    createCard({
      title: m.summary?.slice(0, 30) || "未命名图表",
      chart_type: m.chart.type,
      chart: m.chart,
      data: m.result,
      sql: m.sql || undefined,
    })
      .then(() => {
        msgApi.success("已收藏到仪表盘");
        navigate("/dashboards");
      })
      .catch(() => msgApi.error("收藏失败，请登录"));
  };

  return (
    <>
      <header className="main-header">
        <h2>对话式数据分析</h2>
        <div className="header-actions">
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
                <Button size="small" icon={<ShareAltOutlined />} onClick={handleShare} aria-label="分享" />
              </Tooltip>
              <Tooltip title="常用查询收藏夹">
                <Button size="small" icon={<BookOutlined />} onClick={() => setTemplateDrawerOpen(true)} aria-label="收藏夹" />
              </Tooltip>
            </>
          )}
          {user ? (
            <>
              <span className="user-label">{user.display_name || user.username}</span>
              <Button size="small" onClick={logout}>退出</Button>
            </>
          ) : (
            <Button size="small" type="primary" onClick={() => setLoginOpen(true)}>登录</Button>
          )}
          <span className="message-meta">v0.4</span>
        </div>
      </header>

      <div className="chat-area" ref={chatRef} aria-live="polite" aria-relevant="additions text">
        {showWelcome ? (
          <div className="welcome">
            <div className="welcome-title">你好，我是 ChatBI 助手</div>
            <div className="welcome-sub">问我任何关于业务数据的问题，我会自动生成 SQL、查询并可视化。</div>
            <div className="sample-grid">
              {samples.map((q) => (
                <button key={q} type="button" className="sample-card" onClick={() => sendQuestion(q)}>
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : useVirtual ? (
          <VirtualMessageList messages={messages} onPin={handlePin} onBookmark={handleBookmark} />
        ) : (
          messages.map((m) => (
            <div key={m.id} className={`message ${m.role}`}>
              {m.role === "user" ? (
                <div className="bubble">{m.content}</div>
              ) : m.pending ? (
                <div className="assistant-card">
                  <Spin /> <span className="pending-text">正在分析数据…</span>
                </div>
              ) : (
                <AssistantMessage
                  summary={m.summary || m.content}
                  sql={m.sql}
                  data={m.result}
                  chart={m.chart}
                  error={m.error}
                  clarification={m.clarification}
                  streaming={m.streaming}
          onPin={
            m.chart && m.chart.type !== "empty" && m.chart.type !== "table"
              ? () => handlePin(m)
              : undefined
          }
          onBookmark={() => handleBookmark(m)}
                />
              )}
            </div>
          ))
        )}
      </div>

      <ChatInput value={input} loading={loading} onChange={setInput} onSend={sendQuestion} />

      <LoginModal
        open={loginOpen}
        onClose={() => setLoginOpen(false)}
        onSuccess={() => {
          if (getAuth().user) setUser(getAuth().user);
        }}
      />

      <Modal
        title="分享链接"
        open={shareModalOpen}
        onCancel={() => setShareModalOpen(false)}
        footer={[
          <Button key="close" onClick={() => setShareModalOpen(false)}>关闭</Button>,
          <Button
            key="copy"
            type="primary"
            onClick={() => navigator.clipboard.writeText(shareUrl).then(() => msgApi.success("链接已复制"))}
          >
            复制链接
          </Button>,
        ]}
      >
        <Input value={shareUrl} readOnly onFocus={(e) => e.target.select()} />
      </Modal>

      <TemplateDrawer
        open={templateDrawerOpen}
        onClose={() => setTemplateDrawerOpen(false)}
        onUseTemplate={(q) => sendQuestion(q)}
      />
    </>
  );
}
