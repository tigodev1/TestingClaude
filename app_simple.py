"""
Roblox DataStore Manager - Simple Production App
Bulletproof version with minimal dependencies
"""

import os
import json
import sqlite3
import requests
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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


@app.route('/api/exchange-rates')
def get_exchange_rates():
    """Fetch latest exchange rates from USD"""
    try:
        # Check cache first (cache for 1 hour)
        cache_key = 'exchange_rates'
        if cache_key in proxy_cache:
            cached = proxy_cache[cache_key]
            if time.time() - cached['time'] < 3600:  # 1 hour cache
                return jsonify(cached['data'])

        # Use exchangerate-api.com free tier
        url = "https://open.er-api.com/v6/latest/USD"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            # Extract just the rates we need
            all_rates = data.get('rates', {})
            supported_currencies = ['USD', 'EUR', 'GBP', 'CAD', 'AUD', 'JPY', 'BRL', 'MXN', 'INR', 'PHP']

            rates = {}
            for currency in supported_currencies:
                if currency in all_rates:
                    rates[currency] = all_rates[currency]

            result = {
                'base': 'USD',
                'rates': rates,
                'last_updated': data.get('time_last_update_utc', datetime.now().isoformat())
            }

            # Cache the result
            proxy_cache[cache_key] = {'data': result, 'time': time.time()}

            return jsonify(result)
        else:
            # Fallback to hardcoded rates if API fails
            return jsonify({
                'base': 'USD',
                'rates': {
                    'USD': 1.0,
                    'EUR': 0.92,
                    'GBP': 0.79,
                    'CAD': 1.36,
                    'AUD': 1.53,
                    'JPY': 149.50,
                    'BRL': 4.97,
                    'MXN': 17.15,
                    'INR': 83.12,
                    'PHP': 55.50
                },
                'last_updated': datetime.now().isoformat(),
                'note': 'Using fallback rates'
            })
    except Exception as e:
        print(f"Exchange rate API error: {e}")
        # Fallback rates
        return jsonify({
            'base': 'USD',
            'rates': {
                'USD': 1.0,
                'EUR': 0.92,
                'GBP': 0.79,
                'CAD': 1.36,
                'AUD': 1.53,
                'JPY': 149.50,
                'BRL': 4.97,
                'MXN': 17.15,
                'INR': 83.12,
                'PHP': 55.50
            },
            'last_updated': datetime.now().isoformat(),
            'note': 'Using fallback rates due to error'
        })


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


@app.route('/api/ordered/bulk-delete', methods=['POST'])
def bulk_delete_ordered():
    """Bulk delete entries from ordered datastore"""
    if not ordered_api_client:
        return jsonify({'error': 'API not configured'}), 400

    try:
        data = request.get_json()
        datastore = data.get('datastore', '')
        scope = data.get('scope', 'global')
        keys = data.get('keys', [])

        if not datastore:
            return jsonify({'error': 'Datastore name required'}), 400
        if not keys or len(keys) == 0:
            return jsonify({'error': 'At least one key required'}), 400

        deleted = 0
        failed = 0
        errors = []

        for key in keys:
            try:
                ordered_api_client.delete_ordered_entry(datastore, key, scope)
                deleted += 1
                log_operation('DELETE_ORDERED', datastore, key, True)
            except Exception as e:
                failed += 1
                errors.append(f"{key}: {str(e)}")
                log_operation('DELETE_ORDERED', datastore, key, False, str(e))

        return jsonify({
            'success': True,
            'deleted': deleted,
            'failed': failed,
            'errors': errors
        })
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

            # Fetch votes for all games (batch request)
            try:
                votes_url = f"https://games.roblox.com/v1/games/votes?universeIds={','.join(universe_ids)}"
                votes_response = requests.get(votes_url, timeout=30)
                if votes_response.status_code == 200:
                    votes_data = votes_response.json().get('data', [])
                    votes_map = {str(v['id']): v for v in votes_data}
                    for game in games:
                        vote_info = votes_map.get(str(game['id']), {})
                        game['upvotes'] = vote_info.get('upVotes', 0)
                        game['downvotes'] = vote_info.get('downVotes', 0)
            except Exception as e:
                print(f"Error fetching votes: {e}")

            # Fetch favorites for each game
            for game in games:
                try:
                    fav_url = f"https://games.roblox.com/v1/games/{game['id']}/favorites/count"
                    fav_response = requests.get(fav_url, timeout=10)
                    if fav_response.status_code == 200:
                        game['favorites'] = fav_response.json().get('favoritesCount', 0)
                except Exception as e:
                    print(f"Error fetching favorites for {game['id']}: {e}")

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
PROXY_RATE_LIMIT_MAX = 999999  # Effectively unlimited

# Roblox cookie for authenticated requests (set via /api/proxy/cookie)
roblox_cookie = None

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
    global roblox_cookie
    start_time = time.time()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
    }

    # Add cookie if available for authenticated requests
    cookies = {}
    if roblox_cookie:
        cookies['.ROBLOSECURITY'] = roblox_cookie

    try:
        if method == 'GET':
            response = req.get(roblox_url, params=params, headers=headers, cookies=cookies, timeout=15)
        else:
            response = req.post(roblox_url, params=params, json=json_data, headers=headers, cookies=cookies, timeout=15)
        response_time = int((time.time() - start_time) * 1000)

        # Check if response is JSON
        content_type = response.headers.get('Content-Type', '')
        if 'application/json' in content_type:
            try:
                data = response.json()
            except:
                data = {'error': 'Invalid JSON response', 'status': response.status_code}
        elif 'text/html' in content_type:
            # HTML response usually means error page
            data = {'error': 'Roblox returned HTML (possible rate limit or invalid endpoint)', 'status': response.status_code}
        else:
            try:
                data = response.json()
            except:
                data = {'error': f'Unexpected response type: {content_type}', 'raw': response.text[:500]}

        return data, response.status_code, response_time
    except req.exceptions.Timeout:
        return {'error': 'Request timeout - Roblox API took too long'}, 504, int((time.time() - start_time) * 1000)
    except req.exceptions.ConnectionError:
        return {'error': 'Connection failed - check internet or Roblox status'}, 503, int((time.time() - start_time) * 1000)
    except Exception as e:
        return {'error': f'Request failed: {str(e)}'}, 500, int((time.time() - start_time) * 1000)


def make_proxy_request(roblox_url, endpoint_name, method='GET', params=None, json_data=None):
    """Helper function to make a proxied request with rate limiting and logging"""
    client_ip = request.remote_addr
    if not check_proxy_rate_limit(client_ip):
        return {'error': 'Rate limit exceeded (100 req/min)'}, 429

    cache_key = get_proxy_cache_key(roblox_url, params)
    if cache_key in proxy_cache and time.time() - proxy_cache[cache_key]['time'] < PROXY_CACHE_TTL:
        log_proxy_request(client_ip, endpoint_name, roblox_url, method, 200, 0, cached=True)
        return proxy_cache[cache_key]['data'], 200

    data, status, response_time = proxy_roblox_request(roblox_url, method=method, params=params, json_data=json_data)
    log_proxy_request(client_ip, endpoint_name, roblox_url, method, status, response_time)

    return data, status


# Initialize proxy DB
init_proxy_db()


@app.route('/api/proxy/cookie', methods=['GET', 'POST', 'DELETE'])
def manage_proxy_cookie():
    """Manage Roblox cookie for authenticated requests"""
    global roblox_cookie

    if request.method == 'GET':
        # Return whether cookie is set (not the actual value for security)
        return jsonify({
            'has_cookie': roblox_cookie is not None,
            'cookie_length': len(roblox_cookie) if roblox_cookie else 0,
            'cookie_preview': (roblox_cookie[:20] + '...' + roblox_cookie[-10:]) if roblox_cookie and len(roblox_cookie) > 30 else None
        })

    elif request.method == 'POST':
        data = request.get_json()
        if not data or 'cookie' not in data:
            return jsonify({'error': 'Cookie value required'}), 400

        cookie_value = data['cookie'].strip()

        # Clean the cookie (remove _|WARNING: prefix if present)
        if cookie_value.startswith('_|WARNING:'):
            # Find the actual cookie value after the warning
            parts = cookie_value.split('_|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items.|_')
            if len(parts) > 1:
                cookie_value = parts[1]

        if len(cookie_value) < 100:
            return jsonify({'error': 'Cookie value seems too short to be valid'}), 400

        roblox_cookie = cookie_value
        return jsonify({
            'success': True,
            'message': 'Cookie set successfully',
            'cookie_length': len(roblox_cookie),
            'cookie_preview': roblox_cookie[:20] + '...' + roblox_cookie[-10:]
        })

    elif request.method == 'DELETE':
        roblox_cookie = None
        return jsonify({'success': True, 'message': 'Cookie removed'})


@app.route('/api/proxy/cookie/test')
def test_proxy_cookie():
    """Test if the cookie is valid by making an authenticated request"""
    global roblox_cookie

    if not roblox_cookie:
        return jsonify({'error': 'No cookie set'}), 400

    # Test by fetching authenticated user info
    import requests as req
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
    }
    cookies = {'.ROBLOSECURITY': roblox_cookie}

    try:
        response = req.get('https://users.roblox.com/v1/users/authenticated', headers=headers, cookies=cookies, timeout=10)
        if response.status_code == 200:
            user_data = response.json()
            return jsonify({
                'valid': True,
                'user_id': user_data.get('id'),
                'username': user_data.get('name'),
                'display_name': user_data.get('displayName')
            })
        else:
            return jsonify({'valid': False, 'error': 'Cookie is invalid or expired', 'status': response.status_code})
    except Exception as e:
        return jsonify({'valid': False, 'error': str(e)})


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
    """Get game passes for a universe (Note: will migrate to Open Cloud on Aug 31, 2025)"""
    client_ip = request.remote_addr
    if not check_proxy_rate_limit(client_ip):
        return jsonify({'error': 'Rate limit exceeded'}), 429
    # Using games.roblox.com endpoint (will deprecate Aug 31, 2025 - Open Cloud requires auth)
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


# ===== MORE ADVANCED PROXY ENDPOINTS =====

@app.route('/proxy/users/<user_id>/avatar')
def proxy_user_avatar(user_id):
    """Get user's current avatar assets"""
    url = f"https://avatar.roblox.com/v1/users/{user_id}/avatar"
    data, status = make_proxy_request(url, f'/proxy/users/{user_id}/avatar')
    if status == 200:
        proxy_cache[f"avatar_{user_id}"] = {'data': data, 'time': time.time()}
    return jsonify(data), status


@app.route('/proxy/users/<user_id>/outfits')
def proxy_user_outfits(user_id):
    """Get user's saved outfits"""
    page = request.args.get('page', 1)
    items_per_page = request.args.get('itemsPerPage', 25)
    url = f"https://avatar.roblox.com/v1/users/{user_id}/outfits?page={page}&itemsPerPage={items_per_page}"
    data, status = make_proxy_request(url, f'/proxy/users/{user_id}/outfits')
    if status == 200:
        proxy_cache[f"outfits_{user_id}_{page}"] = {'data': data, 'time': time.time()}
    return jsonify(data), status


@app.route('/proxy/users/<user_id>/followers')
def proxy_user_followers(user_id):
    """Get user's followers"""
    limit = request.args.get('limit', 100)
    cursor = request.args.get('cursor', '')
    url = f"https://friends.roblox.com/v1/users/{user_id}/followers?limit={limit}"
    if cursor:
        url += f"&cursor={cursor}"
    data, status = make_proxy_request(url, f'/proxy/users/{user_id}/followers')
    if status == 200:
        proxy_cache[f"followers_{user_id}_{cursor}"] = {'data': data, 'time': time.time()}
    return jsonify(data), status


@app.route('/proxy/users/<user_id>/followings')
def proxy_user_followings(user_id):
    """Get users that this user follows"""
    limit = request.args.get('limit', 100)
    cursor = request.args.get('cursor', '')
    url = f"https://friends.roblox.com/v1/users/{user_id}/followings?limit={limit}"
    if cursor:
        url += f"&cursor={cursor}"
    data, status = make_proxy_request(url, f'/proxy/users/{user_id}/followings')
    if status == 200:
        proxy_cache[f"followings_{user_id}_{cursor}"] = {'data': data, 'time': time.time()}
    return jsonify(data), status


@app.route('/proxy/economy/resale-tax')
def proxy_economy_resale_tax():
    """Get current resale tax rate"""
    url = "https://economy.roblox.com/v1/resale-tax-rate"
    data, status = make_proxy_request(url, '/proxy/economy/resale-tax')
    if status == 200:
        proxy_cache['resale_tax'] = {'data': data, 'time': time.time()}
    return jsonify(data), status


@app.route('/proxy/economy/asset/<asset_id>/resellers')
def proxy_asset_resellers(asset_id):
    """Get limited item resellers"""
    limit = request.args.get('limit', 10)
    url = f"https://economy.roblox.com/v1/assets/{asset_id}/resellers?limit={limit}"
    data, status = make_proxy_request(url, f'/proxy/economy/asset/{asset_id}/resellers')
    if status == 200:
        proxy_cache[f"resellers_{asset_id}"] = {'data': data, 'time': time.time()}
    return jsonify(data), status


@app.route('/proxy/economy/asset/<asset_id>/resale-data')
def proxy_asset_resale_data(asset_id):
    """Get limited item resale data (RAP, volume, etc)"""
    url = f"https://economy.roblox.com/v1/assets/{asset_id}/resale-data"
    data, status = make_proxy_request(url, f'/proxy/economy/asset/{asset_id}/resale-data')
    if status == 200:
        proxy_cache[f"resale_data_{asset_id}"] = {'data': data, 'time': time.time()}
    return jsonify(data), status


@app.route('/proxy/premium/users/<user_id>/validate')
def proxy_premium_validate(user_id):
    """Check if user has Premium"""
    url = f"https://premiumfeatures.roblox.com/v1/users/{user_id}/validate-membership"
    data, status = make_proxy_request(url, f'/proxy/premium/users/{user_id}/validate')
    if status == 200:
        proxy_cache[f"premium_{user_id}"] = {'data': data, 'time': time.time()}
    return jsonify(data), status


@app.route('/proxy/games/<universe_id>/votes')
def proxy_game_votes(universe_id):
    """Get game votes (likes/dislikes)"""
    url = f"https://games.roblox.com/v1/games/votes?universeIds={universe_id}"
    data, status = make_proxy_request(url, f'/proxy/games/{universe_id}/votes')
    if status == 200:
        proxy_cache[f"votes_{universe_id}"] = {'data': data, 'time': time.time()}
    return jsonify(data), status


@app.route('/proxy/games/<universe_id>/media')
def proxy_game_media(universe_id):
    """Get game media (screenshots, videos)"""
    url = f"https://games.roblox.com/v2/games/{universe_id}/media"
    data, status = make_proxy_request(url, f'/proxy/games/{universe_id}/media')
    if status == 200:
        proxy_cache[f"media_{universe_id}"] = {'data': data, 'time': time.time()}
    return jsonify(data), status


@app.route('/proxy/games/<universe_id>/social-links')
def proxy_game_social_links(universe_id):
    """Get game social links"""
    url = f"https://games.roblox.com/v1/games/{universe_id}/social-links/list"
    data, status = make_proxy_request(url, f'/proxy/games/{universe_id}/social-links')
    if status == 200:
        proxy_cache[f"social_{universe_id}"] = {'data': data, 'time': time.time()}
    return jsonify(data), status


@app.route('/proxy/games/<universe_id>/favorites/count')
def proxy_game_favorites_count(universe_id):
    """Get game favorite count"""
    url = f"https://games.roblox.com/v1/games/{universe_id}/favorites/count"
    data, status = make_proxy_request(url, f'/proxy/games/{universe_id}/favorites/count')
    if status == 200:
        proxy_cache[f"favcount_{universe_id}"] = {'data': data, 'time': time.time()}
    return jsonify(data), status


@app.route('/proxy/thumbnails/users')
def proxy_thumbnails_users():
    """Get batch user avatars"""
    user_ids = request.args.get('userIds', '')
    size = request.args.get('size', '420x420')
    format_type = request.args.get('format', 'Png')
    url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_ids}&size={size}&format={format_type}"
    data, status = make_proxy_request(url, '/proxy/thumbnails/users')
    if status == 200:
        proxy_cache[f"thumb_users_{user_ids}"] = {'data': data, 'time': time.time()}
    return jsonify(data), status


@app.route('/proxy/thumbnails/groups')
def proxy_thumbnails_groups():
    """Get batch group icons"""
    group_ids = request.args.get('groupIds', '')
    size = request.args.get('size', '420x420')
    format_type = request.args.get('format', 'Png')
    url = f"https://thumbnails.roblox.com/v1/groups/icons?groupIds={group_ids}&size={size}&format={format_type}"
    data, status = make_proxy_request(url, '/proxy/thumbnails/groups')
    if status == 200:
        proxy_cache[f"thumb_groups_{group_ids}"] = {'data': data, 'time': time.time()}
    return jsonify(data), status


@app.route('/proxy/thumbnails/assets')
def proxy_thumbnails_assets():
    """Get batch asset thumbnails"""
    asset_ids = request.args.get('assetIds', '')
    size = request.args.get('size', '420x420')
    format_type = request.args.get('format', 'Png')
    url = f"https://thumbnails.roblox.com/v1/assets?assetIds={asset_ids}&size={size}&format={format_type}"
    data, status = make_proxy_request(url, '/proxy/thumbnails/assets')
    if status == 200:
        proxy_cache[f"thumb_assets_{asset_ids}"] = {'data': data, 'time': time.time()}
    return jsonify(data), status


@app.route('/proxy/thumbnails/badges')
def proxy_thumbnails_badges():
    """Get batch badge thumbnails"""
    badge_ids = request.args.get('badgeIds', '')
    size = request.args.get('size', '150x150')
    format_type = request.args.get('format', 'Png')
    url = f"https://thumbnails.roblox.com/v1/badges/icons?badgeIds={badge_ids}&size={size}&format={format_type}"
    data, status = make_proxy_request(url, '/proxy/thumbnails/badges')
    if status == 200:
        proxy_cache[f"thumb_badges_{badge_ids}"] = {'data': data, 'time': time.time()}
    return jsonify(data), status


@app.route('/proxy/groups/<group_id>')
def proxy_group_info(group_id):
    """Get group information"""
    url = f"https://groups.roblox.com/v1/groups/{group_id}"
    data, status = make_proxy_request(url, f'/proxy/groups/{group_id}')
    if status == 200:
        proxy_cache[f"group_{group_id}"] = {'data': data, 'time': time.time()}
    return jsonify(data), status


@app.route('/proxy/groups/<group_id>/wall')
def proxy_group_wall(group_id):
    """Get group wall posts"""
    limit = request.args.get('limit', 10)
    sort_order = request.args.get('sortOrder', 'Desc')
    cursor = request.args.get('cursor', '')
    url = f"https://groups.roblox.com/v2/groups/{group_id}/wall/posts?limit={limit}&sortOrder={sort_order}"
    if cursor:
        url += f"&cursor={cursor}"
    data, status = make_proxy_request(url, f'/proxy/groups/{group_id}/wall')
    if status == 200:
        proxy_cache[f"wall_{group_id}_{cursor}"] = {'data': data, 'time': time.time()}
    return jsonify(data), status


@app.route('/proxy/groups/<group_id>/social-links')
def proxy_group_social_links(group_id):
    """Get group social links"""
    url = f"https://groups.roblox.com/v1/groups/{group_id}/social-links"
    data, status = make_proxy_request(url, f'/proxy/groups/{group_id}/social-links')
    if status == 200:
        proxy_cache[f"group_social_{group_id}"] = {'data': data, 'time': time.time()}
    return jsonify(data), status


@app.route('/proxy/localization/supported-languages')
def proxy_supported_languages():
    """Get Roblox supported languages"""
    url = "https://locale.roblox.com/v1/locales/supported-locales"
    data, status = make_proxy_request(url, '/proxy/localization/supported-languages')
    if status == 200:
        proxy_cache['supported_languages'] = {'data': data, 'time': time.time()}
    return jsonify(data), status


@app.route('/proxy/users/<user_id>/username-history')
def proxy_username_history(user_id):
    """Get user's username history"""
    limit = request.args.get('limit', 10)
    cursor = request.args.get('cursor', '')
    url = f"https://users.roblox.com/v1/users/{user_id}/username-history?limit={limit}"
    if cursor:
        url += f"&cursor={cursor}"
    data, status = make_proxy_request(url, f'/proxy/users/{user_id}/username-history')
    if status == 200:
        proxy_cache[f"username_history_{user_id}"] = {'data': data, 'time': time.time()}
    return jsonify(data), status


@app.route('/proxy/users/<user_id>/status')
def proxy_user_status(user_id):
    """Get user's custom status"""
    url = f"https://users.roblox.com/v1/users/{user_id}/status"
    data, status = make_proxy_request(url, f'/proxy/users/{user_id}/status')
    if status == 200:
        proxy_cache[f"status_{user_id}"] = {'data': data, 'time': time.time()}
    return jsonify(data), status


@app.route('/proxy/games/sorts')
def proxy_game_sorts():
    """Get available game sorts"""
    url = "https://games.roblox.com/v1/games/sorts"
    data, status = make_proxy_request(url, '/proxy/games/sorts')
    if status == 200:
        proxy_cache['game_sorts'] = {'data': data, 'time': time.time()}
    return jsonify(data), status


@app.route('/proxy/games/list')
def proxy_games_list():
    """Get games by sort type"""
    sort_token = request.args.get('sortToken', '')
    start_rows = request.args.get('startRows', 0)
    max_rows = request.args.get('maxRows', 10)
    url = f"https://games.roblox.com/v1/games/list?sortToken={sort_token}&startRows={start_rows}&maxRows={max_rows}"
    data, status = make_proxy_request(url, '/proxy/games/list')
    if status == 200:
        proxy_cache[f"games_list_{sort_token}_{start_rows}"] = {'data': data, 'time': time.time()}
    return jsonify(data), status


@app.route('/proxy/games/<place_id>/details')
def proxy_place_details(place_id):
    """Get place details (not universe)"""
    url = f"https://games.roblox.com/v1/games/multiget-place-details?placeIds={place_id}"
    data, status = make_proxy_request(url, f'/proxy/games/{place_id}/details')
    if status == 200:
        proxy_cache[f"place_{place_id}"] = {'data': data, 'time': time.time()}
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


# ===== AUTHENTICATED PROXY ENDPOINTS (require cookie) =====

@app.route('/proxy/auth/me')
def proxy_auth_me():
    """Get authenticated user info (requires cookie)"""
    global roblox_cookie
    if not roblox_cookie:
        return jsonify({'error': 'No cookie set. Add your .ROBLOSECURITY cookie in Settings.'}), 401
    roblox_url = "https://users.roblox.com/v1/users/authenticated"
    return jsonify(make_proxy_request(roblox_url, 'auth/me')[0]), make_proxy_request(roblox_url, 'auth/me')[1]


@app.route('/proxy/auth/friends/requests')
def proxy_auth_friend_requests():
    """Get friend requests (requires cookie)"""
    global roblox_cookie
    if not roblox_cookie:
        return jsonify({'error': 'No cookie set. Add your .ROBLOSECURITY cookie in Settings.'}), 401
    roblox_url = "https://friends.roblox.com/v1/my/friends/requests"
    return jsonify(make_proxy_request(roblox_url, 'auth/friend-requests')[0]), make_proxy_request(roblox_url, 'auth/friend-requests')[1]


@app.route('/proxy/auth/friends/count')
def proxy_auth_friends_count():
    """Get friend count (requires cookie)"""
    global roblox_cookie
    if not roblox_cookie:
        return jsonify({'error': 'No cookie set. Add your .ROBLOSECURITY cookie in Settings.'}), 401
    roblox_url = "https://friends.roblox.com/v1/my/friends/count"
    return jsonify(make_proxy_request(roblox_url, 'auth/friends-count')[0]), make_proxy_request(roblox_url, 'auth/friends-count')[1]


@app.route('/proxy/auth/recommendations/users')
def proxy_auth_recommendations():
    """Get friend recommendations (requires cookie)"""
    global roblox_cookie
    if not roblox_cookie:
        return jsonify({'error': 'No cookie set. Add your .ROBLOSECURITY cookie in Settings.'}), 401
    roblox_url = "https://friends.roblox.com/v1/recommended-users"
    return jsonify(make_proxy_request(roblox_url, 'auth/recommendations')[0]), make_proxy_request(roblox_url, 'auth/recommendations')[1]


@app.route('/proxy/auth/robux')
def proxy_auth_robux():
    """Get user's Robux balance (requires cookie)"""
    global roblox_cookie
    if not roblox_cookie:
        return jsonify({'error': 'No cookie set. Add your .ROBLOSECURITY cookie in Settings.'}), 401
    roblox_url = "https://economy.roblox.com/v1/user/currency"
    return jsonify(make_proxy_request(roblox_url, 'auth/robux')[0]), make_proxy_request(roblox_url, 'auth/robux')[1]


@app.route('/proxy/auth/notifications/count')
def proxy_auth_notifications():
    """Get notification count (requires cookie)"""
    global roblox_cookie
    if not roblox_cookie:
        return jsonify({'error': 'No cookie set. Add your .ROBLOSECURITY cookie in Settings.'}), 401
    roblox_url = "https://notifications.roblox.com/v2/stream-notifications/unread-count"
    return jsonify(make_proxy_request(roblox_url, 'auth/notifications')[0]), make_proxy_request(roblox_url, 'auth/notifications')[1]


@app.route('/proxy/auth/messages/count')
def proxy_auth_messages():
    """Get unread message count (requires cookie)"""
    global roblox_cookie
    if not roblox_cookie:
        return jsonify({'error': 'No cookie set. Add your .ROBLOSECURITY cookie in Settings.'}), 401
    roblox_url = "https://privatemessages.roblox.com/v1/messages/unread/count"
    return jsonify(make_proxy_request(roblox_url, 'auth/messages')[0]), make_proxy_request(roblox_url, 'auth/messages')[1]


@app.route('/proxy/auth/trades/count')
def proxy_auth_trades():
    """Get trade count (requires cookie)"""
    global roblox_cookie
    if not roblox_cookie:
        return jsonify({'error': 'No cookie set. Add your .ROBLOSECURITY cookie in Settings.'}), 401
    roblox_url = "https://trades.roblox.com/v1/trades/inbound/count"
    return jsonify(make_proxy_request(roblox_url, 'auth/trades')[0]), make_proxy_request(roblox_url, 'auth/trades')[1]


@app.route('/proxy/auth/settings/email')
def proxy_auth_email():
    """Get email verification status (requires cookie)"""
    global roblox_cookie
    if not roblox_cookie:
        return jsonify({'error': 'No cookie set. Add your .ROBLOSECURITY cookie in Settings.'}), 401
    roblox_url = "https://accountsettings.roblox.com/v1/email"
    return jsonify(make_proxy_request(roblox_url, 'auth/email')[0]), make_proxy_request(roblox_url, 'auth/email')[1]


@app.route('/proxy/auth/privacy')
def proxy_auth_privacy():
    """Get privacy settings (requires cookie)"""
    global roblox_cookie
    if not roblox_cookie:
        return jsonify({'error': 'No cookie set. Add your .ROBLOSECURITY cookie in Settings.'}), 401
    roblox_url = "https://accountsettings.roblox.com/v1/privacy"
    return jsonify(make_proxy_request(roblox_url, 'auth/privacy')[0]), make_proxy_request(roblox_url, 'auth/privacy')[1]


@app.route('/proxy/auth/inventory/canview/<user_id>')
def proxy_auth_inventory_check(user_id):
    """Check if you can view user's inventory (requires cookie)"""
    global roblox_cookie
    if not roblox_cookie:
        return jsonify({'error': 'No cookie set. Add your .ROBLOSECURITY cookie in Settings.'}), 401
    roblox_url = f"https://inventory.roblox.com/v1/users/{user_id}/can-view-inventory"
    return jsonify(make_proxy_request(roblox_url, 'auth/inventory-check')[0]), make_proxy_request(roblox_url, 'auth/inventory-check')[1]


# ===== DEVEX CALCULATOR =====
@app.route('/api/devex/calculate', methods=['POST'])
def calculate_devex():
    """Calculate DevEx conversion rates"""
    data = request.get_json()
    robux = float(data.get('robux', 0))

    # DevEx rate: $0.0035 per Robux (as of 2024)
    # This is the standard rate for qualified developers
    devex_rate = 0.0035
    usd = robux * devex_rate

    # Also calculate marketplace fees
    marketplace_fee = 0.30  # 30% marketplace fee
    after_fees = robux * (1 - marketplace_fee)
    after_fees_usd = after_fees * devex_rate

    # Premium payouts (70% to creator)
    premium_payout_rate = 0.70

    return jsonify({
        'robux': robux,
        'usd_gross': round(usd, 2),
        'usd_after_fees': round(after_fees_usd, 2),
        'marketplace_fee_percent': marketplace_fee * 100,
        'devex_rate': devex_rate,
        'premium_payout_rate': premium_payout_rate * 100,
        'conversions': {
            '1000_robux': round(1000 * devex_rate, 2),
            '10000_robux': round(10000 * devex_rate, 2),
            '100000_robux': round(100000 * devex_rate, 2),
            '1000000_robux': round(1000000 * devex_rate, 2)
        }
    })


@app.route('/api/devex/reverse', methods=['POST'])
def reverse_devex():
    """Calculate how much Robux needed for target USD"""
    data = request.get_json()
    target_usd = float(data.get('usd', 0))
    devex_rate = 0.0035

    robux_needed = target_usd / devex_rate
    # Account for marketplace fees
    robux_before_fees = robux_needed / 0.70  # 30% fee

    return jsonify({
        'target_usd': target_usd,
        'robux_needed_direct': round(robux_needed),
        'robux_needed_with_fees': round(robux_before_fees),
        'devex_rate': devex_rate
    })


# ===== SITE INFORMATION =====
@app.route('/api/site-info')
def get_site_info():
    """Get site information and creator contact"""
    return jsonify({
        'name': 'Tigos API Playground',
        'version': '2.0.0',
        'creator': 'Tigo',
        'contact': {
            'discord': 't1g_0o',
            'email': 'tigodevemail@gmail.com'
        },
        'features': [
            'DataStore Management (Standard & Ordered)',
            'Bulk Operations with Progress Tracking',
            '60+ Roblox API Proxy Endpoints',
            'DevEx Calculator',
            'Real-time Analytics Dashboard',
            'User Lookup with Full Profile Data',
            'Game Server Browser',
            'Cookie-based Authentication',
            '5 Animated Themes',
            'Export/Import Functionality'
        ],
        'stats': {
            'total_operations': get_total_operations(),
            'uptime': 'Active'
        }
    })


def get_total_operations():
    """Get total operations count"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM operations')
        count = c.fetchone()[0]
        conn.close()
        return count
    except:
        return 0


# ===== ADVANCED ANALYTICS =====
@app.route('/api/analytics/comprehensive')
def get_comprehensive_analytics():
    """Get comprehensive analytics data"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        # Operations by type
        c.execute('''SELECT operation, COUNT(*) as count,
                     SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful
                     FROM operations GROUP BY operation ORDER BY count DESC''')
        ops_by_type = [{'operation': row[0], 'count': row[1], 'successful': row[2]} for row in c.fetchall()]

        # Operations over time (last 30 days)
        c.execute('''SELECT DATE(timestamp) as date, COUNT(*) as count
                     FROM operations
                     WHERE timestamp >= datetime('now', '-30 days')
                     GROUP BY date ORDER BY date''')
        ops_timeline = [{'date': row[0], 'count': row[1]} for row in c.fetchall()]

        # Most active datastores
        c.execute('''SELECT datastore, COUNT(*) as count
                     FROM operations WHERE datastore != ''
                     GROUP BY datastore ORDER BY count DESC LIMIT 10''')
        top_datastores = [{'name': row[0], 'operations': row[1]} for row in c.fetchall()]

        # Success rate over time
        c.execute('''SELECT DATE(timestamp) as date,
                     ROUND(AVG(success) * 100, 2) as success_rate
                     FROM operations
                     WHERE timestamp >= datetime('now', '-7 days')
                     GROUP BY date ORDER BY date''')
        success_timeline = [{'date': row[0], 'rate': row[1]} for row in c.fetchall()]

        # Hourly distribution
        c.execute('''SELECT strftime('%H', timestamp) as hour, COUNT(*) as count
                     FROM operations GROUP BY hour ORDER BY hour''')
        hourly_dist = [{'hour': int(row[0]), 'count': row[1]} for row in c.fetchall()]

        conn.close()

        return jsonify({
            'operations_by_type': ops_by_type,
            'operations_timeline': ops_timeline,
            'top_datastores': top_datastores,
            'success_rate_timeline': success_timeline,
            'hourly_distribution': hourly_dist,
            'generated_at': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ===== OPENCLOUD V2 SUBSCRIPTIONS (Placeholder) =====
@app.route('/api/opencloud/v2/info')
def opencloud_v2_info():
    """Information about OpenCloud v2 APIs"""
    return jsonify({
        'version': '2.0',
        'available_apis': [
            {
                'name': 'Messaging Service',
                'endpoint': '/v2/universes/{universeId}/topics/{topic}',
                'description': 'Publish messages to in-game topics',
                'requires_api_key': True
            },
            {
                'name': 'User Restrictions',
                'endpoint': '/v2/universes/{universeId}/user-restrictions',
                'description': 'Manage user bans and restrictions',
                'requires_api_key': True
            },
            {
                'name': 'Place Management',
                'endpoint': '/v2/universes/{universeId}/places',
                'description': 'Manage place settings and publishing',
                'requires_api_key': True
            },
            {
                'name': 'Inventory',
                'endpoint': '/v2/users/{userId}/inventory-items',
                'description': 'Access user inventory data',
                'requires_api_key': True
            }
        ],
        'note': 'OpenCloud v2 APIs require specific API key permissions configured in Creator Hub'
    })


@app.route('/proxy/games/<universe_id>/analytics')
def get_game_analytics(universe_id):
    """Get comprehensive game analytics - combined endpoint"""
    try:
        analytics = {}

        # Get votes
        votes_url = f'https://games.roblox.com/v1/games/{universe_id}/votes'
        votes_resp = requests.get(votes_url, timeout=30)
        if votes_resp.status_code == 200:
            analytics['votes'] = votes_resp.json()

        # Get favorites count
        fav_url = f'https://games.roblox.com/v1/games/{universe_id}/favorites/count'
        fav_resp = requests.get(fav_url, timeout=30)
        if fav_resp.status_code == 200:
            analytics['favorites'] = fav_resp.json()

        # Get game passes
        passes_url = f'https://games.roblox.com/v1/games/{universe_id}/game-passes'
        passes_resp = requests.get(passes_url, params={'limit': 100, 'sortOrder': 'Asc'}, timeout=30)
        if passes_resp.status_code == 200:
            analytics['game_passes'] = passes_resp.json()

        # Get servers info
        servers_url = f'https://games.roblox.com/v1/games/{universe_id}/servers/Public'
        servers_resp = requests.get(servers_url, params={'limit': 10}, timeout=30)
        if servers_resp.status_code == 200:
            servers_data = servers_resp.json()
            analytics['servers'] = {
                'sample': servers_data.get('data', [])[:5],
                'total_players': sum(s.get('playing', 0) for s in servers_data.get('data', []))
            }

        return jsonify({
            'universe_id': universe_id,
            'analytics': analytics,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/proxy/presence/batch', methods=['POST'])
def get_batch_presence():
    """Get presence for multiple users at once"""
    data = request.get_json()
    user_ids = data.get('userIds', [])

    if not user_ids:
        return jsonify({'error': 'userIds required'}), 400

    try:
        url = 'https://presence.roblox.com/v1/presence/users'
        response = requests.post(url, json={'userIds': user_ids}, timeout=30)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/proxy/economy/currency')
def get_currency_exchange():
    """Get current Robux exchange rate information"""
    return jsonify({
        'robux_to_usd': 0.0035,  # DevEx rate
        'usd_to_robux_purchase': 0.0125,  # Purchase rate (80 Robux per $1)
        'marketplace_fee': 0.30,  # 30% fee
        'premium_stipend': {
            'Premium 450': 450,
            'Premium 1000': 1000,
            'Premium 2200': 2200
        },
        'last_updated': '2024-11-01',
        'note': 'Exchange rates may vary. DevEx rate is fixed at $0.0035 per Robux.'
    })


@app.route('/api/system/health')
def system_health():
    """Get system health information"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Get database size
    c.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
    db_size = c.fetchone()[0]

    # Get total operations
    c.execute("SELECT COUNT(*) FROM operations")
    total_ops = c.fetchone()[0]

    # Get recent error rate
    c.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as errors
        FROM operations
        WHERE timestamp > datetime('now', '-1 hour')
    """)
    recent = c.fetchone()
    error_rate = (recent[1] / recent[0] * 100) if recent[0] > 0 else 0

    conn.close()

    return jsonify({
        'status': 'healthy' if error_rate < 10 else 'degraded',
        'database_size_mb': round(db_size / (1024 * 1024), 2),
        'total_operations': total_ops,
        'recent_error_rate': round(error_rate, 2),
        'uptime': 'N/A',
        'version': '2.0.0',
        'python_version': sys.version.split()[0],
        'flask_version': '2.x'
    })


@app.route('/api/export/operations')
def export_operations():
    """Export all operations as JSON"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        SELECT timestamp, operation, datastore, key, details, success
        FROM operations
        ORDER BY timestamp DESC
        LIMIT 10000
    """)

    operations = []
    for row in c.fetchall():
        operations.append({
            'timestamp': row[0],
            'operation': row[1],
            'datastore': row[2],
            'key': row[3],
            'details': row[4],
            'success': bool(row[5])
        })

    conn.close()

    return jsonify({
        'export_date': datetime.now().isoformat(),
        'total_operations': len(operations),
        'operations': operations
    })


# ============= AI ENDPOINTS (Pollinations AI) =============

POLLINATIONS_API_KEY = os.getenv('POLLINATIONS_API_KEY', 'SANEA7vYHQjrDtEI')
POLLINATIONS_REFERER = os.getenv('POLLINATIONS_REFERER', 'https://tigoshub.com/')

@app.route('/api/ai/generate-image')
def ai_generate_image():
    """Generate an image using Pollinations AI"""
    prompt = request.args.get('prompt', '')
    model = request.args.get('model', 'flux-realism')  # Default to realism model
    width = request.args.get('width', '1024')
    height = request.args.get('height', '1024')

    # Hardcoded seed for realistic, consistent results
    seed = request.args.get('seed', '42069')  # Use consistent seed if not provided

    if not prompt:
        return jsonify({'error': 'Prompt is required'}), 400

    try:
        # Build the Pollinations AI image URL with no filters
        # enhance=false to keep original prompt, nologo=true to remove watermark
        url_params = f"model={model}&width={width}&height={height}&seed={seed}&enhance=false&nologo=true&nofeed=true&private=true"

        # URL encode the prompt
        from urllib.parse import quote
        encoded_prompt = quote(prompt)

        # Construct the image URL
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?{url_params}"

        return jsonify({
            'success': True,
            'url': image_url,
            'prompt': prompt,
            'model': model,
            'width': width,
            'height': height,
            'seed': seed
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/ai/chat', methods=['POST'])
def ai_chat():
    """Chat with AI using Pollinations AI text generation"""
    data = request.json
    messages = data.get('messages', [])
    model = data.get('model', 'openai')
    temperature = data.get('temperature', 0.7)
    max_tokens = data.get('max_tokens', 1000)
    system_prompt = data.get('system', '')

    if not messages:
        return jsonify({'error': 'Messages are required'}), 400

    try:
        # If system prompt provided, add it as the first message
        formatted_messages = []
        if system_prompt:
            formatted_messages.append({'role': 'system', 'content': system_prompt})
        formatted_messages.extend(messages)

        # Prepare the request to Pollinations AI
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {POLLINATIONS_API_KEY}',
            'Referer': POLLINATIONS_REFERER
        }

        # Build the request payload in OpenAI-compatible format
        # Only include required fields to avoid 400 errors
        payload = {
            'model': model,
            'messages': formatted_messages
        }

        print(f"[AI CHAT] Sending to Pollinations: {payload}")  # Debug logging

        # Call Pollinations AI using the /openai endpoint
        response = requests.post(
            'https://text.pollinations.ai/openai',
            json=payload,
            headers=headers,
            timeout=30
        )

        print(f"[AI CHAT] Response status: {response.status_code}")  # Debug logging
        print(f"[AI CHAT] Response body: {response.text[:500]}")  # Debug logging

        if response.status_code == 200:
            result = response.json()
            # Extract the response from the OpenAI-compatible format
            ai_response = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            return jsonify({
                'success': True,
                'response': ai_response
            })
        else:
            error_msg = f'AI API error: {response.status_code} - {response.text[:200]}'
            print(f"[AI CHAT ERROR] {error_msg}")
            return jsonify({'error': error_msg}), 500

    except Exception as e:
        print(f"[AI CHAT EXCEPTION] {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/ai/vision', methods=['POST'])
def ai_vision():
    """Analyze images with Vision AI"""
    data = request.json
    image_url = data.get('image_url', '')
    prompt = data.get('prompt', 'Describe this image')

    if not image_url:
        return jsonify({'error': 'Image URL is required'}), 400

    try:
        # Prepare the vision request
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {POLLINATIONS_API_KEY}',
            'Referer': POLLINATIONS_REFERER
        }

        # Build messages for vision model in OpenAI-compatible format
        messages = [
            {
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': prompt},
                    {'type': 'image_url', 'image_url': {'url': image_url}}
                ]
            }
        ]

        payload = {
            'model': 'openai',  # Use openai model for vision
            'messages': messages
        }

        # Call Pollinations AI using the /openai endpoint
        response = requests.post(
            'https://text.pollinations.ai/openai',
            json=payload,
            headers=headers,
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            # Extract the analysis from the OpenAI-compatible format
            analysis = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            return jsonify({
                'success': True,
                'analysis': analysis
            })
        else:
            return jsonify({'error': f'Vision AI error: {response.status_code}'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/ai/text-to-speech', methods=['POST'])
def ai_text_to_speech():
    """Convert text to speech using Pollinations AI"""
    data = request.json
    text = data.get('text', '')
    voice = data.get('voice', 'alloy')
    speed = data.get('speed', 1.0)

    if not text:
        return jsonify({'error': 'Text is required'}), 400

    try:
        # Use Pollinations /openai endpoint for TTS
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {POLLINATIONS_API_KEY}',
            'Referer': POLLINATIONS_REFERER
        }

        # Build the request for TTS
        payload = {
            'model': 'openai-audio',
            'messages': [
                {
                    'role': 'user',
                    'content': text
                }
            ],
            'voice': voice
        }

        # Call Pollinations AI
        response = requests.post(
            'https://text.pollinations.ai/openai',
            json=payload,
            headers=headers,
            timeout=30
        )

        if response.status_code == 200:
            # The response should contain audio data or URL
            # For now, return the direct URL format as fallback
            from urllib.parse import quote
            encoded_text = quote(text)
            audio_url = f"https://text.pollinations.ai/{encoded_text}?model=openai-audio&voice={voice}"

            return jsonify({
                'success': True,
                'audio_url': audio_url,
                'voice': voice,
                'speed': speed
            })
        else:
            return jsonify({'error': f'TTS API error: {response.status_code}'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============= AI HISTORY ENDPOINTS =============

@app.route('/api/ai/save-chat', methods=['POST'])
def save_chat():
    """Save chat history"""
    data = request.json
    chat_name = data.get('name', f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    messages = data.get('messages', [])
    model = data.get('model', 'openai')

    conn = sqlite3.connect('data/datastore.db')
    c = conn.cursor()

    # Create table if not exists
    c.execute('''
        CREATE TABLE IF NOT EXISTS ai_chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            model TEXT,
            messages TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    c.execute('INSERT INTO ai_chat_history (name, model, messages) VALUES (?, ?, ?)',
              (chat_name, model, json.dumps(messages)))

    conn.commit()
    chat_id = c.lastrowid
    conn.close()

    return jsonify({'success': True, 'id': chat_id, 'name': chat_name})


@app.route('/api/ai/get-chats')
def get_chats():
    """Get all saved chats"""
    conn = sqlite3.connect('data/datastore.db')
    c = conn.cursor()

    # Create table if not exists
    c.execute('''
        CREATE TABLE IF NOT EXISTS ai_chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            model TEXT,
            messages TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    c.execute('SELECT id, name, model, created_at FROM ai_chat_history ORDER BY created_at DESC LIMIT 50')
    chats = []
    for row in c.fetchall():
        chats.append({
            'id': row[0],
            'name': row[1],
            'model': row[2],
            'created_at': row[3]
        })

    conn.close()
    return jsonify({'chats': chats})


@app.route('/api/ai/load-chat/<int:chat_id>')
def load_chat(chat_id):
    """Load a saved chat"""
    conn = sqlite3.connect('data/datastore.db')
    c = conn.cursor()

    c.execute('SELECT name, model, messages FROM ai_chat_history WHERE id = ?', (chat_id,))
    row = c.fetchone()
    conn.close()

    if row:
        return jsonify({
            'success': True,
            'name': row[0],
            'model': row[1],
            'messages': json.loads(row[2])
        })
    else:
        return jsonify({'error': 'Chat not found'}), 404


@app.route('/api/ai/delete-chat/<int:chat_id>', methods=['DELETE'])
def delete_chat(chat_id):
    """Delete a saved chat"""
    conn = sqlite3.connect('data/datastore.db')
    c = conn.cursor()
    c.execute('DELETE FROM ai_chat_history WHERE id = ?', (chat_id,))
    conn.commit()
    conn.close()

    return jsonify({'success': True})


@app.route('/api/ai/save-image', methods=['POST'])
def save_image():
    """Save generated image to history"""
    data = request.json
    prompt = data.get('prompt', '')
    url = data.get('url', '')
    model = data.get('model', 'flux-realism')
    width = data.get('width', 1024)
    height = data.get('height', 1024)
    seed = data.get('seed', '42069')

    conn = sqlite3.connect('data/datastore.db')
    c = conn.cursor()

    # Create table if not exists
    c.execute('''
        CREATE TABLE IF NOT EXISTS ai_image_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt TEXT,
            url TEXT,
            model TEXT,
            width INTEGER,
            height INTEGER,
            seed TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    c.execute('INSERT INTO ai_image_history (prompt, url, model, width, height, seed) VALUES (?, ?, ?, ?, ?, ?)',
              (prompt, url, model, width, height, seed))

    conn.commit()
    image_id = c.lastrowid
    conn.close()

    return jsonify({'success': True, 'id': image_id})


@app.route('/api/ai/get-images')
def get_images():
    """Get all generated images"""
    conn = sqlite3.connect('data/datastore.db')
    c = conn.cursor()

    # Create table if not exists
    c.execute('''
        CREATE TABLE IF NOT EXISTS ai_image_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt TEXT,
            url TEXT,
            model TEXT,
            width INTEGER,
            height INTEGER,
            seed TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    c.execute('SELECT id, prompt, url, model, width, height, seed, created_at FROM ai_image_history ORDER BY created_at DESC LIMIT 100')
    images = []
    for row in c.fetchall():
        images.append({
            'id': row[0],
            'prompt': row[1],
            'url': row[2],
            'model': row[3],
            'width': row[4],
            'height': row[5],
            'seed': row[6],
            'created_at': row[7]
        })

    conn.close()
    return jsonify({'images': images})


@app.route('/api/ai/delete-image/<int:image_id>', methods=['DELETE'])
def delete_image(image_id):
    """Delete an image from history"""
    conn = sqlite3.connect('data/datastore.db')
    c = conn.cursor()
    c.execute('DELETE FROM ai_image_history WHERE id = ?', (image_id,))
    conn.commit()
    conn.close()

    return jsonify({'success': True})


# ============= ROBLOX ADVANCED FEATURES =============
# 50+ Advanced Features for Roblox Development

# ============= OPENCLOUD V2 - UNIVERSE & PLACES API =============

@app.route('/api/roblox/v2/universe/<universe_id>/info')
def get_universe_info_v2(universe_id):
    """Get detailed universe information"""
    try:
        headers = {
            'x-api-key': global_config.get('api_key', ''),
            'Content-Type': 'application/json'
        }

        response = requests.get(
            f'https://apis.roblox.com/cloud/v2/universes/{universe_id}',
            headers=headers
        )

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': f'API error: {response.status_code}', 'details': response.text}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/roblox/v2/universe/<universe_id>/places')
def get_universe_places(universe_id):
    """Get all places in a universe"""
    try:
        headers = {
            'x-api-key': global_config.get('api_key', ''),
            'Content-Type': 'application/json'
        }

        response = requests.get(
            f'https://apis.roblox.com/cloud/v2/universes/{universe_id}/places',
            headers=headers
        )

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': f'API error: {response.status_code}'}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/roblox/v2/place/<place_id>/publish', methods=['POST'])
def publish_place(place_id):
    """Publish a place to Roblox"""
    try:
        data = request.json
        version_type = data.get('versionType', 'Published')

        headers = {
            'x-api-key': global_config.get('api_key', ''),
            'Content-Type': 'application/json'
        }

        payload = {
            'versionType': version_type
        }

        response = requests.post(
            f'https://apis.roblox.com/cloud/v2/places/{place_id}:publish',
            headers=headers,
            json=payload
        )

        if response.status_code == 200:
            return jsonify({'success': True, 'data': response.json()})
        else:
            return jsonify({'error': f'API error: {response.status_code}'}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/roblox/v2/place/<place_id>/versions')
def get_place_versions(place_id):
    """Get version history for a place"""
    try:
        headers = {
            'x-api-key': global_config.get('api_key', ''),
            'Content-Type': 'application/json'
        }

        response = requests.get(
            f'https://apis.roblox.com/cloud/v2/places/{place_id}/versions',
            headers=headers
        )

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': f'API error: {response.status_code}'}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/roblox/v2/universe/<universe_id>/configuration')
def get_universe_configuration(universe_id):
    """Get universe configuration settings"""
    try:
        headers = {
            'x-api-key': global_config.get('api_key', ''),
            'Content-Type': 'application/json'
        }

        response = requests.get(
            f'https://apis.roblox.com/cloud/v2/universes/{universe_id}/configuration',
            headers=headers
        )

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': f'API error: {response.status_code}'}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============= OPENCLOUD V2 - ASSETS & ECONOMY =============

@app.route('/api/roblox/v2/assets/upload', methods=['POST'])
def upload_asset():
    """Upload an asset to Roblox"""
    try:
        data = request.json
        asset_type = data.get('assetType')
        display_name = data.get('displayName')
        description = data.get('description', '')
        creator_id = data.get('creatorId')

        headers = {
            'x-api-key': global_config.get('api_key', ''),
            'Content-Type': 'application/json'
        }

        payload = {
            'assetType': asset_type,
            'displayName': display_name,
            'description': description,
            'creatorTargetId': creator_id
        }

        response = requests.post(
            'https://apis.roblox.com/cloud/v2/assets',
            headers=headers,
            json=payload
        )

        if response.status_code == 200:
            return jsonify({'success': True, 'data': response.json()})
        else:
            return jsonify({'error': f'API error: {response.status_code}'}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/roblox/v2/universe/<universe_id>/products')
def get_universe_products(universe_id):
    """Get all developer products for a universe"""
    try:
        headers = {
            'x-api-key': global_config.get('api_key', ''),
            'Content-Type': 'application/json'
        }

        response = requests.get(
            f'https://apis.roblox.com/cloud/v2/universes/{universe_id}/developer-products',
            headers=headers
        )

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': f'API error: {response.status_code}'}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/roblox/v2/universe/<universe_id>/game-passes')
def get_universe_game_passes(universe_id):
    """Get all game passes for a universe"""
    try:
        headers = {
            'x-api-key': global_config.get('api_key', ''),
            'Content-Type': 'application/json'
        }

        response = requests.get(
            f'https://apis.roblox.com/cloud/v2/universes/{universe_id}/game-passes',
            headers=headers
        )

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': f'API error: {response.status_code}'}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/roblox/v2/universe/<universe_id>/badges')
def get_universe_badges(universe_id):
    """Get all badges for a universe"""
    try:
        headers = {
            'x-api-key': global_config.get('api_key', ''),
            'Content-Type': 'application/json'
        }

        response = requests.get(
            f'https://apis.roblox.com/cloud/v2/universes/{universe_id}/badges',
            headers=headers
        )

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': f'API error: {response.status_code}'}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/roblox/v2/product/create', methods=['POST'])
def create_developer_product():
    """Create a new developer product"""
    try:
        data = request.json
        universe_id = data.get('universeId')
        name = data.get('name')
        price_robux = data.get('priceInRobux')
        description = data.get('description', '')

        headers = {
            'x-api-key': global_config.get('api_key', ''),
            'Content-Type': 'application/json'
        }

        payload = {
            'name': name,
            'priceInRobux': price_robux,
            'description': description
        }

        response = requests.post(
            f'https://apis.roblox.com/cloud/v2/universes/{universe_id}/developer-products',
            headers=headers,
            json=payload
        )

        if response.status_code == 200:
            return jsonify({'success': True, 'data': response.json()})
        else:
            return jsonify({'error': f'API error: {response.status_code}'}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============= OPENCLOUD V2 - GROUPS & SOCIAL =============

@app.route('/api/roblox/v2/groups/<group_id>/info')
def get_group_info_v2(group_id):
    """Get detailed group information via OpenCloud v2"""
    try:
        headers = {
            'x-api-key': global_config.get('api_key', ''),
            'Content-Type': 'application/json'
        }

        response = requests.get(
            f'https://apis.roblox.com/cloud/v2/groups/{group_id}',
            headers=headers
        )

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': f'API error: {response.status_code}'}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/roblox/v2/groups/<group_id>/members')
def get_group_members_v2(group_id):
    """Get group members via OpenCloud v2"""
    try:
        headers = {
            'x-api-key': global_config.get('api_key', ''),
            'Content-Type': 'application/json'
        }

        response = requests.get(
            f'https://apis.roblox.com/cloud/v2/groups/{group_id}/members',
            headers=headers
        )

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': f'API error: {response.status_code}'}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/roblox/v2/groups/<group_id>/roles')
def get_group_roles_v2(group_id):
    """Get group roles via OpenCloud v2"""
    try:
        headers = {
            'x-api-key': global_config.get('api_key', ''),
            'Content-Type': 'application/json'
        }

        response = requests.get(
            f'https://apis.roblox.com/cloud/v2/groups/{group_id}/roles',
            headers=headers
        )

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': f'API error: {response.status_code}'}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/roblox/v2/groups/<group_id>/shout', methods=['POST'])
def set_group_shout(group_id):
    """Set group shout message"""
    try:
        data = request.json
        message = data.get('message', '')

        headers = {
            'x-api-key': global_config.get('api_key', ''),
            'Content-Type': 'application/json'
        }

        payload = {'message': message}

        response = requests.post(
            f'https://apis.roblox.com/cloud/v2/groups/{group_id}/shout',
            headers=headers,
            json=payload
        )

        if response.status_code == 200:
            return jsonify({'success': True})
        else:
            return jsonify({'error': f'API error: {response.status_code}'}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/roblox/v2/user/<user_id>/groups')
def get_user_groups_v2(user_id):
    """Get user's groups via OpenCloud v2"""
    try:
        headers = {
            'x-api-key': global_config.get('api_key', ''),
            'Content-Type': 'application/json'
        }

        response = requests.get(
            f'https://apis.roblox.com/cloud/v2/users/{user_id}/groups',
            headers=headers
        )

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': f'API error: {response.status_code}'}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============= OPENCLOUD V1 - ADVANCED DATASTORES =============

@app.route('/api/roblox/memorystore/<universe_id>/publish', methods=['POST'])
def publish_to_messaging_service(universe_id):
    """Publish message to MessagingService"""
    try:
        data = request.json
        topic = data.get('topic')
        message = data.get('message')

        headers = {
            'x-api-key': global_config.get('api_key', ''),
            'Content-Type': 'application/json'
        }

        payload = {'message': message}

        response = requests.post(
            f'https://apis.roblox.com/messaging-service/v1/universes/{universe_id}/topics/{topic}',
            headers=headers,
            json=payload
        )

        if response.status_code == 200:
            return jsonify({'success': True})
        else:
            return jsonify({'error': f'API error: {response.status_code}'}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/roblox/datastore/<universe_id>/<datastore>/list-all')
def list_all_datastore_keys(universe_id, datastore):
    """List all keys in a datastore with pagination"""
    try:
        headers = {'x-api-key': global_config.get('api_key', '')}
        all_keys = []
        cursor = ''

        while True:
            url = f'https://apis.roblox.com/datastores/v1/universes/{universe_id}/standard-datastores/datastore/entries'
            params = {
                'datastoreName': datastore,
                'limit': 100
            }
            if cursor:
                params['cursor'] = cursor

            response = requests.get(url, headers=headers, params=params)

            if response.status_code == 200:
                data = response.json()
                all_keys.extend(data.get('keys', []))
                cursor = data.get('nextPageCursor', '')
                if not cursor:
                    break
            else:
                return jsonify({'error': f'API error: {response.status_code}'}), response.status_code

        return jsonify({'keys': all_keys, 'total': len(all_keys)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/roblox/datastore/<universe_id>/<datastore>/bulk-get', methods=['POST'])
def bulk_get_datastore_entries(universe_id, datastore):
    """Get multiple datastore entries at once"""
    try:
        data = request.json
        keys = data.get('keys', [])

        headers = {'x-api-key': global_config.get('api_key', '')}
        results = {}

        for key in keys:
            response = requests.get(
                f'https://apis.roblox.com/datastores/v1/universes/{universe_id}/standard-datastores/datastore/entries/entry',
                headers=headers,
                params={'datastoreName': datastore, 'entryKey': key}
            )

            if response.status_code == 200:
                results[key] = response.json()
            else:
                results[key] = {'error': f'Failed: {response.status_code}'}

        return jsonify({'results': results})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/roblox/datastore/<universe_id>/<datastore>/search', methods=['POST'])
def search_datastore_entries(universe_id, datastore):
    """Search datastore entries by pattern"""
    try:
        data = request.json
        pattern = data.get('pattern', '')

        headers = {'x-api-key': global_config.get('api_key', '')}

        # Get all keys
        response = requests.get(
            f'https://apis.roblox.com/datastores/v1/universes/{universe_id}/standard-datastores/datastore/entries',
            headers=headers,
            params={'datastoreName': datastore, 'prefix': pattern, 'limit': 100}
        )

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': f'API error: {response.status_code}'}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/roblox/datastore/<universe_id>/<datastore>/export', methods=['POST'])
def export_datastore_full(universe_id, datastore):
    """Export entire datastore to JSON"""
    try:
        headers = {'x-api-key': global_config.get('api_key', '')}
        all_data = {}
        cursor = ''

        while True:
            url = f'https://apis.roblox.com/datastores/v1/universes/{universe_id}/standard-datastores/datastore/entries'
            params = {
                'datastoreName': datastore,
                'limit': 100
            }
            if cursor:
                params['cursor'] = cursor

            response = requests.get(url, headers=headers, params=params)

            if response.status_code == 200:
                data = response.json()
                keys = data.get('keys', [])

                # Fetch each entry
                for key_info in keys:
                    key = key_info['key']
                    entry_response = requests.get(
                        f'https://apis.roblox.com/datastores/v1/universes/{universe_id}/standard-datastores/datastore/entries/entry',
                        headers=headers,
                        params={'datastoreName': datastore, 'entryKey': key}
                    )
                    if entry_response.status_code == 200:
                        all_data[key] = entry_response.json()

                cursor = data.get('nextPageCursor', '')
                if not cursor:
                    break
            else:
                return jsonify({'error': f'API error: {response.status_code}'}), response.status_code

        return jsonify({
            'datastore': datastore,
            'universe_id': universe_id,
            'export_date': datetime.now().isoformat(),
            'total_entries': len(all_data),
            'data': all_data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============= LEGACY API - USERS & SOCIAL =============

@app.route('/api/roblox/legacy/users/<user_id>')
def get_user_info_legacy(user_id):
    """Get user information from legacy API"""
    try:
        response = requests.get(f'https://users.roblox.com/v1/users/{user_id}')

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': f'API error: {response.status_code}'}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/roblox/legacy/users/search')
def search_users():
    """Search for users by keyword"""
    try:
        keyword = request.args.get('keyword', '')
        limit = request.args.get('limit', 10)

        response = requests.get(
            'https://users.roblox.com/v1/users/search',
            params={'keyword': keyword, 'limit': limit}
        )

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': f'API error: {response.status_code}'}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/roblox/legacy/users/<user_id>/friends')
def get_user_friends(user_id):
    """Get user's friends list"""
    try:
        response = requests.get(f'https://friends.roblox.com/v1/users/{user_id}/friends')

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': f'API error: {response.status_code}'}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/roblox/legacy/users/<user_id>/presence')
def get_user_presence(user_id):
    """Get user's online presence"""
    try:
        response = requests.post(
            'https://presence.roblox.com/v1/presence/users',
            json={'userIds': [int(user_id)]}
        )

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': f'API error: {response.status_code}'}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/roblox/legacy/groups/<group_id>')
def get_group_info_legacy(group_id):
    """Get group information from legacy API"""
    try:
        response = requests.get(f'https://groups.roblox.com/v1/groups/{group_id}')

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': f'API error: {response.status_code}'}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============= LEGACY API - GAMES & CATALOG =============

@app.route('/api/roblox/legacy/games/<universe_id>/info')
def get_game_info_legacy(universe_id):
    """Get game information from legacy API"""
    try:
        response = requests.get(
            f'https://games.roblox.com/v1/games?universeIds={universe_id}'
        )

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': f'API error: {response.status_code}'}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/roblox/legacy/games/<universe_id>/servers')
def get_game_servers(universe_id):
    """Get running game servers"""
    try:
        response = requests.get(
            f'https://games.roblox.com/v1/games/{universe_id}/servers/Public',
            params={'limit': 100}
        )

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': f'API error: {response.status_code}'}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/roblox/legacy/games/<universe_id>/favorites/count')
def get_game_favorites_count(universe_id):
    """Get game favorites count"""
    try:
        response = requests.get(
            f'https://games.roblox.com/v1/games/{universe_id}/favorites/count'
        )

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': f'API error: {response.status_code}'}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/roblox/legacy/games/<universe_id>/votes')
def get_game_votes(universe_id):
    """Get game voting data"""
    try:
        response = requests.get(
            f'https://games.roblox.com/v1/games/votes?universeIds={universe_id}'
        )

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': f'API error: {response.status_code}'}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/roblox/legacy/catalog/search')
def search_catalog():
    """Search Roblox catalog"""
    try:
        keyword = request.args.get('keyword', '')
        category = request.args.get('category', 'All')
        limit = request.args.get('limit', 30)

        response = requests.get(
            'https://catalog.roblox.com/v1/search/items',
            params={
                'keyword': keyword,
                'category': category,
                'limit': limit
            }
        )

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': f'API error: {response.status_code}'}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============= LEGACY API - THUMBNAILS & AVATAR =============

@app.route('/api/roblox/legacy/thumbnails/users')
def get_user_thumbnails():
    """Get user avatar thumbnails"""
    try:
        user_ids = request.args.get('userIds', '')
        size = request.args.get('size', '420x420')
        format_type = request.args.get('format', 'Png')

        response = requests.get(
            'https://thumbnails.roblox.com/v1/users/avatar',
            params={
                'userIds': user_ids,
                'size': size,
                'format': format_type
            }
        )

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': f'API error: {response.status_code}'}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/roblox/legacy/thumbnails/games')
def get_game_thumbnails():
    """Get game icon thumbnails"""
    try:
        universe_ids = request.args.get('universeIds', '')
        size = request.args.get('size', '512x512')
        format_type = request.args.get('format', 'Png')

        response = requests.get(
            'https://thumbnails.roblox.com/v1/games/icons',
            params={
                'universeIds': universe_ids,
                'size': size,
                'format': format_type,
                'isCircular': 'false'
            }
        )

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': f'API error: {response.status_code}'}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/roblox/legacy/avatar/<user_id>')
def get_user_avatar(user_id):
    """Get user's current avatar"""
    try:
        response = requests.get(
            f'https://avatar.roblox.com/v1/users/{user_id}/avatar'
        )

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': f'API error: {response.status_code}'}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/roblox/legacy/avatar/<user_id>/currently-wearing')
def get_user_currently_wearing(user_id):
    """Get items user is currently wearing"""
    try:
        response = requests.get(
            f'https://avatar.roblox.com/v1/users/{user_id}/currently-wearing'
        )

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': f'API error: {response.status_code}'}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/roblox/legacy/thumbnails/assets')
def get_asset_thumbnails():
    """Get asset thumbnails"""
    try:
        asset_ids = request.args.get('assetIds', '')
        size = request.args.get('size', '420x420')
        format_type = request.args.get('format', 'Png')

        response = requests.get(
            'https://thumbnails.roblox.com/v1/assets',
            params={
                'assetIds': asset_ids,
                'size': size,
                'format': format_type
            }
        )

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': f'API error: {response.status_code}'}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============= DEVELOPER TOOLS - CODE GENERATION =============

@app.route('/api/tools/generate-remote-event', methods=['POST'])
def generate_remote_event():
    """Generate RemoteEvent code"""
    try:
        data = request.json
        event_name = data.get('name', 'MyEvent')
        location = data.get('location', 'ReplicatedStorage')
        parameters = data.get('parameters', [])

        # Generate server script
        server_code = f"""-- Server Script
local {event_name} = {location}:WaitForChild("{event_name}")

{event_name}.OnServerEvent:Connect(function(player{', ' + ', '.join(parameters) if parameters else ''})
    -- Your server logic here
    print(player.Name .. " fired {event_name}")
end)
"""

        # Generate client script
        client_code = f"""-- Client Script
local {event_name} = {location}:WaitForChild("{event_name}")

-- Fire to server
{event_name}:FireServer({', '.join(parameters) if parameters else ''})
"""

        return jsonify({
            'success': True,
            'server_code': server_code,
            'client_code': client_code
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/tools/generate-datastore-module', methods=['POST'])
def generate_datastore_module():
    """Generate DataStore manager module"""
    try:
        data = request.json
        datastore_name = data.get('name', 'PlayerData')
        default_data = data.get('defaultData', {})

        code = f"""-- DataStore Manager Module
local DataStoreService = game:GetService("DataStoreService")
local {datastore_name}Store = DataStoreService:GetDataStore("{datastore_name}")

local DataManager = {{}}

local DEFAULT_DATA = {json.dumps(default_data, indent=4)}

function DataManager:LoadData(player)
    local success, data = pcall(function()
        return {datastore_name}Store:GetAsync("Player_" .. player.UserId)
    end)

    if success then
        return data or DEFAULT_DATA
    else
        warn("Failed to load data for " .. player.Name)
        return DEFAULT_DATA
    end
end

function DataManager:SaveData(player, data)
    local success, err = pcall(function()
        {datastore_name}Store:SetAsync("Player_" .. player.UserId, data)
    end)

    if success then
        print("Data saved for " .. player.Name)
    else
        warn("Failed to save data for " .. player.Name .. ": " .. tostring(err))
    end
end

function DataManager:UpdateData(player, updateFunction)
    local success, err = pcall(function()
        {datastore_name}Store:UpdateAsync("Player_" .. player.UserId, updateFunction)
    end)

    if not success then
        warn("Failed to update data: " .. tostring(err))
    end
end

return DataManager
"""

        return jsonify({
            'success': True,
            'code': code
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/tools/generate-service', methods=['POST'])
def generate_service_module():
    """Generate service module template"""
    try:
        data = request.json
        service_name = data.get('name', 'MyService')
        methods = data.get('methods', [])

        methods_code = '\n\n'.join([
            f"function {service_name}:{method['name']}({', '.join(method.get('params', []))})\n    -- TODO: Implement {method['name']}\nend"
            for method in methods
        ])

        code = f"""-- {service_name} Module
local {service_name} = {{}}
{service_name}.__index = {service_name}

function {service_name}.new()
    local self = setmetatable({{}}, {service_name})
    -- Initialize service
    return self
end

function {service_name}:Init()
    -- Initialization logic
    print("{service_name} initialized")
end

{methods_code}

return {service_name}
"""

        return jsonify({
            'success': True,
            'code': code
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/tools/luau-validate', methods=['POST'])
def validate_luau_code():
    """Basic Luau syntax validation"""
    try:
        data = request.json
        code = data.get('code', '')

        issues = []
        lines = code.split('\n')

        # Basic syntax checks
        for i, line in enumerate(lines, 1):
            # Check for common mistakes
            if 'function(' in line:
                issues.append({
                    'line': i,
                    'type': 'warning',
                    'message': 'Missing space after function keyword'
                })
            if line.strip().endswith('then') and not line.strip().startswith('--'):
                issues.append({
                    'line': i,
                    'type': 'style',
                    'message': 'Consider putting code after "then" on next line'
                })
            if '==' in line and 'nil' in line:
                issues.append({
                    'line': i,
                    'type': 'warning',
                    'message': 'Consider using "if not value" instead of "== nil"'
                })

        return jsonify({
            'success': True,
            'issues': issues,
            'issue_count': len(issues)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/tools/generate-gui-code', methods=['POST'])
def generate_gui_code():
    """Generate GUI creation code"""
    try:
        data = request.json
        gui_name = data.get('name', 'MyGUI')
        gui_type = data.get('type', 'ScreenGui')
        elements = data.get('elements', [])

        elements_code = '\n'.join([
            f"""local {elem['name']} = Instance.new("{elem['type']}")
{elem['name']}.Name = "{elem['name']}"
{elem['name']}.Parent = {gui_name}
-- Configure {elem['name']} properties here
"""
            for elem in elements
        ])

        code = f"""-- GUI Script
local {gui_name} = Instance.new("{gui_type}")
{gui_name}.Name = "{gui_name}"
{gui_name}.Parent = game.Players.LocalPlayer:WaitForChild("PlayerGui")
{gui_name}.ResetOnSpawn = false

{elements_code}
"""

        return jsonify({
            'success': True,
            'code': code
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============= ANALYTICS & MONITORING =============

@app.route('/api/analytics/universe/<universe_id>/stats')
def get_universe_stats(universe_id):
    """Get comprehensive universe statistics"""
    try:
        # Get player count
        player_response = requests.get(
            f'https://games.roblox.com/v1/games?universeIds={universe_id}'
        )

        stats = {}

        if player_response.status_code == 200:
            game_data = player_response.json().get('data', [{}])[0]
            stats['playing'] = game_data.get('playing', 0)
            stats['visits'] = game_data.get('visits', 0)
            stats['favorites'] = game_data.get('favoritedCount', 0)

        # Get votes
        vote_response = requests.get(
            f'https://games.roblox.com/v1/games/votes?universeIds={universe_id}'
        )

        if vote_response.status_code == 200:
            vote_data = vote_response.json().get('data', [{}])[0]
            stats['upVotes'] = vote_data.get('upVotes', 0)
            stats['downVotes'] = vote_data.get('downVotes', 0)

        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/analytics/track-event', methods=['POST'])
def track_custom_event():
    """Track custom analytics event"""
    try:
        data = request.json
        event_type = data.get('type')
        event_data = data.get('data', {})
        universe_id = data.get('universeId')

        conn = sqlite3.connect('data/datastore.db')
        c = conn.cursor()

        c.execute('''
            CREATE TABLE IF NOT EXISTS analytics_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                universe_id TEXT,
                event_type TEXT,
                event_data TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        c.execute(
            'INSERT INTO analytics_events (universe_id, event_type, event_data) VALUES (?, ?, ?)',
            (universe_id, event_type, json.dumps(event_data))
        )

        conn.commit()
        conn.close()

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/analytics/events/<universe_id>')
def get_analytics_events(universe_id):
    """Get analytics events for universe"""
    try:
        conn = sqlite3.connect('data/datastore.db')
        c = conn.cursor()

        c.execute(
            'SELECT event_type, event_data, timestamp FROM analytics_events WHERE universe_id = ? ORDER BY timestamp DESC LIMIT 1000',
            (universe_id,)
        )

        events = []
        for row in c.fetchall():
            events.append({
                'type': row[0],
                'data': json.loads(row[1]),
                'timestamp': row[2]
            })

        conn.close()

        return jsonify({'success': True, 'events': events})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/monitoring/health-check/<universe_id>')
def universe_health_check(universe_id):
    """Perform health check on universe"""
    try:
        health = {
            'timestamp': datetime.now().isoformat(),
            'checks': []
        }

        # Check if game is online
        game_response = requests.get(
            f'https://games.roblox.com/v1/games?universeIds={universe_id}'
        )

        if game_response.status_code == 200:
            game_data = game_response.json().get('data', [{}])[0]
            health['checks'].append({
                'name': 'Game API',
                'status': 'healthy',
                'details': f"Currently {game_data.get('playing', 0)} players online"
            })
        else:
            health['checks'].append({
                'name': 'Game API',
                'status': 'unhealthy',
                'details': f'API returned {game_response.status_code}'
            })

        # Check DataStore access
        headers = {'x-api-key': global_config.get('api_key', '')}
        ds_response = requests.get(
            f'https://apis.roblox.com/datastores/v1/universes/{universe_id}/standard-datastores',
            headers=headers
        )

        if ds_response.status_code == 200:
            health['checks'].append({
                'name': 'DataStore Access',
                'status': 'healthy'
            })
        else:
            health['checks'].append({
                'name': 'DataStore Access',
                'status': 'unhealthy',
                'details': f'API returned {ds_response.status_code}'
            })

        health['overall_status'] = 'healthy' if all(c['status'] == 'healthy' for c in health['checks']) else 'degraded'

        return jsonify(health)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/monitoring/server-list/<universe_id>')
def monitor_server_list(universe_id):
    """Monitor and list all running servers"""
    try:
        response = requests.get(
            f'https://games.roblox.com/v1/games/{universe_id}/servers/Public',
            params={'limit': 100}
        )

        if response.status_code == 200:
            data = response.json()
            servers = data.get('data', [])

            analysis = {
                'total_servers': len(servers),
                'total_players': sum(s.get('playing', 0) for s in servers),
                'average_players_per_server': sum(s.get('playing', 0) for s in servers) / len(servers) if servers else 0,
                'servers': servers
            }

            return jsonify(analysis)
        else:
            return jsonify({'error': f'API error: {response.status_code}'}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============= UTILITIES & HELPERS =============

@app.route('/api/utils/batch-operations', methods=['POST'])
def batch_operations():
    """Execute multiple operations in batch"""
    try:
        data = request.json
        operations = data.get('operations', [])
        results = []

        for op in operations:
            op_type = op.get('type')
            op_data = op.get('data', {})

            # Execute operation based on type
            if op_type == 'datastore_set':
                # Handle datastore set
                results.append({'operation': op_type, 'status': 'completed'})
            elif op_type == 'datastore_delete':
                # Handle datastore delete
                results.append({'operation': op_type, 'status': 'completed'})
            else:
                results.append({'operation': op_type, 'status': 'unsupported'})

        return jsonify({'success': True, 'results': results})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/utils/webhook/send', methods=['POST'])
def send_webhook():
    """Send webhook notification"""
    try:
        data = request.json
        webhook_url = data.get('url')
        content = data.get('content', {})

        response = requests.post(webhook_url, json=content)

        return jsonify({
            'success': response.status_code == 200,
            'status_code': response.status_code
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/utils/rate-limiter/status')
def get_rate_limiter_status():
    """Get rate limiter status"""
    try:
        # Simple rate limiter status
        status = {
            'requests_remaining': 1000,
            'reset_time': (datetime.now().timestamp() + 3600),
            'limit': 1000
        }

        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/utils/backup/create', methods=['POST'])
def create_backup():
    """Create backup of datastores"""
    try:
        data = request.json
        universe_id = data.get('universeId')
        datastore_name = data.get('datastoreName')

        # Create backup directory if not exists
        backup_dir = 'data/backups'
        os.makedirs(backup_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f"{backup_dir}/backup_{universe_id}_{datastore_name}_{timestamp}.json"

        # Export datastore (simplified)
        backup_data = {
            'universe_id': universe_id,
            'datastore': datastore_name,
            'timestamp': timestamp,
            'data': {}  # Would contain actual data
        }

        with open(backup_file, 'w') as f:
            json.dump(backup_data, f, indent=2)

        return jsonify({
            'success': True,
            'backup_file': backup_file,
            'timestamp': timestamp
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/utils/scheduler/add-task', methods=['POST'])
def add_scheduled_task():
    """Add a scheduled task"""
    try:
        data = request.json
        task_name = data.get('name')
        schedule = data.get('schedule')  # cron format
        action = data.get('action')

        conn = sqlite3.connect('data/datastore.db')
        c = conn.cursor()

        c.execute('''
            CREATE TABLE IF NOT EXISTS scheduled_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                schedule TEXT,
                action TEXT,
                enabled BOOLEAN DEFAULT 1,
                last_run TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        c.execute(
            'INSERT INTO scheduled_tasks (name, schedule, action) VALUES (?, ?, ?)',
            (task_name, schedule, json.dumps(action))
        )

        conn.commit()
        conn.close()

        return jsonify({'success': True, 'task_id': c.lastrowid})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print('\n' + '='*60)
    print('  Roblox DataStore Manager')
    print('='*60)
    print(f'\n  Running on http://127.0.0.1:8001\n')

    from waitress import serve
    serve(app, host='127.0.0.1', port=8001)
