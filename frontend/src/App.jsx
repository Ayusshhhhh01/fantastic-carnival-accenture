import { useEffect, useMemo, useState } from "react";
import { BrowserRouter as Router, Routes, Route, useNavigate } from "react-router-dom";
import { Activity, ArrowUpRight, Check, ChevronRight, CircleAlert, RefreshCw, X } from "lucide-react";
import { getDashboard, getNarrative, investigateAlert, saveDecision } from "./api/index.js";
import LoginPage from "./pages/LoginPage.jsx";
import InvestigationDetailPage from "./pages/InvestigationDetailPage.jsx";

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

function DashboardPage() {
  const params = new URLSearchParams(window.location.search);
  const initialPersona = params.get("persona") || "Category Manager";
  const navigate = useNavigate();

  const [persona, setPersona] = useState(initialPersona);
  const [dashboard, setDashboard] = useState(null);
  const [selected, setSelected] = useState(null);
  const [narrative, setNarrative] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [handled, setHandled] = useState({});

  async function loadDashboard() {
    setBusy(true);
    setError("");
    try {
      setDashboard(await getDashboard());
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    loadDashboard();
  }, []);

  const visibleAlerts = useMemo(() => {
    if (!dashboard) return [];
    const categories = PERSONAS[persona].categories;
    return dashboard.alerts.filter(
      (item) =>
        !handled[item.alert.id] &&
        (!categories || categories.includes(item.alert.category))
    );
  }, [dashboard, handled, persona]);

  function handleDismiss(alertId, e) {
    if (e) e.stopPropagation();
    setHandled((current) => ({ ...current, [alertId]: "dismissed" }));
    if (selected?.alert?.id === alertId) {
      setSelected(null);
    }
  }

  async function openAlert(item) {
    setSelected(item);
    setError("");
  }

  function startDiagnosis() {
    if (!selected) return;
    const alertId = selected.alert.id;
    setSelected(null);
    navigate(`/investigate/${alertId}?persona=${encodeURIComponent(persona)}`);
  }

  const impact = visibleAlerts.reduce((sum, item) => sum + Math.abs(item.alert.delta_inr), 0);
  const verified = visibleAlerts.filter((item) => ["RESOLVED", "FAST_PATH"].includes(item.route)).length;

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          <span>accenture</span>
          <b>&gt;</b>
          <strong>CAUSE</strong>
          <small>CAUSAL INTELLIGENCE</small>
        </div>
        <div className="top-actions">
          <span className="status">
            <Activity size={15} /> Live telemetry
          </span>
          <select value={persona} onChange={(event) => setPersona(event.target.value)}>
            <option>Category Manager</option>
            <option>CXO</option>
          </select>
          <button className="icon-button" title="Refresh dashboard" onClick={loadDashboard}>
            <RefreshCw size={17} className={busy ? "spin" : ""} />
          </button>
        </div>
      </header>

      <main>
        <section className="intro">
          <div>
            <p className="eyebrow">{PERSONAS[persona].scope}</p>
            <h1>Find the reason behind the signal.</h1>
            <p className="lede">
              An enterprise decision workspace for retail anomalies, grounded in operational
              evidence and explicit uncertainty.
            </p>
          </div>
          <div className="week">
            <span>Current observation window</span>
            <strong>{dashboard ? `Week of ${dashboard.cur_week}` : "Loading..."}</strong>
          </div>
        </section>

        {error && (
          <div className="error">
            <CircleAlert size={17} />
            {error}
          </div>
        )}
        <section className="metrics">
          <Metric
            label="Active signals"
            value={visibleAlerts.length}
            caption="In your current scope"
          />
          <Metric
            label="Exposure"
            value={formatImpact(impact)}
            caption="Absolute revenue impact"
            accent
          />
          <Metric
            label="Auto-diagnostic rate"
            value={`${visibleAlerts.length ? Math.round((verified / visibleAlerts.length) * 100) : 100}%`}
            caption={`${verified} signals verified`}
          />
        </section>

        <section className="queue-head">
          <div>
            <p className="eyebrow">Prioritized queue</p>
            <h2>
              Telemetry anomalies <span>{visibleAlerts.length}</span>
            </h2>
          </div>
          <span className="queue-note">Ranked by financial impact</span>
        </section>
        <section className="queue">
          {!dashboard ? (
            <div className="loading">Loading telemetry...</div>
          ) : visibleAlerts.length === 0 ? (
            <div className="empty">
              <Check size={25} />
              <h3>All clear</h3>
              <p>There are no unresolved signals in this scope.</p>
            </div>
          ) : (
            visibleAlerts.map((item) => (
              <AlertCard
                key={item.alert.id}
                item={item}
                onOpen={() => openAlert(item)}
                onRemove={(e) => handleDismiss(item.alert.id, e)}
              />
            ))
          )}
        </section>
      </main>

      {selected && (
        <InvestigateModal
          item={selected}
          onClose={() => setSelected(null)}
          onDiagnose={startDiagnosis}
          onRemove={() => handleDismiss(selected.alert.id)}
        />
      )}
    </div>
  );
}

function Metric({ label, value, caption, accent }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong className={accent ? "accent" : ""}>{value}</strong>
      <small>{caption}</small>
    </div>
  );
}

function AlertCard({ item, onOpen, onRemove }) {
  const { alert } = item;
  const change = alert.pct_change == null ? "New signal" : `${alert.pct_change >= 0 ? "+" : ""}${(alert.pct_change * 100).toFixed(1)}%`;

  return (
    <article className="alert-card">
      <div className="card-top">
        <span className={`route ${item.route.toLowerCase()}`}>
          {routeLabel(item.route)}
        </span>
        <span className="severity-tag" style={{ fontSize: '0.75rem', fontWeight: 600, color: '#e53e3e', background: '#fff5f5', padding: '2px 8px', borderRadius: '4px' }}>
          HIGH
        </span>
      </div>
      <h3>{alert.kpi}</h3>
      <p className="context">
        {alert.category} <span>/</span> {alert.region} · Week {alert.week_start}
      </p>
      <div className="card-stats">
        <div>
          <small>Current / Baseline</small>
          <strong>{alert.current_fmt || `₹${(alert.current||0).toLocaleString("en-IN")}`} / {alert.baseline_fmt || `₹${(alert.baseline_mean||0).toLocaleString("en-IN")}`}</strong>
        </div>
        <div>
          <small>Movement</small>
          <strong className={alert.delta_inr < 0 ? "negative" : "positive"}>
            {change}
          </strong>
        </div>
        <div className="impact">
          <small>Business Impact</small>
          <strong>{alert.delta_fmt}</strong>
        </div>
      </div>
      <div className="card-actions" style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
        <button className="secondary-button" style={{ flex: 1, padding: '8px', borderRadius: '6px', fontSize: '0.85rem' }} onClick={onRemove}>
          Remove
        </button>
        <button className="investigate" style={{ flex: 2 }} onClick={onOpen}>
          Investigate <ArrowUpRight size={16} />
        </button>
      </div>
    </article>
  );
}

import KPIChart from "./components/KPIChart.jsx";

function InvestigateModal({ item, onClose, onDiagnose, onRemove }) {
  const { alert } = item;

  return (
    <div
      className="overlay"
      style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 1000 }}
      onMouseDown={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="investigate-modal" style={{ background: '#fff', borderRadius: '12px', width: '90%', maxWidth: '680px', padding: '24px', boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)', maxHeight: '90vh', overflowY: 'auto' }}>
        <div className="modal-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #eee', paddingBottom: '12px', marginBottom: '16px' }}>
          <div>
            <span style={{ fontSize: '0.8rem', color: '#718096', fontWeight: 600 }}>ALERT SNAPSHOT · {alert.id}</span>
            <h2 style={{ margin: '4px 0 0 0', fontSize: '1.4rem' }}>{alert.kpi}</h2>
            <p style={{ margin: '2px 0 0 0', color: '#4a5568', fontSize: '0.9rem' }}>
              {alert.category} · {alert.region} · Week {alert.week_start}
            </p>
          </div>
          <button className="icon-button" onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer' }}>
            <X size={20} />
          </button>
        </div>

        <div className="modal-stats-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', background: '#f7fafc', padding: '12px', borderRadius: '8px', marginBottom: '16px' }}>
          <div>
            <small style={{ color: '#718096', fontSize: '0.75rem', display: 'block' }}>Current / Baseline</small>
            <strong style={{ fontSize: '0.95rem' }}>{alert.current_fmt || `₹${(alert.current||0).toLocaleString("en-IN")}`} / {alert.baseline_fmt || `₹${(alert.baseline_mean||0).toLocaleString("en-IN")}`}</strong>
          </div>
          <div>
            <small style={{ color: '#718096', fontSize: '0.75rem', display: 'block' }}>Movement %</small>
            <strong className={alert.delta_inr < 0 ? "negative" : "positive"} style={{ fontSize: '0.95rem' }}>
              {alert.pct_fmt || `${((alert.pct_change||0)*100).toFixed(1)}%`}
            </strong>
          </div>
          <div>
            <small style={{ color: '#718096', fontSize: '0.75rem', display: 'block' }}>Business Impact</small>
            <strong className={alert.delta_inr < 0 ? "negative" : "positive"} style={{ fontSize: '0.95rem' }}>
              {alert.delta_fmt}
            </strong>
          </div>
        </div>

        <div className="modal-chart-box" style={{ marginBottom: '20px' }}>
          <h4 style={{ margin: '0 0 8px 0', fontSize: '0.9rem', color: '#4a5568' }}>Real Telemetry Historical Trend</h4>
          <KPIChart alert={alert} />
        </div>

        <div className="modal-actions" style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', borderTop: '1px solid #eee', paddingTop: '16px' }}>
          <button
            className="secondary-button"
            onClick={onRemove}
            style={{ padding: '10px 20px', borderRadius: '6px', cursor: 'pointer', border: '1px solid #cbd5e0', background: '#fff' }}
          >
            Remove
          </button>
          <button
            className="primary-button"
            onClick={onDiagnose}
            style={{ padding: '10px 28px', borderRadius: '6px', cursor: 'pointer', background: '#3182ce', color: '#fff', fontWeight: 'bold', border: 'none' }}
          >
            Diagnose
          </button>
        </div>
      </div>
    </div>
  );
}

function Evidence({ label, value }) {
  return (
    <div>
      <small>{label}</small>
      <strong>{value}</strong>
    </div>
  );
}

export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<LoginPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/investigate/:alertId" element={<InvestigationDetailPage />} />
      </Routes>
    </Router>
  );
}
