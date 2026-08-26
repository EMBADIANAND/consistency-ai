import { api } from "../api/client";
import type { Journey } from "../api/types";
import { ErrorState, Loading, Meter } from "../components/ui";
import { useAuth } from "../auth/AuthContext";
import { useAsync } from "../hooks/useAsync";

export function JourneyPage() {
  const { user, signOut } = useAuth();
  const journey = useAsync<Journey>(() => api.journey(), []);

  if (journey.loading) return <Loading label="Drawing your picture…" />;
  if (journey.error) return <ErrorState message={journey.error} onRetry={journey.reload} />;
  if (!journey.data) return null;

  const data = journey.data;

  return (
    <section className="page">
      <p className="eyebrow">YOUR SPACE</p>
      <h1>My Journey ✨</h1>
      <p className="muted">A living picture of the person you're becoming.</p>

      <article className="hero">
        <small>CONSISTENCY SCORE · LAST {data.window_days} DAYS</small>
        <h2>{data.score} / 100</h2>
        <p>
          {data.score === 0
            ? "Your first kept intention starts this."
            : "You're not chasing perfection. You're building reliability."}
        </p>
        <Meter value={data.score} label="Consistency score" />
      </article>

      <div className="stats">
        <div>
          <strong>{data.current_streak} 🔥</strong>
          <span>current streak</span>
        </div>
        <div>
          <strong>{data.longest_streak}</strong>
          <span>longest streak</span>
        </div>
        <div>
          <strong>{data.reliability}%</strong>
          <span>of plans kept</span>
        </div>
        <div>
          <strong>
            {data.active_days}/{data.window_days}
          </strong>
          <span>days you showed up</span>
        </div>
      </div>

      <div className="section-title">Your identity</div>
      <div className="chips static">
        {data.traits.map((trait) => (
          <span key={trait}>{trait}</span>
        ))}
      </div>

      <div className="section-title">Account</div>
      <div className="card account">
        <div>
          <strong>{user?.display_name}</strong>
          <small>{user?.email}</small>
        </div>
        <button className="secondary" onClick={signOut}>
          Sign out
        </button>
      </div>
    </section>
  );
}
