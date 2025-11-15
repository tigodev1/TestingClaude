const initSqlJs = require('sql.js');
const fs = require('fs');
const path = require('path');

class DatabaseService {
  constructor() {
    this.db = null;
    this.SQL = null;
    this.dbPath = path.join(__dirname, '../../analytics.db');
  }

  async initDatabase() {
    try {
      // Initialize sql.js
      this.SQL = await initSqlJs();

      // Load existing database or create new one
      if (fs.existsSync(this.dbPath)) {
        const buffer = fs.readFileSync(this.dbPath);
        this.db = new this.SQL.Database(buffer);
      } else {
        this.db = new this.SQL.Database();
      }

      // Create tables
      this.db.run(`
        CREATE TABLE IF NOT EXISTS universe_snapshots (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          timestamp TEXT NOT NULL,
          display_name TEXT,
          description TEXT,
          visibility TEXT,
          voice_chat_enabled INTEGER,
          desktop_enabled INTEGER,
          mobile_enabled INTEGER,
          tablet_enabled INTEGER,
          console_enabled INTEGER,
          vr_enabled INTEGER,
          private_server_price INTEGER,
          data TEXT NOT NULL
        )
      `);

      this.db.run(`
        CREATE TABLE IF NOT EXISTS place_snapshots (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          timestamp TEXT NOT NULL,
          place_id TEXT,
          display_name TEXT,
          description TEXT,
          server_size INTEGER,
          data TEXT NOT NULL
        )
      `);

      this.db.run(`CREATE INDEX IF NOT EXISTS idx_universe_timestamp ON universe_snapshots(timestamp)`);
      this.db.run(`CREATE INDEX IF NOT EXISTS idx_place_timestamp ON place_snapshots(timestamp)`);

      // Create game statistics table for tracking players, visits, likes, etc.
      this.db.run(`
        CREATE TABLE IF NOT EXISTS game_stats_snapshots (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          timestamp TEXT NOT NULL,
          playing INTEGER DEFAULT 0,
          visits INTEGER DEFAULT 0,
          favorites INTEGER DEFAULT 0,
          up_votes INTEGER DEFAULT 0,
          down_votes INTEGER DEFAULT 0,
          max_players INTEGER DEFAULT 0,
          data TEXT NOT NULL
        )
      `);

      this.db.run(`CREATE INDEX IF NOT EXISTS idx_stats_timestamp ON game_stats_snapshots(timestamp)`);

      // Save the database
      this.saveDatabase();

      console.log('✅ Database initialized');
    } catch (error) {
      console.error('❌ Database initialization failed:', error);
    }
  }

  saveDatabase() {
    if (!this.db) return;
    const data = this.db.export();
    fs.writeFileSync(this.dbPath, data);
  }

  storeUniverseData(data) {
    if (!this.db) return;

    try {
      this.db.run(
        `INSERT INTO universe_snapshots (
          timestamp, display_name, description, visibility,
          voice_chat_enabled, desktop_enabled, mobile_enabled,
          tablet_enabled, console_enabled, vr_enabled,
          private_server_price, data
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        [
          data.timestamp || new Date().toISOString(),
          data.displayName || null,
          data.description || null,
          data.visibility || null,
          data.voiceChatEnabled ? 1 : 0,
          data.desktopEnabled ? 1 : 0,
          data.mobileEnabled ? 1 : 0,
          data.tabletEnabled ? 1 : 0,
          data.consoleEnabled ? 1 : 0,
          data.vrEnabled ? 1 : 0,
          data.privateServerPriceRobux || null,
          JSON.stringify(data)
        ]
      );

      // Save after insert
      this.saveDatabase();
    } catch (error) {
      console.error('Error storing universe data:', error);
    }
  }

  storePlaceData(data) {
    if (!this.db) return;

    try {
      // Extract place ID from path
      let placeId = null;
      if (data.path) {
        const match = data.path.match(/places\/(\d+)/);
        if (match) placeId = match[1];
      }

      this.db.run(
        `INSERT INTO place_snapshots (
          timestamp, place_id, display_name, description,
          server_size, data
        ) VALUES (?, ?, ?, ?, ?, ?)`,
        [
          data.timestamp || new Date().toISOString(),
          placeId,
          data.displayName || null,
          data.description || null,
          data.serverSize || null,
          JSON.stringify(data)
        ]
      );

      // Save after insert
      this.saveDatabase();
    } catch (error) {
      console.error('Error storing place data:', error);
    }
  }

  storeGameStats(stats, votes) {
    if (!this.db) return;

    try {
      this.db.run(
        `INSERT INTO game_stats_snapshots (
          timestamp, playing, visits, favorites,
          up_votes, down_votes, max_players, data
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
        [
          stats.timestamp || new Date().toISOString(),
          stats.playing || 0,
          stats.visits || 0,
          stats.favoritedCount || 0,
          votes.upVotes || 0,
          votes.downVotes || 0,
          stats.maxPlayers || 0,
          JSON.stringify({ stats, votes })
        ]
      );

      // Save after insert
      this.saveDatabase();
    } catch (error) {
      console.error('Error storing game stats:', error);
    }
  }

  getHistoricalData(type = 'universe', period = '7d') {
    if (!this.db) return [];

    try {
      const periodMap = {
        '1d': 1,
        '7d': 7,
        '30d': 30,
        '90d': 90
      };

      const days = periodMap[period] || 7;
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - days);

      let table = 'universe_snapshots';
      if (type === 'place') table = 'place_snapshots';
      if (type === 'stats') table = 'game_stats_snapshots';

      const results = this.db.exec(
        `SELECT * FROM ${table} WHERE timestamp >= ? ORDER BY timestamp ASC`,
        [cutoffDate.toISOString()]
      );

      if (!results || results.length === 0) return [];

      const columns = results[0].columns;
      const values = results[0].values;

      return values.map(row => {
        const obj = {};
        columns.forEach((col, idx) => {
          obj[col] = row[idx];
        });
        if (obj.data) {
          obj.data = JSON.parse(obj.data);
        }
        return obj;
      });
    } catch (error) {
      console.error('Error getting historical data:', error);
      return [];
    }
  }

  getLatestSnapshot(type = 'universe') {
    if (!this.db) return null;

    try {
      const table = type === 'universe' ? 'universe_snapshots' : 'place_snapshots';

      const results = this.db.exec(
        `SELECT * FROM ${table} ORDER BY timestamp DESC LIMIT 1`
      );

      if (!results || results.length === 0 || !results[0].values.length) return null;

      const columns = results[0].columns;
      const row = results[0].values[0];

      const obj = {};
      columns.forEach((col, idx) => {
        obj[col] = row[idx];
      });

      if (obj.data) {
        obj.data = JSON.parse(obj.data);
      }

      return obj;
    } catch (error) {
      console.error('Error getting latest snapshot:', error);
      return null;
    }
  }

  getStats() {
    if (!this.db) return {};

    try {
      const universeResults = this.db.exec('SELECT COUNT(*) as count FROM universe_snapshots');
      const placeResults = this.db.exec('SELECT COUNT(*) as count FROM place_snapshots');

      return {
        totalUniverseSnapshots: universeResults[0]?.values[0]?.[0] || 0,
        totalPlaceSnapshots: placeResults[0]?.values[0]?.[0] || 0
      };
    } catch (error) {
      console.error('Error getting stats:', error);
      return {};
    }
  }
}

module.exports = new DatabaseService();
