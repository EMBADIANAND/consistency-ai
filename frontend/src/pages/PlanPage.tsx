export function PlanPage() {
  const tasks = ["🏋️ Gym before 7 AM","🚶 Reach 10,000 steps","💻 Work on Inventory Project","📖 Read 10 pages","🧠 Learn Python"];
  return <section className="page"><p className="eyebrow">START WITH INTENTION</p><h1>Plan My Day ☀️</h1><p className="muted">Choose a few things that would make today feel like a good day — not an overwhelming list.</p><div className="section-title">Today's intentions</div><div className="card">{tasks.map((t,i)=><label className="task" key={t}><input type="checkbox" defaultChecked={i<2}/><span>{t}<small>{["Take care of your body","Small movement counts","Deep work · 1 hour","The Alchemist","One concept + practice"][i]}</small></span></label>)}</div><button className="primary">Save today's plan</button></section>;
}
