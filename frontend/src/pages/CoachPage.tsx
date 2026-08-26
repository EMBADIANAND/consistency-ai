import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, api } from "../api/client";
import type { ChatMessage, Insight } from "../api/types";
import { ErrorState, Loading } from "../components/ui";
import { useStreamingText } from "../hooks/useStreamingText";

const OPENERS = [
  "Why was this week better?",
  "What should I focus on tomorrow?",
  "Where am I losing consistency?",
  "How long is my streak?",
];

/** How close to the bottom still counts as "following along". */
const STICK_THRESHOLD_PX = 90;

export function CoachPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [provider, setProvider] = useState<string>("mock");
  const [opener, setOpener] = useState<Insight | null>(null);

  const stream = useStreamingText();
  const threadRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const following = useRef(true);
  const committed = useRef(false);

  /* ---------------------------------------------------------------- load */

  useEffect(() => {
    let cancelled = false;
    api
      .conversation()
      .then((conversation) => {
        if (cancelled) return;
        setMessages(conversation.messages);
        setProvider(conversation.ai_provider);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(describe(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    // The "I noticed something" observation opens an empty thread. It is a
    // nice-to-have, so a failure here must not take the chat down with it.
    api
      .coachPrompt()
      .then((insight) => {
        if (!cancelled) setOpener(insight);
      })
      .catch(() => undefined);

    return () => {
      cancelled = true;
    };
  }, []);

  /* -------------------------------------------------------------- scroll */

  // Follow the newest text, but only while the user is already at the bottom —
  // yanking the view while they read back through the thread is worse than
  // letting a new message arrive just off-screen.
  useEffect(() => {
    const thread = threadRef.current;
    if (thread && following.current) thread.scrollTop = thread.scrollHeight;
  });

  const onThreadScroll = useCallback(() => {
    const thread = threadRef.current;
    if (!thread) return;
    const distance = thread.scrollHeight - thread.scrollTop - thread.clientHeight;
    following.current = distance < STICK_THRESHOLD_PX;
  }, []);

  /* --------------------------------------------------------------- reply */

  // The live bubble becomes a stored message once the stream has finished *and*
  // the display has caught up with it, so the text never jumps from
  // half-revealed straight to complete.
  const finished = !sending && stream.settled && stream.complete().length > 0;

  useEffect(() => {
    if (!finished || committed.current) return;
    committed.current = true;
    // Read the text out *before* resetting: a state updater runs after this
    // function returns, so calling stream.complete() inside it would read an
    // already-cleared buffer and commit an empty bubble.
    const reply = localMessage("assistant", stream.complete());
    setMessages((current) => [...current, reply]);
    stream.reset();
  }, [finished, stream]);

  /* ---------------------------------------------------------------- send */

  const send = useCallback(
    async (text: string) => {
      const message = text.trim();
      if (!message || sending) return;

      setError(null);
      setDraft("");
      setSending(true);
      committed.current = false;
      following.current = true;
      stream.reset();

      const optimistic = localMessage("user", message);
      setMessages((current) => [...current, optimistic]);

      try {
        await api.streamChat(message, {
          onStart: (info) => setProvider(info.ai_provider),
          onDelta: stream.push,
        });
      } catch (err: unknown) {
        // Nothing was said, so leave no trace of it in the thread. Putting the
        // text back in the box is the only state the user can act on.
        setMessages((current) => current.filter((m) => m.id !== optimistic.id));
        setDraft(message);
        setError(describe(err));
        stream.reset();
      } finally {
        setSending(false);
        inputRef.current?.focus();
      }
    },
    [sending, stream],
  );

  async function startFresh() {
    if (sending) return;
    try {
      await api.resetConversation();
      setMessages([]);
      setError(null);
      stream.reset();
      inputRef.current?.focus();
    } catch (err: unknown) {
      setError(describe(err));
    }
  }

  function onKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    // Enter sends, Shift+Enter opens a line — the convention everywhere else.
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void send(draft);
    }
  }

  /* -------------------------------------------------------------- render */

  const empty = messages.length === 0 && !sending && stream.shown === "";
  const waiting = sending && stream.shown === "";

  return (
    <section className="page chat">
      <header className="chat-head">
        <div>
          <p className="eyebrow">YOUR PERSONAL AI COACH</p>
          <h1>Let's talk. 🧠</h1>
        </div>
        {messages.length > 0 && (
          <button
            className="secondary"
            onClick={() => void startFresh()}
            disabled={sending}
          >
            New chat
          </button>
        )}
      </header>

      <div
        className="chat-thread"
        ref={threadRef}
        onScroll={onThreadScroll}
        role="log"
        aria-live="polite"
        aria-label="Conversation with your coach"
      >
        {loading && <Loading label="Picking up where we left off…" />}

        {!loading && empty && (
          <div className="chat-welcome">
            <span aria-hidden="true">🧠</span>
            <strong>{opener ? opener.title : "Let's pick something up."}</strong>
            <p className="muted">
              {opener
                ? opener.body
                : "Ask about your patterns, your streak, or what to do tomorrow."}
            </p>
            <p className="muted chat-welcome-hint">
              I remember this conversation now, so follow-ups work — "why?" is a real
              question.
            </p>
          </div>
        )}

        {messages.map((message) => (
          <Bubble key={message.id} role={message.role} content={message.content} />
        ))}

        {stream.shown !== "" && (
          <Bubble role="assistant" content={stream.shown} typing={!stream.settled} />
        )}

        {waiting && (
          <div className="bubble assistant typing-bubble">
            <span className="typing" role="status" aria-label="Thinking">
              <i />
              <i />
              <i />
            </span>
          </div>
        )}
      </div>

      {error && <ErrorState message={error} onRetry={() => void send(draft)} />}

      {empty && !loading && (
        <div className="chips">
          {OPENERS.map((opener) => (
            <button key={opener} disabled={sending} onClick={() => void send(opener)}>
              {opener}
            </button>
          ))}
        </div>
      )}

      <div className="chat-composer">
        <textarea
          ref={inputRef}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Say anything…"
          maxLength={2000}
          rows={1}
          aria-label="Message your coach"
        />
        <button
          className="send"
          onClick={() => void send(draft)}
          disabled={sending || draft.trim() === ""}
          aria-label="Send message"
        >
          {sending ? "…" : "↑"}
        </button>
      </div>

      <p className="chat-foot muted">
        {provider === "anthropic"
          ? "Answering with Claude, grounded in your own numbers."
          : "Answering from your own numbers. Add an API key for a full model."}
      </p>
    </section>
  );
}

function Bubble({
  role,
  content,
  typing = false,
}: {
  role: string;
  content: string;
  typing?: boolean;
}) {
  return (
    <div className={`bubble ${role}`}>
      {content}
      {typing && <span className="caret" aria-hidden="true" />}
    </div>
  );
}

/**
 * A message that so far exists only on this screen.
 *
 * Server ids are positive, so a negative id can never collide with one — which
 * matters because the optimistic user bubble has to be findable again if the
 * send fails.
 */
let localId = 0;
function localMessage(role: "user" | "assistant", content: string): ChatMessage {
  localId -= 1;
  return { id: localId, role, content, created_at: new Date().toISOString() };
}

function describe(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Something went wrong. Try that again.";
}
