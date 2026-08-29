import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

export default function KPIChart({ alert }) {
  const isIllustrative = !alert.historical_series || alert.historical_series.length === 0;

  const data = alert.historical_series && alert.historical_series.length > 0
    ? alert.historical_series
    : [
        { week: "W-4", value: alert.baseline_mean || 100000, expected: alert.baseline_mean || 100000 },
        { week: "W-3", value: alert.baseline_mean || 100000, expected: alert.baseline_mean || 100000 },
        { week: "W-2", value: alert.baseline_mean || 100000, expected: alert.baseline_mean || 100000 },
        { week: "W-1", value: alert.baseline_mean || 100000, expected: alert.baseline_mean || 100000 },
        { week: "Current", value: alert.current || 80000, expected: alert.baseline_mean || 100000 },
      ];

  const isNegativeImpact = (alert.delta_inr || 0) < 0;

  return (
    <div className="kpi-chart-wrapper">
      <div className="chart-header-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <div className="chart-info">
          <div className="chart-stat">
            <span>Baseline</span>
            <strong>{alert.baseline_fmt || `₹${(alert.baseline_mean || 0).toLocaleString("en-IN")}`}</strong>
          </div>
          <div className="chart-stat">
            <span>Current</span>
            <strong className={isNegativeImpact ? "negative" : "positive"}>
              {alert.current_fmt || `₹${(alert.current || 0).toLocaleString("en-IN")}`}
            </strong>
          </div>
          <div className="chart-stat">
            <span>Variance</span>
            <strong className={isNegativeImpact ? "negative" : "positive"}>
              {alert.pct_fmt || (alert.pct_change ? `${(alert.pct_change * 100).toFixed(1)}%` : "N/A")}
            </strong>
          </div>
        </div>
        {isIllustrative && (
          <span style={{ fontSize: '0.8rem', fontStyle: 'italic', color: '#888', background: '#f5f5f5', padding: '4px 8px', borderRadius: '4px' }}>
            Illustrative Baseline Trend (Telemetry Pending)
          </span>
        )}
      </div>

      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data} margin={{ top: 5, right: 30, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e1ddd6" />
          <XAxis dataKey="week" stroke="#77736d" />
          <YAxis stroke="#77736d" tickFormatter={(val) => `₹${(val / 100000).toFixed(1)}L`} />
          <Tooltip
            contentStyle={{
              backgroundColor: "#fffefa",
              border: "1px solid #dfddd8",
              borderRadius: "4px",
              padding: "10px",
            }}
            formatter={(value) => [`₹${Number(value).toLocaleString("en-IN")}`, "Telemetry Value"]}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey="value"
            stroke={isNegativeImpact ? "#a04436" : "#44735a"}
            strokeWidth={2}
            dot={{ fill: isNegativeImpact ? "#a04436" : "#44735a", r: 4 }}
            name="Actual Telemetry"
          />
          <Line
            type="monotone"
            dataKey="expected"
            stroke="#a100ff"
            strokeWidth={2}
            strokeDasharray="5 5"
            dot={false}
            name="Expected Baseline"
          />
        </LineChart>
      </ResponsiveContainer>

      <div className="chart-insight" style={{ marginTop: '8px' }}>
        <p style={{ margin: 0, fontSize: '0.88rem', color: '#555' }}>
          Historical telemetry trend comparing actual observed values against trailing baseline mean.
        </p>
      </div>
    </div>
  );
}
