import { useState, type FormEvent } from "react";
import { api } from "../api/client";
import type { LifeRule } from "../api/types";
import { EmptyState, ErrorState, Loading, Toast } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { today } from "../lib/date";

const EMOJI_CHOICES = ["🏋️", "📚", "📵", "😴", "🧘", "💻", "🥗", "🚶", "💧", "✍️"];

export function RulesPage() {
  const day = today();
  const rules = useAsync<LifeRule[]>(() => api.listRules(day), [day]);
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [emoji, setEmoji] = useState<string>(EMOJI_CHOICES[0]);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  async function toggle(rule: LifeRule) {
    setBusyId(rule.id);
    try {
      const updated = await api.toggleRule(rule.id, day);
      rules.setData((current) => current.map((r) => (r.id === updated.id ? updated : r)));
    } catch (err) {
      setToast(err instanceof Error ? err.message : "Couldn't update that rule");
    } finally {
      setBusyId(null);
    }
  }

  async function create(event: FormEvent) {
    event.preventDefault();
    setFormError(null);
    try {
      const created = await api.createRule(title.trim(), description.trim() || null, emoji);
      rules.setData((current) => [...current, created]);
      setTitle("");
      setDescription("");
      setShowForm(false);
      setToast("Rule created.");
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Couldn't create that rule");
    }
  }

  async function remove(rule: LifeRule) {
    setBusyId(rule.id);
    try {
      await api.deleteRule(rule.id);
      rules.setData((current) => current.filter((r) => r.id !== rule.id));
      setToast("Rule archived. Its history is kept.");
    } catch (err) {
      setToast(err instanceof Error ? err.message : "Couldn't archive that rule");
    } finally {
      setBusyId(null);
    }
  }

  if (rules.loading) return <Loading label="Loading your rules…" />;
  if (rules.error) return <ErrorState message={rules.error} onRetry={rules.reload} />;

  const list = rules.data ?? [];

  return (
    <section className="page">
      <p className="eyebrow">IDENTITY · NOT JUST HABITS</p>
      <h1>My Life Rules 🌟</h1>
      <p className="muted">
        The promises you keep with yourself become the person you're becoming.
      </p>

      {list.length === 0 && !showForm && (
        <EmptyState
          icon="🌱"
          title="No rules yet"
          body="A life rule is a promise you keep daily — move your body, protect your attention, learn something."
          action={
            <button className="secondary" onClick={() => setShowForm(true)}>
              Create my first rule
            </button>
          }
        />
      )}

      {list.map((rule) => (
        <article className="rule" key={rule.id}>
          <div className="rule-head">
            <span className="emoji">{rule.emoji ?? "✅"}</span>
            <h3>{rule.title}</h3>
            <b>
              {rule.streak > 0
                ? `🔥 ${rule.streak} day${rule.streak === 1 ? "" : "s"}`
                : "New"}
            </b>
          </div>
          {rule.description && <p>{rule.description}</p>}
          <div className="rule-actions">
            <button
              className={rule.done_today ? "secondary done" : "secondary"}
              disabled={busyId === rule.id}
              onClick={() => toggle(rule)}
            >
              {rule.done_today ? "✓ Done today" : "Mark done today"}
            </button>
            <button
              className="link danger"
              disabled={busyId === rule.id}
              onClick={() => remove(rule)}
            >
              Archive
            </button>
          </div>
        </article>
      ))}

      {showForm ? (
        <form className="card form" onSubmit={create}>
          <div className="section-title">New life rule</div>
          <label className="field">
            <span>The promise</span>
            <input
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Move my body every day"
              maxLength={120}
              required
            />
          </label>
          <label className="field">
            <span>What it looks like (optional)</span>
            <input
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="Gym · walk · stretching"
              maxLength={2000}
            />
          </label>
          <div className="field">
            <span>Pick an emoji</span>
            <div className="emoji-picker">
              {EMOJI_CHOICES.map((choice) => (
                <button
                  type="button"
                  key={choice}
                  className={choice === emoji ? "selected" : ""}
                  onClick={() => setEmoji(choice)}
                >
                  {choice}
                </button>
              ))}
            </div>
          </div>
          {formError && <p className="form-error">{formError}</p>}
          <button className="primary" type="submit">
            Create rule
          </button>
          <button className="link" type="button" onClick={() => setShowForm(false)}>
            Cancel
          </button>
        </form>
      ) : (
        list.length > 0 && (
          <button className="primary" onClick={() => setShowForm(true)}>
            ＋ Create a new rule
          </button>
        )
      )}

      <Toast message={toast} />
    </section>
  );
}
