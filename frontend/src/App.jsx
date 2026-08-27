import { useEffect, useMemo, useState } from "react";
import { Activity, ArrowUpRight, Check, ChevronRight, CircleAlert, RefreshCw, X } from "lucide-react";
import { getDashboard, getNarrative, saveDecision } from "./api/index.js";

const PERSONAS = {
  "Category Manager": { label: "Category Manager", scope: "Electronics + Apparel & Home", categories: ["Electronics", "Apparel", "Home & Kitchen"] },
  CXO: { label: "CXO Suite", scope: "Enterprise portfolio", categories: null },
};

function formatImpact(value) {
  const absolute = Math.abs(value || 0);
  const sign = value < 0 ? "-" : "+";
  if (absolute >= 1e7) return `${sign}₹${(absolute / 1e7).toFixed(2)}Cr`;
  if (absolute >= 1e5) return `${sign}₹${(absolute / 1e5).toFixed(1)}L`;
  return `${sign}₹${Math.round(absolute).toLocaleString("en-IN")}`;
}

function routeLabel(route) {
  return { RESOLVED: "Diagnosed", FAST_PATH: "Direct match", UNRESOLVED_CONFLICT: "Conflict", ABSTAIN: "Low evidence" }[route] || route;
}

export default function App() {
  const [persona, setPersona] = useState("Category Manager");
  const [dashboard, setDashboard] = useState(null);
  const [selected, setSelected] = useState(null);
  const [narrative, setNarrative] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [handled, setHandled] = useState({});

  async function loadDashboard() {
    setBusy(true);
    setError("");
    try { setDashboard(await getDashboard()); } catch (err) { setError(err.message); } finally { setBusy(false); }
  }

  useEffect(() => { loadDashboard(); }, []);

  const visibleAlerts = useMemo(() => {
    if (!dashboard) return [];
    const categories = PERSONAS[persona].categories;
    return dashboard.alerts.filter((item) => !handled[item.alert.id] && (!categories || categories.includes(item.alert.category)));
  }, [dashboard, handled, persona]);

  async function openAlert(item) {
    setSelected(item);
    setNarrative(null);
    setError("");
    if (item.route !== "ABSTAIN") {
      try { setNarrative(await getNarrative(item.alert.id, persona)); } catch (err) { setError(err.message); }
    }
  }

  async function decide(decision) {
    if (!selected) return;
    setBusy(true);
    try {
      await saveDecision(selected.alert.id, { decision, persona, feedback: "" });
      setHandled((current) => ({ ...current, [selected.alert.id]: decision }));
      setSelected(null);
    } catch (err) { setError(err.message); } finally { setBusy(false); }
  }

  const impact = visibleAlerts.reduce((sum, item) => sum + Math.abs(item.alert.delta_inr), 0);
  const verified = visibleAlerts.filter((item) => ["RESOLVED", "FAST_PATH"].includes(item.route)).length;

  return <div className="shell">
    <header className="topbar">
      <div className="brand"><span>accenture</span><b>&gt;</b><strong>CAUSE</strong><small>CAUSAL INTELLIGENCE</small></div>
      <div className="top-actions"><span className="status"><Activity size={15} /> Live telemetry</span><select value={persona} onChange={(event) => setPersona(event.target.value)}><option>Category Manager</option><option>CXO</option></select><button className="icon-button" title="Refresh dashboard" onClick={loadDashboard}><RefreshCw size={17} className={busy ? "spin" : ""} /></button></div>
    </header>

    <main>
      <section className="intro"><div><p className="eyebrow">{PERSONAS[persona].scope}</p><h1>Find the reason behind the signal.</h1><p className="lede">A decision workspace for retail anomalies, grounded in operational evidence and explicit uncertainty.</p></div><div className="week"><span>Current observation window</span><strong>{dashboard ? `Week of ${dashboard.cur_week}` : "Loading..."}</strong></div></section>

      {error && <div className="error"><CircleAlert size={17} />{error}</div>}
      <section className="metrics"><Metric label="Active signals" value={visibleAlerts.length} caption="In your current scope" /><Metric label="Exposure" value={formatImpact(impact)} caption="Absolute revenue impact" accent /><Metric label="Auto-diagnostic rate" value={`${visibleAlerts.length ? Math.round((verified / visibleAlerts.length) * 100) : 100}%`} caption={`${verified} signals verified`} /></section>

      <section className="queue-head"><div><p className="eyebrow">Prioritized queue</p><h2>Telemetry anomalies <span>{visibleAlerts.length}</span></h2></div><span className="queue-note">Ranked by financial impact</span></section>
      <section className="queue">{!dashboard ? <div className="loading">Loading telemetry...</div> : visibleAlerts.length === 0 ? <div className="empty"><Check size={25} /><h3>All clear</h3><p>There are no unresolved signals in this scope.</p></div> : visibleAlerts.map((item) => <AlertCard key={item.alert.id} item={item} onOpen={() => openAlert(item)} />)}</section>
    </main>

    {selected && <Drawer item={selected} narrative={narrative} onClose={() => setSelected(null)} onDecision={decide} busy={busy} />}
  </div>;
}

function Metric({ label, value, caption, accent }) { return <div className="metric"><span>{label}</span><strong className={accent ? "accent" : ""}>{value}</strong><small>{caption}</small></div>; }

function AlertCard({ item, onOpen }) {
  const { alert } = item;
  const change = alert.pct_change == null ? "New signal" : `${alert.pct_change >= 0 ? "+" : ""}${(alert.pct_change * 100).toFixed(1)}%`;
  return <article className="alert-card"><div className="card-top"><span className={`route ${item.route.toLowerCase()}`}>{routeLabel(item.route)}</span><span className="alert-id">{alert.id}</span></div><h3>{alert.kpi}</h3><p className="context">{alert.category} <span>/</span> {alert.region}</p><div className="card-stats"><div><small>Vs baseline</small><strong className={alert.delta_inr < 0 ? "negative" : "positive"}>{change}</strong></div><div className="impact"><small>Impact</small><strong>{alert.delta_fmt}</strong></div></div><button className="investigate" onClick={onOpen}>Investigate <ArrowUpRight size={16} /></button></article>;
}

function Drawer({ item, narrative, onClose, onDecision, busy }) {
  const { alert } = item;
  const winner = item.hypotheses?.find((hypothesis) => hypothesis.supported);
  return <div className="overlay" onMouseDown={(event) => event.target === event.currentTarget && onClose()}><aside className="drawer"><div className="drawer-head"><div><span className={`route ${item.route.toLowerCase()}`}>{routeLabel(item.route)}</span><p className="eyebrow">{alert.id} / diagnostic brief</p><h2>{alert.kpi}</h2><p className="context">{alert.category} <span>/</span> {alert.region} · {alert.delta_fmt}</p></div><button className="icon-button" onClick={onClose} title="Close"><X size={19} /></button></div>{item.route === "ABSTAIN" ? <div className="notice warning"><CircleAlert size={19} /><div><strong>Diagnostic abstention</strong><p>{item.abstention?.reason}</p><small>{item.abstention?.required_data}</small></div></div> : <><div className="section-label">Evidence-led finding</div><div className="finding"><div className="confidence"><span>Confidence</span><strong>{winner?.confidence_pct || Math.round((item.confidence?.score || 0) * 100)}%</strong></div><h3>{winner?.name || item.recommendation?.driver}</h3><p>{winner?.verdict || item.recommendation?.basis}</p></div><div className="evidence-grid"><Evidence label="Route" value={routeLabel(item.route)} /><Evidence label="Evidence records" value={`${item.rag_evidence?.length || 0} retrieved`} /><Evidence label="Recommendation" value={item.recommendation?.owner || "Review required"} /></div><div className="section-label">Audited narrative</div><div className="narrative">{narrative ? <><p>{narrative.text}</p><small>{narrative.engine} · {narrative.audit}</small></> : <p>Generating the verified brief...</p>}</div><div className="section-label">Recommended action</div><div className="action"><strong>{item.recommendation?.action}</strong><p>{item.recommendation?.monitoring_plan}</p></div><div className="drawer-actions"><button className="secondary" disabled={busy} onClick={() => onDecision("rejected")}>Reject</button><button className="primary" disabled={busy} onClick={() => onDecision("approved")}>Approve <ChevronRight size={16} /></button></div></>}</aside></div>;
}

function Evidence({ label, value }) { return <div><small>{label}</small><strong>{value}</strong></div>; }
