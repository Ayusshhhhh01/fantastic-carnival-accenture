import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

export default function KPIChart({ alert }) {
  const hasSeries = alert?.historical_series && Array.isArray(alert.historical_series) && alert.historical_series.length > 0;

  if (!hasSeries) {
    return (
      <div className="kpi-chart-wrapper unavailable">
        <div className="telemetry-unavailable-box">
          <p className="unavailable-title">Historical telemetry unavailable</p>
          <small className="unavailable-subtitle">
            Baseline mean: {alert.baseline_fmt || `₹${(alert.baseline_mean || 0).toLocaleString("en-IN")}`} · Current value: {alert.current_fmt || `₹${(alert.current || 0).toLocaleString("en-IN")}`}
          </small>
        </div>
      </div>
    );
  }

  const isNegativeImpact = (alert.delta_inr || 0) < 0;

  return (
    <div className="kpi-chart-wrapper">
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={alert.historical_series} margin={{ top: 10, right: 20, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="week" stroke="#718096" tick={{ fontSize: 12 }} />
          <YAxis stroke="#718096" tickFormatter={(val) => `₹${(val / 100000).toFixed(1)}L`} tick={{ fontSize: 12 }} />
          <Tooltip
            contentStyle={{
              backgroundColor: "#ffffff",
              border: "1px solid #cbd5e0",
              borderRadius: "6px",
              padding: "8px 12px",
              fontSize: "13px"
            }}
            formatter={(value) => [`₹${Number(value).toLocaleString("en-IN")}`, "Telemetry Value"]}
          />
          <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "6px" }} />
          <Line
            type="monotone"
            dataKey="value"
            stroke={isNegativeImpact ? "#e53e3e" : "#38a169"}
            strokeWidth={2.5}
            dot={{ fill: isNegativeImpact ? "#e53e3e" : "#38a169", r: 4 }}
            name="Actual Telemetry"
          />
          <Line
            type="monotone"
            dataKey="expected"
            stroke="#7800c4"
            strokeWidth={2}
            strokeDasharray="4 4"
            dot={false}
            name="Expected Baseline"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
