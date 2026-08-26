import type { ReactNode } from "react";
import { useAuth } from "../../auth/AuthContext";
import type { Page } from "../../App";

type Props = { children: ReactNode; page: Page; onNavigate: (page: Page) => void };

const items: Array<{ id: Page; icon: string; label: string }> = [
  { id: "home", icon: "⌂", label: "Home" },
  { id: "plan", icon: "☀️", label: "Plan" },
  { id: "rules", icon: "🌟", label: "Rules" },
  { id: "review", icon: "🌙", label: "Review" },
  { id: "reports", icon: "📊", label: "Reports" },
  { id: "coach", icon: "🧠", label: "Coach" },
  { id: "journey", icon: "◉", label: "Journey" },
];

export function AppShell({ children, page, onNavigate }: Props) {
  const { user } = useAuth();
  const initial = user?.display_name?.trim().charAt(0).toUpperCase() || "?";

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <div className="logo">C</div>
          <div>
            <strong>ConsistencyAI</strong>
            <span>Your day, made meaningful.</span>
          </div>
        </div>
        <button
          className="avatar"
          aria-label="Your journey and account"
          onClick={() => onNavigate("journey")}
        >
          {initial}
        </button>
      </header>
      <main>{children}</main>
      <nav className="bottom-nav" aria-label="Primary navigation">
        {items.map((item) => (
          <button
            key={item.id}
            className={page === item.id ? "nav-item active" : "nav-item"}
            aria-current={page === item.id ? "page" : undefined}
            onClick={() => onNavigate(item.id)}
          >
            <span>{item.icon}</span>
            {item.label}
          </button>
        ))}
      </nav>
    </div>
  );
}
