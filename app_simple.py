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
from src.roblox_api import RobloxDataStoreAPI, OrderedDataStoreAPI

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-this')
CORS(app)

# Global state
api_client = None
ordered_api_client = None
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

    conn.commit()
    conn.close()


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


@app.route('/')
def index():
    return render_template('index_production.html')


@app.route('/api/config', methods=['GET', 'POST'])
def handle_config():
    global api_client, ordered_api_client, config_data

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


# Analytics endpoints (simplified)
@app.route('/api/analytics/dashboard')
def analytics_dashboard():
    return jsonify({
        'success_rate': 100,
        'avg_response_time': 0,
        'read_operations': 0,
        'write_operations': 0
    })


@app.route('/api/analytics/timeseries')
def analytics_timeseries():
    return jsonify({})


@app.route('/api/analytics/top-datastores')
def analytics_top_ds():
    return jsonify({'datastores': []})


@app.route('/api/analytics/errors')
def analytics_errors():
    return jsonify({'total_errors': 0, 'error_patterns': {}, 'errors_by_operation': {}})


# ===== ORDERED DATASTORE ENDPOINTS =====
@app.route('/api/ordered/list')
def list_ordered_entries():
    if not ordered_api_client:
        return jsonify({'error': 'API not configured'}), 400

    try:
        datastore = request.args.get('datastore', '')
        scope = request.args.get('scope', 'global')
        ascending = request.args.get('ascending', 'false').lower() == 'true'
        limit = int(request.args.get('limit', 100))

        if not datastore:
            return jsonify({'error': 'Datastore name required'}), 400

        entries = ordered_api_client.list_entries(datastore, scope, ascending, limit)
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
            value = ordered_api_client.get_entry(datastore, key, scope)
            log_operation('GET_ORDERED', datastore, key, True)
            return jsonify({'value': value})

        elif request.method == 'POST':
            data = request.get_json()
            value = int(data.get('value', 0))
            result = ordered_api_client.set_entry(datastore, key, value, scope)
            log_operation('SET_ORDERED', datastore, key, True)
            return jsonify(result)

        elif request.method == 'DELETE':
            ordered_api_client.delete_entry(datastore, key, scope)
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

        result = ordered_api_client.increment_entry(datastore, key, increment_by, scope)
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


if __name__ == '__main__':
    print('\n' + '='*60)
    print('  Roblox DataStore Manager')
    print('='*60)
    print(f'\n  Running on http://127.0.0.1:8000\n')

    from waitress import serve
    serve(app, host='127.0.0.1', port=8000)
