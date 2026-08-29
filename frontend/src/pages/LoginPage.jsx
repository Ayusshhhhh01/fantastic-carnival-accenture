import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Activity, ArrowRight, User } from "lucide-react";

export default function LoginPage() {
  const navigate = useNavigate();
  const [selectedPersona, setSelectedPersona] = useState(null);
  const [loading, setLoading] = useState(false);

  const personas = [
    {
      id: "Category Manager",
      title: "Category Manager",
      description: "Electronics, Apparel & Home portfolios",
      icon: "📊",
      scope: "Manage specific product categories"
    },
    {
      id: "CXO",
      title: "CXO Suite",
      description: "Enterprise-wide portfolio view",
      icon: "🏢",
      scope: "Executive business intelligence"
    }
  ];

  const handleContinue = async () => {
    if (!selectedPersona) return;
    
    setLoading(true);
    // Simulate a brief loading state for UX
    setTimeout(() => {
      navigate(`/dashboard?persona=${encodeURIComponent(selectedPersona)}`);
      setLoading(false);
    }, 300);
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
          <Activity size={15} /> Live telemetry
        </div>
      </header>

      <main className="login-main">
        <div className="login-container">
          <div className="login-header">
            <h1>Who are you?</h1>
            <p className="login-subtitle">Select your persona to access tailored causal insights and authorization rules</p>
          </div>

          <div className="login-content">
            <div className="login-section">
              <h2>Select Your Persona</h2>
              <p className="login-description">Choose your perspective to access tailored insights</p>

              <div className="personas-grid">
                {personas.map((persona) => (
                  <div
                    key={persona.id}
                    className={`persona-card ${selectedPersona === persona.id ? "active" : ""}`}
                    onClick={() => setSelectedPersona(persona.id)}
                  >
                    <div className="persona-icon">{persona.icon}</div>
                    <h3>{persona.title}</h3>
                    <p className="persona-desc">{persona.description}</p>
                    <small className="persona-scope">{persona.scope}</small>
                    {selectedPersona === persona.id && <div className="checkmark">✓</div>}
                  </div>
                ))}
              </div>
            </div>

            <div className="login-actions">
              <button
                className="primary-button"
                onClick={handleContinue}
                disabled={!selectedPersona || loading}
              >
                {loading ? "Loading..." : "Continue"}
                <ArrowRight size={16} />
              </button>
            </div>

            <div className="login-footer">
              <p>
                <span className="info-icon">ℹ️</span>
                Your role determines which metrics and recommendations you'll see in the dashboard
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
