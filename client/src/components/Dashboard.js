import React, { useState, useEffect } from 'react';
import './Dashboard.css';
import StatCard from './StatCard';
import UniverseChart from './UniverseChart';
import PlatformChart from './PlatformChart';
import HistoricalChart from './HistoricalChart';

function Dashboard() {
  const [universeData, setUniverseData] = useState(null);
  const [placeData, setPlaceData] = useState(null);
  const [historicalData, setHistoricalData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);

  useEffect(() => {
    fetchAllData();

    // Auto-refresh every 5 minutes
    const interval = setInterval(fetchAllData, 5 * 60 * 1000);

    return () => clearInterval(interval);
  }, []);

  const fetchAllData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch universe data
      const universeResponse = await fetch('/api/universe');
      if (!universeResponse.ok) throw new Error('Failed to fetch universe data');
      const universe = await universeResponse.json();
      setUniverseData(universe);

      // Fetch place data
      try {
        const placeResponse = await fetch('/api/places');
        if (placeResponse.ok) {
          const place = await placeResponse.json();
          setPlaceData(place);
        }
      } catch (err) {
        console.error('Place data fetch failed:', err);
      }

      // Fetch historical data
      try {
        const historicalResponse = await fetch('/api/analytics/historical?type=universe&period=7d');
        if (historicalResponse.ok) {
          const historical = await historicalResponse.json();
          setHistoricalData(historical);
        }
      } catch (err) {
        console.error('Historical data fetch failed:', err);
      }

      setLastUpdate(new Date());
      setLoading(false);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  if (loading && !universeData) {
    return (
      <div className="dashboard-loading">
        <div className="spinner"></div>
        <p>Loading analytics...</p>
      </div>
    );
  }

  if (error && !universeData) {
    return (
      <div className="dashboard-error">
        <h2>Error Loading Data</h2>
        <p>{error}</p>
        <button onClick={fetchAllData}>Retry</button>
      </div>
    );
  }

  return (
    <div className="dashboard">
      <div className="dashboard-container">
        {lastUpdate && (
          <div className="update-time">
            Last updated: {lastUpdate.toLocaleTimeString()}
          </div>
        )}

        {/* Overview Stats */}
        <div className="stats-grid">
          <StatCard
            title="Game Name"
            value={universeData?.displayName || 'N/A'}
            icon="🎮"
            color="#4caf50"
          />
          <StatCard
            title="Visibility"
            value={universeData?.visibility || 'N/A'}
            icon="👁️"
            color="#2196f3"
          />
          <StatCard
            title="Voice Chat"
            value={universeData?.voiceChatEnabled ? 'Enabled' : 'Disabled'}
            icon="🎤"
            color="#ff9800"
          />
          <StatCard
            title="Private Server Price"
            value={universeData?.privateServerPriceRobux ? `${universeData.privateServerPriceRobux} R$` : 'Free'}
            icon="💰"
            color="#9c27b0"
          />
        </div>

        {/* Platform Support */}
        <div className="chart-section">
          <h2>Platform Support</h2>
          <div className="chart-grid">
            <PlatformChart universeData={universeData} />
          </div>
        </div>

        {/* Game Details */}
        <div className="details-section">
          <div className="detail-card">
            <h3>Game Description</h3>
            <p>{universeData?.description || 'No description available'}</p>
          </div>

          {placeData && (
            <div className="detail-card">
              <h3>Place Information</h3>
              <div className="detail-grid">
                <div className="detail-item">
                  <span className="detail-label">Place Name:</span>
                  <span className="detail-value">{placeData.displayName || 'N/A'}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Max Server Size:</span>
                  <span className="detail-value">{placeData.serverSize || 'N/A'} players</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Created:</span>
                  <span className="detail-value">
                    {placeData.createTime ? new Date(placeData.createTime).toLocaleDateString() : 'N/A'}
                  </span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Last Updated:</span>
                  <span className="detail-value">
                    {placeData.updateTime ? new Date(placeData.updateTime).toLocaleDateString() : 'N/A'}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Historical Data */}
        {historicalData.length > 0 && (
          <div className="chart-section">
            <h2>Historical Tracking ({historicalData.length} snapshots)</h2>
            <HistoricalChart data={historicalData} />
          </div>
        )}

        {/* Social Links */}
        {(universeData?.facebookLink || universeData?.twitterLink ||
          universeData?.youtubeLink || universeData?.discordLink) && (
          <div className="social-section">
            <h3>Social Links</h3>
            <div className="social-links">
              {universeData.facebookLink && (
                <a href={universeData.facebookLink} target="_blank" rel="noopener noreferrer" className="social-link">
                  Facebook
                </a>
              )}
              {universeData.twitterLink && (
                <a href={universeData.twitterLink} target="_blank" rel="noopener noreferrer" className="social-link">
                  Twitter
                </a>
              )}
              {universeData.youtubeLink && (
                <a href={universeData.youtubeLink} target="_blank" rel="noopener noreferrer" className="social-link">
                  YouTube
                </a>
              )}
              {universeData.discordLink && (
                <a href={universeData.discordLink} target="_blank" rel="noopener noreferrer" className="social-link">
                  Discord
                </a>
              )}
            </div>
          </div>
        )}

        <button className="refresh-button" onClick={fetchAllData} disabled={loading}>
          {loading ? 'Refreshing...' : '🔄 Refresh Data'}
        </button>
      </div>
    </div>
  );
}

export default Dashboard;
