import { BrowserRouter, Routes, Route, Outlet } from "react-router-dom";
import { message as msgApi } from "antd";
import { AuthProvider } from "./contexts/AuthContext";
import { ConversationsProvider, useConversationsContext } from "./contexts/ConversationsContext";
import { ConversationSidebar } from "./components/ConversationSidebar";
import { ChatPage } from "./pages/ChatPage";
import { DashboardsPage } from "./pages/DashboardsPage";
import { SettingsPage } from "./pages/SettingsPage";

function Layout() {
  const {
    conversations,
    activeId,
    newConversation,
    openConversation,
    removeConversation,
  } = useConversationsContext();

  return (
    <div className="layout-root">
      <ConversationSidebar
        conversations={conversations}
        activeId={activeId}
        onNew={newConversation}
        onOpen={openConversation}
        onDelete={async (id) => {
          try {
            await removeConversation(id);
            msgApi.success("已删除");
          } catch {
            msgApi.error("删除失败");
          }
        }}
      />
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ConversationsProvider>
          <Routes>
            <Route element={<Layout />}>
              <Route path="/" element={<ChatPage />} />
              <Route path="/dashboards" element={<DashboardsPage />} />
              <Route path="/settings" element={<SettingsPage />} />
            </Route>
          </Routes>
        </ConversationsProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
