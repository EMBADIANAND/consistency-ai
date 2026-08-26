import type {
  AuthResponse,
  CheckIn,
  CheckInResult,
  CoachAnswer,
  Conversation,
  DailyTask,
  Insight,
  Journey,
  LifeRule,
  PlanItem,
  TodaySummary,
  User,
  WeeklyReport,
} from "./types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";
const TOKEN_KEY = "consistency-ai.token";

export class ApiError extends Error {
  status: number;
  details: Array<{ field: string; message: string }>;

  constructor(
    message: string,
    status: number,
    details: Array<{ field: string; message: string }> = [],
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

/** Fired when the server rejects our token, so the app can send the user to sign in. */
const UNAUTHORIZED_EVENT = "consistency-ai:unauthorized";

export const tokenStore = {
  get(): string | null {
    try {
      return localStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },
  set(token: string): void {
    try {
      localStorage.setItem(TOKEN_KEY, token);
    } catch {
      /* storage unavailable — the session simply won't survive a reload */
    }
  },
  clear(): void {
    try {
      localStorage.removeItem(TOKEN_KEY);
    } catch {
      /* nothing to do */
    }
  },
};

export function onUnauthorized(handler: () => void): () => void {
  window.addEventListener(UNAUTHORIZED_EVENT, handler);
  return () => window.removeEventListener(UNAUTHORIZED_EVENT, handler);
}

type RequestOptions = {
  method?: string;
  body?: unknown;
  auth?: boolean;
};

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, auth = true } = options;
  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (auth) {
    const token = tokenStore.get();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError("Can't reach the server. Check your connection and try again.", 0);
  }

  if (response.status === 401 && auth) {
    tokenStore.clear();
    window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
  }

  if (response.status === 204) return undefined as T;

  const text = await response.text();
  const payload = text ? safeParse(text) : null;

  if (!response.ok) {
    const message =
      (payload && typeof payload === "object" && "error" in payload
        ? String((payload as { error: unknown }).error)
        : null) ?? `Request failed (${response.status})`;
    const details =
      payload && typeof payload === "object" && "details" in payload
        ? ((payload as { details: Array<{ field: string; message: string }> }).details ?? [])
        : [];
    throw new ApiError(message, response.status, details);
  }

  return payload as T;
}

function safeParse(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

/* ==========================================================================
   Streaming
   ========================================================================== */

export type SseEvent = { event: string; data: unknown };

/**
 * Pull whole events out of everything received so far.
 *
 * A network chunk has no relationship to an event boundary — one read can hold
 * three events, or half of one. Anything after the last blank line is returned
 * as `rest` to be prepended to the next read, which is what stops a delta from
 * being dropped or parsed in half.
 */
export function readSseEvents(buffer: string): { events: SseEvent[]; rest: string } {
  const events: SseEvent[] = [];
  let rest = buffer.replace(/\r\n/g, "\n");

  for (let split = rest.indexOf("\n\n"); split !== -1; split = rest.indexOf("\n\n")) {
    const block = rest.slice(0, split);
    rest = rest.slice(split + 2);

    let name = "message";
    const dataLines: string[] = [];
    for (const line of block.split("\n")) {
      if (line.startsWith("event:")) name = line.slice(6).trim();
      else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
    }
    if (dataLines.length === 0) continue;
    events.push({ event: name, data: safeParse(dataLines.join("\n")) });
  }

  return { events, rest };
}

export type ChatStreamHandlers = {
  onStart?: (info: { conversation_id: number; ai_provider: string }) => void;
  onDelta: (text: string) => void;
  onDone?: (info: { message_id: number }) => void;
};

async function streamChat(
  message: string,
  handlers: ChatStreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = tokenStore.get();
  if (token) headers.Authorization = `Bearer ${token}`;

  let response: Response;
  try {
    response = await fetch(`${BASE_URL}/coach/chat`, {
      method: "POST",
      headers,
      body: JSON.stringify({ message }),
      signal,
    });
  } catch (error) {
    if ((error as Error)?.name === "AbortError") return;
    throw new ApiError("Can't reach the server. Check your connection and try again.", 0);
  }

  if (response.status === 401) {
    tokenStore.clear();
    window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
  }

  // An error arrives as ordinary JSON, not as an event stream.
  if (!response.ok) {
    const payload = safeParse(await response.text());
    const message =
      payload && typeof payload === "object" && "error" in payload
        ? String((payload as { error: unknown }).error)
        : `Request failed (${response.status})`;
    throw new ApiError(message, response.status);
  }

  if (!response.body) throw new ApiError("This browser can't stream the reply.", 0);

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      // `stream: true` matters: a multi-byte character can be split across two
      // reads, and decoding each read independently would corrupt it.
      buffer += decoder.decode(value, { stream: true });

      const { events, rest } = readSseEvents(buffer);
      buffer = rest;
      for (const { event, data } of events) {
        if (event === "delta") handlers.onDelta(String((data as { text: string }).text));
        else if (event === "start") handlers.onStart?.(data as never);
        else if (event === "done") handlers.onDone?.(data as never);
      }
    }
  } catch (error) {
    if ((error as Error)?.name !== "AbortError") throw error;
  } finally {
    reader.releaseLock();
  }
}

export const api = {
  register: (email: string, password: string, display_name: string) =>
    request<AuthResponse>("/auth/register", {
      method: "POST",
      body: { email, password, display_name },
      auth: false,
    }),

  login: (email: string, password: string) =>
    request<AuthResponse>("/auth/login", {
      method: "POST",
      body: { email, password },
      auth: false,
    }),

  me: () => request<User>("/auth/me"),

  todaySummary: (date?: string) =>
    request<TodaySummary>(`/summary/today${date ? `?date=${date}` : ""}`),

  listTasks: (date: string) => request<DailyTask[]>(`/daily-tasks?date=${date}`),

  savePlan: (scheduled_for: string, tasks: PlanItem[]) =>
    request<DailyTask[]>("/daily-tasks/plan", {
      method: "PUT",
      body: { scheduled_for, tasks },
    }),

  setTaskCompletion: (id: number, completed: boolean) =>
    request<DailyTask>(`/daily-tasks/${id}/completion`, {
      method: "PATCH",
      body: { completed },
    }),

  deleteTask: (id: number) => request<void>(`/daily-tasks/${id}`, { method: "DELETE" }),

  listRules: (date?: string) =>
    request<LifeRule[]>(`/life-rules${date ? `?date=${date}` : ""}`),

  createRule: (title: string, description: string | null, emoji: string | null) =>
    request<LifeRule>("/life-rules", {
      method: "POST",
      body: { title, description, emoji },
    }),

  deleteRule: (id: number) => request<void>(`/life-rules/${id}`, { method: "DELETE" }),

  toggleRule: (id: number, date?: string) =>
    request<LifeRule>(`/life-rules/${id}/complete${date ? `?date=${date}` : ""}`, {
      method: "POST",
    }),

  getCheckIn: (date: string) => request<CheckIn | null>(`/check-ins/${date}`),

  saveCheckIn: (checkin_date: string, mood: string | null, reflection: string | null) =>
    request<CheckInResult>("/check-ins", {
      method: "POST",
      body: { checkin_date, mood, reflection },
    }),

  weeklyReport: () => request<WeeklyReport>("/reports/weekly"),

  journey: () => request<Journey>("/journey"),

  coachPrompt: () => request<Insight>("/coach/prompt"),

  askCoach: (question: string) =>
    request<CoachAnswer>("/coach/ask", { method: "POST", body: { question } }),

  conversation: () => request<Conversation>("/coach/conversation"),

  resetConversation: () =>
    request<{ id: null; messages: [] }>("/coach/conversation/reset", { method: "POST" }),

  streamChat,
};
