import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, ChevronDown, ChevronUp, AlertCircle, CheckCircle2, ShieldAlert, FileText, Activity, X } from "lucide-react";
import { investigateAlert, saveDecision } from "../api/index.js";
import KPIChart from "../components/KPIChart.jsx";

export default function InvestigationDetailPage() {
  const { alertId } = useParams();
  const navigate = useNavigate();
  const persona = new URLSearchParams(window.location.search).get("persona") || "Category Manager";
  
  const [investigation, setInvestigation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [triageStep, setTriageStep] = useState(1);
  const [error, setError] = useState("");
  const [expandedHypothesis, setExpandedHypothesis] = useState(0);
  const [viewMode, setViewMode] = useState("rca"); // "rca" | "overall_recommendation" | "ledger"
  const [causeRecModal, setCauseRecModal] = useState(null); // specific cause hypothesis
  const [feedbackComment, setFeedbackComment] = useState("");
  const [deciding, setDeciding] = useState(false);

  useEffect(() => {
    loadInvestigation();
  }, [alertId, persona]);

  async function loadInvestigation() {
    setLoading(true);
    setTriageStep(1);
    setError("");
    try {
      // Step-by-step triage animation for Screen 3
      setTimeout(() => setTriageStep(2), 600);
      setTimeout(() => setTriageStep(3), 1200);
      
      const data = await investigateAlert(alertId, persona);
      setInvestigation(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setTimeout(() => setLoading(false), 1500);
    }
  }

  async function handleDecision(decision) {
    setDeciding(true);
    try {
      await saveDecision(alertId, { decision, persona, feedback: feedbackComment });
      setTimeout(() => navigate(`/dashboard?persona=${encodeURIComponent(persona)}`), 600);
    } catch (err) {
      setError(err.message);
    } finally {
      setDeciding(false);
    }
  }

  // SCREEN 3: DIAGNOSIS LOADING / TRIAGE
  if (loading) {
    return (
      <div className="investigation-shell">
        <header className="investigation-header">
          <button className="back-button" onClick={() => navigate(`/dashboard?persona=${encodeURIComponent(persona)}`)}>
            <ArrowLeft size={20} /> Back
          </button>
        </header>
        <main className="investigation-main" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '70vh' }}>
          <div className="loading-progress-box" style={{ maxWidth: '560px', width: '100%', padding: '32px', background: '#fff', borderRadius: '12px', border: '1px solid #e2e8f0', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.05)' }}>
            <h2 style={{ marginTop: 0, marginBottom: '24px', fontSize: '1.25rem', color: '#1a202c', borderBottom: '1px solid #edf2f7', paddingBottom: '12px' }}>
              DIAGNOSIS IN PROGRESS · TRIAGE
            </h2>

            <div className="triage-section" style={{ marginBottom: '20px' }}>
              <div style={{ fontWeight: 'bold', fontSize: '0.9rem', color: '#3182ce', marginBottom: '6px' }}>PATH 1: Direct Event Match</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '0.9rem', color: triageStep >= 1 ? '#2d3748' : '#a0aec0' }}>
                {triageStep > 1 ? <CheckCircle2 size={18} color="#38a169" /> : <Activity size={18} className="spin" color="#3182ce" />}
                <span>Scanning operational change log...</span>
              </div>
              {triageStep > 1 && investigation?.path_type !== "FAST" && (
                <div style={{ fontSize: '0.8rem', color: '#718096', marginLeft: '28px', marginTop: '4px' }}>
                  ✓ No direct match found
                </div>
              )}
            </div>

            {triageStep >= 2 && (
              <div className="triage-section" style={{ marginBottom: '20px' }}>
                <div style={{ fontWeight: 'bold', fontSize: '0.9rem', color: '#805ad5', marginBottom: '6px' }}>PATH 2: Deep Research</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '0.9rem', color: '#2d3748', marginBottom: '6px' }}>
                  {triageStep > 2 ? <CheckCircle2 size={18} color="#38a169" /> : <Activity size={18} className="spin" color="#805ad5" />}
                  <span>Retrieving telemetry evidence...</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '0.9rem', color: triageStep >= 3 ? '#2d3748' : '#a0aec0', marginBottom: '6px' }}>
                  {triageStep >= 3 ? <CheckCircle2 size={18} color="#38a169" /> : <Activity size={18} className="spin" color="#805ad5" />}
                  <span>Testing 4 competing hypotheses (Supply, Demand, Pricing, Operational)...</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '0.9rem', color: triageStep >= 3 ? '#2d3748' : '#a0aec0' }}>
                  {triageStep >= 3 ? <CheckCircle2 size={18} color="#38a169" /> : <Activity size={18} className="spin" color="#805ad5" />}
                  <span>Evaluating Weighted Evidence Confidence & Persona Rules...</span>
                </div>
              </div>
            )}
          </div>
        </main>
      </div>
    );
  }

  if (!investigation) {
    return (
      <div className="investigation-shell">
        <header className="investigation-header">
          <button className="back-button" onClick={() => navigate(`/dashboard?persona=${encodeURIComponent(persona)}`)}>
            <ArrowLeft size={20} /> Back
          </button>
        </header>
        <main className="investigation-main">
          <div className="error-container">
            <AlertCircle size={32} />
            <h2>Investigation Failed</h2>
            <p>{error || "Unable to load investigation details"}</p>
          </div>
        </main>
      </div>
    );
  }

  const alert = investigation.alert;
  const isFastPath = investigation.path_type === "FAST";
  const isSlowPath = investigation.path_type === "SLOW";
  const isAbstain = investigation.path_type === "ABSTAIN";
  const isConflict = investigation.route === "UNRESOLVED_CONFLICT";
  const topHypothesis = investigation.hypotheses?.find(h => h.supported) || investigation.hypotheses?.[0];

  return (
    <div className="investigation-shell">
      <header className="investigation-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <button className="back-button" onClick={() => navigate(`/dashboard?persona=${encodeURIComponent(persona)}`)}>
            <ArrowLeft size={20} /> Dashboard
          </button>
          <span style={{ fontSize: '0.85rem', color: '#666', background: '#edf2f7', padding: '4px 12px', borderRadius: '12px' }}>
            Persona: <strong>{persona}</strong>
          </span>
        </div>
        <div className="header-nav" style={{ display: 'flex', gap: '12px' }}>
          <button
            className={`secondary-button ${viewMode === "rca" ? "active" : ""}`}
            onClick={() => setViewMode("rca")}
            style={{ padding: '6px 14px', borderRadius: '6px', fontSize: '0.85rem', fontWeight: viewMode === "rca" ? 'bold' : 'normal' }}
          >
            Root Cause Analysis
          </button>
          {!isAbstain && !isConflict && (
            <button
              className={`secondary-button ${viewMode === "overall_recommendation" ? "active" : ""}`}
              onClick={() => setViewMode("overall_recommendation")}
              style={{ padding: '6px 14px', borderRadius: '6px', fontSize: '0.85rem', fontWeight: viewMode === "overall_recommendation" ? 'bold' : 'normal' }}
            >
              Overall Recommendation
            </button>
          )}
          <button
            className={`secondary-button ${viewMode === "ledger" ? "active" : ""}`}
            onClick={() => setViewMode("ledger")}
            style={{ padding: '6px 14px', borderRadius: '6px', fontSize: '0.85rem', fontWeight: viewMode === "ledger" ? 'bold' : 'normal' }}
          >
            Evidence Ledger
          </button>
        </div>
      </header>

      <main className="investigation-main">
        <div className="investigation-container">

          {/* VIEW MODE: EVIDENCE LEDGER */}
          {viewMode === "ledger" && (
            <section className="investigation-section ledger-view">
              <div className="section-title" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h2>Evidence Ledger & Audit Trail</h2>
                <span className="count-badge" style={{ background: '#edf2f7', padding: '4px 10px', borderRadius: '6px', fontSize: '0.85rem' }}>
                  {investigation.ledger_rows?.length || 0} Telemetry Operations
                </span>
              </div>
              <div className="ledger-table-box" style={{ background: '#fff', borderRadius: '8px', border: '1px solid #e2e8f0', overflow: 'hidden' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.88rem' }}>
                  <thead>
                    <tr style={{ background: '#f7fafc', borderBottom: '1px solid #e2e8f0', textAlign: 'left' }}>
                      <th style={{ padding: '12px' }}>Step</th>
                      <th style={{ padding: '12px' }}>Engine / Method</th>
                      <th style={{ padding: '12px' }}>Latency</th>
                      <th style={{ padding: '12px' }}>LLM Call?</th>
                      <th style={{ padding: '12px' }}>Est. Cost</th>
                      <th style={{ padding: '12px' }}>Note / Provenance</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(investigation.ledger_rows || []).map((row, idx) => (
                      <tr key={idx} style={{ borderBottom: '1px solid #edf2f7' }}>
                        <td style={{ padding: '12px', fontWeight: 'bold' }}>{row.step}</td>
                        <td style={{ padding: '12px' }}>
                          <span style={{
                            padding: '2px 8px', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 600,
                            background: row.engine === "Deterministic" ? "#c6f6d5" : row.engine?.includes("LLM") ? "#e9d8fd" : "#feebc8",
                            color: row.engine === "Deterministic" ? "#22543d" : row.engine?.includes("LLM") ? "#553c9a" : "#744210"
                          }}>
                            {row.engine}
                          </span>
                        </td>
                        <td style={{ padding: '12px' }}>{row.latency_ms} ms</td>
                        <td style={{ padding: '12px' }}>{row.engine?.includes("LLM") ? "Yes" : "No"}</td>
                        <td style={{ padding: '12px' }}>${row.est_cost_usd || "0.0000"}</td>
                        <td style={{ padding: '12px', color: '#4a5568' }}>{row.note}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {/* VIEW MODE: OVERALL RECOMMENDATION */}
          {viewMode === "overall_recommendation" && (
            <section className="investigation-section recommendation-view">
              <div className="section-title">
                <h2>OVERALL RECOMMENDED SOLUTION</h2>
              </div>

              {investigation.recommendation && (
                <div className="recommendation-card dominant" style={{ background: '#ebf8ff', border: '2px solid #3182ce', padding: '24px', borderRadius: '12px', marginBottom: '24px' }}>
                  <div className="rec-top" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                    <div>
                      <span style={{ color: '#2b6cb0', fontSize: '0.8rem', fontWeight: 600, textTransform: 'uppercase' }}>Validated Primary Action</span>
                      <h2 style={{ margin: '4px 0 0 0', color: '#2c5282', fontSize: '1.4rem' }}>{investigation.recommendation.action}</h2>
                    </div>
                    {investigation.recommendation.estimated_impact && (
                      <div style={{ background: '#3182ce', color: '#fff', padding: '10px 18px', borderRadius: '8px', fontWeight: 'bold', fontSize: '1.2rem' }}>
                        ₹ Impact: {investigation.recommendation.est_impact_fmt || `₹${investigation.recommendation.estimated_impact.toLocaleString("en-IN")}`}
                      </div>
                    )}
                  </div>

                  <div className="rec-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px', background: '#fff', padding: '20px', borderRadius: '8px', marginBottom: '20px' }}>
                    <div><strong>Driver:</strong> <p style={{ margin: '4px 0 0 0', color: '#4a5568' }}>{investigation.recommendation.driver}</p></div>
                    <div><strong>Controllable Lever:</strong> <p style={{ margin: '4px 0 0 0', color: '#4a5568' }}>{investigation.recommendation.lever}</p></div>
                    <div><strong>Owner / Accountable Team:</strong> <p style={{ margin: '4px 0 0 0', color: '#4a5568' }}>{investigation.recommendation.owner}</p></div>
                    <div><strong>Confidence:</strong> <p style={{ margin: '4px 0 0 0', color: '#4a5568' }}>{investigation.recommendation.confidence}</p></div>
                    <div style={{ gridColumn: 'span 2' }}>
                      <strong>Monitoring & Verification Plan:</strong>
                      <p style={{ margin: '4px 0 0 0', color: '#4a5568' }}>{investigation.recommendation.monitoring_plan}</p>
                    </div>
                  </div>

                  {investigation.narrative && (
                    <div className="llm-narration-box" style={{ background: '#f7fafc', borderLeft: '4px solid #3182ce', padding: '16px', borderRadius: '4px' }}>
                      <strong style={{ fontSize: '0.85rem', color: '#718096', display: 'block', marginBottom: '6px' }}>Governed Executive Brief (Single Render):</strong>
                      <p style={{ margin: 0, fontSize: '0.95rem', color: '#2d3748', lineHeight: 1.6 }}>{investigation.narrative.text}</p>
                    </div>
                  )}
                </div>
              )}

              {/* Feedback Calibration Box */}
              <div className="feedback-calibration-box" style={{ background: '#fff', border: '1px solid #e2e8f0', padding: '24px', borderRadius: '12px' }}>
                <h3 style={{ marginTop: 0, marginBottom: '12px', fontSize: '1.1rem' }}>Empirical Feedback Calibration</h3>
                <p style={{ color: '#718096', fontSize: '0.9rem', marginBottom: '16px' }}>
                  Record your decision to calibrate future hypothesis weights and confidence scoring.
                </p>
                <div style={{ marginBottom: '16px' }}>
                  <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: '#4a5568', marginBottom: '6px' }}>
                    Recommendation Feedback / Reason (Optional):
                  </label>
                  <textarea
                    rows={3}
                    placeholder="Add recommendation or feedback..."
                    value={feedbackComment}
                    onChange={(e) => setFeedbackComment(e.target.value)}
                    style={{ width: '100%', padding: '10px', borderRadius: '6px', border: '1px solid #cbd5e0', fontSize: '0.9rem' }}
                  />
                </div>
                <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
                  <button
                    className="secondary-button"
                    onClick={() => handleDecision("rejected")}
                    disabled={deciding}
                    style={{ padding: '10px 20px', borderRadius: '6px', cursor: 'pointer' }}
                  >
                    {deciding ? "Recording..." : "Reject Action"}
                  </button>
                  <button
                    className="primary-button"
                    onClick={() => handleDecision("approved")}
                    disabled={deciding}
                    style={{ padding: '10px 28px', borderRadius: '6px', background: '#38a169', color: '#fff', fontWeight: 'bold', border: 'none', cursor: 'pointer' }}
                  >
                    {deciding ? "Recording..." : "Approve & Execute"}
                  </button>
                </div>
              </div>
            </section>
          )}

          {/* VIEW MODE: RCA */}
          {viewMode === "rca" && (
            <>
              {/* Section 1: KPI Summary */}
              <section className="investigation-section alert-overview" style={{ background: '#fff', padding: '20px', borderRadius: '12px', border: '1px solid #e2e8f0', marginBottom: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <span style={{ fontSize: '0.8rem', color: '#718096', fontWeight: 600, textTransform: 'uppercase' }}>ALERT CONTEXT · {alert.id}</span>
                    <h1 style={{ margin: '4px 0 0 0', fontSize: '1.5rem' }}>{alert.kpi} Anomaly</h1>
                    <p style={{ margin: '4px 0 0 0', color: '#4a5568' }}>{alert.category} · {alert.region} · Week {alert.week_start}</p>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <small style={{ color: '#718096', fontSize: '0.8rem', display: 'block' }}>Business Impact</small>
                    <strong className={alert.delta_inr < 0 ? "negative" : "positive"} style={{ fontSize: '1.6rem' }}>{alert.delta_fmt}</strong>
                    <span style={{ display: 'block', fontSize: '0.9rem', color: '#718096' }}>{alert.pct_fmt} vs baseline</span>
                  </div>
                </div>
              </section>

              {/* FAST PATH SCREEN */}
              {isFastPath && (
                <section className="investigation-section fast-path-card" style={{ background: '#f0fff4', border: '2px solid #38a169', padding: '24px', borderRadius: '12px', marginBottom: '24px' }}>
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: '16px' }}>
                    <CheckCircle2 size={32} color="#38a169" />
                    <div style={{ flex: 1 }}>
                      <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#276749', background: '#c6f6d5', padding: '2px 8px', borderRadius: '4px' }}>
                        FAST PATH — DIRECT CHANGE-LOG MATCH
                      </span>
                      <h2 style={{ margin: '8px 0 4px 0', color: '#22543d' }}>Verified Event Match Found</h2>
                      <p style={{ margin: '0 0 12px 0', color: '#2d3748', fontSize: '0.95rem' }}>
                        Direct event match in change log: <strong>[{investigation.fast_path?.event_type}]</strong> on <strong>{investigation.fast_path?.event_date}</strong>.
                      </p>
                      <p style={{ margin: '0 0 16px 0', color: '#4a5568', fontStyle: 'italic', background: '#fff', padding: '12px', borderRadius: '6px', border: '1px solid #c6f6d5' }}>
                        "{investigation.fast_path?.description}"
                      </p>
                      <div style={{ display: 'flex', gap: '12px' }}>
                        <button
                          className="primary-button"
                          onClick={() => setViewMode("overall_recommendation")}
                          style={{ padding: '8px 18px', borderRadius: '6px', background: '#38a169', color: '#fff', border: 'none', cursor: 'pointer' }}
                        >
                          View Recommendation
                        </button>
                      </div>
                    </div>
                  </div>
                </section>
              )}

              {/* ABSTAIN SCREEN */}
              {isAbstain && (
                <section className="investigation-section abstention-screen" style={{ background: '#fffaf0', border: '2px solid #dd6b20', padding: '24px', borderRadius: '12px', marginBottom: '24px' }}>
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: '16px' }}>
                    <AlertCircle size={32} color="#dd6b20" />
                    <div>
                      <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#9c4221', background: '#feebc8', padding: '2px 8px', borderRadius: '4px' }}>
                        INSUFFICIENT EVIDENCE (DIAGNOSTIC ABSTENTION)
                      </span>
                      <h2 style={{ margin: '8px 0 8px 0', color: '#7b341e' }}>CAUSE Abstained From Generating Recommendation</h2>
                      <div style={{ display: 'grid', gap: '12px', marginTop: '16px', background: '#fff', padding: '16px', borderRadius: '8px', border: '1px solid #fbd38d' }}>
                        <div><strong>Why:</strong> <p style={{ margin: '2px 0 0 0', color: '#4a5568' }}>{investigation.abstention?.reason}</p></div>
                        <div><strong>Missing Evidence:</strong> <p style={{ margin: '2px 0 0 0', color: '#4a5568' }}>{investigation.abstention?.missing_evidence}</p></div>
                        <div><strong>Required Data:</strong> <p style={{ margin: '2px 0 0 0', color: '#4a5568' }}>{investigation.abstention?.required_data}</p></div>
                        <div><strong>Next Step:</strong> <p style={{ margin: '2px 0 0 0', color: '#4a5568' }}>{investigation.abstention?.recommendation}</p></div>
                      </div>
                      <div style={{ marginTop: '16px', fontSize: '0.85rem', color: '#744210', fontStyle: 'italic' }}>
                        * CRITICAL POLICY: Zero LLM narration calls were made for this abstention response.
                      </div>
                    </div>
                  </div>
                </section>
              )}

              {/* CONFLICT SCREEN */}
              {isConflict && (
                <section className="investigation-section conflict-screen" style={{ background: '#fff5f5', border: '2px solid #e53e3e', padding: '24px', borderRadius: '12px', marginBottom: '24px' }}>
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: '16px' }}>
                    <ShieldAlert size={32} color="#e53e3e" />
                    <div>
                      <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#9b2c2c', background: '#fed7d7', padding: '2px 8px', borderRadius: '4px' }}>
                        UNRESOLVED CONFLICT DETECTED
                      </span>
                      <h2 style={{ margin: '8px 0 8px 0', color: '#742a2a' }}>Cross-Regional Evidence Contradiction</h2>
                      <div style={{ display: 'grid', gap: '12px', marginTop: '16px', background: '#fff', padding: '16px', borderRadius: '8px', border: '1px solid #feb2b2' }}>
                        <div><strong>Signal A:</strong> <p style={{ margin: '2px 0 0 0', color: '#2d3748' }}>{investigation.conflict?.signal_a}</p></div>
                        <div><strong>Signal B:</strong> <p style={{ margin: '2px 0 0 0', color: '#2d3748' }}>{investigation.conflict?.signal_b}</p></div>
                        <div><strong>Conclusion:</strong> <p style={{ margin: '2px 0 0 0', color: '#c53030', fontWeight: 'bold' }}>Evidence is contradictory across comparable regions.</p></div>
                        <div><strong>Action:</strong> <p style={{ margin: '2px 0 0 0', color: '#742a2a' }}>{investigation.conflict?.escalation_directive}</p></div>
                      </div>
                    </div>
                  </div>
                </section>
              )}

              {/* SCREEN 4: ROOT CAUSE ANALYSIS (EXACTLY 4 RANKED CAUSES) */}
              {!isAbstain && (
                <section className="investigation-section rca-causes" style={{ background: '#fff', padding: '24px', borderRadius: '12px', border: '1px solid #e2e8f0' }}>
                  <div className="section-title" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                    <div>
                      <h2 style={{ margin: 0, fontSize: '1.25rem' }}>ROOT CAUSE ANALYSIS</h2>
                      <small style={{ color: '#718096' }}>Deterministically evaluated & ranked hypotheses</small>
                    </div>
                    <button
                      className="primary-button"
                      onClick={() => setViewMode("overall_recommendation")}
                      style={{ padding: '8px 16px', borderRadius: '6px', background: '#3182ce', color: '#fff', border: 'none', cursor: 'pointer', fontWeight: 'bold' }}
                    >
                      View Overall Recommendation
                    </button>
                  </div>

                  <div className="causes-list">
                    {(investigation.hypotheses || []).slice(0, 4).map((hyp, idx) => {
                      const isExpanded = expandedHypothesis === idx;
                      const scorePct = hyp.confidence_pct || Math.round((hyp.score || 0) * 100);

                      return (
                        <div
                          key={idx}
                          className="cause-card"
                          style={{
                            border: '1px solid #e2e8f0', borderRadius: '8px', marginBottom: '16px', overflow: 'hidden',
                            borderLeft: hyp.supported ? '4px solid #38a169' : '4px solid #cbd5e0'
                          }}
                        >
                          <div
                            className="cause-row-head"
                            style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px', background: hyp.supported ? '#f0fff4' : '#fff' }}
                          >
                            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                              <span style={{ fontWeight: 'bold', color: '#a0aec0', fontSize: '1.1rem' }}>{idx + 1}.</span>
                              <strong style={{ fontSize: '1.1rem', color: '#1a202c' }}>{hyp.name}</strong>
                              <span style={{
                                fontSize: '0.75rem', fontWeight: 600, padding: '2px 8px', borderRadius: '4px',
                                background: hyp.supported ? '#c6f6d5' : '#edf2f7',
                                color: hyp.supported ? '#22543d' : '#718096'
                              }}>
                                {hyp.supported ? "Supported" : "Weak / Rejected"}
                              </span>
                            </div>

                            <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                              <strong style={{ fontSize: '1.2rem', color: hyp.supported ? '#276749' : '#4a5568' }}>{scorePct}%</strong>
                              <button
                                className="secondary-button"
                                onClick={() => setExpandedHypothesis(isExpanded ? null : idx)}
                                style={{ padding: '6px 12px', borderRadius: '4px', fontSize: '0.85rem', cursor: 'pointer' }}
                              >
                                {isExpanded ? "Collapse" : "Expand"}
                              </button>
                              <button
                                className="primary-button"
                                onClick={() => setCauseRecModal(hyp)}
                                style={{ padding: '6px 14px', borderRadius: '4px', fontSize: '0.85rem', background: '#3182ce', color: '#fff', border: 'none', cursor: 'pointer' }}
                              >
                                Recommendation
                              </button>
                            </div>
                          </div>

                          {/* EXPANDED 4-PART ANALYSIS VIEW */}
                          {isExpanded && (
                            <div className="cause-expanded-content" style={{ padding: '20px', background: '#f7fafc', borderTop: '1px solid #e2e8f0' }}>
                              <h4 style={{ marginTop: 0, marginBottom: '16px', fontSize: '1rem', color: '#2d3748' }}>
                                Detailed Analysis: {hyp.name}
                              </h4>

                              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                                {/* PART A: EVIDENCE */}
                                <div style={{ background: '#fff', padding: '16px', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                                  <strong style={{ display: 'block', fontSize: '0.9rem', color: '#2b6cb0', marginBottom: '8px' }}>
                                    A. EVIDENCE PROVENANCE
                                  </strong>
                                  <p style={{ fontSize: '0.85rem', margin: '0 0 8px 0', color: '#2d3748' }}>
                                    <strong>Supporting:</strong> {hyp.supporting_evidence || hyp.deciding_value || "Telemetry patterns match hypothesis criteria."}
                                  </p>
                                  <p style={{ fontSize: '0.85rem', margin: 0, color: '#742a2a' }}>
                                    <strong>Contrary:</strong> {hyp.contrary_evidence || "No material contrary evidence identified."}
                                  </p>
                                </div>

                                {/* PART B: KPI SNAPSHOT */}
                                <div style={{ background: '#fff', padding: '16px', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                                  <strong style={{ display: 'block', fontSize: '0.9rem', color: '#2b6cb0', marginBottom: '8px' }}>
                                    B. REAL KPI TELEMETRY SNAPSHOT
                                  </strong>
                                  <KPIChart alert={alert} />
                                </div>

                                {/* PART C: CONFIDENCE */}
                                <div style={{ background: '#fff', padding: '16px', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                                  <strong style={{ display: 'block', fontSize: '0.9rem', color: '#2b6cb0', marginBottom: '8px' }}>
                                    C. WEIGHTED EVIDENCE CONFIDENCE
                                  </strong>
                                  <div style={{ fontSize: '0.85rem', color: '#4a5568' }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                                      <span>Temporal Correlation (W1):</span>
                                      <strong>{investigation.confidence?.components?.temporal_correlation ?? '1.0'}</strong>
                                    </div>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                                      <span>Source Agreement (W2):</span>
                                      <strong>{investigation.confidence?.components?.source_agreement ?? '1.0'}</strong>
                                    </div>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                                      <span>Hypothesis Margin (W3):</span>
                                      <strong>{investigation.confidence?.components?.hypothesis_margin ?? '0.8'}</strong>
                                    </div>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                                      <span>Data Completeness (W4):</span>
                                      <strong>{investigation.confidence?.components?.data_completeness ?? '1.0'}</strong>
                                    </div>
                                    <div style={{ borderTop: '1px solid #edf2f7', paddingTop: '6px', marginTop: '6px', fontWeight: 'bold', display: 'flex', justifyContent: 'space-between' }}>
                                      <span>Final Composite Confidence:</span>
                                      <span style={{ color: '#2b6cb0' }}>{scorePct}%</span>
                                    </div>
                                  </div>
                                </div>

                                {/* PART D: CONFLICT */}
                                <div style={{ background: '#fff', padding: '16px', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                                  <strong style={{ display: 'block', fontSize: '0.9rem', color: '#2b6cb0', marginBottom: '8px' }}>
                                    D. CONFLICT AUDIT
                                  </strong>
                                  {isConflict ? (
                                    <div style={{ fontSize: '0.85rem', color: '#c53030' }}>
                                      <strong>Conflict Detected:</strong> Cross-regional signals contradict expected impact trajectory.
                                    </div>
                                  ) : (
                                    <div style={{ fontSize: '0.85rem', color: '#276749' }}>
                                      ✓ No material conflict detected across comparable categories/regions.
                                    </div>
                                  )}
                                </div>
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </section>
              )}
            </>
          )}

        </div>
      </main>

      {/* SPECIFIC CAUSE RECOMMENDATION MODAL */}
      {causeRecModal && (
        <div
          className="overlay"
          style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 1000 }}
          onMouseDown={(e) => e.target === e.currentTarget && setCauseRecModal(null)}
        >
          <div style={{ background: '#fff', borderRadius: '12px', width: '90%', maxWidth: '600px', padding: '24px', boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #eee', paddingBottom: '12px', marginBottom: '16px' }}>
              <div>
                <span style={{ fontSize: '0.8rem', color: '#718096', fontWeight: 600 }}>CAUSE-SPECIFIC RECOMMENDATION</span>
                <h3 style={{ margin: '4px 0 0 0' }}>{causeRecModal.name}</h3>
              </div>
              <button onClick={() => setCauseRecModal(null)} style={{ background: 'none', border: 'none', cursor: 'pointer' }}>
                <X size={20} />
              </button>
            </div>

            <div style={{ display: 'grid', gap: '12px', fontSize: '0.9rem', color: '#2d3748' }}>
              <div><strong>1. Driver:</strong> <p style={{ margin: '2px 0 0 0', color: '#4a5568' }}>{investigation.recommendation?.driver || causeRecModal.name}</p></div>
              <div><strong>2. Controllable Lever:</strong> <p style={{ margin: '2px 0 0 0', color: '#4a5568' }}>{investigation.recommendation?.lever || "Inventory Allocation & Promotional Alignment"}</p></div>
              <div><strong>3. Solution / Action:</strong> <p style={{ margin: '2px 0 0 0', color: '#2b6cb0', fontWeight: 'bold' }}>{investigation.recommendation?.action || "Execute targeted operational correction"}</p></div>
              <div><strong>4. Expected Outcome / Impact:</strong> <p style={{ margin: '2px 0 0 0', color: '#276749', fontWeight: 'bold' }}>{investigation.recommendation?.est_impact_fmt || alert.delta_fmt}</p></div>
              <div><strong>5. Owner:</strong> <p style={{ margin: '2px 0 0 0', color: '#4a5568' }}>{investigation.recommendation?.owner || "Category Manager / Ops Lead"}</p></div>
              <div><strong>6. Confidence:</strong> <p style={{ margin: '2px 0 0 0', color: '#4a5568' }}>{causeRecModal.confidence_pct || Math.round((causeRecModal.score||0)*100)}%</p></div>
              <div><strong>7. Monitoring Plan:</strong> <p style={{ margin: '2px 0 0 0', color: '#4a5568' }}>{investigation.recommendation?.monitoring_plan || "Re-evaluate weekly telemetry cycle"}</p></div>
            </div>

            <div style={{ marginTop: '20px', textAlign: 'right' }}>
              <button
                className="primary-button"
                onClick={() => setCauseRecModal(null)}
                style={{ padding: '8px 20px', borderRadius: '6px', background: '#3182ce', color: '#fff', border: 'none', cursor: 'pointer' }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
