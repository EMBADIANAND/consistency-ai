import { useState } from "react";
import { AppShell } from "./components/layout/AppShell";
import { HomePage } from "./pages/HomePage";
import { PlanPage } from "./pages/PlanPage";
import { RulesPage } from "./pages/RulesPage";
import { ReviewPage } from "./pages/ReviewPage";
import { ReportsPage } from "./pages/ReportsPage";
import { CoachPage } from "./pages/CoachPage";
import { JourneyPage } from "./pages/JourneyPage";

export type Page = "home" | "plan" | "rules" | "review" | "reports" | "coach" | "journey";

export default function App() {
  const [page, setPage] = useState<Page>("home");

  const content = {
    home: <HomePage onNavigate={setPage} />,
    plan: <PlanPage />,
    rules: <RulesPage />,
    review: <ReviewPage />,
    reports: <ReportsPage />,
    coach: <CoachPage />,
    journey: <JourneyPage />,
  }[page];

  return <AppShell page={page} onNavigate={setPage}>{content}</AppShell>;
}
