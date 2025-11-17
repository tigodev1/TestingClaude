"""
Roblox DataStore Manager - Simple Production App
Bulletproof version with minimal dependencies
"""

import os
import json
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

# Import our API client
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.roblox_api import RobloxDataStoreAPI, OrderedDataStoreAPI, OpenCloudAPI

# Import proxy routes
try:
    from roblox_proxy import app as proxy_app
    HAS_PROXY = True
except ImportError:
    HAS_PROXY = False

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-this')
CORS(app)

# Global state
api_client = None
ordered_api_client = None
cloud_api = None
config_data = {
    'api_key': '',
    'universe_id': ''
}

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'app.db')


def init_db():
    """Initialize SQLite database"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS operations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        operation TEXT,
        datastore TEXT,
        key_name TEXT,
        success INTEGER,
        details TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS backups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        datastore TEXT,
        filename TEXT,
        count INTEGER
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS config (
        id INTEGER PRIMARY KEY,
        api_key TEXT,
        universe_id TEXT,
        updated_at TEXT
    )''')

    conn.commit()
    conn.close()


def save_config_to_db(api_key, universe_id):
    """Save config to database for persistence"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO config (id, api_key, universe_id, updated_at)
                     VALUES (1, ?, ?, ?)''',
                  (api_key, universe_id, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Save config error: {e}")


def load_config_from_db():
    """Load config from database"""
    global api_client, ordered_api_client, cloud_api, config_data
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT api_key, universe_id FROM config WHERE id = 1')
        row = c.fetchone()
        conn.close()

        if row and row[0] and row[1]:
            config_data['api_key'] = row[0]
            config_data['universe_id'] = row[1]
            api_client = RobloxDataStoreAPI(row[0], row[1])
            ordered_api_client = OrderedDataStoreAPI(row[0], row[1])
            cloud_api = OpenCloudAPI(row[0])
            print(f"Loaded config for universe: {row[1]}")
            return True
    except Exception as e:
        print(f"Load config error: {e}")
    return False


def log_operation(op_type, datastore='', key='', success=True, details=''):
    """Log operation to database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''INSERT INTO operations (timestamp, operation, datastore, key_name, success, details)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (datetime.now().isoformat(), op_type, datastore, key, int(success), details))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Log error: {e}")


# Initialize database on startup
init_db()

# Load saved config on startup
load_config_from_db()


@app.route('/')
def index():
    return render_template('index_production.html')


@app.route('/api/config', methods=['GET', 'POST'])
def handle_config():
    global api_client, ordered_api_client, cloud_api, config_data

    try:
        if request.method == 'POST':
            data = request.get_json()

            if not data:
                return jsonify({'error': 'No data provided'}), 400

            api_key = data.get('api_key', '').strip()
            universe_id = data.get('universe_id', '').strip()

            if not api_key or not universe_id:
                return jsonify({'error': 'API key and Universe ID required'}), 400

            if not universe_id.isdigit():
                return jsonify({'error': 'Universe ID must be numeric'}), 400

            # Save config
            config_data['api_key'] = api_key
            config_data['universe_id'] = universe_id

            # Create API clients (both standard and ordered)
            api_client = RobloxDataStoreAPI(api_key, universe_id)
            ordered_api_client = OrderedDataStoreAPI(api_key, universe_id)
            cloud_api = OpenCloudAPI(api_key)

            # Save to database for persistence across restarts
            save_config_to_db(api_key, universe_id)

            log_operation('CONFIG_SAVED', success=True, details=f'Universe: {universe_id}')
            return jsonify({'status': 'success', 'message': 'Configuration saved'})

        # GET request
        return jsonify({
            'has_key': bool(config_data['api_key']),
            'universe_id': config_data['universe_id'],
            'is_configured': api_client is not None
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/test-connection', methods=['POST'])
def test_connection():
    global api_client

    if not api_client:
        return jsonify({'status': 'error', 'message': 'API not configured. Save configuration first.'}), 400

    try:
        # Try to list datastores (limit 1 to be fast)
        result = api_client.list_datastores(limit=1)
        log_operation('TEST_CONNECTION', success=True)
        return jsonify({'status': 'success', 'message': 'Connection successful!'})
    except Exception as e:
        log_operation('TEST_CONNECTION', success=False, details=str(e))
        return jsonify({'status': 'error', 'message': str(e)}), 400


@app.route('/api/datastores/all')
def list_all_datastores():
    if not api_client:
        return jsonify({'error': 'API not configured'}), 400

    try:
        datastores = api_client.list_all_datastores()
        log_operation('LIST_DATASTORES', success=True, details=f'Found {len(datastores)}')
        return jsonify({'datastores': datastores, 'count': len(datastores)})
    except Exception as e:
        log_operation('LIST_DATASTORES', success=False, details=str(e))
        return jsonify({'error': str(e)}), 500


@app.route('/api/entries')
def list_entries():
    if not api_client:
        return jsonify({'error': 'API not configured'}), 400

    try:
        datastore = request.args.get('datastore', '')
        scope = request.args.get('scope', 'global')
        prefix = request.args.get('prefix', '')
        cursor = request.args.get('cursor', '')

        if not datastore:
            return jsonify({'error': 'Datastore name required'}), 400

        result = api_client.list_entries(datastore, scope, prefix, cursor=cursor)
        log_operation('LIST_ENTRIES', datastore, success=True)
        return jsonify(result)
    except Exception as e:
        log_operation('LIST_ENTRIES', request.args.get('datastore', ''), success=False, details=str(e))
        return jsonify({'error': str(e)}), 500


@app.route('/api/entries/all')
def list_all_entries():
    if not api_client:
        return jsonify({'error': 'API not configured'}), 400

    try:
        datastore = request.args.get('datastore', '')
        scope = request.args.get('scope', 'global')
        prefix = request.args.get('prefix', '')

        if not datastore:
            return jsonify({'error': 'Datastore name required'}), 400

        entries = api_client.list_all_entries(datastore, scope, prefix)
        log_operation('LIST_ALL_ENTRIES', datastore, success=True, details=f'Found {len(entries)}')
        return jsonify({'keys': entries, 'count': len(entries)})
    except Exception as e:
        log_operation('LIST_ALL_ENTRIES', request.args.get('datastore', ''), success=False, details=str(e))
        return jsonify({'error': str(e)}), 500


@app.route('/api/entry', methods=['GET', 'POST', 'DELETE'])
def handle_entry():
    if not api_client:
        return jsonify({'error': 'API not configured'}), 400

    datastore = request.args.get('datastore', '')
    key = request.args.get('key', '')
    scope = request.args.get('scope', 'global')

    if not datastore or not key:
        return jsonify({'error': 'Datastore and key required'}), 400

    try:
        if request.method == 'GET':
            value, metadata = api_client.get_entry(datastore, key, scope)
            log_operation('GET_ENTRY', datastore, key, True)
            return jsonify({'value': value, 'metadata': metadata})

        elif request.method == 'POST':
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400

            value = data.get('value')
            user_ids = data.get('user_ids', [])
            attributes = data.get('attributes', {})
            exclusive = data.get('exclusive_create', False)

            result = api_client.set_entry(
                datastore, key, value, scope,
                user_ids=user_ids if user_ids else None,
                attributes=attributes if attributes else None,
                exclusive_create=exclusive
            )
            log_operation('SET_ENTRY', datastore, key, True)
            return jsonify(result)

        elif request.method == 'DELETE':
            api_client.delete_entry(datastore, key, scope)
            log_operation('DELETE_ENTRY', datastore, key, True)
            return jsonify({'status': 'success', 'message': f'Entry {key} deleted'})

    except Exception as e:
        log_operation(request.method + '_ENTRY', datastore, key, False, str(e))
        return jsonify({'error': str(e)}), 500


@app.route('/api/entry/increment', methods=['POST'])
def increment_entry():
    if not api_client:
        return jsonify({'error': 'API not configured'}), 400

    try:
        datastore = request.args.get('datastore', '')
        key = request.args.get('key', '')
        scope = request.args.get('scope', 'global')

        data = request.get_json()
        increment_by = data.get('increment_by', 1)

        result = api_client.increment_entry(datastore, key, increment_by, scope)
        log_operation('INCREMENT_ENTRY', datastore, key, True)
        return jsonify({'value': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/versions')
def list_versions():
    if not api_client:
        return jsonify({'error': 'API not configured'}), 400

    try:
        datastore = request.args.get('datastore', '')
        key = request.args.get('key', '')
        scope = request.args.get('scope', 'global')

        result = api_client.list_versions(datastore, key, scope)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/version')
def get_version():
    if not api_client:
        return jsonify({'error': 'API not configured'}), 400

    try:
        datastore = request.args.get('datastore', '')
        key = request.args.get('key', '')
        version = request.args.get('version', '')
        scope = request.args.get('scope', 'global')

        result = api_client.get_version(datastore, key, version, scope)
        return jsonify({'value': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/bulk/delete', methods=['POST'])
def bulk_delete():
    if not api_client:
        return jsonify({'error': 'API not configured'}), 400

    try:
        data = request.get_json()
        datastore = data.get('datastore', '')
        keys = data.get('keys', [])
        scope = data.get('scope', 'global')

        results = api_client.bulk_delete_entries(datastore, keys, scope)
        success_count = sum(1 for v in results.values() if v)
        log_operation('BULK_DELETE', datastore, success=True, details=f'{success_count}/{len(keys)}')
        return jsonify({'results': results, 'success_count': success_count})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/export', methods=['POST'])
def export_datastore():
    if not api_client:
        return jsonify({'error': 'API not configured'}), 400

    try:
        data = request.get_json()
        datastore = data.get('datastore', '')
        scope = data.get('scope', 'global')
        include_meta = data.get('include_metadata', True)

        export_data = api_client.export_datastore(datastore, scope, include_meta)

        # Save to file
        os.makedirs('backups', exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'backups/{datastore}_{timestamp}.json'

        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)

        # Log backup
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('INSERT INTO backups (timestamp, datastore, filename, count) VALUES (?, ?, ?, ?)',
                  (datetime.now().isoformat(), datastore, filename, len(export_data)))
        conn.commit()
        conn.close()

        log_operation('EXPORT', datastore, success=True, details=f'{len(export_data)} entries')
        return jsonify({
            'status': 'success',
            'filename': filename,
            'entry_count': len(export_data),
            'data': export_data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/import', methods=['POST'])
def import_datastore():
    if not api_client:
        return jsonify({'error': 'API not configured'}), 400

    try:
        data = request.get_json()
        datastore = data.get('datastore', '')
        entries = data.get('entries', [])
        scope = data.get('scope', 'global')
        overwrite = data.get('overwrite', False)

        results = api_client.import_datastore(datastore, entries, scope, overwrite)
        log_operation('IMPORT', datastore, success=True, details=f'{results["success"]} imported')
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats')
def get_stats():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        c.execute('SELECT COUNT(*) FROM operations')
        total = c.fetchone()[0]

        c.execute('SELECT COUNT(*) FROM operations WHERE success = 1')
        success = c.fetchone()[0]

        c.execute('SELECT COUNT(*) FROM operations WHERE success = 0')
        failed = c.fetchone()[0]

        c.execute('SELECT COUNT(*) FROM backups')
        backups = c.fetchone()[0]

        conn.close()

        return jsonify({
            'total_operations': total,
            'successful_operations': success,
            'failed_operations': failed,
            'total_backups': backups
        })
    except Exception as e:
        return jsonify({
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'total_backups': 0
        })


@app.route('/api/history')
def get_history():
    try:
        limit = int(request.args.get('limit', 50))
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT * FROM operations ORDER BY id DESC LIMIT ?', (limit,))
        rows = c.fetchall()
        conn.close()

        history = []
        for row in rows:
            history.append({
                'id': row[0],
                'timestamp': row[1],
                'operation_type': row[2],
                'datastore_name': row[3],
                'key_name': row[4],
                'success': bool(row[5]),
                'error_message': row[6] if not row[5] else ''
            })

        return jsonify({'history': history})
    except Exception as e:
        return jsonify({'history': []})


@app.route('/api/backups')
def list_backups():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT * FROM backups ORDER BY id DESC LIMIT 50')
        rows = c.fetchall()
        conn.close()

        backups = []
        for row in rows:
            backups.append({
                'id': row[0],
                'timestamp': row[1],
                'datastore_name': row[2],
                'backup_file': row[3],
                'entry_count': row[4]
            })

        return jsonify({'backups': backups})
    except Exception as e:
        return jsonify({'backups': []})


@app.route('/api/request-log')
def get_request_log():
    if api_client:
        return jsonify({'log': api_client.get_request_log()})
    return jsonify({'log': []})


@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})


@app.route('/api/rate-limit')
def get_rate_limit():
    """Get current rate limit from API client"""
    if api_client:
        return jsonify({
            'remaining': api_client.rate_limit_remaining,
            'max': 300
        })
    return jsonify({'remaining': 300, 'max': 300})


# Analytics endpoints - Now with real data!
@app.route('/api/analytics/dashboard')
def analytics_dashboard():
    try:
        days = int(request.args.get('days', 30))
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        # Get stats for the time period
        from datetime import timedelta
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        # Total operations
        c.execute('SELECT COUNT(*) FROM operations WHERE timestamp > ?', (cutoff,))
        total = c.fetchone()[0]

        # Successful operations
        c.execute('SELECT COUNT(*) FROM operations WHERE timestamp > ? AND success = 1', (cutoff,))
        successful = c.fetchone()[0]

        # Calculate success rate
        success_rate = round((successful / total * 100) if total > 0 else 100, 1)

        # Read operations (GET, LIST, etc.)
        c.execute('''SELECT COUNT(*) FROM operations WHERE timestamp > ?
                     AND (operation LIKE '%GET%' OR operation LIKE '%LIST%' OR operation LIKE '%VERSION%')''', (cutoff,))
        read_ops = c.fetchone()[0]

        # Write operations (SET, CREATE, INCREMENT, etc.)
        c.execute('''SELECT COUNT(*) FROM operations WHERE timestamp > ?
                     AND (operation LIKE '%SET%' OR operation LIKE '%CREATE%' OR operation LIKE '%INCREMENT%' OR operation LIKE '%IMPORT%')''', (cutoff,))
        write_ops = c.fetchone()[0]

        # Delete operations
        c.execute('''SELECT COUNT(*) FROM operations WHERE timestamp > ? AND operation LIKE '%DELETE%' ''', (cutoff,))
        delete_ops = c.fetchone()[0]

        conn.close()

        return jsonify({
            'success_rate': success_rate,
            'avg_response_time': 150,  # Placeholder - would need request timing
            'read_operations': read_ops,
            'write_operations': write_ops,
            'delete_operations': delete_ops,
            'total_operations': total
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/analytics/timeseries')
def analytics_timeseries():
    try:
        days = int(request.args.get('days', 30))
        from datetime import timedelta
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        # Group operations by day
        c.execute('''SELECT DATE(timestamp) as day, COUNT(*) as total,
                            SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                            SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed
                     FROM operations
                     WHERE timestamp > ?
                     GROUP BY DATE(timestamp)
                     ORDER BY day''', (cutoff,))

        rows = c.fetchall()
        conn.close()

        result = {}
        for row in rows:
            result[row[0]] = {
                'operations': row[1],
                'success': row[2],
                'failed': row[3]
            }

        # Fill in missing days with zeros
        current = datetime.now()
        for i in range(days):
            day = (current - timedelta(days=i)).strftime('%Y-%m-%d')
            if day not in result:
                result[day] = {'operations': 0, 'success': 0, 'failed': 0}

        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/analytics/top-datastores')
def analytics_top_ds():
    try:
        days = int(request.args.get('days', 30))
        limit = int(request.args.get('limit', 5))
        from datetime import timedelta
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        c.execute('''SELECT datastore, COUNT(*) as ops
                     FROM operations
                     WHERE timestamp > ? AND datastore != ''
                     GROUP BY datastore
                     ORDER BY ops DESC
                     LIMIT ?''', (cutoff, limit))

        rows = c.fetchall()
        conn.close()

        datastores = [{'name': row[0], 'operations': row[1]} for row in rows]
        return jsonify({'datastores': datastores})
    except Exception as e:
        return jsonify({'datastores': []})


@app.route('/api/analytics/errors')
def analytics_errors():
    try:
        days = int(request.args.get('days', 7))
        from datetime import timedelta
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        # Total errors
        c.execute('SELECT COUNT(*) FROM operations WHERE timestamp > ? AND success = 0', (cutoff,))
        total_errors = c.fetchone()[0]

        # Error patterns (by details)
        c.execute('''SELECT details, COUNT(*) as cnt
                     FROM operations
                     WHERE timestamp > ? AND success = 0 AND details != ''
                     GROUP BY details
                     ORDER BY cnt DESC
                     LIMIT 10''', (cutoff,))

        error_patterns = {row[0]: row[1] for row in c.fetchall()}

        # Errors by operation type
        c.execute('''SELECT operation, COUNT(*) as cnt
                     FROM operations
                     WHERE timestamp > ? AND success = 0
                     GROUP BY operation
                     ORDER BY cnt DESC''', (cutoff,))

        errors_by_op = {row[0]: row[1] for row in c.fetchall()}

        conn.close()

        return jsonify({
            'total_errors': total_errors,
            'error_patterns': error_patterns,
            'errors_by_operation': errors_by_op
        })
    except Exception as e:
        return jsonify({'total_errors': 0, 'error_patterns': {}, 'errors_by_operation': {}})


# ===== ORDERED DATASTORE ENDPOINTS =====
@app.route('/api/ordered/list')
def list_ordered_entries_route():
    if not ordered_api_client:
        return jsonify({'error': 'API not configured'}), 400

    try:
        datastore = request.args.get('datastore', '')
        scope = request.args.get('scope', 'global')
        ascending = request.args.get('ascending', 'false').lower() == 'true'
        limit = int(request.args.get('limit', 100))

        if not datastore:
            return jsonify({'error': 'Datastore name required'}), 400

        # Use the correct method name
        result = ordered_api_client.list_ordered_entries(datastore, scope, ascending, limit)
        entries = result.get('entries', [])
        log_operation('LIST_ORDERED', datastore, success=True, details=f'Found {len(entries)}')
        return jsonify({'entries': entries, 'count': len(entries)})
    except Exception as e:
        log_operation('LIST_ORDERED', request.args.get('datastore', ''), success=False, details=str(e))
        return jsonify({'error': str(e)}), 500


@app.route('/api/ordered/entry', methods=['GET', 'POST', 'DELETE'])
def handle_ordered_entry():
    if not ordered_api_client:
        return jsonify({'error': 'API not configured'}), 400

    datastore = request.args.get('datastore', '')
    key = request.args.get('key', '')
    scope = request.args.get('scope', 'global')

    if not datastore or not key:
        return jsonify({'error': 'Datastore and key required'}), 400

    try:
        if request.method == 'GET':
            # Ordered datastores don't have a direct "get" - we'd need to list and filter
            # For now, return an error
            return jsonify({'error': 'Direct get not supported for ordered datastores'}), 400

        elif request.method == 'POST':
            data = request.get_json()
            value = int(data.get('value', 0))
            # Create or update ordered entry
            result = ordered_api_client.create_ordered_entry(datastore, key, value, scope)
            log_operation('SET_ORDERED', datastore, key, True)
            return jsonify(result)

        elif request.method == 'DELETE':
            ordered_api_client.delete_ordered_entry(datastore, key, scope)
            log_operation('DELETE_ORDERED', datastore, key, True)
            return jsonify({'status': 'success', 'message': f'Ordered entry {key} deleted'})

    except Exception as e:
        log_operation(request.method + '_ORDERED', datastore, key, False, str(e))
        return jsonify({'error': str(e)}), 500


@app.route('/api/ordered/increment', methods=['POST'])
def increment_ordered():
    if not ordered_api_client:
        return jsonify({'error': 'API not configured'}), 400

    try:
        datastore = request.args.get('datastore', '')
        key = request.args.get('key', '')
        scope = request.args.get('scope', 'global')

        data = request.get_json()
        increment_by = int(data.get('increment_by', 1))

        result = ordered_api_client.increment_ordered_entry(datastore, key, increment_by, scope)
        log_operation('INCREMENT_ORDERED', datastore, key, True)
        return jsonify({'value': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ===== DELETE ALL KEYS =====
@app.route('/api/bulk/delete-all', methods=['POST'])
def delete_all_keys():
    if not api_client:
        return jsonify({'error': 'API not configured'}), 400

    try:
        data = request.get_json()
        datastore = data.get('datastore', '')
        scope = data.get('scope', 'global')
        confirm = data.get('confirm', False)

        if not datastore:
            return jsonify({'error': 'Datastore name required'}), 400

        if not confirm:
            return jsonify({'error': 'Please confirm deletion by setting confirm=true'}), 400

        # First get all keys
        all_keys = api_client.list_all_entries(datastore, scope, '')

        if not all_keys:
            return jsonify({'status': 'success', 'deleted': 0, 'message': 'No keys found'})

        # Delete all keys
        results = api_client.bulk_delete_entries(datastore, [k['key'] for k in all_keys], scope)
        success_count = sum(1 for v in results.values() if v)

        log_operation('DELETE_ALL', datastore, success=True, details=f'{success_count}/{len(all_keys)} deleted')
        return jsonify({
            'status': 'success',
            'deleted': success_count,
            'total': len(all_keys),
            'message': f'Deleted {success_count} of {len(all_keys)} keys'
        })
    except Exception as e:
        log_operation('DELETE_ALL', data.get('datastore', ''), success=False, details=str(e))
        return jsonify({'error': str(e)}), 500


# ===== OPEN CLOUD API ENDPOINTS =====
@app.route('/api/universe/info')
def get_universe_info():
    """Get current universe info and stats"""
    if not cloud_api or not config_data['universe_id']:
        return jsonify({'error': 'API not configured'}), 400

    try:
        universe_id = config_data['universe_id']

        # Get thumbnail
        thumbnail = cloud_api.get_universe_thumbnail(universe_id)

        # Get visits and stats
        visits_data = cloud_api.get_universe_visits(universe_id)
        game_data = {}
        if visits_data.get('data') and len(visits_data['data']) > 0:
            game_data = visits_data['data'][0]

        # Get votes
        votes_data = cloud_api.get_universe_votes(universe_id)
        votes = {}
        if votes_data.get('data') and len(votes_data['data']) > 0:
            votes = votes_data['data'][0]

        return jsonify({
            'universe_id': universe_id,
            'name': game_data.get('name', 'Unknown'),
            'description': game_data.get('description', ''),
            'creator': game_data.get('creator', {}),
            'visits': game_data.get('visits', 0),
            'playing': game_data.get('playing', 0),
            'favorites': game_data.get('favoritedCount', 0),
            'thumbnail': thumbnail,
            'upvotes': votes.get('upVotes', 0),
            'downvotes': votes.get('downVotes', 0),
            'created': game_data.get('created', ''),
            'updated': game_data.get('updated', '')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/user/resolve')
def resolve_user():
    """Resolve username to user ID"""
    if not cloud_api:
        return jsonify({'error': 'API not configured'}), 400

    try:
        username = request.args.get('username', '')
        if not username:
            return jsonify({'error': 'Username required'}), 400

        user_data = cloud_api.get_user_by_username(username)
        return jsonify({
            'id': user_data.get('id'),
            'name': user_data.get('name'),
            'displayName': user_data.get('displayName')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/user/info')
def get_user_info():
    """Get user information with enhanced stats"""
    if not cloud_api:
        return jsonify({'error': 'API not configured'}), 400

    try:
        user_id = request.args.get('user_id', '')
        if not user_id:
            return jsonify({'error': 'User ID required'}), 400

        user_data = cloud_api.get_user_info(user_id)
        thumbnail = cloud_api.get_user_thumbnail(user_id)
        friends_count = cloud_api.get_user_friends_count(user_id)
        followers_count = cloud_api.get_user_followers_count(user_id)

        return jsonify({
            'id': user_data.get('id'),
            'name': user_data.get('name'),
            'displayName': user_data.get('displayName'),
            'description': user_data.get('description', ''),
            'created': user_data.get('created'),
            'isBanned': user_data.get('isBanned', False),
            'thumbnail': thumbnail,
            'friends': friends_count,
            'followers': followers_count
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/user/games')
def get_user_games():
    """Get games created by user with enhanced data"""
    if not cloud_api:
        return jsonify({'error': 'API not configured'}), 400

    try:
        user_id = request.args.get('user_id', '')
        if not user_id:
            return jsonify({'error': 'User ID required'}), 400

        games_data = cloud_api.get_user_games(user_id)
        games = []
        universe_ids = []

        # First pass - collect basic info and universe IDs
        for game in games_data.get('data', []):
            universe_id = str(game.get('id', ''))
            if universe_id:
                universe_ids.append(universe_id)
            games.append({
                'id': game.get('id'),
                'rootPlaceId': game.get('rootPlaceId', ''),
                'name': game.get('name'),
                'description': game.get('description', ''),
                'visits': game.get('placeVisits', 0),
                'playing': game.get('playing', 0),
                'favorites': 0,
                'upvotes': 0,
                'downvotes': 0,
                'created': game.get('created'),
                'updated': game.get('updated'),
                'thumbnail': ''
            })

        # Batch fetch thumbnails (single API call for all games)
        if universe_ids:
            thumbnails = cloud_api.get_game_thumbnails_batch(universe_ids)
            for game in games:
                game['thumbnail'] = thumbnails.get(str(game['id']), '')

        return jsonify({'games': games, 'count': len(games)})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/user/groups')
def get_user_groups():
    """Get groups user is a member of"""
    if not cloud_api:
        return jsonify({'error': 'API not configured'}), 400

    try:
        user_id = request.args.get('user_id', '')
        if not user_id:
            return jsonify({'error': 'User ID required'}), 400

        groups_data = cloud_api.get_user_groups(user_id)
        groups = []
        group_ids = []

        # First pass - collect group info and IDs
        for group_entry in groups_data.get('data', []):
            group = group_entry.get('group', {})
            role = group_entry.get('role', {})
            group_id = str(group.get('id', ''))
            if group_id:
                group_ids.append(group_id)

            groups.append({
                'id': group.get('id'),
                'name': group.get('name'),
                'description': group.get('description', ''),
                'memberCount': group.get('memberCount', 0),
                'role': role.get('name', 'Member'),
                'roleRank': role.get('rank', 0),
                'thumbnail': ''
            })

        # Batch fetch thumbnails (single API call)
        if group_ids:
            thumbnails = cloud_api.get_group_thumbnails_batch(group_ids)
            for group in groups:
                group['thumbnail'] = thumbnails.get(str(group['id']), '')

        return jsonify({'groups': groups, 'count': len(groups)})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/user/group-games')
def get_user_group_games():
    """Get all games from groups the user has HIGH RANK in (100+)"""
    if not cloud_api:
        return jsonify({'error': 'API not configured'}), 400

    try:
        user_id = request.args.get('user_id', '')
        min_rank = int(request.args.get('min_rank', 100))  # Default: only show if rank 100+
        if not user_id:
            return jsonify({'error': 'User ID required'}), 400

        # First get user's groups
        groups_data = cloud_api.get_user_groups(user_id)
        all_games = []
        seen_ids = set()
        universe_ids = []

        for group_entry in groups_data.get('data', []):
            group = group_entry.get('group', {})
            role = group_entry.get('role', {})
            role_rank = role.get('rank', 0)

            # Only include groups where user has high rank (developer/admin access)
            if role_rank < min_rank:
                continue

            group_id = str(group.get('id', ''))
            group_name = group.get('name', 'Unknown Group')
            role_name = role.get('name', 'Member')

            if not group_id:
                continue

            # Get games for this group
            try:
                games_data = cloud_api.get_group_games(group_id)
                for game in games_data.get('data', []):
                    game_id = game.get('id')
                    if game_id and game_id not in seen_ids:
                        seen_ids.add(game_id)
                        universe_id = str(game_id)
                        universe_ids.append(universe_id)

                        all_games.append({
                            'id': game_id,
                            'rootPlaceId': game.get('rootPlaceId', ''),
                            'name': game.get('name'),
                            'description': game.get('description', ''),
                            'visits': game.get('placeVisits', 0),
                            'playing': game.get('playing', 0),
                            'favorites': 0,
                            'upvotes': 0,
                            'downvotes': 0,
                            'thumbnail': '',
                            'groupName': group_name,
                            'groupId': group_id,
                            'userRole': role_name,
                            'userRank': role_rank
                        })
            except:
                continue  # Skip groups we can't fetch games for

        # Batch fetch thumbnails (single API call for all games)
        if universe_ids:
            thumbnails = cloud_api.get_game_thumbnails_batch(universe_ids)
            for game in all_games:
                game['thumbnail'] = thumbnails.get(str(game['id']), '')

        return jsonify({'games': all_games, 'count': len(all_games)})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/group/info')
def get_group_info():
    """Get group information"""
    if not cloud_api:
        return jsonify({'error': 'API not configured'}), 400

    try:
        group_id = request.args.get('group_id', '')
        if not group_id:
            return jsonify({'error': 'Group ID required'}), 400

        group_data = cloud_api.get_group_info(group_id)
        thumbnail = cloud_api.get_group_thumbnail(group_id)

        return jsonify({
            'id': group_data.get('id'),
            'name': group_data.get('name'),
            'description': group_data.get('description', ''),
            'owner': group_data.get('owner', {}),
            'memberCount': group_data.get('memberCount', 0),
            'isBuildersClubOnly': group_data.get('isBuildersClubOnly', False),
            'publicEntryAllowed': group_data.get('publicEntryAllowed', True),
            'thumbnail': thumbnail
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/group/games')
def get_group_games():
    """Get games owned by group"""
    if not cloud_api:
        return jsonify({'error': 'API not configured'}), 400

    try:
        group_id = request.args.get('group_id', '')
        if not group_id:
            return jsonify({'error': 'Group ID required'}), 400

        games_data = cloud_api.get_group_games(group_id)
        games = []

        for game in games_data.get('data', []):
            universe_id = str(game.get('id', ''))
            thumbnail = cloud_api.get_universe_thumbnail(universe_id) if universe_id else ''

            games.append({
                'id': game.get('id'),
                'name': game.get('name'),
                'description': game.get('description', ''),
                'visits': game.get('placeVisits', 0),
                'created': game.get('created'),
                'updated': game.get('updated'),
                'thumbnail': thumbnail
            })

        return jsonify({'games': games, 'count': len(games)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ===== PROXY ENDPOINTS =====
# Integrated proxy with caching and analytics

import time
import hashlib

# Proxy cache and rate limiting
proxy_cache = {}
PROXY_CACHE_TTL = 60  # seconds
proxy_rate_limits = {}
PROXY_RATE_LIMIT_WINDOW = 60
PROXY_RATE_LIMIT_MAX = 100

PROXY_DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'proxy.db')


def init_proxy_db():
    """Initialize proxy database"""
    conn = sqlite3.connect(PROXY_DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS proxy_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        client_ip TEXT,
        endpoint TEXT,
        roblox_api TEXT,
        method TEXT,
        status_code INTEGER,
        response_time_ms INTEGER,
        cached INTEGER,
        error TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS proxy_stats (
        id INTEGER PRIMARY KEY,
        total_requests INTEGER DEFAULT 0,
        cached_requests INTEGER DEFAULT 0,
        failed_requests INTEGER DEFAULT 0,
        total_bandwidth_kb REAL DEFAULT 0,
        last_updated TEXT
    )''')
    c.execute('INSERT OR IGNORE INTO proxy_stats (id, total_requests, last_updated) VALUES (1, 0, ?)',
              (datetime.now().isoformat(),))
    conn.commit()
    conn.close()


def log_proxy_request(client_ip, endpoint, roblox_api, method, status_code, response_time_ms, cached=False, error=''):
    """Log proxy request"""
    try:
        conn = sqlite3.connect(PROXY_DB_PATH)
        c = conn.cursor()
        c.execute('''INSERT INTO proxy_requests (timestamp, client_ip, endpoint, roblox_api, method, status_code, response_time_ms, cached, error)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (datetime.now().isoformat(), client_ip, endpoint, roblox_api, method, status_code, response_time_ms, int(cached), error))
        c.execute('UPDATE proxy_stats SET total_requests = total_requests + 1, last_updated = ? WHERE id = 1',
                  (datetime.now().isoformat(),))
        if cached:
            c.execute('UPDATE proxy_stats SET cached_requests = cached_requests + 1 WHERE id = 1')
        if status_code >= 400:
            c.execute('UPDATE proxy_stats SET failed_requests = failed_requests + 1 WHERE id = 1')
        conn.commit()
        conn.close()
    except:
        pass


def check_proxy_rate_limit(client_ip):
    """Check rate limit"""
    now = time.time()
    if client_ip not in proxy_rate_limits:
        proxy_rate_limits[client_ip] = {'count': 0, 'window_start': now}
    client_rate = proxy_rate_limits[client_ip]
    if now - client_rate['window_start'] > PROXY_RATE_LIMIT_WINDOW:
        client_rate['count'] = 0
        client_rate['window_start'] = now
    if client_rate['count'] >= PROXY_RATE_LIMIT_MAX:
        return False
    client_rate['count'] += 1
    return True


def get_proxy_cache_key(url, params=None):
    """Generate cache key"""
    key_data = url + json.dumps(params or {}, sort_keys=True)
    return hashlib.md5(key_data.encode()).hexdigest()


def proxy_roblox_request(roblox_url, method='GET', params=None, json_data=None):
    """Make proxied request to Roblox"""
    import requests as req
    start_time = time.time()
    headers = {'User-Agent': 'RobloxProxy/1.0', 'Accept': 'application/json'}
    try:
        if method == 'GET':
            response = req.get(roblox_url, params=params, headers=headers, timeout=30)
        else:
            response = req.post(roblox_url, params=params, json=json_data, headers=headers, timeout=30)
        response_time = int((time.time() - start_time) * 1000)
        try:
            data = response.json()
        except:
            data = {'raw': response.text}
        return data, response.status_code, response_time
    except req.exceptions.Timeout:
        return {'error': 'Timeout'}, 504, int((time.time() - start_time) * 1000)
    except Exception as e:
        return {'error': str(e)}, 500, int((time.time() - start_time) * 1000)


# Initialize proxy DB
init_proxy_db()


@app.route('/proxy/users/<user_id>')
def proxy_user_info(user_id):
    """Proxy user info"""
    client_ip = request.remote_addr
    if not check_proxy_rate_limit(client_ip):
        return jsonify({'error': 'Rate limit exceeded'}), 429
    roblox_url = f"https://users.roblox.com/v1/users/{user_id}"
    cache_key = get_proxy_cache_key(roblox_url)
    if cache_key in proxy_cache and time.time() - proxy_cache[cache_key]['time'] < PROXY_CACHE_TTL:
        log_proxy_request(client_ip, f'/proxy/users/{user_id}', roblox_url, 'GET', 200, 0, cached=True)
        return jsonify(proxy_cache[cache_key]['data'])
    data, status, response_time = proxy_roblox_request(roblox_url)
    log_proxy_request(client_ip, f'/proxy/users/{user_id}', roblox_url, 'GET', status, response_time)
    if status == 200:
        proxy_cache[cache_key] = {'data': data, 'time': time.time()}
    return jsonify(data), status


@app.route('/proxy/users/username', methods=['POST'])
def proxy_username_lookup():
    """Proxy username lookup"""
    client_ip = request.remote_addr
    if not check_proxy_rate_limit(client_ip):
        return jsonify({'error': 'Rate limit exceeded'}), 429
    req_data = request.get_json()
    usernames = req_data.get('usernames', [])
    roblox_url = "https://users.roblox.com/v1/usernames/users"
    data, status, response_time = proxy_roblox_request(roblox_url, method='POST', json_data={'usernames': usernames, 'excludeBannedUsers': False})
    log_proxy_request(client_ip, '/proxy/users/username', roblox_url, 'POST', status, response_time)
    return jsonify(data), status


@app.route('/proxy/users/<user_id>/games')
def proxy_user_games(user_id):
    """Proxy user games"""
    client_ip = request.remote_addr
    if not check_proxy_rate_limit(client_ip):
        return jsonify({'error': 'Rate limit exceeded'}), 429
    limit = request.args.get('limit', 50)
    access_filter = request.args.get('accessFilter', 2)
    roblox_url = f"https://games.roblox.com/v2/users/{user_id}/games"
    params = {'accessFilter': access_filter, 'limit': limit, 'sortOrder': 'Asc'}
    cache_key = get_proxy_cache_key(roblox_url, params)
    if cache_key in proxy_cache and time.time() - proxy_cache[cache_key]['time'] < PROXY_CACHE_TTL:
        log_proxy_request(client_ip, f'/proxy/users/{user_id}/games', roblox_url, 'GET', 200, 0, cached=True)
        return jsonify(proxy_cache[cache_key]['data'])
    data, status, response_time = proxy_roblox_request(roblox_url, params=params)
    log_proxy_request(client_ip, f'/proxy/users/{user_id}/games', roblox_url, 'GET', status, response_time)
    if status == 200:
        proxy_cache[cache_key] = {'data': data, 'time': time.time()}
    return jsonify(data), status


@app.route('/proxy/groups/<group_id>/games')
def proxy_group_games(group_id):
    """Proxy group games"""
    client_ip = request.remote_addr
    if not check_proxy_rate_limit(client_ip):
        return jsonify({'error': 'Rate limit exceeded'}), 429
    limit = request.args.get('limit', 50)
    access_filter = request.args.get('accessFilter', 2)
    roblox_url = f"https://games.roblox.com/v2/groups/{group_id}/games"
    params = {'accessFilter': access_filter, 'limit': limit, 'sortOrder': 'Asc'}
    cache_key = get_proxy_cache_key(roblox_url, params)
    if cache_key in proxy_cache and time.time() - proxy_cache[cache_key]['time'] < PROXY_CACHE_TTL:
        log_proxy_request(client_ip, f'/proxy/groups/{group_id}/games', roblox_url, 'GET', 200, 0, cached=True)
        return jsonify(proxy_cache[cache_key]['data'])
    data, status, response_time = proxy_roblox_request(roblox_url, params=params)
    log_proxy_request(client_ip, f'/proxy/groups/{group_id}/games', roblox_url, 'GET', status, response_time)
    if status == 200:
        proxy_cache[cache_key] = {'data': data, 'time': time.time()}
    return jsonify(data), status


@app.route('/proxy/thumbnails/games')
def proxy_game_thumbnails():
    """Proxy game thumbnails"""
    client_ip = request.remote_addr
    if not check_proxy_rate_limit(client_ip):
        return jsonify({'error': 'Rate limit exceeded'}), 429
    universe_ids = request.args.get('universeIds', '')
    size = request.args.get('size', '512x512')
    roblox_url = "https://thumbnails.roblox.com/v1/games/icons"
    params = {'universeIds': universe_ids, 'size': size, 'format': 'Png', 'isCircular': 'false'}
    cache_key = get_proxy_cache_key(roblox_url, params)
    if cache_key in proxy_cache and time.time() - proxy_cache[cache_key]['time'] < PROXY_CACHE_TTL:
        log_proxy_request(client_ip, '/proxy/thumbnails/games', roblox_url, 'GET', 200, 0, cached=True)
        return jsonify(proxy_cache[cache_key]['data'])
    data, status, response_time = proxy_roblox_request(roblox_url, params=params)
    log_proxy_request(client_ip, '/proxy/thumbnails/games', roblox_url, 'GET', status, response_time)
    if status == 200:
        proxy_cache[cache_key] = {'data': data, 'time': time.time()}
    return jsonify(data), status


@app.route('/proxy/users/<user_id>/presence')
def proxy_user_presence(user_id):
    """Get user presence (online status)"""
    client_ip = request.remote_addr
    if not check_proxy_rate_limit(client_ip):
        return jsonify({'error': 'Rate limit exceeded'}), 429
    roblox_url = "https://presence.roblox.com/v1/presence/users"
    data, status, response_time = proxy_roblox_request(roblox_url, method='POST', json_data={'userIds': [int(user_id)]})
    log_proxy_request(client_ip, f'/proxy/users/{user_id}/presence', roblox_url, 'POST', status, response_time)
    return jsonify(data), status


@app.route('/proxy/users/<user_id>/badges')
def proxy_user_badges(user_id):
    """Get user badges"""
    client_ip = request.remote_addr
    if not check_proxy_rate_limit(client_ip):
        return jsonify({'error': 'Rate limit exceeded'}), 429
    limit = request.args.get('limit', 100)
    roblox_url = f"https://badges.roblox.com/v1/users/{user_id}/badges"
    params = {'limit': limit, 'sortOrder': 'Desc'}
    cache_key = get_proxy_cache_key(roblox_url, params)
    if cache_key in proxy_cache and time.time() - proxy_cache[cache_key]['time'] < PROXY_CACHE_TTL:
        log_proxy_request(client_ip, f'/proxy/users/{user_id}/badges', roblox_url, 'GET', 200, 0, cached=True)
        return jsonify(proxy_cache[cache_key]['data'])
    data, status, response_time = proxy_roblox_request(roblox_url, params=params)
    log_proxy_request(client_ip, f'/proxy/users/{user_id}/badges', roblox_url, 'GET', status, response_time)
    if status == 200:
        proxy_cache[cache_key] = {'data': data, 'time': time.time()}
    return jsonify(data), status


@app.route('/proxy/users/<user_id>/friends')
def proxy_user_friends(user_id):
    """Get user friends list"""
    client_ip = request.remote_addr
    if not check_proxy_rate_limit(client_ip):
        return jsonify({'error': 'Rate limit exceeded'}), 429
    roblox_url = f"https://friends.roblox.com/v1/users/{user_id}/friends"
    cache_key = get_proxy_cache_key(roblox_url)
    if cache_key in proxy_cache and time.time() - proxy_cache[cache_key]['time'] < PROXY_CACHE_TTL:
        log_proxy_request(client_ip, f'/proxy/users/{user_id}/friends', roblox_url, 'GET', 200, 0, cached=True)
        return jsonify(proxy_cache[cache_key]['data'])
    data, status, response_time = proxy_roblox_request(roblox_url)
    log_proxy_request(client_ip, f'/proxy/users/{user_id}/friends', roblox_url, 'GET', status, response_time)
    if status == 200:
        proxy_cache[cache_key] = {'data': data, 'time': time.time()}
    return jsonify(data), status


@app.route('/proxy/games/<universe_id>/servers')
def proxy_game_servers(universe_id):
    """Get game servers (active servers list)"""
    client_ip = request.remote_addr
    if not check_proxy_rate_limit(client_ip):
        return jsonify({'error': 'Rate limit exceeded'}), 429
    limit = request.args.get('limit', 100)
    server_type = request.args.get('serverType', 'Public')
    roblox_url = f"https://games.roblox.com/v1/games/{universe_id}/servers/{server_type}"
    params = {'limit': limit}
    cache_key = get_proxy_cache_key(roblox_url, params)
    if cache_key in proxy_cache and time.time() - proxy_cache[cache_key]['time'] < 30:  # 30s cache for servers
        log_proxy_request(client_ip, f'/proxy/games/{universe_id}/servers', roblox_url, 'GET', 200, 0, cached=True)
        return jsonify(proxy_cache[cache_key]['data'])
    data, status, response_time = proxy_roblox_request(roblox_url, params=params)
    log_proxy_request(client_ip, f'/proxy/games/{universe_id}/servers', roblox_url, 'GET', status, response_time)
    if status == 200:
        proxy_cache[cache_key] = {'data': data, 'time': time.time()}
    return jsonify(data), status


@app.route('/proxy/games/<universe_id>/passes')
def proxy_game_passes(universe_id):
    """Get game passes for a universe"""
    client_ip = request.remote_addr
    if not check_proxy_rate_limit(client_ip):
        return jsonify({'error': 'Rate limit exceeded'}), 429
    roblox_url = f"https://games.roblox.com/v1/games/{universe_id}/game-passes"
    params = {'limit': 100, 'sortOrder': 'Asc'}
    cache_key = get_proxy_cache_key(roblox_url, params)
    if cache_key in proxy_cache and time.time() - proxy_cache[cache_key]['time'] < PROXY_CACHE_TTL:
        log_proxy_request(client_ip, f'/proxy/games/{universe_id}/passes', roblox_url, 'GET', 200, 0, cached=True)
        return jsonify(proxy_cache[cache_key]['data'])
    data, status, response_time = proxy_roblox_request(roblox_url, params=params)
    log_proxy_request(client_ip, f'/proxy/games/{universe_id}/passes', roblox_url, 'GET', status, response_time)
    if status == 200:
        proxy_cache[cache_key] = {'data': data, 'time': time.time()}
    return jsonify(data), status


@app.route('/proxy/assets/<asset_id>')
def proxy_asset_info(asset_id):
    """Get asset info"""
    client_ip = request.remote_addr
    if not check_proxy_rate_limit(client_ip):
        return jsonify({'error': 'Rate limit exceeded'}), 429
    roblox_url = f"https://economy.roblox.com/v2/assets/{asset_id}/details"
    cache_key = get_proxy_cache_key(roblox_url)
    if cache_key in proxy_cache and time.time() - proxy_cache[cache_key]['time'] < PROXY_CACHE_TTL:
        log_proxy_request(client_ip, f'/proxy/assets/{asset_id}', roblox_url, 'GET', 200, 0, cached=True)
        return jsonify(proxy_cache[cache_key]['data'])
    data, status, response_time = proxy_roblox_request(roblox_url)
    log_proxy_request(client_ip, f'/proxy/assets/{asset_id}', roblox_url, 'GET', status, response_time)
    if status == 200:
        proxy_cache[cache_key] = {'data': data, 'time': time.time()}
    return jsonify(data), status


@app.route('/proxy/badges/<badge_id>')
def proxy_badge_info(badge_id):
    """Get badge info"""
    client_ip = request.remote_addr
    if not check_proxy_rate_limit(client_ip):
        return jsonify({'error': 'Rate limit exceeded'}), 429
    roblox_url = f"https://badges.roblox.com/v1/badges/{badge_id}"
    cache_key = get_proxy_cache_key(roblox_url)
    if cache_key in proxy_cache and time.time() - proxy_cache[cache_key]['time'] < PROXY_CACHE_TTL:
        log_proxy_request(client_ip, f'/proxy/badges/{badge_id}', roblox_url, 'GET', 200, 0, cached=True)
        return jsonify(proxy_cache[cache_key]['data'])
    data, status, response_time = proxy_roblox_request(roblox_url)
    log_proxy_request(client_ip, f'/proxy/badges/{badge_id}', roblox_url, 'GET', status, response_time)
    if status == 200:
        proxy_cache[cache_key] = {'data': data, 'time': time.time()}
    return jsonify(data), status


@app.route('/proxy/groups/<group_id>/roles')
def proxy_group_roles(group_id):
    """Get group roles"""
    client_ip = request.remote_addr
    if not check_proxy_rate_limit(client_ip):
        return jsonify({'error': 'Rate limit exceeded'}), 429
    roblox_url = f"https://groups.roblox.com/v1/groups/{group_id}/roles"
    cache_key = get_proxy_cache_key(roblox_url)
    if cache_key in proxy_cache and time.time() - proxy_cache[cache_key]['time'] < PROXY_CACHE_TTL:
        log_proxy_request(client_ip, f'/proxy/groups/{group_id}/roles', roblox_url, 'GET', 200, 0, cached=True)
        return jsonify(proxy_cache[cache_key]['data'])
    data, status, response_time = proxy_roblox_request(roblox_url)
    log_proxy_request(client_ip, f'/proxy/groups/{group_id}/roles', roblox_url, 'GET', status, response_time)
    if status == 200:
        proxy_cache[cache_key] = {'data': data, 'time': time.time()}
    return jsonify(data), status


@app.route('/proxy/groups/<group_id>/members')
def proxy_group_members(group_id):
    """Get group members"""
    client_ip = request.remote_addr
    if not check_proxy_rate_limit(client_ip):
        return jsonify({'error': 'Rate limit exceeded'}), 429
    limit = request.args.get('limit', 100)
    sort_order = request.args.get('sortOrder', 'Asc')
    roblox_url = f"https://groups.roblox.com/v1/groups/{group_id}/users"
    params = {'limit': limit, 'sortOrder': sort_order}
    cache_key = get_proxy_cache_key(roblox_url, params)
    if cache_key in proxy_cache and time.time() - proxy_cache[cache_key]['time'] < PROXY_CACHE_TTL:
        log_proxy_request(client_ip, f'/proxy/groups/{group_id}/members', roblox_url, 'GET', 200, 0, cached=True)
        return jsonify(proxy_cache[cache_key]['data'])
    data, status, response_time = proxy_roblox_request(roblox_url, params=params)
    log_proxy_request(client_ip, f'/proxy/groups/{group_id}/members', roblox_url, 'GET', status, response_time)
    if status == 200:
        proxy_cache[cache_key] = {'data': data, 'time': time.time()}
    return jsonify(data), status


@app.route('/proxy/catalog/search')
def proxy_catalog_search():
    """Search the catalog"""
    client_ip = request.remote_addr
    if not check_proxy_rate_limit(client_ip):
        return jsonify({'error': 'Rate limit exceeded'}), 429
    keyword = request.args.get('keyword', '')
    category = request.args.get('category', 'All')
    limit = request.args.get('limit', 30)
    roblox_url = "https://catalog.roblox.com/v1/search/items"
    params = {'keyword': keyword, 'category': category, 'limit': limit}
    cache_key = get_proxy_cache_key(roblox_url, params)
    if cache_key in proxy_cache and time.time() - proxy_cache[cache_key]['time'] < PROXY_CACHE_TTL:
        log_proxy_request(client_ip, '/proxy/catalog/search', roblox_url, 'GET', 200, 0, cached=True)
        return jsonify(proxy_cache[cache_key]['data'])
    data, status, response_time = proxy_roblox_request(roblox_url, params=params)
    log_proxy_request(client_ip, '/proxy/catalog/search', roblox_url, 'GET', status, response_time)
    if status == 200:
        proxy_cache[cache_key] = {'data': data, 'time': time.time()}
    return jsonify(data), status


@app.route('/proxy/inventory/<user_id>')
def proxy_user_inventory(user_id):
    """Get user inventory"""
    client_ip = request.remote_addr
    if not check_proxy_rate_limit(client_ip):
        return jsonify({'error': 'Rate limit exceeded'}), 429
    asset_type = request.args.get('assetType', 'Hat')
    limit = request.args.get('limit', 100)
    roblox_url = f"https://inventory.roblox.com/v2/users/{user_id}/inventory/{asset_type}"
    params = {'limit': limit, 'sortOrder': 'Desc'}
    cache_key = get_proxy_cache_key(roblox_url, params)
    if cache_key in proxy_cache and time.time() - proxy_cache[cache_key]['time'] < PROXY_CACHE_TTL:
        log_proxy_request(client_ip, f'/proxy/inventory/{user_id}', roblox_url, 'GET', 200, 0, cached=True)
        return jsonify(proxy_cache[cache_key]['data'])
    data, status, response_time = proxy_roblox_request(roblox_url, params=params)
    log_proxy_request(client_ip, f'/proxy/inventory/{user_id}', roblox_url, 'GET', status, response_time)
    if status == 200:
        proxy_cache[cache_key] = {'data': data, 'time': time.time()}
    return jsonify(data), status


@app.route('/proxy/games/search')
def proxy_games_search():
    """Search games"""
    client_ip = request.remote_addr
    if not check_proxy_rate_limit(client_ip):
        return jsonify({'error': 'Rate limit exceeded'}), 429
    keyword = request.args.get('keyword', '')
    limit = request.args.get('limit', 25)
    roblox_url = "https://games.roblox.com/v1/games/list"
    params = {'keyword': keyword, 'maxRows': limit, 'sortToken': 'relevanceDefault'}
    cache_key = get_proxy_cache_key(roblox_url, params)
    if cache_key in proxy_cache and time.time() - proxy_cache[cache_key]['time'] < PROXY_CACHE_TTL:
        log_proxy_request(client_ip, '/proxy/games/search', roblox_url, 'GET', 200, 0, cached=True)
        return jsonify(proxy_cache[cache_key]['data'])
    data, status, response_time = proxy_roblox_request(roblox_url, params=params)
    log_proxy_request(client_ip, '/proxy/games/search', roblox_url, 'GET', status, response_time)
    if status == 200:
        proxy_cache[cache_key] = {'data': data, 'time': time.time()}
    return jsonify(data), status


@app.route('/proxy/analytics/stats')
def proxy_analytics_stats():
    """Get proxy stats"""
    try:
        conn = sqlite3.connect(PROXY_DB_PATH)
        c = conn.cursor()
        c.execute('SELECT total_requests, cached_requests, failed_requests FROM proxy_stats WHERE id = 1')
        row = c.fetchone()
        conn.close()
        if row:
            cache_hit_rate = (row[1] / row[0] * 100) if row[0] > 0 else 0
            success_rate = ((row[0] - row[2]) / row[0] * 100) if row[0] > 0 else 100
            return jsonify({
                'total_requests': row[0],
                'cached_requests': row[1],
                'failed_requests': row[2],
                'cache_hit_rate': round(cache_hit_rate, 1),
                'success_rate': round(success_rate, 1)
            })
        return jsonify({'error': 'No stats'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/proxy/analytics/top-endpoints')
def proxy_analytics_top_endpoints():
    """Get top endpoints"""
    try:
        days = int(request.args.get('days', 7))
        limit = int(request.args.get('limit', 10))
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        conn = sqlite3.connect(PROXY_DB_PATH)
        c = conn.cursor()
        c.execute('''SELECT endpoint, COUNT(*) as count, AVG(response_time_ms) as avg_time
                     FROM proxy_requests WHERE timestamp > ?
                     GROUP BY endpoint ORDER BY count DESC LIMIT ?''', (cutoff, limit))
        rows = c.fetchall()
        conn.close()
        endpoints = [{'endpoint': row[0], 'count': row[1], 'avg_response_ms': round(row[2], 1)} for row in rows]
        return jsonify({'endpoints': endpoints})
    except Exception as e:
        return jsonify({'endpoints': []})


@app.route('/proxy/analytics/recent')
def proxy_analytics_recent():
    """Get recent requests"""
    try:
        limit = int(request.args.get('limit', 50))
        conn = sqlite3.connect(PROXY_DB_PATH)
        c = conn.cursor()
        c.execute('''SELECT timestamp, client_ip, endpoint, roblox_api, method, status_code, response_time_ms, cached, error
                     FROM proxy_requests ORDER BY id DESC LIMIT ?''', (limit,))
        rows = c.fetchall()
        conn.close()
        requests_list = []
        for row in rows:
            requests_list.append({
                'timestamp': row[0], 'client_ip': row[1], 'endpoint': row[2], 'roblox_api': row[3],
                'method': row[4], 'status_code': row[5], 'response_time_ms': row[6], 'cached': bool(row[7]), 'error': row[8]
            })
        return jsonify({'requests': requests_list})
    except Exception as e:
        return jsonify({'requests': []})


if __name__ == '__main__':
    print('\n' + '='*60)
    print('  Roblox DataStore Manager')
    print('='*60)
    print(f'\n  Running on http://127.0.0.1:8000\n')

    from waitress import serve
    serve(app, host='127.0.0.1', port=8000)
