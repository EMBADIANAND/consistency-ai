import { useState } from "react";
import type { WeeklyReport } from "../api/types";

type Day = WeeklyReport["days"][number];

/**
 * One series (daily completion rate), so a single brand hue carries it and no
 * legend is needed — the heading names the measure. A day with nothing planned
 * is drawn as an empty track and labelled "—", so it is never confused with a
 * day scored 0%: the difference is stated in text, not just in colour.
 */
export function WeeklyChart({ days }: { days: Day[] }) {
  const [hovered, setHovered] = useState<string | null>(null);
  const [showTable, setShowTable] = useState(false);

  const planned = days.filter((day) => !day.future && day.total > 0);
  const best = planned.reduce<Day | null>(
    (winner, day) => (winner === null || day.rate > winner.rate ? day : winner),
    null,
  );

  const summary = planned
    .map((day) => `${day.label} ${day.rate} percent`)
    .join(", ");

  return (
    <div className="chart-block">
      <div className="chart-head">
        <span className="chart-title">Completion by day</span>
        <button className="link" onClick={() => setShowTable((current) => !current)}>
          {showTable ? "Show chart" : "Show as table"}
        </button>
      </div>

      {showTable ? (
        <table className="data-table">
          <thead>
            <tr>
              <th scope="col">Day</th>
              <th scope="col">Kept</th>
              <th scope="col">Planned</th>
              <th scope="col">Rate</th>
            </tr>
          </thead>
          <tbody>
            {days.map((day) => (
              <tr key={day.date}>
                <th scope="row">{day.label}</th>
                <td>{day.completed}</td>
                <td>{day.total}</td>
                <td>{day.future ? "To come" : day.total ? `${day.rate}%` : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <div
          className="chart"
          role="img"
          aria-label={
            planned.length
              ? `Daily completion rate this week: ${summary}.`
              : "No intentions planned yet this week."
          }
        >
          {days.map((day) => {
            const isBest = best !== null && day.date === best.date && day.rate > 0;
            return (
              <div
                className={day.future ? "chart-col future" : "chart-col"}
                key={day.date}
                onMouseEnter={() => setHovered(day.date)}
                onMouseLeave={() => setHovered(null)}
                onFocus={() => setHovered(day.date)}
                onBlur={() => setHovered(null)}
                tabIndex={0}
              >
                {hovered === day.date && (
                  <div className="chart-tip" role="tooltip">
                    {day.future
                      ? "Still to come"
                      : day.total
                        ? `${day.completed} of ${day.total} kept · ${day.rate}%`
                        : "Nothing planned"}
                  </div>
                )}
                <div className="chart-track">
                  <div
                    className={day.total && !day.future ? "chart-bar" : "chart-bar none"}
                    style={{
                      height: day.total && !day.future ? `${Math.max(day.rate, 3)}%` : "0%",
                    }}
                  />
                </div>
                <span className={isBest ? "chart-value best" : "chart-value"}>
                  {day.future ? "·" : day.total ? `${day.rate}%` : "—"}
                </span>
                <span className="chart-label">{day.label}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
