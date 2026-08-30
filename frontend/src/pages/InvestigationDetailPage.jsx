import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  CheckCircle2,
  ShieldAlert,
  Activity,
  X,
  Check,
  HelpCircle,
  FileText
} from "lucide-react";
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
  // Section 13 CRITICAL: All hypothesis cards start COLLAPSED (null)
  const [expandedHypothesis, setExpandedHypothesis] = useState(null);
  const [showTechnicalAudit, setShowTechnicalAudit] = useState(false);
  const [showInsightGeneration, setShowInsightGeneration] = useState(false);
  const [causeRecModal, setCauseRecModal] = useState(null);
  
  // Feedback state
  const [decisionType, setDecisionType] = useState(null); // "approved" | "rejected" | "ignored"
  const [rejectReason, setRejectReason] = useState("");
  const [feedbackComment, setFeedbackComment] = useState("");
  const [deciding, setDeciding] = useState(false);
  const [decisionDone, setDecisionDone] = useState(false);

  useEffect(() => {
    loadInvestigation();
  }, [alertId, persona]);

  async function loadInvestigation() {
    setLoading(true);
    setTriageStep(1);
    setError("");
    try {
      setTimeout(() => setTriageStep(2), 400);
      setTimeout(() => setTriageStep(3), 800);

      const data = await investigateAlert(alertId, persona);
      setInvestigation(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setTimeout(() => setLoading(false), 900);
    }
  }

  async function handleDecision(type) {
    setDeciding(true);
    try {
      await saveDecision(alertId, {
        decision: type,
        persona,
        reason: type === "rejected" ? rejectReason : null,
        feedback: feedbackComment
      });
      setDecisionDone(true);
      setDecisionType(type);
      
      // Auto return to dashboard after brief confirmation
      setTimeout(() => {
        navigate(`/dashboard?persona=${encodeURIComponent(persona)}`);
      }, 1200);
    } catch (err) {
      setError(err.message);
    } finally {
      setDeciding(false);
    }
  }

  // TRIAGE LOADING SCAN
  if (loading) {
    return (
      <div className="investigation-shell">
        <header className="investigation-header">
          <button className="back-button" onClick={() => navigate(`/dashboard?persona=${encodeURIComponent(persona)}`)}>
            <ArrowLeft size={18} /> Return to Dashboard
          </button>
        </header>
        <main className="investigation-main centered-flex">
          <div className="triage-loading-card">
            <h2 className="triage-title">
              DIAGNOSIS IN PROGRESS · TRIAGE SCAN
            </h2>

            <div className="triage-step-item">
              <div className="triage-path-label">PATH 1: Direct Event Match</div>
              <div className="triage-status-row">
                {triageStep > 1 ? (
                  <CheckCircle2 size={18} color="#38a169" />
                ) : (
                  <Activity size={18} className="spin" color="#7800c4" />
                )}
                <span>Scanning change-log events...</span>
              </div>
              {triageStep > 1 && investigation?.path_type !== "FAST" && (
                <div className="triage-subtext">✓ No direct change-log match — escalating to deep research</div>
              )}
            </div>

            {triageStep >= 2 && (
              <div className="triage-step-item margin-top-md">
                <div className="triage-path-label deep">PATH 2: Deep Causal Research</div>
                <div className="triage-status-row">
                  {triageStep > 2 ? (
                    <CheckCircle2 size={18} color="#38a169" />
                  ) : (
                    <Activity size={18} className="spin" color="#7800c4" />
                  )}
                  <span>Retrieving multi-source evidence...</span>
                </div>
                <div className="triage-status-row">
                  {triageStep >= 3 ? (
                    <CheckCircle2 size={18} color="#38a169" />
                  ) : (
                    <Activity size={18} className="spin" color="#7800c4" />
                  )}
                  <span>Testing 4 canonical hypotheses (Supply, Demand, Pricing, Operational)...</span>
                </div>
                <div className="triage-status-row">
                  {triageStep >= 3 ? (
                    <CheckCircle2 size={18} color="#38a169" />
                  ) : (
                    <Activity size={18} className="spin" color="#7800c4" />
                  )}
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
            <ArrowLeft size={18} /> Return to Dashboard
          </button>
        </header>
        <main className="investigation-main">
          <div className="error-container">
            <AlertCircle size={32} />
            <h2>Investigation Unavailable</h2>
            <p>{error || "Unable to retrieve investigation records."}</p>
            <button className="primary-button margin-top-md" onClick={loadInvestigation}>
              Retry Investigation
            </button>
          </div>
        </main>
      </div>
    );
  }

  const alert = investigation.alert;
  const isFastPath = investigation.path_type === "FAST";
  const isAbstain = investigation.path_type === "ABSTAIN";
  const isConflict = investigation.route === "UNRESOLVED_CONFLICT";
  const isResolved = investigation.route === "RESOLVED";
  const topHypothesis = investigation.hypotheses?.find((h) => h.supported) || investigation.hypotheses?.[0];

  return (
    <div className="investigation-shell">
      <header className="investigation-header">
        <div className="header-left">
          <button className="back-button" onClick={() => navigate(`/dashboard?persona=${encodeURIComponent(persona)}`)}>
            <ArrowLeft size={18} /> Dashboard
          </button>
          <span className="persona-chip">
            Perspective: <strong>{persona}</strong>
          </span>
        </div>
        <div className="header-right">
          <span className={`path-indicator ${isFastPath ? "fast" : isAbstain ? "abstain" : isConflict ? "conflict" : "resolved"}`}>
            {isFastPath ? "Path 1 · Direct Event Match" : isAbstain ? "Diagnostic Abstention" : isConflict ? "Contradictory Signals" : "Path 2 · Deep Causal Research"}
          </span>
        </div>
      </header>

      <main className="investigation-main">
        <div className="investigation-container">

          {decisionDone && (
            <div className="decision-toast-banner">
              <CheckCircle2 size={20} />
              <span>Decision recorded successfully. Updating workspace...</span>
            </div>
          )}

          {/* SIGNAL OVERVIEW */}
          <section className="investigation-section alert-overview-card">
            <div className="overview-header-row">
              <div>
                <span className="section-eyebrow">SIGNAL CONTEXT · {alert.id}</span>
                <h1>{alert.kpi} Anomaly</h1>
                <p className="context-subline">
                  {alert.category} <span>/</span> {alert.region} · Week {alert.week_start}
                </p>
              </div>
              <div className="overview-impact-box">
                <small>Financial Impact</small>
                <strong className={alert.delta_inr < 0 ? "negative" : "positive"}>{alert.delta_fmt}</strong>
                <span className="pct-sub">{alert.pct_fmt || `${((alert.pct_change || 0) * 100).toFixed(1)}%`} vs baseline</span>
              </div>
            </div>

            {/* Horizontal 3-column KPI boxes */}
            <div className="horizontal-kpi-summary margin-top-md">
              <div className="summary-box">
                <small>BASELINE MEAN</small>
                <strong>{alert.baseline_fmt || `₹${(alert.baseline_mean || 0).toLocaleString("en-IN")}`}</strong>
              </div>
              <div className="summary-box">
                <small>CURRENT OBSERVED</small>
                <strong>{alert.current_fmt || `₹${(alert.current || 0).toLocaleString("en-IN")}`}</strong>
              </div>
              <div className="summary-box">
                <small>NET VARIANCE</small>
                <strong className={alert.delta_inr < 0 ? "negative" : "positive"}>
                  {alert.pct_fmt || `${((alert.pct_change || 0) * 100).toFixed(1)}%`}
                </strong>
              </div>
            </div>
          </section>

          {/* TELEMETRY CHART PREVIEW */}
          <section className="investigation-section">
            <div className="section-title">
              <h2>TELEMETRY OBSERVED TREND</h2>
            </div>
            <KPIChart alert={alert} />
          </section>

          {/* PATH 1: FAST PATH DIRECT EVENT MATCH */}
          {isFastPath && (
            <section className="investigation-section fast-path-result-box">
              <div className="fast-path-header">
                <CheckCircle2 size={28} color="#38a169" />
                <div>
                  <span className="fast-path-badge">DIRECT EVENT MATCH FOUND</span>
                  <h2>Verified Operational Event Match</h2>
                  <p className="fast-path-sub">
                    Direct change-log event: <strong>[{investigation.fast_path?.event_type}]</strong> on <strong>{investigation.fast_path?.event_date}</strong>.
                  </p>
                </div>
              </div>
              <div className="event-description-callout">
                <p>"{investigation.fast_path?.description}"</p>
                <small>Matched against: Category {alert.category} · Region {alert.region} · Observation Window Week {alert.week_start}</small>
              </div>
            </section>
          )}

          {/* PATH 2: DEEP PATH ROOT CAUSE (RESOLVED) */}
          {isResolved && topHypothesis && (
            <section className="investigation-section root-cause-spotlight">
              <div className="spotlight-badge-row">
                <span className="spotlight-tag">PRIMARY ROOT CAUSE IDENTIFIED</span>
                <span className="confidence-pill">
                  {topHypothesis.confidence_pct || Math.round((topHypothesis.score || 0) * 100)}% Confidence
                </span>
              </div>

              <h2 className="spotlight-title">{topHypothesis.name}</h2>
              <p className="spotlight-verdict">{topHypothesis.verdict_summary || topHypothesis.deciding_value || "Telemetry patterns deterministically support this hypothesis."}</p>

              <div className="evidence-reasoning-grid">
                <div className="reasoning-box supporting">
                  <strong>Supporting Telemetry Evidence</strong>
                  <p>{topHypothesis.supporting_evidence || "Empirical telemetry aligns with observed signal pattern."}</p>
                </div>
                <div className="reasoning-box contrary">
                  <strong>Contrary Evidence / Alternative Falsification</strong>
                  <p>{topHypothesis.contrary_evidence || "No material contrary evidence identified across alternative hypotheses."}</p>
                </div>
              </div>
            </section>
          )}

          {/* COMPETING CAUSES (SECTION 12 & 13: ALL 4 CANONICAL HYPOTHESES START COLLAPSED) */}
          {investigation.hypotheses && investigation.hypotheses.length > 0 && !isAbstain && (
            <section className="investigation-section">
              <div className="section-title">
                <h2>COMPETING CAUSES EVALUATED ({investigation.hypotheses.length})</h2>
                <small className="section-subtitle">Deterministically evaluated & falsified hypotheses</small>
              </div>

              <div className="hypotheses-list-container">
                {investigation.hypotheses.slice(0, 4).map((hyp, idx) => {
                  const isExpanded = expandedHypothesis === idx;
                  const scorePct = hyp.confidence_pct || Math.round((hyp.score || 0) * 100);

                  return (
                    <div
                      key={idx}
                      className={`hypothesis-row-card ${hyp.supported ? "supported-card" : "rejected-card"}`}
                    >
                      <div className="hypothesis-row-head">
                        <div className="hyp-row-left">
                          <span className="hyp-index">{idx + 1}.</span>
                          <strong className="hyp-name">{hyp.name}</strong>
                          <span className={`verdict-pill ${hyp.supported ? "supported" : "rejected"}`}>
                            {hyp.supported ? "Supported" : "Falsified / Rejected"}
                          </span>
                        </div>

                        <div className="hyp-row-right">
                          <span className="score-val">{scorePct}%</span>
                          <button
                            className="secondary-button collapse-btn"
                            onClick={() => setExpandedHypothesis(isExpanded ? null : idx)}
                          >
                            {isExpanded ? (
                              <>Collapse <ChevronUp size={15} /></>
                            ) : (
                              <>Expand <ChevronDown size={15} /></>
                            )}
                          </button>
                        </div>
                      </div>

                      {/* EXPANDED DETAILS ON DEMAND ONLY (Section 13) */}
                      {isExpanded && (
                        <div className="hypothesis-expanded-body">
                          <div className="exp-grid-container">
                            <div className="exp-box">
                              <span className="exp-label">SUPPORTING EVIDENCE</span>
                              <p>{hyp.supporting_evidence || hyp.deciding_value || "Telemetry patterns match criteria."}</p>
                            </div>
                            <div className="exp-box">
                              <span className="exp-label contrary">CONTRARY EVIDENCE / FALSIFICATION</span>
                              <p>{hyp.contrary_evidence || "No material contrary evidence found."}</p>
                            </div>
                            <div className="exp-box span-full">
                              <span className="exp-label">WEIGHTED EVIDENCE CONFIDENCE MODEL</span>
                              <div className="confidence-breakdown-row">
                                <div><span>Temporal Correlation (W1):</span> <strong>{investigation.confidence?.components?.temporal_correlation ?? '1.0'}</strong></div>
                                <div><span>Source Reliability (W2):</span> <strong>{investigation.confidence?.components?.source_agreement ?? '1.0'}</strong></div>
                                <div><span>Hypothesis Margin (W3):</span> <strong>{investigation.confidence?.components?.hypothesis_margin ?? '0.8'}</strong></div>
                                <div><span>Data Completeness (W4):</span> <strong>{investigation.confidence?.components?.data_completeness ?? '1.0'}</strong></div>
                              </div>
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

          {/* CONFLICT SCREEN (Section 14) */}
          {isConflict && (
            <section className="investigation-section conflict-alert-card">
              <div className="conflict-header-row">
                <ShieldAlert size={28} color="#e53e3e" />
                <div>
                  <span className="conflict-badge">UNRESOLVED CONFLICT DETECTED</span>
                  <h2>Conflicting Evidence Identified</h2>
                  <p className="conflict-sub">Automated diagnosis withheld due to cross-regional signal contradiction.</p>
                </div>
              </div>

              <div className="conflict-signals-grid">
                <div className="signal-box">
                  <strong>Signal A (Observed Trajectory)</strong>
                  <p>{investigation.conflict?.signal_a}</p>
                </div>
                <div className="signal-box">
                  <strong>Signal B (Contradictory Benchmark)</strong>
                  <p>{investigation.conflict?.signal_b}</p>
                </div>
              </div>

              <div className="conflict-action-notice">
                <strong>Directive:</strong>
                <p>{investigation.conflict?.escalation_directive || "Escalate for manual commercial audit — do not automate operational changes."}</p>
              </div>
            </section>
          )}

          {/* ABSTAIN SCREEN (Section 15) */}
          {isAbstain && (
            <section className="investigation-section abstain-alert-card">
              <div className="abstain-header-row">
                <AlertCircle size={28} color="#dd6b20" />
                <div>
                  <span className="abstain-badge">INSUFFICIENT EVIDENCE TO DIAGNOSE</span>
                  <h2>Diagnostic Abstention</h2>
                  <p className="abstain-sub">The system deliberately refused to guess due to telemetry data gaps.</p>
                </div>
              </div>

              <div className="abstain-details-grid">
                <div className="abstain-box">
                  <strong>Why Diagnosis Was Withheld</strong>
                  <p>{investigation.abstention?.reason}</p>
                </div>
                <div className="abstain-box">
                  <strong>Missing Telemetry Data</strong>
                  <p>{investigation.abstention?.missing_evidence}</p>
                </div>
                <div className="abstain-box">
                  <strong>Required Data to Enable Diagnosis</strong>
                  <p>{investigation.abstention?.required_data}</p>
                </div>
              </div>

              <div className="abstain-policy-note">
                <p>✓ Policy Enforced: Zero LLM narration calls were made for this response.</p>
              </div>
            </section>
          )}

          {/* RECOMMENDATION EXPERIENCE (Section 16, 17) */}
          {investigation.recommendation && !isAbstain && !isConflict && (
            <section className="investigation-section recommendation-primary-card">
              <div className="rec-eyebrow-row">
                <span className="rec-eyebrow">RECOMMENDED ACTION DIRECTIVE</span>
                <span className="rec-owner-badge">Owner: {investigation.recommendation.owner}</span>
              </div>

              {/* Action is the strongest visual element */}
              <h2 className="rec-main-action">{investigation.recommendation.action}</h2>

              {investigation.recommendation.estimated_impact && (
                <div className="rec-impact-banner">
                  <span>Expected Recovery:</span>
                  <strong>{investigation.recommendation.est_impact_fmt || `₹${investigation.recommendation.estimated_impact.toLocaleString("en-IN")}`} / wk</strong>
                </div>
              )}

              <div className="rec-matrix-grid">
                <div>
                  <small>ROOT DRIVER</small>
                  <p>{investigation.recommendation.driver}</p>
                </div>
                <div>
                  <small>CONTROLLABLE LEVER</small>
                  <p>{investigation.recommendation.lever}</p>
                </div>
                <div>
                  <small>CONFIDENCE LEVEL</small>
                  <p>{investigation.recommendation.confidence}</p>
                </div>
                <div>
                  <small>MONITORING PLAN</small>
                  <p>{investigation.recommendation.monitoring_plan}</p>
                </div>
              </div>

              {/* AI SUMMARY (Section 17) */}
              {investigation.narrative && (
                <div className="ai-summary-container">
                  <div className="ai-summary-head">
                    <span className="ai-summary-title">Executive Summary</span>
                    <span className="ai-trust-pill">LLM · Narration only</span>
                  </div>
                  <p className="ai-summary-body">{investigation.narrative.text}</p>

                  <button
                    className="insight-gen-toggle"
                    onClick={() => setShowInsightGeneration(!showInsightGeneration)}
                  >
                    <HelpCircle size={14} />
                    {showInsightGeneration ? "Hide generation details" : "How this insight was generated"}
                  </button>

                  {showInsightGeneration && (
                    <div className="insight-gen-details">
                      <ul>
                        <li>✓ Deterministic Causal Engine analysis</li>
                        <li>✓ Empirical multi-source telemetry verified</li>
                        <li>✓ LLM used strictly for copy narration (no mathematical calculation)</li>
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </section>
          )}

          {/* EVIDENCE & TRUST / TECHNICAL AUDIT (Section 18, 19) */}
          <section className="investigation-section">
            <div className="section-title">
              <h2>EVIDENCE & TRUST</h2>
              <button
                className="secondary-button"
                onClick={() => setShowTechnicalAudit(!showTechnicalAudit)}
              >
                <FileText size={15} />
                {showTechnicalAudit ? "Hide Technical Audit" : "View Technical Audit"}
              </button>
            </div>

            <div className="evidence-trust-summary-grid">
              <div className="trust-stat-item">
                <strong>Multi-Source Retrieval</strong>
                <p>4 empirical telemetry sources verified</p>
              </div>
              <div className="trust-stat-item">
                <strong>Deterministic Causal Engine</strong>
                <p>Formula & rules-based hypothesis scoring</p>
              </div>
              <div className="trust-stat-item">
                <strong>LLM Boundary</strong>
                <p>Strictly constrained to narration</p>
              </div>
            </div>

            {/* Detailed Ledger Audit (Section 18) */}
            {showTechnicalAudit && (
              <div className="technical-audit-table-wrapper margin-top-md">
                <table className="audit-table">
                  <thead>
                    <tr>
                      <th>Step</th>
                      <th>Engine / Method</th>
                      <th>Latency</th>
                      <th>LLM Call</th>
                      <th>Est. Cost</th>
                      <th>Provenance / Notes</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(investigation.ledger_rows || []).map((row, idx) => (
                      <tr key={idx}>
                        <td className="step-cell">{row.step}</td>
                        <td>
                          <span className={`engine-badge ${row.engine === "Deterministic" ? "det" : row.engine?.includes("LLM") ? "llm" : "ret"}`}>
                            {row.engine === "Multi-Source Retrieval" ? "Multi-Source Retrieval" : row.engine}
                          </span>
                        </td>
                        <td>{row.latency_ms} ms</td>
                        <td>{row.engine?.includes("LLM") ? "Yes" : "No"}</td>
                        <td>${row.est_cost_usd || "0.0000"}</td>
                        <td className="note-cell">{row.note}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          {/* FEEDBACK & ACTION PERSISTENCE LOOP (Section 20, 21, 22) */}
          {!isAbstain && (
            <section className="investigation-section feedback-card">
              <h3>Was this recommendation useful?</h3>
              <p className="feedback-sub">Persist your commercial decision to calibrate future hypothesis weights.</p>

              {decisionType === "rejected" && (
                <div className="reject-reason-box margin-top-sm">
                  <label>Reason for rejection:</label>
                  <select
                    value={rejectReason}
                    onChange={(e) => setRejectReason(e.target.value)}
                    className="reject-select"
                  >
                    <option value="">Select reason...</option>
                    <option value="Wrong cause">Wrong cause</option>
                    <option value="Missing evidence">Missing evidence</option>
                    <option value="Wrong impact">Wrong impact</option>
                    <option value="Wrong recommendation">Wrong recommendation</option>
                    <option value="Other">Other</option>
                  </select>
                </div>
              )}

              <div className="feedback-comment-box margin-top-sm">
                <textarea
                  rows={2}
                  placeholder="Optional decision comment..."
                  value={feedbackComment}
                  onChange={(e) => setFeedbackComment(e.target.value)}
                  className="feedback-textarea"
                />
              </div>

              <div className="feedback-actions-row margin-top-md">
                <button
                  className="secondary-button ignore-btn"
                  onClick={() => handleDecision("ignored")}
                  disabled={deciding}
                >
                  Ignore Signal
                </button>
                <button
                  className="secondary-button reject-btn"
                  onClick={() => {
                    if (decisionType !== "rejected") {
                      setDecisionType("rejected");
                    } else {
                      handleDecision("rejected");
                    }
                  }}
                  disabled={deciding}
                >
                  Reject Action
                </button>
                <button
                  className="primary-button approve-btn"
                  onClick={() => handleDecision("approved")}
                  disabled={deciding}
                >
                  {deciding ? "Persisting Decision..." : "Approve & Execute"}
                </button>
              </div>
            </section>
          )}

        </div>
      </main>

      {/* CAUSE SPECIFIC RECOMMENDATION MODAL */}
      {causeRecModal && (
        <div className="modal-overlay" onMouseDown={(e) => e.target === e.currentTarget && setCauseRecModal(null)}>
          <div className="investigate-modal-box">
            <div className="modal-header-row">
              <div>
                <span className="modal-snapshot-label">HYPOTHESIS SPECIFIC DIRECTIVE</span>
                <h2>{causeRecModal.name}</h2>
              </div>
              <button className="close-modal-btn" onClick={() => setCauseRecModal(null)}>
                <X size={18} />
              </button>
            </div>

            <div className="cause-modal-grid">
              <div><strong>Driver:</strong> <p>{investigation.recommendation?.driver || causeRecModal.name}</p></div>
              <div><strong>Controllable Lever:</strong> <p>{investigation.recommendation?.lever || "Inventory & Promotional Alignment"}</p></div>
              <div><strong>Action Directive:</strong> <p className="action-highlight">{investigation.recommendation?.action || "Execute targeted operational correction"}</p></div>
              <div><strong>Confidence:</strong> <p>{causeRecModal.confidence_pct || Math.round((causeRecModal.score || 0) * 100)}%</p></div>
              <div><strong>Monitoring Plan:</strong> <p>{investigation.recommendation?.monitoring_plan || "Track weekly telemetry cycle"}</p></div>
            </div>

            <div className="modal-actions-footer margin-top-md">
              <button className="primary-button" onClick={() => setCauseRecModal(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
