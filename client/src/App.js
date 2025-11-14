import React, { useState, useEffect } from 'react';
import './App.css';
import Dashboard from './components/Dashboard';
import Header from './components/Header';
import ErrorBoundary from './components/ErrorBoundary';

function App() {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkHealth();
  }, []);

  const checkHealth = async () => {
    try {
      const response = await fetch('/api/health');
      const data = await response.json();
      setHealth(data);
      setLoading(false);
    } catch (error) {
      console.error('Health check failed:', error);
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="App">
        <div className="loading-screen">
          <div className="spinner"></div>
          <p>Loading Roblox Analytics...</p>
        </div>
      </div>
    );
  }

  if (!health?.apiKeyConfigured || !health?.universeIdConfigured) {
    return (
      <div className="App">
        <div className="config-warning">
          <h1>⚙️ Configuration Required</h1>
          <div className="warning-content">
            <p>Please configure your Roblox API credentials:</p>
            <ol>
              <li>Copy <code>.env.example</code> to <code>.env</code></li>
              <li>Set your <code>ROBLOX_API_KEY</code></li>
              <li>Set your <code>UNIVERSE_ID</code></li>
              <li>Restart the server</li>
            </ol>
            <div className="status-checks">
              <p className={health?.apiKeyConfigured ? 'ok' : 'error'}>
                {health?.apiKeyConfigured ? '✅' : '❌'} API Key
              </p>
              <p className={health?.universeIdConfigured ? 'ok' : 'error'}>
                {health?.universeIdConfigured ? '✅' : '❌'} Universe ID
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <ErrorBoundary>
      <div className="App">
        <Header />
        <Dashboard />
      </div>
    </ErrorBoundary>
  );
}

export default App;
