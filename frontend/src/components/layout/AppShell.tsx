import type { ReactNode } from "react";
import type { Page } from "../../App";

type Props = { children: ReactNode; page: Page; onNavigate: (page: Page) => void };

const items: Array<{ id: Page; icon: string; label: string }> = [
  { id: "home", icon: "⌂", label: "Home" },
  { id: "plan", icon: "☀️", label: "Plan" },
  { id: "rules", icon: "🌟", label: "Rules" },
  { id: "reports", icon: "📊", label: "Reports" },
  { id: "coach", icon: "🧠", label: "Coach" },
  { id: "journey", icon: "◉", label: "Journey" },
];

export function AppShell({ children, page, onNavigate }: Props) {
  return (
    <div className="app">
      <header className="topbar">
        <div className="brand"><div className="logo">C</div><div><strong>ConsistencyAI</strong><span>Your day, made meaningful.</span></div></div>
        <div className="avatar" aria-label="Profile">A</div>
      </header>
      <main>{children}</main>
      <nav className="bottom-nav" aria-label="Primary navigation">
        {items.map(item => (
          <button key={item.id} className={page === item.id ? "nav-item active" : "nav-item"} onClick={() => onNavigate(item.id)}>
            <span>{item.icon}</span>{item.label}
          </button>
        ))}
      </nav>
    </div>
  );
}
