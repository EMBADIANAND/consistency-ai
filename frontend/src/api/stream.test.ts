import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api, readSseEvents, tokenStore } from "./client";

/** A streaming Response whose body arrives in the given network-level chunks. */
function sseResponse(chunks: string[], status = 200): Response {
  const encoder = new TextEncoder();
  const body = new ReadableStream({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk));
      controller.close();
    },
  });
  return new Response(body, {
    status,
    headers: { "Content-Type": "text/event-stream" },
  });
}

const event = (name: string, data: unknown) =>
  `event: ${name}\ndata: ${JSON.stringify(data)}\n\n`;

describe("readSseEvents", () => {
  it("holds back a partial event until the rest of it arrives", () => {
    const whole = event("delta", { text: "hello" });
    const half = whole.slice(0, 18);

    const first = readSseEvents(half);
    expect(first.events).toEqual([]);
    expect(first.rest).toBe(half);

    const second = readSseEvents(first.rest + whole.slice(18));
    expect(second.events).toEqual([{ event: "delta", data: { text: "hello" } }]);
    expect(second.rest).toBe("");
  });

  it("reads several events out of one chunk", () => {
    const { events, rest } = readSseEvents(
      event("start", { ai_provider: "mock" }) +
        event("delta", { text: "a" }) +
        event("delta", { text: "b" }),
    );
    expect(events.map((e) => e.event)).toEqual(["start", "delta", "delta"]);
    expect(rest).toBe("");
  });

  it("tolerates CRLF line endings from a proxy", () => {
    const { events } = readSseEvents('event: delta\r\ndata: {"text":"x"}\r\n\r\n');
    expect(events).toEqual([{ event: "delta", data: { text: "x" } }]);
  });
});

describe("api.streamChat", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("delivers deltas in order and reports the provider", async () => {
    tokenStore.set("token-123");
    const fetchMock = vi.fn().mockResolvedValue(
      sseResponse([
        event("start", { conversation_id: 1, ai_provider: "anthropic" }),
        event("delta", { text: "You're " }),
        event("delta", { text: "doing fine." }),
        event("done", { message_id: 2 }),
      ]),
    );
    vi.stubGlobal("fetch", fetchMock);

    const deltas: string[] = [];
    let provider = "";
    let doneWith = 0;

    await api.streamChat("how am I?", {
      onStart: (info) => {
        provider = info.ai_provider;
      },
      onDelta: (text) => deltas.push(text),
      onDone: (info) => {
        doneWith = info.message_id;
      },
    });

    expect(deltas.join("")).toBe("You're doing fine.");
    expect(provider).toBe("anthropic");
    expect(doneWith).toBe(2);

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/v1/coach/chat");
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer token-123");
  });

  it("reassembles an event split across two network reads", async () => {
    const whole = event("delta", { text: "unbroken" });
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(sseResponse([whole.slice(0, 11), whole.slice(11)])),
    );

    const deltas: string[] = [];
    await api.streamChat("hi", { onDelta: (text) => deltas.push(text) });

    expect(deltas).toEqual(["unbroken"]);
  });

  it("keeps a multi-byte character split across two reads intact", async () => {
    // "🧠" is four bytes; decoding each read on its own would mangle it.
    const bytes = new TextEncoder().encode(event("delta", { text: "🧠 ok" }));
    const body = new ReadableStream({
      start(controller) {
        controller.enqueue(bytes.slice(0, 22));
        controller.enqueue(bytes.slice(22));
        controller.close();
      },
    });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(body, { status: 200 })));

    const deltas: string[] = [];
    await api.streamChat("hi", { onDelta: (text) => deltas.push(text) });

    expect(deltas.join("")).toBe("🧠 ok");
  });

  it("raises the server's message when the stream never starts", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ error: "Start a new one to keep going." }), {
          status: 409,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    await expect(api.streamChat("hi", { onDelta: () => {} })).rejects.toMatchObject({
      status: 409,
      message: "Start a new one to keep going.",
    });
  });

  it("clears the session on a rejected token", async () => {
    tokenStore.set("expired");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ error: "nope" }), { status: 401 }),
      ),
    );
    const onUnauthorized = vi.fn();
    window.addEventListener("consistency-ai:unauthorized", onUnauthorized);

    await expect(api.streamChat("hi", { onDelta: () => {} })).rejects.toBeInstanceOf(
      ApiError,
    );
    expect(tokenStore.get()).toBeNull();
    expect(onUnauthorized).toHaveBeenCalled();
    window.removeEventListener("consistency-ai:unauthorized", onUnauthorized);
  });

  it("turns an unreachable server into a readable message", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

    await expect(api.streamChat("hi", { onDelta: () => {} })).rejects.toMatchObject({
      status: 0,
      message: "Can't reach the server. Check your connection and try again.",
    });
  });
});
