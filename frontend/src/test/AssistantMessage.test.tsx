import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { AssistantMessage } from "../components/AssistantMessage";

describe("AssistantMessage", () => {
  it("renders summary text", () => {
    render(<AssistantMessage summary="销售额增长 10%" />);
    expect(screen.getByText("销售额增长 10%")).toBeInTheDocument();
  });

  it("renders error state", () => {
    render(<AssistantMessage summary="" error="查询失败" />);
    expect(screen.getByText(/查询失败/)).toBeInTheDocument();
  });
});
