import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, ChevronDown, ChevronUp, AlertCircle, CheckCircle2, ShieldAlert, FileText, Activity } from "lucide-react";
import { investigateAlert, saveDecision } from "../api/index.js";
import KPIChart from "../components/KPIChart.jsx";

export default function InvestigationDetailPage() {
  const { alertId } = useParams();
  const navigate = useNavigate();
  const persona = new URLSearchParams(window.location.search).get("persona") || "Category Manager";
  
  const [investigation, setInvestigation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [expandedHypothesis, setExpandedHypothesis] = useState(0);
  const [deciding, setDeciding] = useState(false);

  useEffect(() => {
    loadInvestigation();
  }, [alertId, persona]);

  async function loadInvestigation() {
    setLoading(true);
    setError("");
    try {
      const data = await investigateAlert(alertId, persona);
      setInvestigation(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleDecision(decision) {
    setDeciding(true);
    try {
      await saveDecision(alertId, { decision, persona, feedback: "" });
      setTimeout(() => navigate(`/dashboard?persona=${encodeURIComponent(persona)}`), 500);
    } catch (err) {
      setError(err.message);
    } finally {
      setDeciding(false);
    }
  }

  if (loading) {
    return (
      <div className="investigation-shell">
        <header className="investigation-header">
          <button className="back-button" onClick={() => navigate(`/dashboard?persona=${encodeURIComponent(persona)}`)}>
            <ArrowLeft size={20} /> Back
          </button>
        </header>
        <main className="investigation-main">
          <div className="loading-progress-box" style={{ maxWidth: '600px', margin: '40px auto', padding: '24px', background: '#fff', borderRadius: '8px', border: '1px solid #e1ddd6' }}>
            <h3 style={{ marginTop: 0, marginBottom: '16px', fontSize: '1.1rem', color: '#222' }}>CAUSE Causal Pipeline Progress</h3>
            <div className="progress-step" style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px', color: '#44735a' }}>
              <CheckCircle2 size={18} />
              <span>PATH 1 · DIRECT EVENT MATCH — Scanning operational change log...</span>
            </div>
            <div className="progress-step" style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px', color: '#44735a' }}>
              <CheckCircle2 size={18} />
              <span>PATH 2 · DEEP ANALYSIS — Multi-Source Evidence Retrieval...</span>
            </div>
            <div className="progress-step" style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px', color: '#44735a' }}>
              <CheckCircle2 size={18} />
              <span>Testing 4 Competing Hypotheses & Falsification Matrix...</span>
            </div>
            <div className="progress-step" style={{ display: 'flex', alignItems: 'center', gap: '10px', color: '#777' }}>
              <Activity size={18} className="spin" />
              <span>Weighted Evidence Confidence & Persona Security Gate...</span>
            </div>
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

  return (
    <div className="investigation-shell">
      <header className="investigation-header">
        <button className="back-button" onClick={() => navigate(`/dashboard?persona=${encodeURIComponent(persona)}`)}>
          <ArrowLeft size={20} /> Back to Dashboard
        </button>
        <div className="header-info" style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '0.85rem', color: '#666', background: '#eee', padding: '4px 10px', borderRadius: '12px' }}>
            Persona: <strong>{persona}</strong>
          </span>
          <span className={`path-badge ${investigation.path_type.toLowerCase()}`}>
            {isFastPath ? "🚀 Path 1 (Fast Event Match)" : isSlowPath ? "🔍 Path 2 (Deep Causal Analysis)" : "⚠️ Abstain Path"}
          </span>
        </div>
      </header>

      <main className="investigation-main">
        <div className="investigation-container">
          {/* Section 1: KPI Movement & Business Impact */}
          <section className="investigation-section alert-overview">
            <div className="overview-header">
              <div className="alert-title">
                <h1>{alert.kpi} Anomaly Analysis</h1>
                <p className="alert-meta">{alert.category} · {alert.region} · Week Starting {alert.week_start}</p>
              </div>
              <div className="alert-impact">
                <div className="impact-card" style={{ background: alert.delta_inr < 0 ? '#fff5f5' : '#f0fff4', border: '1px solid ' + (alert.delta_inr < 0 ? '#feb2b2' : '#9ae6b4') }}>
                  <small>Business Impact (₹)</small>
                  <strong className={alert.delta_inr < 0 ? "negative" : "positive"} style={{ fontSize: '1.5rem' }}>
                    {alert.delta_fmt}
                  </strong>
                </div>
                <div className="impact-card">
                  <small>Variance</small>
                  <strong className={alert.pct_change < 0 ? "negative" : "positive"}>
                    {alert.pct_fmt} (z={alert.z_fmt})
                  </strong>
                </div>
              </div>
            </div>
          </section>

          {/* Section 2: Telemetry Trend Analysis */}
          <section className="investigation-section chart-section">
            <div className="section-title">
              <h2>KPI Trend Analysis & Telemetry</h2>
            </div>
            <div className="chart-container">
              <KPIChart alert={alert} />
            </div>
          </section>

          {/* Section 3: Diagnostic Abstention or Full Investigation Results */}
          {isAbstain ? (
            <section className="investigation-section abstention-notice">
              <div className="notice-card warning" style={{ background: '#fffaf0', border: '1px solid #fbd38d', padding: '20px', borderRadius: '8px' }}>
                <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                  <AlertCircle size={28} color="#dd6b20" />
                  <div>
                    <h3 style={{ margin: '0 0 8px 0', color: '#c05621' }}>Diagnostic Abstention</h3>
                    <p style={{ margin: '0 0 12px 0', fontWeight: 600, fontSize: '1rem', color: '#2d3748' }}>
                      Insufficient evidence — CAUSE abstained from generating a definitive explanation.
                    </p>
                    <div style={{ fontSize: '0.9rem', color: '#4a5568', lineHeight: 1.5 }}>
                      <p><strong>Reason:</strong> {investigation.abstention?.reason}</p>
                      <p><strong>Missing Evidence:</strong> {investigation.abstention?.missing_evidence}</p>
                      <p><strong>Required Data:</strong> {investigation.abstention?.required_data}</p>
                      <p><strong>Recommended Action:</strong> {investigation.abstention?.recommendation}</p>
                    </div>
                  </div>
                </div>
              </div>
            </section>
          ) : (
            <>
              {/* Section 4: 4 Competing Hypotheses & Falsification Matrix */}
              <section className="investigation-section slow-path-section">
                <div className="section-title" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <h2>4 Competing Hypotheses (Ranked Falsification Analysis)</h2>
                  <span className="count-badge" style={{ background: '#edf2f7', color: '#2d3748', padding: '2px 8px', borderRadius: '4px', fontSize: '0.85rem' }}>
                    Exactly 4 Evaluated
                  </span>
                </div>
                <div className="hypotheses-list slow-path">
                  {investigation.hypotheses.slice(0, 4).map((hyp, idx) => (
                    <div key={idx} className={`hypothesis-card expandable ${hyp.supported ? 'supported-card' : 'rejected-card'}`} style={{ borderLeft: hyp.supported ? '4px solid #38a169' : '4px solid #e53e3e', marginBottom: '12px' }}>
                      <div
                        className="hypothesis-header"
                        onClick={() => setExpandedHypothesis(expandedHypothesis === idx ? null : idx)}
                        style={{ cursor: 'pointer', padding: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
                      >
                        <div className="hypothesis-info">
                          <span className="ranking" style={{ fontWeight: 'bold', marginRight: '8px', color: '#718096' }}>#{idx + 1}</span>
                          <strong style={{ fontSize: '1.05rem', color: '#1a202c' }}>{hyp.name}</strong>
                          <span className={`status-tag ${hyp.supported ? 'supported' : 'rejected'}`} style={{ marginLeft: '12px', padding: '2px 8px', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 600, background: hyp.supported ? '#c6f6d5' : '#fed7d7', color: hyp.supported ? '#22543d' : '#742a2a' }}>
                            {hyp.supported ? "SUPPORTED" : "REJECTED"}
                          </span>
                          <p className="hypothesis-verdict" style={{ margin: '4px 0 0 0', fontSize: '0.88rem', color: '#4a5568' }}>{hyp.verdict}</p>
                        </div>
                        <div className="hypothesis-meta" style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                          <div className="hypothesis-confidence" style={{ textAlign: 'right' }}>
                            <strong style={{ fontSize: '1.1rem' }}>{hyp.confidence_pct || Math.round((hyp.score || 0) * 100)}%</strong>
                            <small style={{ display: 'block', color: '#718096', fontSize: '0.75rem' }}>Score</small>
                          </div>
                          <button className="expand-button" style={{ background: 'none', border: 'none', cursor: 'pointer' }}>
                            {expandedHypothesis === idx ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                          </button>
                        </div>
                      </div>
                      
                      {expandedHypothesis === idx && (
                        <div className="hypothesis-detail" style={{ padding: '16px', borderTop: '1px solid #e2e8f0', background: '#f7fafc' }}>
                          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '12px' }}>
                            <div style={{ background: '#f0fff4', padding: '10px', borderRadius: '6px', border: '1px solid #c6f6d5' }}>
                              <strong style={{ color: '#22543d', fontSize: '0.85rem', display: 'block', marginBottom: '4px' }}>Supporting Evidence:</strong>
                              <p style={{ margin: 0, fontSize: '0.85rem', color: '#2d3748' }}>{hyp.supporting_evidence || hyp.deciding_value}</p>
                            </div>
                            <div style={{ background: '#fff5f5', padding: '10px', borderRadius: '6px', border: '1px solid #fed7d7' }}>
                              <strong style={{ color: '#742a2a', fontSize: '0.85rem', display: 'block', marginBottom: '4px' }}>Contrary Evidence:</strong>
                              <p style={{ margin: 0, fontSize: '0.85rem', color: '#2d3748' }}>{hyp.contrary_evidence || "None identified"}</p>
                            </div>
                          </div>
                          <div style={{ fontSize: '0.85rem', color: '#718096' }}>
                            <span><strong>Data Source:</strong> {hyp.data_source}</span> · <span><strong>Deciding Metric:</strong> {hyp.deciding_metric}</span>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </section>

              {/* Section 5: Multi-Source Evidence Retrieval Cards */}
              {investigation.rag_evidence && investigation.rag_evidence.length > 0 && (
                <section className="investigation-section evidence-section">
                  <div className="section-title">
                    <h2>Multi-Source Evidence Retrieval</h2>
                    <span className="count-badge">{investigation.rag_evidence.length} Provenance Records</span>
                  </div>
                  <div className="evidence-list" style={{ display: 'grid', gap: '8px' }}>
                    {investigation.rag_evidence.map((evidence, idx) => (
                      <div key={idx} className="evidence-item" style={{ background: '#fff', padding: '12px', borderRadius: '6px', border: '1px solid #e2e8f0', fontSize: '0.88rem' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', color: '#718096', fontSize: '0.8rem', marginBottom: '4px' }}>
                          <span><strong>Source:</strong> {evidence.source}</span>
                          <span><strong>Relevance:</strong> {(evidence.relevance_score ? (evidence.relevance_score * 100).toFixed(0) : '95')}%</span>
                        </div>
                        <p style={{ margin: 0, color: '#2d3748' }}>{evidence.text || evidence.snippet || evidence.context}</p>
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {/* Section 6: Weighted Evidence Confidence & Conflict Panel */}
              <section className="investigation-section confidence-conflict-section">
                {investigation.conflict && investigation.conflict.conflict ? (
                  <div className="notice-card conflict" style={{ background: '#fff5f5', border: '1px solid #feb2b2', padding: '16px', borderRadius: '8px', marginBottom: '16px' }}>
                    <div style={{ display: 'flex', gap: '12px' }}>
                      <ShieldAlert size={24} color="#e53e3e" />
                      <div>
                        <h3 style={{ margin: '0 0 4px 0', color: '#9b2c2c' }}>Conflicting Evidence Detected Across Regions</h3>
                        <p style={{ margin: '0 0 8px 0', fontSize: '0.9rem', color: '#2d3748' }}>
                          <strong>Signal A:</strong> {investigation.conflict.signal_a}
                        </p>
                        <p style={{ margin: '0 0 8px 0', fontSize: '0.9rem', color: '#2d3748' }}>
                          <strong>Signal B:</strong> {investigation.conflict.signal_b}
                        </p>
                        <p style={{ margin: 0, fontSize: '0.85rem', color: '#742a2a', fontStyle: 'italic' }}>
                          Directive: {investigation.conflict.escalation_directive}
                        </p>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="confidence-breakdown-card" style={{ background: '#edf2f7', padding: '16px', borderRadius: '8px', marginBottom: '16px' }}>
                    <h3 style={{ margin: '0 0 12px 0', fontSize: '1rem', color: '#2d3748' }}>
                      Weighted Evidence Confidence: <strong>{investigation.confidence?.score}</strong> ({investigation.confidence?.tier} Tier)
                    </h3>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px', fontSize: '0.8rem', textAlign: 'center' }}>
                      <div style={{ background: '#fff', padding: '8px', borderRadius: '4px' }}>
                        <span style={{ color: '#718096', display: 'block' }}>W1 Temporal</span>
                        <strong>{investigation.confidence?.components?.temporal_correlation ?? '1.0'}</strong>
                      </div>
                      <div style={{ background: '#fff', padding: '8px', borderRadius: '4px' }}>
                        <span style={{ color: '#718096', display: 'block' }}>W2 Reliability</span>
                        <strong>{investigation.confidence?.components?.source_agreement ?? '1.0'}</strong>
                      </div>
                      <div style={{ background: '#fff', padding: '8px', borderRadius: '4px' }}>
                        <span style={{ color: '#718096', display: 'block' }}>W3 Margin</span>
                        <strong>{investigation.confidence?.components?.hypothesis_margin ?? '0.8'}</strong>
                      </div>
                      <div style={{ background: '#fff', padding: '8px', borderRadius: '4px' }}>
                        <span style={{ color: '#718096', display: 'block' }}>W4 Completeness</span>
                        <strong>{investigation.confidence?.components?.data_completeness ?? '1.0'}</strong>
                      </div>
                    </div>
                  </div>
                )}
              </section>

              {/* Section 7: 7-Part Recommended Action (Visually Dominant) */}
              {investigation.recommendation && (
                <section className="investigation-section recommendation-section">
                  <div className="section-title">
                    <h2>Recommended Action</h2>
                  </div>
                  <div className="recommendation-card dominant" style={{ background: '#ebf8ff', border: '2px solid #3182ce', padding: '20px', borderRadius: '8px' }}>
                    <div className="recommendation-header" style={{ marginBottom: '16px' }}>
                      <h3 style={{ margin: '0 0 8px 0', fontSize: '1.25rem', color: '#2b6cb0' }}>{investigation.recommendation.action}</h3>
                      {investigation.recommendation.estimated_impact && (
                        <div style={{ background: '#3182ce', color: '#fff', padding: '8px 14px', borderRadius: '6px', display: 'inline-block', fontWeight: 'bold', fontSize: '1.1rem' }}>
                          Estimated Recovery: ₹{investigation.recommendation.estimated_impact.toLocaleString("en-IN")}
                        </div>
                      )}
                    </div>
                    <div className="recommendation-details" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', background: '#fff', padding: '16px', borderRadius: '6px' }}>
                      <div className="rec-item">
                        <strong>Driver:</strong> <p style={{ margin: '2px 0 0 0' }}>{investigation.recommendation.driver}</p>
                      </div>
                      <div className="rec-item">
                        <strong>Controllable Lever:</strong> <p style={{ margin: '2px 0 0 0' }}>{investigation.recommendation.lever}</p>
                      </div>
                      <div className="rec-item">
                        <strong>Owner:</strong> <p style={{ margin: '2px 0 0 0' }}>{investigation.recommendation.owner}</p>
                      </div>
                      <div className="rec-item">
                        <strong>Confidence:</strong> <p style={{ margin: '2px 0 0 0' }}>{investigation.recommendation.confidence}</p>
                      </div>
                      <div className="rec-item" style={{ gridColumn: 'span 2' }}>
                        <strong>Monitoring Plan:</strong> <p style={{ margin: '2px 0 0 0' }}>{investigation.recommendation.monitoring_plan}</p>
                      </div>
                    </div>
                  </div>
                </section>
              )}

              {/* Section 8: Compact Single-Render LLM Executive Brief */}
              {investigation.narrative && (
                <section className="investigation-section narrative-section">
                  <div className="section-title">
                    <h2>Executive Brief</h2>
                    <span className="confidence-badge" style={{ fontSize: '0.8rem', color: '#718096' }}>
                      {investigation.narrative.engine}
                    </span>
                  </div>
                  <div className="narrative-card" style={{ background: '#f7fafc', padding: '16px', borderRadius: '8px', border: '1px solid #e2e8f0', lineHeight: 1.6 }}>
                    <p style={{ margin: 0, fontSize: '0.95rem', color: '#2d3748' }}>{investigation.narrative.text}</p>
                    {investigation.narrative.audit && (
                      <small className="narrative-meta" style={{ display: 'block', marginTop: '8px', color: '#a0aec0', fontSize: '0.75rem' }}>
                        Audit Status: {investigation.narrative.audit}
                      </small>
                    )}
                  </div>
                </section>
              )}
            </>
          )}

          {/* Section 9: Empirical Feedback Calibration */}
          <section className="investigation-section action-section">
            <div className="section-title">
              <h2>Empirical Feedback Calibration</h2>
            </div>
            <div className="action-buttons" style={{ display: 'flex', gap: '12px' }}>
              <button
                className="secondary-button"
                onClick={() => handleDecision("rejected")}
                disabled={deciding}
                style={{ padding: '10px 20px', borderRadius: '6px', cursor: 'pointer' }}
              >
                {deciding ? "Recording..." : "Reject Cause"}
              </button>
              <button
                className="secondary-button"
                onClick={() => handleDecision("ignored")}
                disabled={deciding}
                style={{ padding: '10px 20px', borderRadius: '6px', cursor: 'pointer' }}
              >
                Ignore / Defer
              </button>
              <button
                className="primary-button"
                onClick={() => handleDecision("approved")}
                disabled={deciding}
                style={{ padding: '10px 24px', borderRadius: '6px', background: '#3182ce', color: '#fff', fontWeight: 'bold', border: 'none', cursor: 'pointer' }}
              >
                {deciding ? "Recording..." : "Approve & Execute Action"}
              </button>
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}
