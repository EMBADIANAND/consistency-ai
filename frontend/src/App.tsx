import { useState } from "react";
import { AppShell } from "./components/layout/AppShell";
import { Loading } from "./components/ui";
import { useAuth } from "./auth/AuthContext";
import { AuthPage } from "./pages/AuthPage";
import { CoachPage } from "./pages/CoachPage";
import { HomePage } from "./pages/HomePage";
import { JourneyPage } from "./pages/JourneyPage";
import { PlanPage } from "./pages/PlanPage";
import { ReportsPage } from "./pages/ReportsPage";
import { ReviewPage } from "./pages/ReviewPage";
import { RulesPage } from "./pages/RulesPage";

export type Page = "home" | "plan" | "rules" | "review" | "reports" | "coach" | "journey";

export default function App() {
  const { user, ready } = useAuth();
  const [page, setPage] = useState<Page>("home");

  if (!ready) {
    return (
      <div className="app boot">
        <Loading label="Getting your day ready…" />
      </div>
    );
  }

  if (!user) return <AuthPage />;

  const content = {
    home: <HomePage onNavigate={setPage} />,
    plan: <PlanPage />,
    rules: <RulesPage />,
    review: <ReviewPage onNavigate={setPage} />,
    reports: <ReportsPage onNavigate={setPage} />,
    coach: <CoachPage />,
    journey: <JourneyPage />,
  }[page];

  return (
    <AppShell page={page} onNavigate={setPage}>
      {/* Remounting on page change keeps each screen's data fetch simple and fresh. */}
      <div key={page}>{content}</div>
    </AppShell>
  );
}
