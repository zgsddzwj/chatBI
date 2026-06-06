import { Button, Input } from "antd";
import { SendOutlined } from "@ant-design/icons";

interface Props {
  value: string;
  loading: boolean;
  onChange: (value: string) => void;
  onSend: (text: string) => void;
}

export function ChatInput({ value, loading, onChange, onSend }: Props) {
  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSend(value);
    }
  };

  return (
    <div className="input-area">
      <div className="input-wrap">
        <Input.TextArea
          autoSize={{ minRows: 1, maxRows: 5 }}
          placeholder="问我：例如 '2024 年每个月的销售额？'（Enter 发送，Shift+Enter 换行）"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={onKeyDown}
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
      </div>
      <div className="tip">仅支持只读 SELECT 查询 · LLM 生成的结果请人工核对</div>
    </div>
  );
}
