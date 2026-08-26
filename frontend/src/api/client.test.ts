import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api, tokenStore } from "./client";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("api client", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("attaches the stored token to authenticated calls", async () => {
    tokenStore.set("token-123");
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse([]));
    vi.stubGlobal("fetch", fetchMock);

    await api.listTasks("2026-08-23");

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/v1/daily-tasks?date=2026-08-23");
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer token-123");
  });

  it("does not attach a token when signing in", async () => {
    tokenStore.set("token-123");
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse({ access_token: "new", user: {} }));
    vi.stubGlobal("fetch", fetchMock);

    await api.login("a@b.com", "password");

    const [, init] = fetchMock.mock.calls[0];
    expect((init.headers as Record<string, string>).Authorization).toBeUndefined();
  });

  it("surfaces the server's message and field errors", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(
          {
            error: "Please check the highlighted fields",
            details: [{ field: "email", message: "Enter a valid email address" }],
          },
          400,
        ),
      ),
    );

    await expect(api.login("nope", "password")).rejects.toMatchObject({
      status: 400,
      message: "Please check the highlighted fields",
      details: [{ field: "email", message: "Enter a valid email address" }],
    });
  });

  it("clears the token and announces a rejected session on 401", async () => {
    tokenStore.set("expired");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ error: "nope" }, 401)));
    const onUnauthorized = vi.fn();
    window.addEventListener("consistency-ai:unauthorized", onUnauthorized);

    await expect(api.journey()).rejects.toBeInstanceOf(ApiError);

    expect(tokenStore.get()).toBeNull();
    expect(onUnauthorized).toHaveBeenCalled();
    window.removeEventListener("consistency-ai:unauthorized", onUnauthorized);
  });

  it("turns a network failure into a readable message", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

    await expect(api.journey()).rejects.toMatchObject({
      status: 0,
      message: "Can't reach the server. Check your connection and try again.",
    });
  });

  it("handles a 204 with no body", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 204 })));
    await expect(api.deleteTask(7)).resolves.toBeUndefined();
  });
});
