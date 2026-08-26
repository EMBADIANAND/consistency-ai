import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { CheckIn, DailyTask, Insight } from "../api/types";
import { EmptyState, ErrorState, Loading, Toast } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { today } from "../lib/date";
import type { Page } from "../App";

const MOODS = ["😄", "🙂", "😐", "😕", "😔"];

export function ReviewPage({ onNavigate }: { onNavigate: (page: Page) => void }) {
  const day = today();
  const tasks = useAsync<DailyTask[]>(() => api.listTasks(day), [day]);
  const existing = useAsync<CheckIn | null>(() => api.getCheckIn(day), [day]);

  const [mood, setMood] = useState<string | null>(null);
  const [reflection, setReflection] = useState("");
  const [insight, setInsight] = useState<Insight | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  // Re-opening the screen should show what you already recorded today.
  useEffect(() => {
    if (existing.data) {
      setMood(existing.data.mood);
      setReflection(existing.data.reflection ?? "");
    }
  }, [existing.data]);

  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(null), 2600);
    return () => clearTimeout(timer);
  }, [toast]);

  async function toggle(task: DailyTask) {
    setBusyId(task.id);
    tasks.setData((current) =>
      current.map((t) => (t.id === task.id ? { ...t, completed: !t.completed } : t)),
    );
    try {
      const updated = await api.setTaskCompletion(task.id, !task.completed);
      tasks.setData((current) => current.map((t) => (t.id === updated.id ? updated : t)));
    } catch {
      tasks.reload();
    } finally {
      setBusyId(null);
    }
  }

  async function complete() {
    setSaving(true);
    setError(null);
    try {
      const result = await api.saveCheckIn(day, mood, reflection.trim() || null);
      setInsight(result.insight);
      setToast("Day recorded.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't save your check-in");
    } finally {
      setSaving(false);
    }
  }

  if (tasks.loading || existing.loading) return <Loading label="Gathering your day…" />;
  if (tasks.error) return <ErrorState message={tasks.error} onRetry={tasks.reload} />;

  const list = tasks.data ?? [];

  return (
    <section className="page">
      <p className="eyebrow">END YOUR DAY WITH A CHECK-IN</p>
      <h1>How did today feel? 🌙</h1>
      <p className="muted">No guilt. No grades. Just a quick honest reflection.</p>

      <div className="section-title">What did you actually do?</div>
      {list.length === 0 ? (
        <EmptyState
          icon="🌙"
          title="Nothing was planned today"
          body="You can still record how the day felt, or plan tomorrow instead."
          action={
            <button className="secondary" onClick={() => onNavigate("plan")}>
              Plan a day
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
              </span>
            </label>
          ))}
        </div>
      )}

      <div className="section-title">Pick your mood</div>
      <div className="moods">
        {MOODS.map((choice) => (
          <button
            key={choice}
            className={choice === mood ? "selected" : ""}
            aria-pressed={choice === mood}
            onClick={() => setMood(choice)}
          >
            {choice}
          </button>
        ))}
      </div>

      <div className="section-title">Anything worth remembering?</div>
      <textarea
        value={reflection}
        onChange={(event) => setReflection(event.target.value)}
        placeholder="One honest sentence is enough…"
        maxLength={5000}
      />

      {insight && (
        <article className="insight">
          <strong>✨ {insight.title}</strong>
          <p>{insight.body}</p>
        </article>
      )}

      {error && <ErrorState message={error} />}

      <button className="primary" onClick={complete} disabled={saving}>
        {saving ? "Saving…" : existing.data ? "Update my day" : "Complete my day"}
      </button>

      <Toast message={toast} />
    </section>
  );
}
