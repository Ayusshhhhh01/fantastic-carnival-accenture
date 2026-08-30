import { useEffect, useMemo, useState } from "react";
import { BrowserRouter as Router, Routes, Route, useNavigate } from "react-router-dom";
import { Activity, ArrowUpRight, Check, CircleAlert, RefreshCw, X, RotateCcw } from "lucide-react";
import { getDashboard, saveDecision, resetDemo } from "./api/index.js";
import LoginPage from "./pages/LoginPage.jsx";
import InvestigationDetailPage from "./pages/InvestigationDetailPage.jsx";
import KPIChart from "./components/KPIChart.jsx";

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
  return { RESOLVED: "Diagnosed", FAST_PATH: "Direct Match", UNRESOLVED_CONFLICT: "Conflict", ABSTAIN: "Low Evidence" }[route] || route;
}

function DashboardPage() {
  const params = new URLSearchParams(window.location.search);
  const initialPersona = params.get("persona") || "Category Manager";
  const navigate = useNavigate();

  const [persona, setPersona] = useState(initialPersona);
  const [dashboard, setDashboard] = useState(null);
  const [selected, setSelected] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [handled, setHandled] = useState({});
  const [toastMessage, setToastMessage] = useState("");

  async function loadDashboard(currentPersona = persona) {
    setBusy(true);
    setError("");
    try {
      setDashboard(await getDashboard(currentPersona));
    } catch (err) {
      setError(err.message || "Failed to connect to decision server");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    loadDashboard(persona);
  }, [persona]);

  const visibleAlerts = useMemo(() => {
    if (!dashboard || !dashboard.alerts) return [];
    const categories = PERSONAS[persona]?.categories;
    return dashboard.alerts.filter(
      (item) =>
        !handled[item.alert.id] &&
        (!categories || categories.includes(item.alert.category))
    );
  }, [dashboard, handled, persona]);

  async function handleDismiss(alertId, e) {
    if (e) e.stopPropagation();
    setHandled((current) => ({ ...current, [alertId]: "dismissed" }));
    if (selected?.alert?.id === alertId) {
      setSelected(null);
    }
    showToast("Signal removed from queue");
    try {
      await saveDecision(alertId, {
        decision: "dismissed",
        persona,
        feedback: "Dismissed from dashboard queue"
      });
    } catch (err) {
      // Background persistence error silent log
    }
  }

  async function handleResetDemo() {
    setBusy(true);
    try {
      await resetDemo();
      setHandled({});
      await loadDashboard(persona);
      showToast("Demo queue restored with initial signals");
    } catch (err) {
      setError("Failed to reset demo queue: " + err.message);
    } finally {
      setBusy(false);
    }
  }

  function showToast(msg) {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(""), 3000);
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
            <Activity size={15} /> Telemetry connected
          </span>
          <select value={persona} onChange={(event) => setPersona(event.target.value)}>
            <option>Category Manager</option>
            <option>CXO</option>
          </select>
          <button className="icon-button" title="Reset Demo Queue" onClick={handleResetDemo}>
            <RotateCcw size={17} />
          </button>
          <button className="icon-button" title="Refresh dashboard" onClick={() => loadDashboard(persona)}>
            <RefreshCw size={17} className={busy ? "spin" : ""} />
          </button>
        </div>
      </header>

      <main>
        <section className="intro">
          <div>
            <p className="eyebrow">{PERSONAS[persona]?.scope}</p>
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

        {/* STATE 3: API/DATA FAILURE STATE */}
        {error && (
          <div className="error-container margin-bottom-md">
            <CircleAlert size={20} color="#e53e3e" />
            <div className="error-text">
              <strong>Unable to load telemetry signals</strong>
              <p>{error}</p>
            </div>
            <button className="secondary-button margin-top-sm" onClick={() => loadDashboard(persona)}>
              Retry Loading
            </button>
          </div>
        )}

        {toastMessage && (
          <div className="toast-notification">
            <Check size={16} />
            {toastMessage}
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
            <p className="eyebrow">Prioritized queue ({persona} Lens)</p>
            <h2>
              Telemetry anomalies <span>{visibleAlerts.length}</span>
            </h2>
          </div>
          <span className="queue-note">
            {persona === "CXO" ? "Ranked by financial impact & strategic risk" : "Ranked by operational velocity & driver impact"}
          </span>
        </section>

        <section className="queue">
          {busy && !dashboard ? (
            <div className="loading">Loading telemetry...</div>
          ) : error ? (
            null
          ) : visibleAlerts.length === 0 ? (
            /* STATE 2: ALL ALERTS HAVE BEEN HANDLED STATE */
            <div className="empty-state-box">
              <Check size={32} color="#38a169" />
              <h3>You're all caught up</h3>
              <p>All active signals in your current scope have been reviewed and handled.</p>
              <button className="secondary-button margin-top-sm" onClick={handleResetDemo}>
                <RotateCcw size={15} /> Reset Demo Queue
              </button>
            </div>
          ) : (
            /* STATE 1: ACTIVE ALERTS EXIST STATE */
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
        <span className="kpi-tag">{alert.kpi}</span>
      </div>
      <h3>{alert.kpi}</h3>
      <p className="context">
        {alert.category} <span>/</span> {alert.region} · Week {alert.week_start}
      </p>
      <div className="card-stats">
        <div>
          <small>Baseline</small>
          <strong>{alert.baseline_fmt || `₹${(alert.baseline_mean||0).toLocaleString("en-IN")}`}</strong>
        </div>
        <div>
          <small>Current</small>
          <strong>{alert.current_fmt || `₹${(alert.current||0).toLocaleString("en-IN")}`}</strong>
        </div>
        <div className="impact">
          <small>Variance</small>
          <strong className={alert.delta_inr < 0 ? "negative" : "positive"}>
            {change}
          </strong>
        </div>
      </div>
      <div className="card-actions-row">
        <button className="secondary-button remove-btn" onClick={onRemove}>
          Remove
        </button>
        <button className="investigate-btn" onClick={onOpen}>
          Investigate <ArrowUpRight size={16} />
        </button>
      </div>
    </article>
  );
}

function InvestigateModal({ item, onClose, onDiagnose, onRemove }) {
  const { alert } = item;

  useEffect(() => {
    function handleKeyDown(e) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  return (
    <div
      className="modal-overlay"
      onMouseDown={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="investigate-modal-box">
        <div className="modal-header-row">
          <div>
            <span className="modal-snapshot-label">INVESTIGATION PREVIEW · {alert.id}</span>
            <h2>{alert.kpi} Anomaly</h2>
            <p className="modal-subtitle-text">
              {alert.category} · {alert.region} · Week {alert.week_start}
            </p>
          </div>
          <button className="close-modal-btn" onClick={onClose} title="Close preview (Esc)">
            <X size={18} />
          </button>
        </div>

        <div className="horizontal-kpi-summary">
          <div className="summary-box">
            <small>BASELINE</small>
            <strong>{alert.baseline_fmt || `₹${(alert.baseline_mean||0).toLocaleString("en-IN")}`}</strong>
          </div>
          <div className="summary-box">
            <small>CURRENT</small>
            <strong>{alert.current_fmt || `₹${(alert.current||0).toLocaleString("en-IN")}`}</strong>
          </div>
          <div className="summary-box">
            <small>VARIANCE</small>
            <strong className={alert.delta_inr < 0 ? "negative" : "positive"}>
              {alert.pct_fmt || `${((alert.pct_change||0)*100).toFixed(1)}%`} ({alert.delta_fmt})
            </strong>
          </div>
        </div>

        <div className="modal-chart-preview">
          <h4>Telemetry Trend Preview</h4>
          <KPIChart alert={alert} />
        </div>

        <div className="modal-actions-footer">
          <button className="secondary-button" onClick={onRemove}>
            Remove Signal
          </button>
          <button className="primary-button diagnose-cta" onClick={onDiagnose}>
            Diagnose <ArrowUpRight size={16} />
          </button>
        </div>
      </div>
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
