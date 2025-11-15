import React from 'react';
import './StatCard.css';

function StatCard({ title, value, icon, color, subtitle, trend }) {
  const getTrendIcon = () => {
    if (!trend || trend === '0.0') return null;
    const numTrend = parseFloat(trend);
    if (numTrend > 0) return <span className="trend-up">↑ {trend}%</span>;
    if (numTrend < 0) return <span className="trend-down">↓ {Math.abs(trend)}%</span>;
    return null;
  };

  return (
    <div className="stat-card" style={{ '--card-color': color }}>
      <div className="stat-icon">{icon}</div>
      <div className="stat-content">
        <div className="stat-title">{title}</div>
        <div className="stat-value">{value}</div>
        {subtitle && <div className="stat-subtitle">{subtitle}</div>}
        {trend && <div className="stat-trend">{getTrendIcon()}</div>}
      </div>
    </div>
  );
}

export default React.memo(StatCard);
