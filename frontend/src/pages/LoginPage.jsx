import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Activity, ArrowRight } from "lucide-react";

export default function LoginPage() {
  const navigate = useNavigate();
  const [selectedPersona, setSelectedPersona] = useState(null);
  const [loading, setLoading] = useState(false);

  const personas = [
    {
      id: "Category Manager",
      title: "Category Manager",
      description: "Operational category intelligence",
      icon: "📊",
      scope: "Investigate SKU, regional and supply-demand signals."
    },
    {
      id: "CXO",
      title: "CXO Suite",
      description: "Enterprise portfolio intelligence",
      icon: "🏢",
      scope: "Monitor portfolio-level impact and strategic risk."
    }
  ];

  const handleContinue = () => {
    if (!selectedPersona) return;
    setLoading(true);
    setTimeout(() => {
      navigate(`/dashboard?persona=${encodeURIComponent(selectedPersona)}`);
      setLoading(false);
    }, 200);
  };

  return (
    <div className="login-shell">
      <header className="login-topbar">
        <div className="brand">
          <span>accenture</span>
          <b>&gt;</b>
          <strong>CAUSE</strong>
          <small>CAUSAL INTELLIGENCE</small>
        </div>
        <div className="status-badge">
          <Activity size={15} /> Telemetry connected
        </div>
      </header>

      <main className="login-main">
        <div className="login-container">
          <div className="login-header">
            <h1>Select your perspective</h1>
            <p className="login-subtitle">Choose how you want to investigate business signals.</p>
          </div>

          <div className="login-content">
            <div className="personas-grid-horizontal">
              {personas.map((persona) => {
                const isSelected = selectedPersona === persona.id;
                return (
                  <div
                    key={persona.id}
                    role="button"
                    tabIndex={0}
                    aria-pressed={isSelected}
                    className={`persona-card-item ${isSelected ? "active" : ""}`}
                    onClick={() => setSelectedPersona(persona.id)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        setSelectedPersona(persona.id);
                      }
                    }}
                  >
                    <div className="persona-card-header">
                      <span className="persona-icon-badge">{persona.icon}</span>
                      {isSelected && <span className="checkmark-badge">✓</span>}
                    </div>
                    <h3>{persona.title}</h3>
                    <p className="persona-desc-text">{persona.description}</p>
                    <p className="persona-scope-text">{persona.scope}</p>
                  </div>
                );
              })}
            </div>

            <div className="login-actions-row">
              <button
                className="primary-button continue-btn"
                onClick={handleContinue}
                disabled={!selectedPersona || loading}
              >
                {loading ? "Entering Workspace..." : "Continue"}
                <ArrowRight size={16} />
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
