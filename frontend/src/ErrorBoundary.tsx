import { Component, type ErrorInfo, type ReactNode } from "react";
import { Button, Result } from "antd";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  message?: string;
  stack?: string;
  timestamp?: number;
}

/** 防止子树未捕获异常导致整页白屏。 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(err: Error): State {
    return {
      hasError: true,
      message: err.message,
      stack: err.stack,
      timestamp: Date.now(),
    };
  }

  componentDidCatch(err: Error, info: ErrorInfo) {
    console.error("ErrorBoundary:", err, info.componentStack);
  }

  handleReset = () => {
    this.setState({ hasError: false, message: undefined, stack: undefined });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 48, maxWidth: 560, margin: "0 auto" }}>
          <Result
            status="error"
            title="页面出现异常"
            subTitle={this.state.message || "请刷新页面后重试。若问题持续，请联系管理员。"}
            extra={[
              <Button key="reload" type="primary" onClick={() => window.location.reload()}>
                刷新页面
              </Button>,
              <Button key="reset" onClick={this.handleReset}>
                重试
              </Button>,
            ]}
          />
          {this.state.stack && (
            <details style={{ marginTop: 16, fontSize: 12, color: "#9aa0b5" }}>
              <summary>错误堆栈</summary>
              <pre style={{ whiteSpace: "pre-wrap", wordBreak: "break-all" }}>
                {this.state.stack}
              </pre>
            </details>
          )}
        </div>
      );
    }
    return this.props.children;
  }
}
