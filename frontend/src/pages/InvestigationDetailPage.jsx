import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, ChevronDown, ChevronUp, TrendingDown, Zap, Target, AlertCircle } from "lucide-react";
import { investigateAlert, saveDecision } from "../api/index.js";
import KPIChart from "../components/KPIChart.jsx";

export default function InvestigationDetailPage() {
  const { alertId } = useParams();
  const navigate = useNavigate();
  const persona = new URLSearchParams(window.location.search).get("persona") || "Category Manager";
  
  const [investigation, setInvestigation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [expandedHypothesis, setExpandedHypothesis] = useState(null);
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
          <div className="loading">Loading investigation details...</div>
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
        <div className="header-info">
          <span className={`path-badge ${investigation.path_type.toLowerCase()}`}>
            {investigation.path_type === "FAST" ? "🚀 Fast Path" : investigation.path_type === "SLOW" ? "🔍 Detailed Analysis" : "⚠️ Low Evidence"}
          </span>
        </div>
      </header>

      <main className="investigation-main">
        <div className="investigation-container">
          {/* Alert Overview */}
          <section className="investigation-section alert-overview">
            <div className="overview-header">
              <div className="alert-title">
                <h1>{alert.kpi}</h1>
                <p className="alert-meta">{alert.category} · {alert.region} · Week {alert.week_start}</p>
              </div>
              <div className="alert-impact">
                <div className="impact-card">
                  <small>Revenue Impact</small>
                  <strong className={alert.delta_inr < 0 ? "negative" : "positive"}>
                    {alert.delta_fmt}
                  </strong>
                </div>
                <div className="impact-card">
                  <small>Change %</small>
                  <strong className={alert.pct_change < 0 ? "negative" : "positive"}>
                    {alert.pct_change ? `${(alert.pct_change * 100).toFixed(1)}%` : "New Signal"}
                  </strong>
                </div>
              </div>
            </div>
          </section>

          {/* KPI Trend Chart */}
          <section className="investigation-section chart-section">
            <div className="section-title">
              <h2>KPI Trend Analysis</h2>
            </div>
            <div className="chart-container">
              <KPIChart alert={alert} />
            </div>
          </section>

          {isAbstain ? (
            <section className="investigation-section abstention-notice">
              <div className="notice-card warning">
                <AlertCircle size={24} />
                <div>
                  <h3>Diagnostic Abstention</h3>
                  <p>{investigation.abstention?.reason}</p>
                  {investigation.abstention?.required_data && (
                    <small>Required data: {investigation.abstention.required_data}</small>
                  )}
                </div>
              </div>
            </section>
          ) : (
            <>
              {/* Narrative */}
              <section className="investigation-section narrative-section">
                <div className="section-title">
                  <h2>Evidence-Led Finding</h2>
                  <span className="confidence-badge">
                    Confidence: <strong>{investigation.hypothesis?.confidence_pct || Math.round((investigation.confidence?.score || 0) * 100)}%</strong>
                  </span>
                </div>
                <div className="narrative-card">
                  {investigation.narrative ? (
                    <>
                      <p>{investigation.narrative.text}</p>
                      <small className="narrative-meta">{investigation.narrative.engine} · {investigation.narrative.audit}</small>
                    </>
                  ) : (
                    <p>Loading narrative...</p>
                  )}
                </div>
              </section>

              {/* Recommendations */}
              {investigation.recommendation && (
                <section className="investigation-section recommendation-section">
                  <div className="section-title">
                    <h2>Recommended Action</h2>
                  </div>
                  <div className="recommendation-card">
                    <div className="recommendation-header">
                      <h3>{investigation.recommendation.action}</h3>
                      <span className="confidence-label">{investigation.recommendation.confidence}</span>
                    </div>
                    <div className="recommendation-details">
                      <div className="rec-item">
                        <strong>Driver</strong>
                        <p>{investigation.recommendation.driver}</p>
                      </div>
                      <div className="rec-item">
                        <strong>Lever</strong>
                        <p>{investigation.recommendation.lever}</p>
                      </div>
                      <div className="rec-item">
                        <strong>Owner</strong>
                        <p>{investigation.recommendation.owner}</p>
                      </div>
                      <div className="rec-item">
                        <strong>Monitoring Plan</strong>
                        <p>{investigation.recommendation.monitoring_plan}</p>
                      </div>
                      {investigation.recommendation.estimated_impact && (
                        <div className="rec-item">
                          <strong>Estimated Impact</strong>
                          <p>₹{investigation.recommendation.estimated_impact.toLocaleString("en-IN")}</p>
                        </div>
                      )}
                    </div>
                  </div>
                </section>
              )}

              {/* Fast Path Detailed Results */}
              {isFastPath && investigation.hypotheses.length > 0 && (
                <section className="investigation-section hypotheses-section">
                  <div className="section-title">
                    <h2>Verified Root Causes</h2>
                  </div>
                  <div className="hypotheses-list">
                    {investigation.hypotheses.slice(0, 1).map((hyp, idx) => (
                      <div key={idx} className="hypothesis-card primary">
                        <div className="hypothesis-header">
                          <div className="hypothesis-info">
                            <h3>{hyp.name}</h3>
                            <p className="hypothesis-verdict">{hyp.verdict}</p>
                          </div>
                          <div className="hypothesis-confidence">
                            <strong>{hyp.confidence_pct || Math.round((hyp.score || 0) * 100)}%</strong>
                            <small>Confidence</small>
                          </div>
                        </div>
                        {hyp.detail && (
                          <div className="hypothesis-detail">
                            {Object.entries(hyp.detail).map(([key, value]) => (
                              <div key={key} className="detail-row">
                                <span>{key}</span>
                                <strong>{String(value)}</strong>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {/* Slow Path - Top 5 Results */}
              {isSlowPath && investigation.hypotheses.length > 0 && (
                <section className="investigation-section slow-path-section">
                  <div className="section-title">
                    <h2>Top Hypotheses (Ranked by Confidence)</h2>
                    <span className="count-badge">{investigation.hypotheses.length}</span>
                  </div>
                  <div className="hypotheses-list slow-path">
                    {investigation.hypotheses.slice(0, 5).map((hyp, idx) => (
                      <div key={idx} className="hypothesis-card expandable">
                        <div
                          className="hypothesis-header"
                          onClick={() => setExpandedHypothesis(expandedHypothesis === idx ? null : idx)}
                        >
                          <div className="hypothesis-info">
                            <span className="ranking">#{idx + 1}</span>
                            <h3>{hyp.name}</h3>
                            <p className="hypothesis-verdict">{hyp.verdict}</p>
                          </div>
                          <div className="hypothesis-meta">
                            <div className="hypothesis-confidence">
                              <strong>{hyp.confidence_pct || Math.round((hyp.score || 0) * 100)}%</strong>
                              <small>Confidence</small>
                            </div>
                            <button className="expand-button">
                              {expandedHypothesis === idx ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                            </button>
                          </div>
                        </div>
                        {expandedHypothesis === idx && hyp.detail && (
                          <div className="hypothesis-detail">
                            {Object.entries(hyp.detail).map(([key, value]) => (
                              <div key={key} className="detail-row">
                                <span>{key}</span>
                                <strong>{String(value)}</strong>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {/* Evidence Retrieved */}
              {investigation.rag_evidence && investigation.rag_evidence.length > 0 && (
                <section className="investigation-section evidence-section">
                  <div className="section-title">
                    <h2>Supporting Evidence</h2>
                    <span className="count-badge">{investigation.rag_evidence.length} records</span>
                  </div>
                  <div className="evidence-list">
                    {investigation.rag_evidence.map((evidence, idx) => (
                      <div key={idx} className="evidence-item">
                        <p>{evidence.text || evidence.context || "Evidence retrieved"}</p>
                      </div>
                    ))}
                  </div>
                </section>
              )}
            </>
          )}

          {/* Action Buttons */}
          <section className="investigation-section action-section">
            <div className="action-buttons">
              <button
                className="secondary-button"
                onClick={() => handleDecision("rejected")}
                disabled={deciding}
              >
                Reject
              </button>
              <button
                className="primary-button"
                onClick={() => handleDecision("approved")}
                disabled={deciding}
              >
                {deciding ? "Processing..." : "Approve & Proceed"}
              </button>
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}
