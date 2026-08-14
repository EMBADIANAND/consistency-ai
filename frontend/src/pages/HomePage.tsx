import type { Page } from "../App";
export function HomePage({ onNavigate }: { onNavigate: (page: Page) => void }) {
  return <section className="page">
    <p className="eyebrow">TODAY · YOUR RHYTHM</p>
    <h1>Good evening, Anand ☁️</h1>
    <p className="muted">You showed up for yourself today. Let’s see what your day became.</p>
    <article className="hero"><small>✨ TODAY'S RHYTHM</small><h2>Strong momentum.</h2><p>You completed meaningful actions across movement, learning and focused work.</p><div className="progress"><i /></div></article>
    <div className="stats"><div><strong>7/10</strong><span>intentions completed</span></div><div><strong>12 🔥</strong><span>day consistency streak</span></div></div>
    <div className="section-title">Today at a glance</div>
    <div className="card">
      {["🏋️ Move your body","💻 Build something","📚 Learn something useful"].map((x,i)=><label className="task" key={x}><input type="checkbox" defaultChecked={i<2}/><span>{x}<small>{["Gym session completed","Inventory project · 1h","Python practice"][i]}</small></span></label>)}
    </div>
    <button className="primary" onClick={() => onNavigate("review")}>🌙 End-of-day check-in</button>
  </section>;
}
