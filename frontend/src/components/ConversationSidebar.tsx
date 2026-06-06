import { Button, Popconfirm } from "antd";
import { PlusOutlined, DeleteOutlined, BarChartOutlined } from "@ant-design/icons";
import { Link, useLocation } from "react-router-dom";
import type { Conversation } from "../types";

interface Props {
  conversations: Conversation[];
  activeId: number | null;
  onNew: () => void;
  onOpen: (id: number) => void;
  onDelete: (id: number) => void;
}

export function ConversationSidebar({
  conversations,
  activeId,
  onNew,
  onOpen,
  onDelete,
}: Props) {
  const location = useLocation();

  return (
    <aside className="sidebar">
      <div className="sidebar-title">
        <BarChartOutlined /> ChatBI
      </div>
      <nav className="sidebar-nav" aria-label="主导航">
        <Link to="/" className={location.pathname === "/" ? "nav-link active" : "nav-link"}>
          对话
        </Link>
        <Link
          to="/dashboards"
          className={location.pathname.startsWith("/dashboards") ? "nav-link active" : "nav-link"}
        >
          仪表盘
        </Link>
        <Link
          to="/settings"
          className={location.pathname.startsWith("/settings") ? "nav-link active" : "nav-link"}
        >
          设置
        </Link>
      </nav>
      <Button className="sidebar-new-btn" icon={<PlusOutlined />} type="primary" block onClick={onNew}>
        新对话
      </Button>
      <div className="conv-list">
        {conversations.map((c) => (
          <button
            key={c.id}
            type="button"
            className={`conv-item ${activeId === c.id ? "active" : ""}`}
            onClick={() => onOpen(c.id)}
          >
            <span className="conv-title">{c.title}</span>
            <Popconfirm
              title="删除该会话？"
              onConfirm={(e) => {
                e?.stopPropagation();
                onDelete(c.id);
              }}
              onCancel={(e) => e?.stopPropagation()}
            >
              <DeleteOutlined
                className="conv-delete"
                onClick={(e) => e.stopPropagation()}
                aria-label="删除会话"
              />
            </Popconfirm>
          </button>
        ))}
        {conversations.length === 0 && (
          <div className="conv-empty">暂无历史会话</div>
        )}
      </div>
    </aside>
  );
}
