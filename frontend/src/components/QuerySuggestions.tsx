import { useEffect, useRef, useState } from "react";
import { Spin, Tag } from "antd";
import { BulbOutlined, FireOutlined, HistoryOutlined } from "@ant-design/icons";
import { getSuggestions, getAutocomplete } from "../api";

interface Props {
  input: string;
  conversationId?: number;
  onSelect: (text: string) => void;
  visible: boolean;
}

interface Suggestion {
  text: string;
  source: string;
  score: number;
}

export function QuerySuggestions({ input, conversationId, onSelect, visible }: Props) {
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    if (!visible) {
      setSuggestions([]);
      return;
    }

    if (debounceRef.current) clearTimeout(debounceRef.current);

    debounceRef.current = setTimeout(() => {
      setLoading(true);
      const fetcher = input.length >= 2
        ? getAutocomplete(input, 8)
        : getSuggestions(input, conversationId, 8).then((r) => r.suggestions);

      fetcher
        .then((results: any) => {
          if (Array.isArray(results)) {
            if (results.length > 0 && typeof results[0] === "string") {
              setSuggestions(results.map((text: string) => ({ text, source: "autocomplete", score: 1 })));
            } else {
              setSuggestions(results);
            }
          } else {
            setSuggestions([]);
          }
        })
        .catch(() => setSuggestions([]))
        .finally(() => setLoading(false));
    }, 200);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [input, visible, conversationId]);

  if (!visible || suggestions.length === 0) return null;

  const sourceIcon = (source: string) => {
    switch (source) {
      case "popular": return <FireOutlined style={{ color: "#ff4d4f", marginRight: 4 }} />;
      case "history": return <HistoryOutlined style={{ color: "#1890ff", marginRight: 4 }} />;
      default: return <BulbOutlined style={{ color: "#52c41a", marginRight: 4 }} />;
    }
  };

  const sourceLabel = (source: string) => {
    switch (source) {
      case "sample": return "示例";
      case "popular": return "热门";
      case "history": return "历史";
      case "intent": return "推荐";
      case "autocomplete": return "补全";
      default: return "建议";
    }
  };

  return (
    <div className="query-suggestions">
      {loading && <Spin size="small" style={{ display: "block", margin: "8px auto" }} />}
      {suggestions.map((s, idx) => (
        <div
          key={idx}
          className="suggestion-item"
          onClick={() => onSelect(s.text)}
          onMouseDown={(e) => e.preventDefault()}
        >
          {sourceIcon(s.source)}
          <span className="suggestion-text">{s.text}</span>
          <Tag className="suggestion-tag">{sourceLabel(s.source)}</Tag>
        </div>
      ))}
    </div>
  );
}
