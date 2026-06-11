import { useState } from "react";
import { Button, Input } from "antd";
import { SendOutlined } from "@ant-design/icons";
import { QuerySuggestions } from "./QuerySuggestions";

interface Props {
  value: string;
  loading: boolean;
  onChange: (value: string) => void;
  onSend: (text: string) => void;
  conversationId?: number;
}

export function ChatInput({ value, loading, onChange, onSend, conversationId }: Props) {
  const [focused, setFocused] = useState(false);

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSend(value);
    }
  };

  return (
    <div className="input-area">
      <div className="input-wrap" style={{ position: "relative" }}>
        <Input.TextArea
          autoSize={{ minRows: 1, maxRows: 5 }}
          placeholder="问我：例如 '2024 年每个月的销售额？'（Enter 发送，Shift+Enter 换行）"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={onKeyDown}
          onFocus={() => setFocused(true)}
          onBlur={() => setTimeout(() => setFocused(false), 200)}
          disabled={loading}
          aria-label="输入问题"
        />
        <Button
          type="primary"
          icon={<SendOutlined />}
          loading={loading}
          onClick={() => onSend(value)}
          disabled={!value.trim()}
        >
          发送
        </Button>
        <QuerySuggestions
          input={value}
          conversationId={conversationId}
          onSelect={(text) => {
            onChange(text);
            onSend(text);
          }}
          visible={focused && !loading}
        />
      </div>
      <div className="tip">仅支持只读 SELECT 查询 · LLM 生成的结果请人工核对</div>
    </div>
  );
}
