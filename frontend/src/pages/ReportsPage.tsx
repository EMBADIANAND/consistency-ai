import { api } from "../api/client";
import type { WeeklyReport } from "../api/types";
import { EmptyState, ErrorState, Loading, Meter } from "../components/ui";
import { WeeklyChart } from "../components/WeeklyChart";
import { useAsync } from "../hooks/useAsync";
import type { Page } from "../App";

export function ReportsPage({ onNavigate }: { onNavigate: (page: Page) => void }) {
  const report = useAsync<WeeklyReport>(() => api.weeklyReport(), []);

  if (report.loading) return <Loading label="Looking for patterns…" />;
  if (report.error) return <ErrorState message={report.error} onRetry={report.reload} />;
  if (!report.data) return null;

  const data = report.data;
  const hasHistory = data.days.some((day) => day.total > 0);
  const deltaLabel =
    data.delta > 0
      ? `↑ ${data.delta}% from last week`
      : data.delta < 0
        ? `↓ ${Math.abs(data.delta)}% from last week`
        : "Level with last week";

  return (
    <section className="page">
      <p className="eyebrow">YOUR PATTERNS, NOT JUST NUMBERS</p>
      <h1>AI Reports 📊</h1>
      <p className="muted">
        ConsistencyAI turns completed days into useful stories and patterns.
      </p>

      {!hasHistory ? (
        <EmptyState
          icon="📊"
          title="No data for this week yet"
          body="Plan a day and check a few things off — your first report appears as soon as there's something to read."
          action={
            <button className="secondary" onClick={() => onNavigate("plan")}>
              Plan my day
            </button>
          }
        />
      ) : (
        <>
          <article className="report">
            <small>THIS WEEK'S CONSISTENCY</small>
            <strong>{data.consistency}%</strong>
            <span>{deltaLabel}</span>
          </article>

          <WeeklyChart days={data.days} />

          {data.rule_breakdown.length > 0 && (
            <>
              <div className="section-title">How each rule held up</div>
              <div className="card">
                {data.rule_breakdown.map((rule) => (
                  <div className="breakdown" key={rule.id}>
                    <div className="breakdown-head">
                      <span>
                        {rule.emoji ?? "✅"} {rule.title}
                      </span>
                      <b>
                        {rule.planned ? `${rule.kept}/${rule.planned}` : "Not planned"}
                      </b>
                    </div>
                    <Meter value={rule.rate} label={`${rule.title} completion`} />
                  </div>
                ))}
              </div>
            </>
          )}

          <div className="section-title">
            AI found these patterns
            {data.ai_provider === "mock" && <em className="tag">rule-based</em>}
          </div>
          {data.patterns.map((pattern) => (
            <article className="insight" key={pattern.title}>
              <strong>{pattern.title}</strong>
              <p>{pattern.body}</p>
            </article>
          ))}
        </>
      )}
    </section>
  );
}
