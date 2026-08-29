import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

export default function KPIChart({ alert }) {
  // Generate sample time series data for the KPI trend
  // In production, this would come from actual data
  const generateTrendData = () => {
    const weeks = [];
    const baseValue = Math.abs(alert.delta_inr);
    const volatility = baseValue * 0.15;

    for (let i = 8; i >= 0; i--) {
      const variance = (Math.random() - 0.5) * volatility * 2;
      weeks.push({
        week: `Week -${i}`,
        value: baseValue / 2 + variance,
        expected: baseValue / 2,
      });
    }
    return weeks;
  };

  const data = generateTrendData();
  const isNegativeImpact = alert.delta_inr < 0;

  return (
    <div className="kpi-chart-wrapper">
      <div className="chart-info">
        <div className="chart-stat">
          <span>Baseline</span>
          <strong>₹{(Math.abs(alert.delta_inr) / 2).toLocaleString("en-IN")}</strong>
        </div>
        <div className="chart-stat">
          <span>Current</span>
          <strong className={isNegativeImpact ? "negative" : "positive"}>
            ₹{Math.abs(alert.delta_inr).toLocaleString("en-IN")}
          </strong>
        </div>
        <div className="chart-stat">
          <span>Variance</span>
          <strong className={isNegativeImpact ? "negative" : "positive"}>
            {alert.pct_change ? `${(alert.pct_change * 100).toFixed(1)}%` : "New"}
          </strong>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e1ddd6" />
          <XAxis dataKey="week" stroke="#77736d" />
          <YAxis stroke="#77736d" />
          <Tooltip
            contentStyle={{
              backgroundColor: "#fffefa",
              border: "1px solid #dfddd8",
              borderRadius: "4px",
              padding: "10px",
            }}
            formatter={(value) => `₹${value.toLocaleString("en-IN")}`}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey="value"
            stroke={isNegativeImpact ? "#a04436" : "#44735a"}
            strokeWidth={2}
            dot={{ fill: isNegativeImpact ? "#a04436" : "#44735a", r: 4 }}
            name="Actual Value"
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

      <div className="chart-insight">
        <p>
          The KPI shows a {isNegativeImpact ? "decline" : "increase"} from the baseline over recent weeks.
          {alert.pct_change && alert.pct_change > 0.2 && " The deviation is significant and requires attention."}
          {alert.pct_change && alert.pct_change < -0.1 && " Recent improvements are visible."}
        </p>
      </div>
    </div>
  );
}
