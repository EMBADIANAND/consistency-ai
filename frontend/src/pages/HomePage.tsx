import { useState } from "react";
import { api } from "../api/client";
import type { DailyTask, TodaySummary } from "../api/types";
import { EmptyState, ErrorState, Loading, Meter } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { today } from "../lib/date";
import type { Page } from "../App";

export function HomePage({ onNavigate }: { onNavigate: (page: Page) => void }) {
  const day = today();
  const summary = useAsync<TodaySummary>(() => api.todaySummary(day), [day]);
  const tasks = useAsync<DailyTask[]>(() => api.listTasks(day), [day]);
  const [busyId, setBusyId] = useState<number | null>(null);

  async function toggle(task: DailyTask) {
    setBusyId(task.id);
    // Optimistic: the checkbox responds immediately, then reconciles with the server.
    tasks.setData((current) =>
      current.map((t) => (t.id === task.id ? { ...t, completed: !t.completed } : t)),
    );
    try {
      const updated = await api.setTaskCompletion(task.id, !task.completed);
      tasks.setData((current) => current.map((t) => (t.id === updated.id ? updated : t)));
      summary.reload();
    } catch {
      tasks.reload();
    } finally {
      setBusyId(null);
    }
  }

  if (summary.loading || tasks.loading) return <Loading label="Reading your day…" />;
  if (summary.error) return <ErrorState message={summary.error} onRetry={summary.reload} />;
  if (!summary.data) return null;

  const list = tasks.data ?? [];
  const stats = summary.data;

  return (
    <section className="page">
      <p className="eyebrow">TODAY · YOUR RHYTHM</p>
      <h1>
        {stats.greeting}, {stats.display_name} ☁️
      </h1>
      <p className="muted">
        {stats.total_tasks === 0
          ? "Nothing planned yet. What would make today feel like a good day?"
          : "You showed up for yourself today. Let's see what your day became."}
      </p>

      <article className="hero">
        <small>✨ TODAY'S RHYTHM</small>
        <h2>{stats.headline}</h2>
        <p>
          {stats.total_tasks === 0
            ? "Your rhythm starts with one intention."
            : `You've kept ${stats.completed_tasks} of ${stats.total_tasks} intentions so far.`}
        </p>
        <Meter value={stats.completion_rate} label="Today's completion" />
      </article>

      <div className="stats">
        <div>
          <strong>
            {stats.completed_tasks}/{stats.total_tasks}
          </strong>
          <span>intentions completed</span>
        </div>
        <div>
          <strong>{stats.streak} 🔥</strong>
          <span>day consistency streak</span>
        </div>
      </div>

      <div className="section-title">Today at a glance</div>
      {list.length === 0 ? (
        <EmptyState
          icon="🌤️"
          title="Your day is still open"
          body="Plan a few intentions and they'll show up here."
          action={
            <button className="secondary" onClick={() => onNavigate("plan")}>
              Plan my day
            </button>
          }
        />
      ) : (
        <div className="card">
          {list.map((task) => (
            <label className="task" key={task.id}>
              <input
                type="checkbox"
                checked={task.completed}
                disabled={busyId === task.id}
                onChange={() => toggle(task)}
              />
              <span>
                {task.emoji ? `${task.emoji} ` : ""}
                {task.title}
                {task.completed && <small>Done</small>}
              </span>
            </label>
          ))}
        </div>
      )}

      <button className="primary" onClick={() => onNavigate("review")}>
        {stats.checked_in ? "🌙 Update today's check-in" : "🌙 End-of-day check-in"}
      </button>
    </section>
  );
}
