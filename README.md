# Roblox Analytics Dashboard

An advanced, real-time analytics dashboard for your Roblox games using the Roblox Cloud API. Monitor your game's configuration, platform support, and track changes over time with beautiful visualizations.

## Features

- **Real-time Data Monitoring** - Fetch live data from Roblox Cloud API
- **Beautiful Dashboard** - Modern UI with gradient backgrounds and glass-morphism effects
- **Automatic Data Collection** - Hourly snapshots stored in SQLite database
- **Historical Tracking** - View trends and changes over time with interactive charts
- **Platform Analytics** - Visualize which platforms your game supports
- **Auto-refresh** - Dashboard updates every 5 minutes automatically
- **Responsive Design** - Works on desktop, tablet, and mobile devices

## Screenshots

The dashboard displays:
- Game name, visibility, voice chat status, and private server pricing
- Platform support visualization (Desktop, Mobile, Tablet, Console, VR)
- Game description and place information
- Historical data tracking with line charts
- Social media links
- Server size and creation dates

## Prerequisites

- Node.js (v14 or higher)
- npm or yarn
- A Roblox account with API access
- Your game's Universe ID

## Installation

### 1. Clone or download this repository

```bash
cd /path/to/TestingClaude
```

### 2. Install dependencies

Install both server and client dependencies:

```bash
npm run install-all
```

Or manually:

```bash
# Install server dependencies
npm install

# Install client dependencies
cd client
npm install
cd ..
```

## Configuration

### Getting Your API Key

1. Go to https://create.roblox.com/credentials
2. Click "Create API Key"
3. Give it a name (e.g., "Analytics Dashboard")
4. Select the following permissions:
   - `universe:read`
   - `place:read`
   - `instance:read` (optional, for future features)
5. Add your IP address or use `0.0.0.0/0` for testing (not recommended for production)
6. Copy the generated API key

### Finding Your Universe ID

1. Go to https://create.roblox.com/dashboard/creations
2. Click on your game
3. Look at the URL: `https://create.roblox.com/dashboard/creations/experiences/{UNIVERSE_ID}/...`
4. The number after `/experiences/` is your Universe ID

### Setting Up Environment Variables

1. Copy the example environment file:

```bash
cp .env.example .env
```

2. Edit `.env` and add your credentials:

```env
ROBLOX_API_KEY=your_api_key_here
UNIVERSE_ID=your_universe_id_here
PORT=3001
```

**IMPORTANT:**
- Replace `your_api_key_here` with your actual API key from step 1
- Replace `your_universe_id_here` with your Universe ID from step 2
- Never commit your `.env` file to version control (it's already in `.gitignore`)

## Running the Application

### Development Mode

Run both the server and client simultaneously:

```bash
npm run dev
```

This will start:
- Backend server on http://localhost:3001
- Frontend dashboard on http://localhost:3000

### Production Mode

Build the client:

```bash
npm run build
```

Then serve the built files with your preferred static server.

## API Endpoints

The backend provides the following REST endpoints:

- `GET /api/health` - Check if API key and Universe ID are configured
- `GET /api/universe` - Get current universe data
- `GET /api/places` - Get place information
- `GET /api/analytics/historical?type=universe&period=7d` - Get historical data
  - Types: `universe`, `place`
  - Periods: `1d`, `7d`, `30d`, `90d`
- `GET /api/analytics/summary` - Get comprehensive analytics summary

## How It Works

### Backend (Node.js + Express)

- **Server**: Express.js REST API (`server/index.js`)
- **Roblox Service**: Handles all Roblox Cloud API calls (`server/services/robloxService.js`)
- **Database Service**: SQLite database for storing historical snapshots (`server/services/dbService.js`)
- **Cron Jobs**: Automatic hourly data collection using `node-cron`

### Frontend (React)

- **Dashboard**: Main analytics view with auto-refresh
- **Charts**: Interactive visualizations using Chart.js
- **Components**:
  - Header with live indicator
  - Stat cards for key metrics
  - Platform support bar chart
  - Historical data line chart
  - Game details and social links

### Database Schema

Two main tables:

1. **universe_snapshots**: Stores universe data over time
   - Tracks: name, description, visibility, platform support, voice chat, etc.

2. **place_snapshots**: Stores place data over time
   - Tracks: place name, server size, creation time, etc.

## Troubleshooting

### "ROBLOX_API_KEY not configured" error

- Make sure you've created a `.env` file (not `.env.example`)
- Check that `ROBLOX_API_KEY` is set in your `.env` file
- Restart the server after changing `.env`

### "Failed to fetch universe data" error

- Verify your Universe ID is correct
- Check that your API key has the correct permissions (`universe:read`)
- Make sure your IP address is whitelisted in the API key settings
- Check the server console for detailed error messages

### Port already in use

If port 3001 or 3000 is already in use:

1. Change `PORT` in `.env` to another port (e.g., 3002)
2. Update the proxy in `client/package.json` to match

### Charts not displaying

- Clear your browser cache
- Check the browser console for errors
- Make sure historical data exists (wait for the hourly cron job or refresh manually)

## Data Collection

The system automatically collects data:

- **On demand**: When you click "Refresh Data"
- **Automatic**: Every hour via cron job
- **On startup**: When the server first starts

All data is stored in `analytics.db` SQLite database.

## Project Structure

```
TestingClaude/
├── server/
│   ├── index.js                 # Express server
│   └── services/
│       ├── robloxService.js     # Roblox API integration
│       └── dbService.js         # Database operations
├── client/
│   ├── public/
│   │   └── index.html
│   └── src/
│       ├── components/
│       │   ├── Dashboard.js     # Main dashboard
│       │   ├── Header.js        # App header
│       │   ├── StatCard.js      # Metric cards
│       │   ├── PlatformChart.js # Platform visualization
│       │   ├── HistoricalChart.js # Time-series chart
│       │   └── ErrorBoundary.js # Error handling
│       ├── App.js              # Root component
│       └── index.js            # Entry point
├── .env                        # Your configuration (create this!)
├── .env.example                # Example configuration
├── package.json                # Server dependencies
└── README.md                   # This file
```

## Technologies Used

### Backend
- Node.js
- Express.js
- Axios (HTTP client)
- sql.js (SQLite database - pure JavaScript, works on Windows without build tools)
- node-cron (Scheduled tasks)
- dotenv (Environment variables)

### Frontend
- React 18
- Chart.js & react-chartjs-2 (Charts)
- Recharts (Additional charts)
- Axios (API calls)
- CSS3 (Styling with glass-morphism effects)

## Future Enhancements

Possible features to add:

- Player count tracking (requires additional Roblox APIs)
- Revenue analytics (using economy endpoints)
- Server performance metrics
- Notification system for important changes
- Export data to CSV/Excel
- Multi-game support
- User authentication
- Custom date range selection
- More chart types (heatmaps, radar charts, etc.)

## Security Notes

- **Never commit your `.env` file** - It contains sensitive API keys
- **Restrict API key permissions** - Only grant necessary permissions
- **Whitelist IP addresses** - Don't use `0.0.0.0/0` in production
- **Use HTTPS in production** - Especially if exposing to the internet
- **Rotate API keys regularly** - Good security practice

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

## License

MIT License - feel free to use this for your own Roblox games!

## Support

If you encounter any issues:

1. Check the troubleshooting section above
2. Look at server console logs for detailed errors
3. Check browser console for client-side errors
4. Verify your API key permissions and IP whitelist

## Credits

Created with Roblox Cloud API - https://create.roblox.com/docs/cloud

---

**Happy monitoring!** Track your Roblox game's configuration and watch it grow over time!