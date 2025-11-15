const express = require('express');
const cors = require('cors');
const dotenv = require('dotenv');
const cron = require('node-cron');
const robloxService = require('./services/robloxService');
const dbService = require('./services/dbService');

dotenv.config();

const app = express();
const PORT = process.env.PORT || 3001;

// Middleware
app.use(cors());
app.use(express.json());

// Async server startup
async function startServer() {
  // Initialize database
  await dbService.initDatabase();

// API Routes
app.get('/api/universe', async (req, res) => {
  try {
    const universeData = await robloxService.getUniverse();

    // Store in database for historical tracking
    dbService.storeUniverseData(universeData);

    res.json(universeData);
  } catch (error) {
    console.error('Error fetching universe data:', error.message);
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/places', async (req, res) => {
  try {
    const universeData = await robloxService.getUniverse();
    const rootPlaceId = universeData.rootPlaceId;

    if (!rootPlaceId) {
      return res.status(404).json({ error: 'No root place found' });
    }

    const placeData = await robloxService.getPlace(rootPlaceId);

    // Store in database
    dbService.storePlaceData(placeData);

    res.json(placeData);
  } catch (error) {
    console.error('Error fetching place data:', error.message);
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/analytics/historical', async (req, res) => {
  try {
    const { type, period } = req.query;
    const data = dbService.getHistoricalData(type || 'universe', period || '7d');
    res.json(data);
  } catch (error) {
    console.error('Error fetching historical data:', error.message);
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/analytics/summary', async (req, res) => {
  try {
    const summary = {
      universe: await robloxService.getUniverse(),
      historicalStats: {
        universe: dbService.getHistoricalData('universe', '30d'),
        place: dbService.getHistoricalData('place', '30d')
      },
      lastUpdate: new Date().toISOString()
    };

    res.json(summary);
  } catch (error) {
    console.error('Error fetching summary:', error.message);
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/health', (req, res) => {
  res.json({
    status: 'ok',
    timestamp: new Date().toISOString(),
    apiKeyConfigured: !!process.env.ROBLOX_API_KEY,
    universeIdConfigured: !!process.env.UNIVERSE_ID
  });
});

// Automatic data collection - runs every hour
cron.schedule('0 * * * *', async () => {
  console.log('Running scheduled data collection...');
  try {
    const universeData = await robloxService.getUniverse();
    dbService.storeUniverseData(universeData);

    if (universeData.rootPlaceId) {
      const placeData = await robloxService.getPlace(universeData.rootPlaceId);
      dbService.storePlaceData(placeData);
    }

    console.log('Scheduled data collection completed');
  } catch (error) {
    console.error('Error in scheduled collection:', error.message);
  }
});

  app.listen(PORT, () => {
    console.log(`🚀 Roblox Analytics Server running on http://localhost:${PORT}`);
    console.log(`📊 Dashboard will be available at http://localhost:3000`);
    console.log(`⚙️  API Key configured: ${!!process.env.ROBLOX_API_KEY}`);
    console.log(`🎮 Universe ID: ${process.env.UNIVERSE_ID || 'NOT SET'}`);
  });
}

// Start the server
startServer().catch(err => {
  console.error('Failed to start server:', err);
  process.exit(1);
});
