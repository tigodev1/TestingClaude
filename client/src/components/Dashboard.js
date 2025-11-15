import React, { useState, useEffect, useCallback, useMemo } from 'react';
import './Dashboard.css';
import StatCard from './StatCard';
import PlatformChart from './PlatformChart';
import HistoricalChart from './HistoricalChart';
import StatsChart from './StatsChart';
import TrendChart from './TrendChart';

function Dashboard() {
  const [universeData, setUniverseData] = useState(null);
  const [placeData, setPlaceData] = useState(null);
  const [gameStats, setGameStats] = useState(null);
  const [statsHistory, setStatsHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);

  const fetchAllData = useCallback(async () => {
    try {
      if (!loading) setLoading(true);
      setError(null);

      // Fetch all data in parallel for better performance
      const [universeResponse, placeResponse, statsResponse, statsHistoryResponse] = await Promise.all([
        fetch('/api/universe').catch(() => null),
        fetch('/api/places').catch(() => null),
        fetch('/api/stats').catch(() => null),
        fetch('/api/analytics/historical?type=stats&period=7d').catch(() => null)
      ]);

      // Process universe data
      if (universeResponse?.ok) {
        const universe = await universeResponse.json();
        setUniverseData(universe);
      }

      // Process place data
      if (placeResponse?.ok) {
        const place = await placeResponse.json();
        setPlaceData(place);
      }

      // Process game stats
      if (statsResponse?.ok) {
        const stats = await statsResponse.json();
        setGameStats(stats);
      }

      // Process historical stats
      if (statsHistoryResponse?.ok) {
        const history = await statsHistoryResponse.json();
        setStatsHistory(history);
      }

      setLastUpdate(new Date());
      setLoading(false);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  }, [loading]);

  useEffect(() => {
    fetchAllData();

    // Auto-refresh every 2 minutes (reduced from 5 for better real-time data)
    const interval = setInterval(fetchAllData, 2 * 60 * 1000);

    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Calculate like/dislike ratio
  const likeRatio = useMemo(() => {
    if (!gameStats || !gameStats.upVotes) return 0;
    const total = gameStats.upVotes + gameStats.downVotes;
    if (total === 0) return 0;
    return ((gameStats.upVotes / total) * 100).toFixed(1);
  }, [gameStats]);

  // Calculate growth from historical data
  const calculateGrowth = useCallback((metric) => {
    if (!statsHistory || statsHistory.length < 2) return null;

    const latest = statsHistory[statsHistory.length - 1]?.[metric] || 0;
    const previous = statsHistory[Math.max(0, statsHistory.length - 7)]?.[metric] || 0;

    if (previous === 0) return null;

    const growth = ((latest - previous) / previous) * 100;
    return growth.toFixed(1);
  }, [statsHistory]);

  if (loading && !gameStats) {
    return (
      <div className="dashboard-loading">
        <div className="spinner"></div>
        <p>Loading analytics...</p>
      </div>
    );
  }

  if (error && !gameStats) {
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

        {/* Live Statistics */}
        <div className="section-title">Live Statistics</div>
        <div className="stats-grid">
          <StatCard
            title="Players Online"
            value={gameStats?.playing?.toLocaleString() || '0'}
            icon="👥"
            color="#4caf50"
            subtitle="Currently playing"
            trend={calculateGrowth('playing')}
          />
          <StatCard
            title="Total Visits"
            value={gameStats?.visits?.toLocaleString() || '0'}
            icon="👁️"
            color="#2196f3"
            subtitle="All-time visits"
            trend={calculateGrowth('visits')}
          />
          <StatCard
            title="Favorites"
            value={gameStats?.favoritedCount?.toLocaleString() || '0'}
            icon="⭐"
            color="#ff9800"
            subtitle="Favorited by players"
            trend={calculateGrowth('favorites')}
          />
          <StatCard
            title="Like Ratio"
            value={`${likeRatio}%`}
            icon="👍"
            color="#9c27b0"
            subtitle={`${gameStats?.upVotes?.toLocaleString() || 0} likes`}
          />
        </div>

        {/* Game Information */}
        <div className="section-title">Game Information</div>
        <div className="stats-grid">
          <StatCard
            title="Game Name"
            value={universeData?.displayName || gameStats?.name || 'N/A'}
            icon="🎮"
            color="#4caf50"
          />
          <StatCard
            title="Max Server Size"
            value={placeData?.serverSize || gameStats?.maxPlayers || 'N/A'}
            icon="👤"
            color="#2196f3"
          />
          <StatCard
            title="Voice Chat"
            value={universeData?.voiceChatEnabled ? 'Enabled' : 'Disabled'}
            icon="🎤"
            color="#ff9800"
          />
          <StatCard
            title="Visibility"
            value={universeData?.visibility || 'N/A'}
            icon="🌐"
            color="#9c27b0"
          />
        </div>

        {/* Trending Charts */}
        {statsHistory && statsHistory.length > 0 && (
          <div className="chart-section">
            <h2>📈 Player Trends (Last 7 Days)</h2>
            <TrendChart data={statsHistory} />
          </div>
        )}

        {/* Platform Support */}
        {universeData && (
          <div className="chart-section">
            <h2>Platform Support</h2>
            <div className="chart-grid">
              <PlatformChart universeData={universeData} />
            </div>
          </div>
        )}

        {/* Vote Distribution */}
        {gameStats && (gameStats.upVotes > 0 || gameStats.downVotes > 0) && (
          <div className="chart-section">
            <h2>👍👎 Likes vs Dislikes</h2>
            <StatsChart gameStats={gameStats} />
          </div>
        )}

        {/* Game Details */}
        <div className="details-section">
          <div className="detail-card">
            <h3>Game Description</h3>
            <p>{universeData?.description || gameStats?.description || 'No description available'}</p>
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
                  <span className="detail-label">Created:</span>
                  <span className="detail-value">
                    {gameStats?.created ? new Date(gameStats.created).toLocaleDateString() : 'N/A'}
                  </span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Last Updated:</span>
                  <span className="detail-value">
                    {gameStats?.updated ? new Date(gameStats.updated).toLocaleDateString() : 'N/A'}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Refresh Button */}
        <button className="refresh-button" onClick={fetchAllData} disabled={loading}>
          {loading ? '🔄 Refreshing...' : '🔄 Refresh Data'}
        </button>
      </div>
    </div>
  );
}

export default React.memo(Dashboard);
