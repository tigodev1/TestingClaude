const Database = require('better-sqlite3');
const path = require('path');

class DatabaseService {
  constructor() {
    this.db = null;
  }

  initDatabase() {
    const dbPath = path.join(__dirname, '../../analytics.db');
    this.db = new Database(dbPath);

    // Create tables
    this.db.exec(`
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
      );

      CREATE TABLE IF NOT EXISTS place_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        place_id TEXT,
        display_name TEXT,
        description TEXT,
        server_size INTEGER,
        data TEXT NOT NULL
      );

      CREATE INDEX IF NOT EXISTS idx_universe_timestamp ON universe_snapshots(timestamp);
      CREATE INDEX IF NOT EXISTS idx_place_timestamp ON place_snapshots(timestamp);
    `);

    console.log('✅ Database initialized');
  }

  storeUniverseData(data) {
    if (!this.db) return;

    const stmt = this.db.prepare(`
      INSERT INTO universe_snapshots (
        timestamp, display_name, description, visibility,
        voice_chat_enabled, desktop_enabled, mobile_enabled,
        tablet_enabled, console_enabled, vr_enabled,
        private_server_price, data
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `);

    stmt.run(
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
    );
  }

  storePlaceData(data) {
    if (!this.db) return;

    const stmt = this.db.prepare(`
      INSERT INTO place_snapshots (
        timestamp, place_id, display_name, description,
        server_size, data
      ) VALUES (?, ?, ?, ?, ?, ?)
    `);

    // Extract place ID from path
    let placeId = null;
    if (data.path) {
      const match = data.path.match(/places\/(\d+)/);
      if (match) placeId = match[1];
    }

    stmt.run(
      data.timestamp || new Date().toISOString(),
      placeId,
      data.displayName || null,
      data.description || null,
      data.serverSize || null,
      JSON.stringify(data)
    );
  }

  getHistoricalData(type = 'universe', period = '7d') {
    if (!this.db) return [];

    const periodMap = {
      '1d': 1,
      '7d': 7,
      '30d': 30,
      '90d': 90
    };

    const days = periodMap[period] || 7;
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - days);

    const table = type === 'universe' ? 'universe_snapshots' : 'place_snapshots';

    const stmt = this.db.prepare(`
      SELECT * FROM ${table}
      WHERE timestamp >= ?
      ORDER BY timestamp ASC
    `);

    const rows = stmt.all(cutoffDate.toISOString());

    return rows.map(row => ({
      ...row,
      data: JSON.parse(row.data)
    }));
  }

  getLatestSnapshot(type = 'universe') {
    if (!this.db) return null;

    const table = type === 'universe' ? 'universe_snapshots' : 'place_snapshots';

    const stmt = this.db.prepare(`
      SELECT * FROM ${table}
      ORDER BY timestamp DESC
      LIMIT 1
    `);

    const row = stmt.get();

    if (!row) return null;

    return {
      ...row,
      data: JSON.parse(row.data)
    };
  }

  getStats() {
    if (!this.db) return {};

    const universeCount = this.db.prepare('SELECT COUNT(*) as count FROM universe_snapshots').get();
    const placeCount = this.db.prepare('SELECT COUNT(*) as count FROM place_snapshots').get();

    return {
      totalUniverseSnapshots: universeCount.count,
      totalPlaceSnapshots: placeCount.count
    };
  }
}

module.exports = new DatabaseService();
