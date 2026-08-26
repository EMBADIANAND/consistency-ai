import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { StrictMode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ChatStreamHandlers } from "../api/client";

const conversation = vi.fn();
const coachPrompt = vi.fn();
const streamChat = vi.fn();

vi.mock("../api/client", async () => {
  const actual = await vi.importActual<typeof import("../api/client")>("../api/client");
  return {
    ...actual,
    api: {
      conversation: () => conversation(),
      coachPrompt: () => coachPrompt(),
      streamChat: (message: string, handlers: ChatStreamHandlers) =>
        streamChat(message, handlers),
      resetConversation: vi.fn(),
    },
  };
});

const { CoachPage } = await import("./CoachPage");

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("CoachPage", () => {
  it("keeps the streamed reply once the stream finishes", async () => {
    // Asserts the property that broke in the browser: the finished reply keeps
    // its text. (The original failure only reproduced under a real browser's
    // scheduling — reading the buffer inside a state updater that ran after it
    // was cleared — so this guards the outcome, not that exact timing.)
    conversation.mockResolvedValue({ id: 7, messages: [], ai_provider: "mock" });
    coachPrompt.mockResolvedValue({ title: "✨ Noticed", body: "Something." });
    streamChat.mockImplementation(async (_message: string, handlers: ChatStreamHandlers) => {
      handlers.onStart?.({ conversation_id: 7, ai_provider: "mock" });
      handlers.onDelta?.("Your streak ");
      handlers.onDelta?.("is holding.");
    });

    const { container } = render(
      <StrictMode>
        <CoachPage />
      </StrictMode>,
    );
    await screen.findByPlaceholderText("Say anything…");

    const textarea = container.querySelector("textarea")!;
    const { fireEvent } = await import("@testing-library/dom");
    fireEvent.change(textarea, { target: { value: "how am I doing?" } });
    fireEvent.keyDown(textarea, { key: "Enter" });

    await screen.findByText("how am I doing?");

    await waitFor(
      () => {
        const assistant = container.querySelectorAll(".bubble.assistant");
        expect(assistant.length).toBe(1);
        expect(assistant[0].textContent).toContain("Your streak is holding.");
      },
      { timeout: 4000 },
    );
  });

  it("renders a thread loaded from the server", async () => {
    conversation.mockResolvedValue({
      id: 3,
      messages: [
        { id: 1, role: "user", content: "hey", created_at: "2026-08-24T10:00:00Z" },
        {
          id: 2,
          role: "assistant",
          content: "Good to see you.",
          created_at: "2026-08-24T10:00:01Z",
        },
      ],
      ai_provider: "mock",
    });
    coachPrompt.mockResolvedValue({ title: "✨", body: "x" });

    render(
      <StrictMode>
        <CoachPage />
      </StrictMode>,
    );
    expect(await screen.findByText("Good to see you.")).toBeTruthy();
    expect(screen.getByText("hey")).toBeTruthy();
  });

  it("puts the message back in the box when sending fails", async () => {
    conversation.mockResolvedValue({ id: 9, messages: [], ai_provider: "mock" });
    coachPrompt.mockResolvedValue({ title: "✨", body: "x" });
    streamChat.mockRejectedValue(new Error("network is gone"));

    const { container } = render(
      <StrictMode>
        <CoachPage />
      </StrictMode>,
    );
    await screen.findByPlaceholderText("Say anything…");

    const textarea = container.querySelector("textarea")! as HTMLTextAreaElement;
    const { fireEvent } = await import("@testing-library/dom");
    fireEvent.change(textarea, { target: { value: "are you there?" } });
    fireEvent.keyDown(textarea, { key: "Enter" });

    await waitFor(() => {
      // No half-exchange left behind, and the text is recoverable.
      expect(container.querySelectorAll(".bubble.user").length).toBe(0);
      expect(textarea.value).toBe("are you there?");
    });
  });
});
