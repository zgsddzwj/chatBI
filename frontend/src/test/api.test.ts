import { describe, expect, it, vi, beforeEach } from "vitest";
import { getToken, setAuth, clearAuth } from "../auth";

describe("auth token", () => {
  beforeEach(() => {
    clearAuth();
    localStorage.clear();
  });

  it("stores and retrieves token", () => {
    setAuth({
      token: "tok-abc",
      user: { id: 1, username: "u", display_name: "U", role: "analyst" },
    });
    expect(getToken()).toBe("tok-abc");
  });
});

describe("sendChatStream auth header", () => {
  beforeEach(() => {
    clearAuth();
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("includes Authorization when token exists", async () => {
    setAuth({
      token: "stream-token",
      user: { id: 1, username: "u", display_name: "U", role: "analyst" },
    });
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      body: {
        getReader: () => ({
          read: async () => ({ done: true, value: undefined }),
        }),
      },
    });
    vi.stubGlobal("fetch", fetchMock);

    const { sendChatStream } = await import("../api");
    sendChatStream({ question: "hi" }, () => undefined);
    await new Promise((r) => setTimeout(r, 50));

    expect(fetchMock).toHaveBeenCalled();
    const headers = fetchMock.mock.calls[0][1].headers as Record<string, string>;
    expect(headers.Authorization).toBe("Bearer stream-token");
  });
});
