import React from 'react';
import './StatCard.css';

function StatCard({ title, value, icon, color }) {
  return (
    <div className="stat-card" style={{ '--card-color': color }}>
      <div className="stat-icon">{icon}</div>
      <div className="stat-content">
        <div className="stat-title">{title}</div>
        <div className="stat-value">{value}</div>
      </div>
    </div>
  );
}

export default StatCard;
