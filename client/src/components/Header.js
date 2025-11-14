import React from 'react';
import './Header.css';

function Header() {
  return (
    <header className="header">
      <div className="header-content">
        <div className="logo">
          <div className="roblox-icon">
            <svg viewBox="0 0 24 24" fill="currentColor" width="40" height="40">
              <rect x="5" y="5" width="14" height="14" transform="rotate(15 12 12)" />
            </svg>
          </div>
          <div>
            <h1>Roblox Analytics</h1>
            <p>Advanced Game Dashboard</p>
          </div>
        </div>
        <div className="header-actions">
          <div className="live-indicator">
            <span className="pulse"></span>
            Live
          </div>
        </div>
      </div>
    </header>
  );
}

export default Header;
