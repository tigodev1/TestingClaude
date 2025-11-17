"""
Roblox DataStore Manager - Advanced Open Cloud Management Tool
Main Flask Application
"""

import os
import json
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from src.roblox_api import RobloxDataStoreAPI, OrderedDataStoreAPI
import threading
import time

app = Flask(__name__)
CORS(app)

# Global state
api_client = None
ordered_api_client = None
config = {
    "api_key": "",
    "universe_id": "",
    "theme": "dark",
    "auto_refresh": False,
    "refresh_interval": 30
}

# Database for local caching and history
DB_PATH = "data/datastore_manager.db"


def init_database():
    """Initialize SQLite database for caching and history"""
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS operation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            operation_type TEXT,
            datastore_name TEXT,
            key_name TEXT,
            details TEXT,
            success INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cached_datastores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            universe_id TEXT,
            datastore_name TEXT,
            created_time TEXT,
            last_accessed TEXT,
            UNIQUE(universe_id, datastore_name)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookmarked_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            universe_id TEXT,
            datastore_name TEXT,
            key_name TEXT,
            scope TEXT,
            notes TEXT,
            created_at TEXT,
            UNIQUE(universe_id, datastore_name, key_name, scope)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS backup_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            universe_id TEXT,
            datastore_name TEXT,
            backup_file TEXT,
            entry_count INTEGER
        )
    """)

    conn.commit()
    conn.close()


def log_operation(operation_type: str, datastore_name: str, key_name: str, details: str, success: bool):
    """Log operation to history database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO operation_history (timestamp, operation_type, datastore_name, key_name, details, success)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (datetime.now().isoformat(), operation_type, datastore_name, key_name, details, int(success)))
    conn.commit()
    conn.close()


# ===== API ROUTES =====

@app.route("/")
def index():
    """Main dashboard"""
    return render_template("index.html")


@app.route("/api/config", methods=["GET", "POST"])
def handle_config():
    """Get or update configuration"""
    global api_client, ordered_api_client, config

    if request.method == "POST":
        data = request.json
        config.update(data)

        # Initialize API clients
        if config["api_key"] and config["universe_id"]:
            api_client = RobloxDataStoreAPI(config["api_key"], config["universe_id"])
            ordered_api_client = OrderedDataStoreAPI(config["api_key"], config["universe_id"])

        # Save config to file
        os.makedirs("data", exist_ok=True)
        with open("data/config.json", "w") as f:
            # Don't save API key to file for security
            safe_config = {k: v for k, v in config.items() if k != "api_key"}
            json.dump(safe_config, f)

        return jsonify({"status": "success"})

    return jsonify(config)


@app.route("/api/test-connection", methods=["POST"])
def test_connection():
    """Test API connection"""
    global api_client

    if not api_client:
        return jsonify({"status": "error", "message": "API not configured"}), 400

    try:
        datastores = api_client.list_datastores(limit=1)
        return jsonify({
            "status": "success",
            "message": "Connection successful",
            "rate_limit": api_client.get_rate_limit_status()
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route("/api/datastores", methods=["GET"])
def list_datastores():
    """List all datastores"""
    if not api_client:
        return jsonify({"error": "API not configured"}), 400

    try:
        prefix = request.args.get("prefix", "")
        cursor = request.args.get("cursor", "")

        result = api_client.list_datastores(prefix=prefix, cursor=cursor)
        return jsonify(result)
    except Exception as e:
        log_operation("LIST_DATASTORES", "", "", str(e), False)
        return jsonify({"error": str(e)}), 500


@app.route("/api/datastores/all", methods=["GET"])
def list_all_datastores():
    """List all datastores with pagination"""
    if not api_client:
        return jsonify({"error": "API not configured"}), 400

    try:
        datastores = api_client.list_all_datastores()
        log_operation("LIST_ALL_DATASTORES", "", "", f"Found {len(datastores)} datastores", True)
        return jsonify({"datastores": datastores, "count": len(datastores)})
    except Exception as e:
        log_operation("LIST_ALL_DATASTORES", "", "", str(e), False)
        return jsonify({"error": str(e)}), 500


@app.route("/api/entries", methods=["GET"])
def list_entries():
    """List entries in a datastore"""
    if not api_client:
        return jsonify({"error": "API not configured"}), 400

    try:
        datastore_name = request.args.get("datastore", "")
        scope = request.args.get("scope", "global")
        prefix = request.args.get("prefix", "")
        cursor = request.args.get("cursor", "")
        all_scopes = request.args.get("all_scopes", "false").lower() == "true"

        if not datastore_name:
            return jsonify({"error": "Datastore name required"}), 400

        result = api_client.list_entries(datastore_name, scope, prefix, cursor=cursor, all_scopes=all_scopes)
        return jsonify(result)
    except Exception as e:
        log_operation("LIST_ENTRIES", datastore_name, "", str(e), False)
        return jsonify({"error": str(e)}), 500


@app.route("/api/entries/all", methods=["GET"])
def list_all_entries():
    """List all entries with pagination"""
    if not api_client:
        return jsonify({"error": "API not configured"}), 400

    try:
        datastore_name = request.args.get("datastore", "")
        scope = request.args.get("scope", "global")
        prefix = request.args.get("prefix", "")

        if not datastore_name:
            return jsonify({"error": "Datastore name required"}), 400

        entries = api_client.list_all_entries(datastore_name, scope, prefix)
        log_operation("LIST_ALL_ENTRIES", datastore_name, "", f"Found {len(entries)} entries", True)
        return jsonify({"keys": entries, "count": len(entries)})
    except Exception as e:
        log_operation("LIST_ALL_ENTRIES", datastore_name, "", str(e), False)
        return jsonify({"error": str(e)}), 500


@app.route("/api/entry", methods=["GET", "POST", "DELETE"])
def handle_entry():
    """Get, set, or delete an entry"""
    if not api_client:
        return jsonify({"error": "API not configured"}), 400

    datastore_name = request.args.get("datastore", "")
    key = request.args.get("key", "")
    scope = request.args.get("scope", "global")

    if not datastore_name or not key:
        return jsonify({"error": "Datastore name and key required"}), 400

    try:
        if request.method == "GET":
            value, metadata = api_client.get_entry(datastore_name, key, scope)
            log_operation("GET_ENTRY", datastore_name, key, "Success", True)
            return jsonify({
                "value": value,
                "metadata": metadata
            })

        elif request.method == "POST":
            data = request.json
            value = data.get("value")
            user_ids = data.get("user_ids", [])
            attributes = data.get("attributes", {})
            match_version = data.get("match_version")
            exclusive_create = data.get("exclusive_create", False)

            result = api_client.set_entry(
                datastore_name, key, value, scope,
                user_ids=user_ids if user_ids else None,
                attributes=attributes if attributes else None,
                match_version=match_version,
                exclusive_create=exclusive_create
            )
            log_operation("SET_ENTRY", datastore_name, key, json.dumps(value)[:100], True)
            return jsonify(result)

        elif request.method == "DELETE":
            api_client.delete_entry(datastore_name, key, scope)
            log_operation("DELETE_ENTRY", datastore_name, key, "Success", True)
            return jsonify({"status": "success", "message": f"Entry {key} deleted"})

    except Exception as e:
        log_operation(request.method + "_ENTRY", datastore_name, key, str(e), False)
        return jsonify({"error": str(e)}), 500


@app.route("/api/entry/increment", methods=["POST"])
def increment_entry():
    """Increment a numeric entry"""
    if not api_client:
        return jsonify({"error": "API not configured"}), 400

    try:
        datastore_name = request.args.get("datastore", "")
        key = request.args.get("key", "")
        scope = request.args.get("scope", "global")

        data = request.json
        increment_by = data.get("increment_by", 1)
        user_ids = data.get("user_ids", [])
        attributes = data.get("attributes", {})

        if not datastore_name or not key:
            return jsonify({"error": "Datastore name and key required"}), 400

        result = api_client.increment_entry(
            datastore_name, key, increment_by, scope,
            user_ids=user_ids if user_ids else None,
            attributes=attributes if attributes else None
        )
        log_operation("INCREMENT_ENTRY", datastore_name, key, f"Increment by {increment_by}", True)
        return jsonify({"value": result})

    except Exception as e:
        log_operation("INCREMENT_ENTRY", datastore_name, key, str(e), False)
        return jsonify({"error": str(e)}), 500


@app.route("/api/versions", methods=["GET"])
def list_versions():
    """List version history for an entry"""
    if not api_client:
        return jsonify({"error": "API not configured"}), 400

    try:
        datastore_name = request.args.get("datastore", "")
        key = request.args.get("key", "")
        scope = request.args.get("scope", "global")
        sort_order = request.args.get("sort_order", "Descending")

        if not datastore_name or not key:
            return jsonify({"error": "Datastore name and key required"}), 400

        result = api_client.list_versions(datastore_name, key, scope, sort_order)
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/version", methods=["GET"])
def get_version():
    """Get a specific version of an entry"""
    if not api_client:
        return jsonify({"error": "API not configured"}), 400

    try:
        datastore_name = request.args.get("datastore", "")
        key = request.args.get("key", "")
        version = request.args.get("version", "")
        scope = request.args.get("scope", "global")

        if not datastore_name or not key or not version:
            return jsonify({"error": "Datastore name, key, and version required"}), 400

        result = api_client.get_version(datastore_name, key, version, scope)
        return jsonify({"value": result})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/bulk/delete", methods=["POST"])
def bulk_delete():
    """Delete multiple entries"""
    if not api_client:
        return jsonify({"error": "API not configured"}), 400

    try:
        data = request.json
        datastore_name = data.get("datastore", "")
        keys = data.get("keys", [])
        scope = data.get("scope", "global")

        if not datastore_name or not keys:
            return jsonify({"error": "Datastore name and keys required"}), 400

        results = api_client.bulk_delete_entries(datastore_name, keys, scope)
        success_count = sum(1 for v in results.values() if v)
        log_operation("BULK_DELETE", datastore_name, "", f"Deleted {success_count}/{len(keys)} entries", True)
        return jsonify({"results": results, "success_count": success_count})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/export", methods=["POST"])
def export_datastore():
    """Export datastore to JSON"""
    if not api_client:
        return jsonify({"error": "API not configured"}), 400

    try:
        data = request.json
        datastore_name = data.get("datastore", "")
        scope = data.get("scope", "global")
        include_metadata = data.get("include_metadata", True)

        if not datastore_name:
            return jsonify({"error": "Datastore name required"}), 400

        export_data = api_client.export_datastore(datastore_name, scope, include_metadata)

        # Save to file
        os.makedirs("backups", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"backups/{datastore_name}_{timestamp}.json"

        with open(filename, "w") as f:
            json.dump({
                "universe_id": config["universe_id"],
                "datastore_name": datastore_name,
                "scope": scope,
                "exported_at": datetime.now().isoformat(),
                "entry_count": len(export_data),
                "entries": export_data
            }, f, indent=2)

        # Log to database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO backup_history (timestamp, universe_id, datastore_name, backup_file, entry_count)
            VALUES (?, ?, ?, ?, ?)
        """, (datetime.now().isoformat(), config["universe_id"], datastore_name, filename, len(export_data)))
        conn.commit()
        conn.close()

        log_operation("EXPORT", datastore_name, "", f"Exported {len(export_data)} entries to {filename}", True)

        return jsonify({
            "status": "success",
            "filename": filename,
            "entry_count": len(export_data),
            "data": export_data
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/import", methods=["POST"])
def import_datastore():
    """Import data into datastore"""
    if not api_client:
        return jsonify({"error": "API not configured"}), 400

    try:
        data = request.json
        datastore_name = data.get("datastore", "")
        entries = data.get("entries", [])
        scope = data.get("scope", "global")
        overwrite = data.get("overwrite", False)

        if not datastore_name or not entries:
            return jsonify({"error": "Datastore name and entries required"}), 400

        results = api_client.import_datastore(datastore_name, entries, scope, overwrite)
        log_operation("IMPORT", datastore_name, "", f"Imported {results['success']} entries", True)
        return jsonify(results)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/history", methods=["GET"])
def get_history():
    """Get operation history"""
    try:
        limit = int(request.args.get("limit", 50))
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM operation_history
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()

        history = []
        for row in rows:
            history.append({
                "id": row[0],
                "timestamp": row[1],
                "operation_type": row[2],
                "datastore_name": row[3],
                "key_name": row[4],
                "details": row[5],
                "success": bool(row[6])
            })

        return jsonify({"history": history})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/bookmarks", methods=["GET", "POST", "DELETE"])
def handle_bookmarks():
    """Manage bookmarked keys"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        if request.method == "GET":
            cursor.execute("""
                SELECT * FROM bookmarked_keys
                WHERE universe_id = ?
                ORDER BY created_at DESC
            """, (config.get("universe_id", ""),))
            rows = cursor.fetchall()
            bookmarks = []
            for row in rows:
                bookmarks.append({
                    "id": row[0],
                    "universe_id": row[1],
                    "datastore_name": row[2],
                    "key_name": row[3],
                    "scope": row[4],
                    "notes": row[5],
                    "created_at": row[6]
                })
            return jsonify({"bookmarks": bookmarks})

        elif request.method == "POST":
            data = request.json
            cursor.execute("""
                INSERT OR REPLACE INTO bookmarked_keys
                (universe_id, datastore_name, key_name, scope, notes, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                config.get("universe_id", ""),
                data.get("datastore_name", ""),
                data.get("key_name", ""),
                data.get("scope", "global"),
                data.get("notes", ""),
                datetime.now().isoformat()
            ))
            conn.commit()
            return jsonify({"status": "success"})

        elif request.method == "DELETE":
            bookmark_id = request.args.get("id", "")
            cursor.execute("DELETE FROM bookmarked_keys WHERE id = ?", (bookmark_id,))
            conn.commit()
            return jsonify({"status": "success"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/backups", methods=["GET"])
def list_backups():
    """List backup history"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM backup_history
            ORDER BY timestamp DESC
            LIMIT 50
        """)
        rows = cursor.fetchall()
        conn.close()

        backups = []
        for row in rows:
            backups.append({
                "id": row[0],
                "timestamp": row[1],
                "universe_id": row[2],
                "datastore_name": row[3],
                "backup_file": row[4],
                "entry_count": row[5]
            })

        return jsonify({"backups": backups})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/request-log", methods=["GET"])
def get_request_log():
    """Get API request log"""
    if not api_client:
        return jsonify({"log": []})

    return jsonify({
        "log": api_client.get_request_log(),
        "rate_limit": api_client.get_rate_limit_status()
    })


@app.route("/api/stats", methods=["GET"])
def get_stats():
    """Get dashboard statistics"""
    stats = {
        "total_operations": 0,
        "successful_operations": 0,
        "failed_operations": 0,
        "total_backups": 0,
        "total_bookmarks": 0
    }

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM operation_history")
        stats["total_operations"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM operation_history WHERE success = 1")
        stats["successful_operations"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM operation_history WHERE success = 0")
        stats["failed_operations"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM backup_history")
        stats["total_backups"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM bookmarked_keys WHERE universe_id = ?",
                       (config.get("universe_id", ""),))
        stats["total_bookmarks"] = cursor.fetchone()[0]

        conn.close()

        if api_client:
            stats["rate_limit"] = api_client.get_rate_limit_status()

    except Exception as e:
        pass

    return jsonify(stats)


# Initialize on startup
init_database()

# Load saved config if exists
if os.path.exists("data/config.json"):
    try:
        with open("data/config.json", "r") as f:
            saved_config = json.load(f)
            config.update(saved_config)
    except:
        pass


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  Roblox DataStore Manager - Advanced Open Cloud Tool")
    print("=" * 60)
    print("\n  Starting server on http://127.0.0.1:5000")
    print("  Press Ctrl+C to stop the server\n")

    # Use Waitress for production-ready server
    from waitress import serve
    serve(app, host="127.0.0.1", port=5000)
