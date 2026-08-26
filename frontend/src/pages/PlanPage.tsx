import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { DailyTask, LifeRule } from "../api/types";
import { ErrorState, Loading, Toast } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { friendlyDate, shiftDays, today } from "../lib/date";

type Draft = {
  key: string;
  title: string;
  emoji: string | null;
  life_rule_id: number | null;
  completed: boolean;
};

function toDraft(task: DailyTask): Draft {
  return {
    key: `task-${task.id}`,
    title: task.title,
    emoji: task.emoji,
    life_rule_id: task.life_rule_id,
    completed: task.completed,
  };
}

export function PlanPage() {
  const [day, setDay] = useState(today());
  const tasks = useAsync<DailyTask[]>(() => api.listTasks(day), [day]);
  const rules = useAsync<LifeRule[]>(() => api.listRules(day), [day]);

  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [newTitle, setNewTitle] = useState("");
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  // The draft list is the editable copy; it resets whenever a new day loads.
  useEffect(() => {
    if (tasks.data) setDrafts(tasks.data.map(toDraft));
  }, [tasks.data]);

  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(null), 2600);
    return () => clearTimeout(timer);
  }, [toast]);

  function addDraft(title: string, emoji: string | null, ruleId: number | null) {
    const clean = title.trim();
    if (!clean) return;
    const duplicate = drafts.some(
      (d) => d.title.toLowerCase() === clean.toLowerCase() && d.life_rule_id === ruleId,
    );
    if (duplicate) {
      setToast("That's already on today's list.");
      return;
    }
    setDrafts((current) => [
      ...current,
      {
        key: `draft-${Date.now()}-${current.length}`,
        title: clean,
        emoji,
        life_rule_id: ruleId,
        completed: false,
      },
    ]);
  }

  async function save() {
    setSaving(true);
    setSaveError(null);
    try {
      const saved = await api.savePlan(
        day,
        drafts.map(({ title, emoji, life_rule_id, completed }) => ({
          title,
          emoji,
          life_rule_id,
          completed,
        })),
      );
      tasks.setData(saved);
      setDrafts(saved.map(toDraft));
      setToast("Plan saved.");
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Couldn't save your plan");
    } finally {
      setSaving(false);
    }
  }

  if (tasks.loading && drafts.length === 0) return <Loading label="Opening your plan…" />;
  if (tasks.error) return <ErrorState message={tasks.error} onRetry={tasks.reload} />;

  const unusedRules = (rules.data ?? []).filter(
    (rule) => !drafts.some((draft) => draft.life_rule_id === rule.id),
  );

  return (
    <section className="page">
      <p className="eyebrow">START WITH INTENTION</p>
      <h1>Plan My Day ☀️</h1>
      <p className="muted">
        Choose a few things that would make today feel like a good day — not an overwhelming
        list.
      </p>

      <div className="day-switch">
        <button className="secondary" onClick={() => setDay(shiftDays(day, -1))}>
          ← Previous
        </button>
        <strong>{friendlyDate(day)}</strong>
        <button className="secondary" onClick={() => setDay(shiftDays(day, 1))}>
          Next →
        </button>
      </div>

      {unusedRules.length > 0 && (
        <>
          <div className="section-title">Pull in a life rule</div>
          <div className="chips">
            {unusedRules.map((rule) => (
              <button
                key={rule.id}
                onClick={() => addDraft(rule.title, rule.emoji, rule.id)}
              >
                {rule.emoji ?? "＋"} {rule.title}
              </button>
            ))}
          </div>
        </>
      )}

      <div className="section-title">Today's intentions</div>
      <div className="card">
        {drafts.length === 0 && <p className="muted inline-empty">Nothing here yet.</p>}
        {drafts.map((draft, index) => (
          <label className="task" key={draft.key}>
            <input
              type="checkbox"
              checked={draft.completed}
              onChange={() =>
                setDrafts((current) =>
                  current.map((d, i) =>
                    i === index ? { ...d, completed: !d.completed } : d,
                  ),
                )
              }
            />
            <span>
              {draft.emoji ? `${draft.emoji} ` : ""}
              {draft.title}
              {draft.life_rule_id && <small>From your life rules</small>}
            </span>
            <button
              className="remove"
              aria-label={`Remove ${draft.title}`}
              onClick={(event) => {
                event.preventDefault();
                setDrafts((current) => current.filter((_, i) => i !== index));
              }}
            >
              ✕
            </button>
          </label>
        ))}
      </div>

      <form
        className="inline-form"
        onSubmit={(event) => {
          event.preventDefault();
          addDraft(newTitle, null, null);
          setNewTitle("");
        }}
      >
        <input
          value={newTitle}
          onChange={(event) => setNewTitle(event.target.value)}
          placeholder="Add an intention…"
          maxLength={180}
        />
        <button className="secondary" type="submit">
          Add
        </button>
      </form>

      {saveError && <ErrorState message={saveError} />}

      <button className="primary" onClick={save} disabled={saving}>
        {saving ? "Saving…" : `Save ${friendlyDate(day).toLowerCase()}'s plan`}
      </button>

      <Toast message={toast} />
    </section>
  );
}
