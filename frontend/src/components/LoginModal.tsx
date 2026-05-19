import { useState } from "react";
import { Modal, Form, Input, Button, Tabs, message as msgApi } from "antd";
import { UserOutlined, LockOutlined } from "@ant-design/icons";
import { login, register } from "../api";
import { setAuth } from "../auth";

interface Props {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const LoginModal: React.FC<Props> = ({ open, onClose, onSuccess }) => {
  const [tab, setTab] = useState<"login" | "register">("login");
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();

  const handleLogin = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      const res = await login(values);
      setAuth({ token: res.access_token, user: res.user });
      msgApi.success("登录成功");
      onSuccess();
      onClose();
    } catch (err: any) {
      msgApi.error(err?.response?.data?.detail || "登录失败");
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (values: { username: string; password: string; display_name?: string }) => {
    setLoading(true);
    try {
      await register(values);
      msgApi.success("注册成功，请登录");
      setTab("login");
      form.resetFields();
    } catch (err: any) {
      msgApi.error(err?.response?.data?.detail || "注册失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      open={open}
      onCancel={onClose}
      footer={null}
      title={null}
      closable={false}
      maskClosable={false}
      centered
      width={400}
    >
      <div style={{ textAlign: "center", marginBottom: 24 }}>
        <div style={{ fontSize: 24, fontWeight: 600, color: "#2f3548" }}>ChatBI</div>
        <div style={{ fontSize: 13, color: "#6b7184", marginTop: 4 }}>对话式数据分析平台</div>
      </div>
      <Tabs activeKey={tab} onChange={(k) => setTab(k as any)} centered>
        <Tabs.TabPane tab="登录" key="login" />
        <Tabs.TabPane tab="注册" key="register" />
      </Tabs>
      <Form form={form} onFinish={tab === "login" ? handleLogin : handleRegister} layout="vertical">
        <Form.Item
          name="username"
          rules={[{ required: true, message: "请输入用户名" }]}
        >
          <Input prefix={<UserOutlined />} placeholder="用户名" />
        </Form.Item>
        {tab === "register" && (
          <Form.Item name="display_name">
            <Input placeholder="显示名称（可选）" />
          </Form.Item>
        )}
        <Form.Item
          name="password"
          rules={[{ required: true, message: "请输入密码" }]}
        >
          <Input.Password prefix={<LockOutlined />} placeholder="密码" />
        </Form.Item>
        <Form.Item>
          <Button type="primary" htmlType="submit" block loading={loading}>
            {tab === "login" ? "登录" : "注册"}
          </Button>
        </Form.Item>
      </Form>
      {tab === "login" && (
        <div style={{ textAlign: "center", fontSize: 12, color: "#9aa0b5" }}>
          默认管理员: admin / admin123
        </div>
      )}
    </Modal>
  );
};
