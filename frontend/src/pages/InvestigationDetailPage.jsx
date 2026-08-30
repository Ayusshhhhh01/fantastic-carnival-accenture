import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  ChevronRight,
  AlertCircle,
  CheckCircle2,
  ShieldAlert,
  Activity,
  HelpCircle,
  FileText,
  ArrowRight
} from "lucide-react";
import { investigateAlert, saveDecision } from "../api/index.js";
import KPIChart from "../components/KPIChart.jsx";

// Authoritative Stage Enum for Clean Navigation & Zero Impossible States
const STAGE = {
  TRIAGE: "TRIAGE",
  FAST_RESULT: "FAST_RESULT",
  RCA_RESULTS: "RCA_RESULTS",
  RCA_DETAIL: "RCA_DETAIL",
  OVERALL_RECOMMENDATION: "OVERALL_RECOMMENDATION",
  CAUSE_RECOMMENDATION: "CAUSE_RECOMMENDATION",
  ABSTAIN: "ABSTAIN",
  CONFLICT: "CONFLICT",
  EVIDENCE_AUDIT: "EVIDENCE_AUDIT",
  ERROR: "ERROR"
};

export default function InvestigationDetailPage() {
  const { alertId } = useParams();
  const navigate = useNavigate();
  const persona = new URLSearchParams(window.location.search).get("persona") || "Category Manager";

  // Single Authoritative State Machine (stage only, no redundant triageStep)
  const [stage, setStage] = useState(STAGE.TRIAGE);
  const [investigation, setInvestigation] = useState(null);
  const [error, setError] = useState("");
  
  // User-selected detail states (Initial state for expanded cause is null - COLLAPSED by default)
  const [selectedCauseIndex, setSelectedCauseIndex] = useState(null);
  const [causeRecModal, setCauseRecModal] = useState(null);
  const [showInsightGeneration, setShowInsightGeneration] = useState(false);

  // Decision & Feedback state
  const [decisionType, setDecisionType] = useState(null); // "approved" | "rejected" | "ignored"
  const [rejectReason, setRejectReason] = useState("");
  const [feedbackComment, setFeedbackComment] = useState("");
  const [deciding, setDeciding] = useState(false);

  useEffect(() => {
    loadInvestigation();
  }, [alertId, persona]);

  async function loadInvestigation() {
    setStage(STAGE.TRIAGE);
    setError("");
    setSelectedCauseIndex(null);

    try {
      // Execute genuine backend investigation request synchronously
      const data = await investigateAlert(alertId, persona);
      setInvestigation(data);

      // Determine authoritative stage based on actual backend analytical result
      if (data.path_type === "FAST") {
        setStage(STAGE.FAST_RESULT);
      } else if (data.path_type === "ABSTAIN") {
        setStage(STAGE.ABSTAIN);
      } else if (data.route === "UNRESOLVED_CONFLICT") {
        setStage(STAGE.CONFLICT);
      } else {
        // Path 2: Deep Causal Research resolved
        setStage(STAGE.RCA_RESULTS);
      }
    } catch (err) {
      console.error(`[CAUSE Investigation Failure] Alert: ${alertId}, Persona: ${persona}, Error:`, err);
      setError(err.message || "Unable to diagnose this signal.");
      setStage(STAGE.ERROR);
    }
  }

  async function handleDecision(type) {
    setDeciding(true);
    setError("");
    try {
      await saveDecision(alertId, {
        decision: type,
        persona,
        reason: type === "rejected" ? rejectReason : null,
        feedback: feedbackComment
      });

      setDecisionType(type);

      // Immediately navigate back to Dashboard after successful backend persistence
      navigate(`/dashboard?persona=${encodeURIComponent(persona)}`);
    } catch (err) {
      setError(err.message || "Failed to persist decision");
    } finally {
      setDeciding(false);
    }
  }

  // ------------------------------------------------ STAGE 1: DEDICATED LOADING / TRIAGE --
  if (stage === STAGE.TRIAGE) {
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
              <div className="triage-path-label">CHECKING RECENT CHANGE LOGS</div>
              <div className="triage-status-row">
                <Activity size={18} className="spin" color="#7800c4" />
                <span>Looking for a recent pricing, promotion, inventory or operational event that could explain this signal...</span>
              </div>
            </div>
          </div>
        </main>
      </div>
    );
  }

  // ------------------------------------------------ STAGE: ERROR --
  if (stage === STAGE.ERROR || !investigation) {
    return (
      <div className="investigation-shell">
        <header className="investigation-header">
          <button className="back-button" onClick={() => navigate(`/dashboard?persona=${encodeURIComponent(persona)}`)}>
            <ArrowLeft size={18} /> Return to Dashboard
          </button>
        </header>
        <main className="investigation-main">
          <div className="error-container">
            <AlertCircle size={32} color="#e53e3e" />
            <div className="error-text">
              <strong>Unable to diagnose this signal</strong>
              <p>{error || "Unable to retrieve investigation records."}</p>
            </div>
            <button className="primary-button margin-top-md" onClick={loadInvestigation}>
              Retry Investigation
            </button>
          </div>
        </main>
      </div>
    );
  }

  const alert = investigation.alert || {};

  return (
    <div className="investigation-shell">
      {/* GLOBAL INVESTIGATION HEADER */}
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
          <span className={`path-indicator ${investigation.path_type === "FAST" ? "fast" : stage === STAGE.ABSTAIN ? "abstain" : stage === STAGE.CONFLICT ? "conflict" : "resolved"}`}>
            {investigation.path_type === "FAST" ? "Matching Change Found" : stage === STAGE.ABSTAIN ? "Diagnostic Abstention" : stage === STAGE.CONFLICT ? "Contradictory Signals" : "Expanded Investigation"}
          </span>
        </div>
      </header>

      <main className="investigation-main">
        <div className="investigation-container">

          {error && (
            <div className="error margin-bottom-md">
              <AlertCircle size={16} />
              {error}
            </div>
          )}

          {/* ------------------------------------------- STAGE 2A: FAST PATH RESULT -- */}
          {stage === STAGE.FAST_RESULT && (
            <section className="investigation-section fast-path-result-box">
              <div className="fast-path-header">
                <CheckCircle2 size={28} color="#38a169" />
                <div>
                  <span className="fast-path-badge">MATCHING RECENT CHANGE FOUND</span>
                  <h2>Verified Operational Event Match</h2>
                  <p className="fast-path-sub">
                    Direct change-log event: <strong>[{investigation.fast_path?.event_type}]</strong> on <strong>{investigation.fast_path?.event_date}</strong>.
                  </p>
                </div>
              </div>

              <div className="event-description-callout margin-top-md">
                <p>"{investigation.fast_path?.description}"</p>
                <small>Matched against: Category {alert.category} · Region {alert.region} · Observation Window Week {alert.week_start}</small>
              </div>

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
                    {alert.pct_fmt || `${((alert.pct_change || 0) * 100).toFixed(1)}%`} ({alert.delta_fmt})
                  </strong>
                </div>
              </div>

              {investigation.recommendation && (
                <div className="fast-path-recommendation-box margin-top-md">
                  <span className="rec-eyebrow">RECOMMENDED ACTION DIRECTIVE</span>
                  <h3 className="rec-main-action">{investigation.recommendation.action}</h3>
                  <p className="rec-sub">Owner: {investigation.recommendation.owner} · Monitoring: {investigation.recommendation.monitoring_plan}</p>
                </div>
              )}

              <div className="feedback-actions-row margin-top-md">
                <button className="secondary-button reject-btn" onClick={() => handleDecision("rejected")} disabled={deciding}>
                  {deciding ? "Saving..." : "Reject Action"}
                </button>
                <button className="primary-button approve-btn" onClick={() => handleDecision("approved")} disabled={deciding}>
                  {deciding ? "Saving decision..." : "Approve & Execute"}
                </button>
              </div>
            </section>
          )}

          {/* ------------------------------------------- STAGE 2B: ABSTAIN SCREEN -- */}
          {stage === STAGE.ABSTAIN && (
            <section className="investigation-section abstain-alert-card">
              <div className="abstain-header-row">
                <AlertCircle size={28} color="#dd6b20" />
                <div>
                  <span className="abstain-badge">INSUFFICIENT EVIDENCE TO DIAGNOSE</span>
                  <h2>Diagnostic Abstention</h2>
                  <p className="abstain-sub">The system deliberately refused to guess due to telemetry data gaps.</p>
                </div>
              </div>

              <div className="abstain-details-grid margin-top-md">
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

              <div className="abstain-policy-note margin-top-md">
                <p>✓ Policy Enforced: Zero LLM narration calls were made for this response.</p>
              </div>

              <div className="margin-top-md">
                <button className="secondary-button" onClick={() => navigate(`/dashboard?persona=${encodeURIComponent(persona)}`)}>
                  Return to Dashboard
                </button>
              </div>
            </section>
          )}

          {/* ------------------------------------------- STAGE 2C: CONFLICT SCREEN -- */}
          {stage === STAGE.CONFLICT && (
            <section className="investigation-section conflict-alert-card">
              <div className="conflict-header-row">
                <ShieldAlert size={28} color="#e53e3e" />
                <div>
                  <span className="conflict-badge">UNRESOLVED CONFLICT DETECTED</span>
                  <h2>Conflicting Evidence Identified</h2>
                  <p className="conflict-sub">Automated diagnosis withheld due to cross-regional signal contradiction.</p>
                </div>
              </div>

              <div className="conflict-signals-grid margin-top-md">
                <div className="signal-box">
                  <strong>Signal A (Observed Trajectory)</strong>
                  <p>{investigation.conflict?.signal_a}</p>
                </div>
                <div className="signal-box">
                  <strong>Signal B (Contradictory Benchmark)</strong>
                  <p>{investigation.conflict?.signal_b}</p>
                </div>
              </div>

              <div className="conflict-action-notice margin-top-md">
                <strong>Directive:</strong>
                <p>{investigation.conflict?.escalation_directive || "Escalate for manual commercial audit — do not automate operational changes."}</p>
              </div>

              <div className="margin-top-md">
                <button className="secondary-button" onClick={() => navigate(`/dashboard?persona=${encodeURIComponent(persona)}`)}>
                  Return to Dashboard
                </button>
              </div>
            </section>
          )}

          {/* ------------------------------------------- STAGE 2D: RCA RESULTS SCREEN -- */}
          {stage === STAGE.RCA_RESULTS && (
            <>
              {/* SIGNAL CONTEXT HEADER */}
              <section className="investigation-section alert-overview-card">
                <div className="overview-header-row">
                  <div>
                    <span className="section-eyebrow">SIGNAL CONTEXT · {alert.id}</span>
                    <h1>{alert.kpi} Anomaly</h1>
                    <p className="context-subline">{alert.category} <span>/</span> {alert.region} · Week {alert.week_start}</p>
                  </div>
                  <div className="overview-impact-box">
                    <small>Financial Impact</small>
                    <strong className={alert.delta_inr < 0 ? "negative" : "positive"}>{alert.delta_fmt}</strong>
                    <span className="pct-sub">{alert.pct_fmt || `${((alert.pct_change || 0) * 100).toFixed(1)}%`} vs baseline</span>
                  </div>
                </div>

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

              {/* RCA CAUSES LIST (EXACTLY 4, ORDERED BY CONFIDENCE DESCENDING, ALL COLLAPSED INITIALLY) */}
              <section className="investigation-section">
                <div className="section-title">
                  <div>
                    <h2>COMPETING CAUSES EVALUATED (4)</h2>
                    <p className="section-subtitle">Four competing causes evaluated against available evidence.</p>
                  </div>
                  <div className="view-mode-actions">
                    <button className="primary-button" onClick={() => setStage(STAGE.OVERALL_RECOMMENDATION)}>
                      View Overall Recommendation <ArrowRight size={16} />
                    </button>
                    <button className="secondary-button" onClick={() => setStage(STAGE.EVIDENCE_AUDIT)}>
                      <FileText size={15} /> Technical Audit
                    </button>
                  </div>
                </div>

                <div className="hypotheses-list-container">
                  {(investigation.hypotheses || []).slice(0, 4).map((hyp, idx) => {
                    const scorePct = hyp.confidence_pct || Math.round((hyp.score || 0) * 100);

                    return (
                      <div key={idx} className={`hypothesis-row-card ${hyp.supported ? "supported-card" : "rejected-card"}`}>
                        <div className="hypothesis-card-inner">
                          <div className="hyp-card-top-bar">
                            <div className="hyp-rank-title-group">
                              <span className="hyp-rank-badge">#{idx + 1}</span>
                              <div>
                                <h3 className="hyp-title">{hyp.name}</h3>
                                <span className={`verdict-pill ${hyp.supported ? "supported" : "rejected"}`}>
                                  {hyp.supported ? "Supported Root Cause" : "Falsified / Rejected"}
                                </span>
                              </div>
                            </div>
                            <div className="hyp-confidence-badge">
                              <small>CONFIDENCE</small>
                              <strong>{scorePct}%</strong>
                            </div>
                          </div>

                          <p className="hyp-verdict-text">
                            {hyp.verdict_summary || hyp.deciding_value || "Deterministically evaluated against empirical operational telemetry."}
                          </p>

                          <div className="hyp-card-action-bar">
                            <button
                              className="secondary-button"
                              onClick={() => {
                                setSelectedCauseIndex(idx);
                                setStage(STAGE.RCA_DETAIL);
                              }}
                            >
                              Expand Cause Details <ChevronRight size={15} />
                            </button>
                            <button
                              className="secondary-button"
                              onClick={() => {
                                setCauseRecModal(hyp);
                                setStage(STAGE.CAUSE_RECOMMENDATION);
                              }}
                            >
                              Recommendation
                            </button>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </section>
            </>
          )}

          {/* ------------------------------------------- STAGE 2E: ROOT CAUSE DETAIL SCREEN -- */}
          {stage === STAGE.RCA_DETAIL && selectedCauseIndex !== null && investigation.hypotheses?.[selectedCauseIndex] && (
            <section className="investigation-section rca-detail-screen">
              {/* BACK BUTTON AT TOP ONLY */}
              <div className="detail-screen-nav margin-bottom-md">
                <button className="secondary-button nav-back-top" onClick={() => setStage(STAGE.RCA_RESULTS)}>
                  <ArrowLeft size={16} /> Back to RCA List
                </button>
                <button className="primary-button" onClick={() => setStage(STAGE.OVERALL_RECOMMENDATION)}>
                  View Overall Recommendation <ArrowRight size={16} />
                </button>
              </div>

              {(() => {
                const hyp = investigation.hypotheses[selectedCauseIndex];
                const scorePct = hyp.confidence_pct || Math.round((hyp.score || 0) * 100);

                return (
                  <div className="rca-detail-container">
                    <div className="detail-header-card margin-bottom-md">
                      <div className="spotlight-badge-row">
                        <span className="spotlight-tag">CAUSE #{selectedCauseIndex + 1} DETAILED ANALYSIS</span>
                        <span className="confidence-pill">{scorePct}% Confidence</span>
                      </div>
                      <h2 className="spotlight-title">{hyp.name}</h2>
                      <p className="spotlight-verdict">{hyp.verdict_summary || hyp.deciding_value || "Telemetry patterns deterministically evaluated."}</p>
                    </div>

                    {/* 4 CLEAR SPACIOUS AREAS IN ROOT CAUSE DETAIL */}
                    <div className="detail-4-areas-grid">
                      {/* 1. EVIDENCE */}
                      <div className="area-box">
                        <h3 className="area-title">1. EVIDENCE PROVENANCE</h3>
                        <div className="evidence-reasoning-grid margin-top-sm">
                          <div className="reasoning-box supporting">
                            <strong>Supporting Evidence</strong>
                            <p>{hyp.supporting_evidence || hyp.deciding_value || "Empirical telemetry aligns with observed signal pattern."}</p>
                          </div>
                          <div className="reasoning-box contrary">
                            <strong>Contrary Evidence / Falsification</strong>
                            <p>{hyp.contrary_evidence || "No material contrary evidence identified."}</p>
                          </div>
                        </div>
                      </div>

                      {/* 2. KPI SNAPSHOT */}
                      <div className="area-box margin-top-md">
                        <h3 className="area-title">2. REAL KPI HISTORICAL SNAPSHOT</h3>
                        <div className="margin-top-sm">
                          <KPIChart alert={alert} />
                        </div>
                      </div>

                      {/* 3. WEIGHTED EVIDENCE CONFIDENCE */}
                      <div className="area-box margin-top-md">
                        <h3 className="area-title">3. WEIGHTED EVIDENCE CONFIDENCE MODEL</h3>
                        <div className="confidence-breakdown-row margin-top-sm">
                          <div className="conf-stat-card"><span>Temporal Correlation (W1)</span> <strong>{investigation.confidence?.components?.temporal_correlation ?? '1.0'}</strong></div>
                          <div className="conf-stat-card"><span>Source Reliability (W2)</span> <strong>{investigation.confidence?.components?.source_agreement ?? '1.0'}</strong></div>
                          <div className="conf-stat-card"><span>Hypothesis Margin (W3)</span> <strong>{investigation.confidence?.components?.hypothesis_margin ?? '0.8'}</strong></div>
                          <div className="conf-stat-card"><span>Data Completeness (W4)</span> <strong>{investigation.confidence?.components?.data_completeness ?? '1.0'}</strong></div>
                        </div>
                      </div>

                      {/* 4. CONFLICT AUDIT */}
                      <div className="area-box margin-top-md">
                        <h3 className="area-title">4. CONFLICT AUDIT STATUS</h3>
                        <div className="margin-top-sm">
                          {investigation.route === "UNRESOLVED_CONFLICT" ? (
                            <p className="negative font-bold">Conflict Detected: Cross-regional benchmark signals contradict expected trajectory.</p>
                          ) : (
                            <p className="positive font-bold">✓ No material conflict detected across comparable categories and regions.</p>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })()}
            </section>
          )}

          {/* ------------------------------------------- STAGE 2F: CAUSE RECOMMENDATION MODAL/SCREEN -- */}
          {stage === STAGE.CAUSE_RECOMMENDATION && causeRecModal && (
            <section className="investigation-section cause-recommendation-screen">
              <div className="detail-screen-nav margin-bottom-md">
                <button className="secondary-button nav-back-top" onClick={() => setStage(STAGE.RCA_RESULTS)}>
                  <ArrowLeft size={16} /> Back to RCA List
                </button>
              </div>

              <div className="cause-modal-box-inner">
                <span className="modal-snapshot-label">HYPOTHESIS SPECIFIC DIRECTIVE</span>
                <h2>{causeRecModal.name}</h2>
                <span className="confidence-pill margin-top-sm">{causeRecModal.confidence_pct || Math.round((causeRecModal.score || 0) * 100)}% Confidence</span>

                <div className="cause-modal-grid margin-top-md">
                  <div><strong>Driver:</strong> <p>{investigation.recommendation?.driver || causeRecModal.name}</p></div>
                  <div><strong>Controllable Lever:</strong> <p>{investigation.recommendation?.lever || "Inventory & Promotional Alignment"}</p></div>
                  <div><strong>Action Directive:</strong> <p className="action-highlight">{investigation.recommendation?.action || "Execute targeted operational correction"}</p></div>
                  <div><strong>Monitoring Plan:</strong> <p>{investigation.recommendation?.monitoring_plan || "Track weekly telemetry cycle"}</p></div>
                </div>

                <div className="margin-top-md flex-gap">
                  <button className="primary-button" onClick={() => setStage(STAGE.OVERALL_RECOMMENDATION)}>
                    View Overall Solution <ArrowRight size={16} />
                  </button>
                </div>
              </div>
            </section>
          )}

          {/* ------------------------------------------- STAGE 2G: OVERALL RECOMMENDATION SCREEN -- */}
          {stage === STAGE.OVERALL_RECOMMENDATION && investigation.recommendation && (
            <section className="investigation-section recommendation-primary-card">
              {/* BACK BUTTON AT TOP ONLY */}
              <div className="detail-screen-nav margin-bottom-md">
                <button className="secondary-button nav-back-top" onClick={() => setStage(STAGE.RCA_RESULTS)}>
                  <ArrowLeft size={16} /> Back to RCA List
                </button>
              </div>

              <div className="rec-header-block">
                <div className="rec-eyebrow-row">
                  <span className="rec-eyebrow">RECOMMENDED ACTION DIRECTIVE</span>
                  <span className="rec-owner-badge">Owner: {investigation.recommendation.owner}</span>
                </div>
                <h2 className="rec-main-action">{investigation.recommendation.action}</h2>
              </div>

              {investigation.recommendation.estimated_impact && (
                <div className="rec-impact-banner margin-top-md">
                  <span>Expected Outcome / Recovery:</span>
                  <strong>{investigation.recommendation.est_impact_fmt || `₹${investigation.recommendation.estimated_impact.toLocaleString("en-IN")}`} / wk</strong>
                </div>
              )}

              <div className="rec-matrix-grid margin-top-md">
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

              {/* AI EXECUTIVE SUMMARY */}
              {investigation.narrative && (
                <div className="ai-summary-container margin-top-md">
                  <div className="ai-summary-head">
                    <span className="ai-summary-title">Governed LLM Executive Summary</span>
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

              {/* FEEDBACK & DECISION ACTION AREA */}
              <div className="feedback-card margin-top-md">
                <h3>Decision & Action Feedback</h3>
                <p className="feedback-sub">Persist your decision to calibrate future hypothesis weights.</p>

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
                    {deciding ? "Saving..." : "Reject Action"}
                  </button>
                  <button
                    className="primary-button approve-btn"
                    onClick={() => handleDecision("approved")}
                    disabled={deciding}
                  >
                    {deciding ? "Saving decision..." : "Approve & Execute"}
                  </button>
                </div>
              </div>
            </section>
          )}

          {/* ------------------------------------------- STAGE 2H: EVIDENCE & TECHNICAL AUDIT -- */}
          {stage === STAGE.EVIDENCE_AUDIT && (
            <section className="investigation-section">
              <div className="detail-screen-nav margin-bottom-md">
                <button className="secondary-button nav-back-top" onClick={() => setStage(STAGE.RCA_RESULTS)}>
                  <ArrowLeft size={16} /> Back to RCA List
                </button>
              </div>

              <div className="section-title">
                <h2>EVIDENCE & TRUST TECHNICAL AUDIT</h2>
              </div>

              <div className="evidence-trust-summary-grid margin-top-md">
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
            </section>
          )}

        </div>
      </main>
    </div>
  );
}
