"""
Roblox DataStore Manager - Production Application
Advanced Open Cloud Management Tool with full production features
"""

import os
import json
import hashlib
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
from flask_migrate import Migrate
from flask_caching import Cache
from src.models import db, OperationHistory, Backup, Bookmark, Analytics, DataStoreCache
from src.config import config
from src.roblox_api import RobloxDataStoreAPI, OrderedDataStoreAPI
from src.security import EncryptionManager, RateLimiter, InputValidator, generate_csrf_token
from src.analytics import AnalyticsEngine

# Initialize extensions
migrate = Migrate()
cache = Cache()
limiter = RateLimiter(max_requests=100, window_seconds=60)


def create_app(config_name='default'):
    """Application factory"""
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize extensions
    CORS(app)
    db.init_app(app)
    migrate.init_app(app, db)
    cache.init_app(app)

    # Create tables
    with app.app_context():
        db.create_all()

    # Security setup
    if app.config.get('ENCRYPTION_KEY'):
        encryption = EncryptionManager(app.config['ENCRYPTION_KEY'])
    else:
        encryption = EncryptionManager()

    # Store in app context
    app.encryption = encryption
    app.analytics_engine = None

    @app.before_request
    def before_request():
        """Setup before each request"""
        if app.analytics_engine is None:
            app.analytics_engine = AnalyticsEngine(db.session)

        # Rate limiting
        client_ip = request.remote_addr
        if not limiter.is_allowed(client_ip):
            return jsonify({
                'error': 'Rate limit exceeded',
                'reset_in': limiter.get_reset_time(client_ip)
            }), 429

    @app.context_processor
    def inject_csrf():
        """Inject CSRF token into templates"""
        return dict(csrf_token=generate_csrf_token)

    # Global state for API client
    api_state = {
        'client': None,
        'config': {
            'api_key': '',
            'universe_id': '',
            'theme': 'dark'
        }
    }

    # ===== ROUTES =====

    @app.route('/')
    def index():
        """Main dashboard"""
        return render_template('index_production.html')

    @app.route('/api/csrf-token')
    def get_csrf():
        """Get CSRF token"""
        return jsonify({'token': generate_csrf_token()})

    @app.route('/api/config', methods=['GET', 'POST'])
    def handle_config():
        """Get or update configuration"""
        if request.method == 'POST':
            data = request.json

            # Validate inputs
            if 'universe_id' in data:
                valid, error = InputValidator.validate_universe_id(data['universe_id'])
                if not valid:
                    return jsonify({'error': error}), 400

            if 'api_key' in data:
                valid, error = InputValidator.validate_api_key(data['api_key'])
                if not valid:
                    return jsonify({'error': error}), 400

            # Update config
            api_state['config'].update(data)

            # Initialize API client
            if api_state['config']['api_key'] and api_state['config']['universe_id']:
                api_state['client'] = RobloxDataStoreAPI(
                    api_state['config']['api_key'],
                    api_state['config']['universe_id']
                )

            # Store encrypted key in session
            if 'api_key' in data:
                session['encrypted_key'] = app.encryption.encrypt(data['api_key'])

            return jsonify({'status': 'success'})

        return jsonify({
            'universe_id': api_state['config'].get('universe_id', ''),
            'theme': api_state['config'].get('theme', 'dark'),
            'has_key': bool(api_state['config'].get('api_key'))
        })

    @app.route('/api/test-connection', methods=['POST'])
    def test_connection():
        """Test API connection"""
        if not api_state['client']:
            return jsonify({'status': 'error', 'message': 'API not configured'}), 400

        try:
            datastores = api_state['client'].list_datastores(limit=1)
            return jsonify({
                'status': 'success',
                'message': 'Connection successful',
                'rate_limit': api_state['client'].get_rate_limit_status()
            })
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 400

    @app.route('/api/datastores', methods=['GET'])
    @cache.cached(timeout=60, query_string=True)
    def list_datastores():
        """List all datastores"""
        if not api_state['client']:
            return jsonify({'error': 'API not configured'}), 400

        try:
            prefix = request.args.get('prefix', '')
            cursor = request.args.get('cursor', '')

            result = api_state['client'].list_datastores(prefix=prefix, cursor=cursor)

            # Log operation
            log_operation(
                'LIST_DATASTORES',
                '',
                '',
                json.dumps({'prefix': prefix}),
                True,
                0
            )

            return jsonify(result)
        except Exception as e:
            log_operation('LIST_DATASTORES', '', '', str(e), False, 0)
            return jsonify({'error': str(e)}), 500

    @app.route('/api/datastores/all', methods=['GET'])
    def list_all_datastores():
        """List all datastores with pagination"""
        if not api_state['client']:
            return jsonify({'error': 'API not configured'}), 400

        try:
            start_time = datetime.utcnow()
            datastores = api_state['client'].list_all_datastores()
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            log_operation(
                'LIST_ALL_DATASTORES',
                '',
                '',
                f'Found {len(datastores)} datastores',
                True,
                response_time
            )

            # Cache datastore info
            for ds in datastores:
                cache_datastore_info(ds)

            return jsonify({
                'datastores': datastores,
                'count': len(datastores),
                'response_time_ms': round(response_time, 2)
            })
        except Exception as e:
            log_operation('LIST_ALL_DATASTORES', '', '', str(e), False, 0)
            return jsonify({'error': str(e)}), 500

    @app.route('/api/entries', methods=['GET'])
    def list_entries():
        """List entries in a datastore"""
        if not api_state['client']:
            return jsonify({'error': 'API not configured'}), 400

        try:
            datastore_name = request.args.get('datastore', '')
            scope = request.args.get('scope', 'global')
            prefix = request.args.get('prefix', '')
            cursor = request.args.get('cursor', '')
            all_scopes = request.args.get('all_scopes', 'false').lower() == 'true'

            # Validate
            valid, error = InputValidator.validate_datastore_name(datastore_name)
            if not valid:
                return jsonify({'error': error}), 400

            start_time = datetime.utcnow()
            result = api_state['client'].list_entries(
                datastore_name, scope, prefix, cursor=cursor, all_scopes=all_scopes
            )
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            log_operation(
                'LIST_ENTRIES',
                datastore_name,
                '',
                f'Found {len(result.get("keys", []))} entries',
                True,
                response_time
            )

            return jsonify(result)
        except Exception as e:
            log_operation('LIST_ENTRIES', datastore_name, '', str(e), False, 0)
            return jsonify({'error': str(e)}), 500

    @app.route('/api/entries/all', methods=['GET'])
    def list_all_entries():
        """List all entries with pagination"""
        if not api_state['client']:
            return jsonify({'error': 'API not configured'}), 400

        try:
            datastore_name = request.args.get('datastore', '')
            scope = request.args.get('scope', 'global')
            prefix = request.args.get('prefix', '')

            valid, error = InputValidator.validate_datastore_name(datastore_name)
            if not valid:
                return jsonify({'error': error}), 400

            start_time = datetime.utcnow()
            entries = api_state['client'].list_all_entries(datastore_name, scope, prefix)
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            log_operation(
                'LIST_ALL_ENTRIES',
                datastore_name,
                '',
                f'Found {len(entries)} entries',
                True,
                response_time
            )

            return jsonify({
                'keys': entries,
                'count': len(entries),
                'response_time_ms': round(response_time, 2)
            })
        except Exception as e:
            log_operation('LIST_ALL_ENTRIES', datastore_name, '', str(e), False, 0)
            return jsonify({'error': str(e)}), 500

    @app.route('/api/entry', methods=['GET', 'POST', 'DELETE'])
    def handle_entry():
        """Get, set, or delete an entry"""
        if not api_state['client']:
            return jsonify({'error': 'API not configured'}), 400

        datastore_name = request.args.get('datastore', '')
        key = request.args.get('key', '')
        scope = request.args.get('scope', 'global')

        # Validate
        valid, error = InputValidator.validate_datastore_name(datastore_name)
        if not valid:
            return jsonify({'error': error}), 400

        valid, error = InputValidator.validate_key_name(key)
        if not valid:
            return jsonify({'error': error}), 400

        try:
            if request.method == 'GET':
                start_time = datetime.utcnow()
                value, metadata = api_state['client'].get_entry(datastore_name, key, scope)
                response_time = (datetime.utcnow() - start_time).total_seconds() * 1000

                log_operation('GET_ENTRY', datastore_name, key, 'Success', True, response_time)

                # Record analytics
                app.analytics_engine.record_operation({
                    'universe_id': api_state['config']['universe_id'],
                    'datastore_name': datastore_name,
                    'operation_type': 'GET_ENTRY',
                    'success': True,
                    'response_time_ms': response_time
                })

                return jsonify({
                    'value': value,
                    'metadata': metadata,
                    'response_time_ms': round(response_time, 2)
                })

            elif request.method == 'POST':
                data = request.json
                value = data.get('value')
                user_ids = data.get('user_ids', [])
                attributes = data.get('attributes', {})
                match_version = data.get('match_version')
                exclusive_create = data.get('exclusive_create', False)

                start_time = datetime.utcnow()
                result = api_state['client'].set_entry(
                    datastore_name, key, value, scope,
                    user_ids=user_ids if user_ids else None,
                    attributes=attributes if attributes else None,
                    match_version=match_version,
                    exclusive_create=exclusive_create
                )
                response_time = (datetime.utcnow() - start_time).total_seconds() * 1000

                log_operation(
                    'SET_ENTRY',
                    datastore_name,
                    key,
                    json.dumps(value)[:200],
                    True,
                    response_time
                )

                app.analytics_engine.record_operation({
                    'universe_id': api_state['config']['universe_id'],
                    'datastore_name': datastore_name,
                    'operation_type': 'SET_ENTRY',
                    'success': True,
                    'response_time_ms': response_time
                })

                return jsonify({**result, 'response_time_ms': round(response_time, 2)})

            elif request.method == 'DELETE':
                start_time = datetime.utcnow()
                api_state['client'].delete_entry(datastore_name, key, scope)
                response_time = (datetime.utcnow() - start_time).total_seconds() * 1000

                log_operation('DELETE_ENTRY', datastore_name, key, 'Success', True, response_time)

                app.analytics_engine.record_operation({
                    'universe_id': api_state['config']['universe_id'],
                    'datastore_name': datastore_name,
                    'operation_type': 'DELETE_ENTRY',
                    'success': True,
                    'response_time_ms': response_time
                })

                return jsonify({
                    'status': 'success',
                    'message': f'Entry {key} deleted',
                    'response_time_ms': round(response_time, 2)
                })

        except Exception as e:
            log_operation(request.method + '_ENTRY', datastore_name, key, str(e), False, 0)
            app.analytics_engine.record_operation({
                'universe_id': api_state['config']['universe_id'],
                'datastore_name': datastore_name,
                'operation_type': f'{request.method}_ENTRY',
                'success': False,
                'response_time_ms': 0
            })
            return jsonify({'error': str(e)}), 500

    @app.route('/api/entry/increment', methods=['POST'])
    def increment_entry():
        """Increment a numeric entry"""
        if not api_state['client']:
            return jsonify({'error': 'API not configured'}), 400

        try:
            datastore_name = request.args.get('datastore', '')
            key = request.args.get('key', '')
            scope = request.args.get('scope', 'global')
            data = request.json
            increment_by = data.get('increment_by', 1)

            start_time = datetime.utcnow()
            result = api_state['client'].increment_entry(datastore_name, key, increment_by, scope)
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            log_operation(
                'INCREMENT_ENTRY',
                datastore_name,
                key,
                f'Increment by {increment_by}',
                True,
                response_time
            )

            return jsonify({'value': result, 'response_time_ms': round(response_time, 2)})
        except Exception as e:
            log_operation('INCREMENT_ENTRY', datastore_name, key, str(e), False, 0)
            return jsonify({'error': str(e)}), 500

    @app.route('/api/versions', methods=['GET'])
    def list_versions():
        """List version history"""
        if not api_state['client']:
            return jsonify({'error': 'API not configured'}), 400

        try:
            datastore_name = request.args.get('datastore', '')
            key = request.args.get('key', '')
            scope = request.args.get('scope', 'global')
            sort_order = request.args.get('sort_order', 'Descending')

            result = api_state['client'].list_versions(datastore_name, key, scope, sort_order)
            return jsonify(result)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/version', methods=['GET'])
    def get_version():
        """Get specific version"""
        if not api_state['client']:
            return jsonify({'error': 'API not configured'}), 400

        try:
            datastore_name = request.args.get('datastore', '')
            key = request.args.get('key', '')
            version = request.args.get('version', '')
            scope = request.args.get('scope', 'global')

            result = api_state['client'].get_version(datastore_name, key, version, scope)
            return jsonify({'value': result})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/bulk/delete', methods=['POST'])
    def bulk_delete():
        """Bulk delete entries"""
        if not api_state['client']:
            return jsonify({'error': 'API not configured'}), 400

        try:
            data = request.json
            datastore_name = data.get('datastore', '')
            keys = data.get('keys', [])
            scope = data.get('scope', 'global')

            results = api_state['client'].bulk_delete_entries(datastore_name, keys, scope)
            success_count = sum(1 for v in results.values() if v)

            log_operation(
                'BULK_DELETE',
                datastore_name,
                '',
                f'Deleted {success_count}/{len(keys)} entries',
                True,
                0
            )

            return jsonify({'results': results, 'success_count': success_count})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/export', methods=['POST'])
    def export_datastore():
        """Export datastore"""
        if not api_state['client']:
            return jsonify({'error': 'API not configured'}), 400

        try:
            data = request.json
            datastore_name = data.get('datastore', '')
            scope = data.get('scope', 'global')
            include_metadata = data.get('include_metadata', True)

            start_time = datetime.utcnow()
            export_data = api_state['client'].export_datastore(datastore_name, scope, include_metadata)
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            # Save backup
            os.makedirs('backups', exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'backups/{datastore_name}_{timestamp}.json'

            backup_content = {
                'universe_id': api_state['config']['universe_id'],
                'datastore_name': datastore_name,
                'scope': scope,
                'exported_at': datetime.now().isoformat(),
                'entry_count': len(export_data),
                'entries': export_data
            }

            with open(filename, 'w') as f:
                json.dump(backup_content, f, indent=2)

            file_size = os.path.getsize(filename)
            checksum = hashlib.sha256(json.dumps(backup_content).encode()).hexdigest()

            # Record backup
            backup = Backup(
                universe_id=api_state['config']['universe_id'],
                datastore_name=datastore_name,
                scope=scope,
                backup_file=filename,
                file_size_bytes=file_size,
                entry_count=len(export_data),
                checksum=checksum
            )
            db.session.add(backup)
            db.session.commit()

            log_operation(
                'EXPORT',
                datastore_name,
                '',
                f'Exported {len(export_data)} entries to {filename}',
                True,
                response_time
            )

            return jsonify({
                'status': 'success',
                'filename': filename,
                'entry_count': len(export_data),
                'file_size_bytes': file_size,
                'checksum': checksum,
                'response_time_ms': round(response_time, 2),
                'data': export_data
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/import', methods=['POST'])
    def import_datastore():
        """Import data"""
        if not api_state['client']:
            return jsonify({'error': 'API not configured'}), 400

        try:
            data = request.json
            datastore_name = data.get('datastore', '')
            entries = data.get('entries', [])
            scope = data.get('scope', 'global')
            overwrite = data.get('overwrite', False)

            results = api_state['client'].import_datastore(datastore_name, entries, scope, overwrite)

            log_operation(
                'IMPORT',
                datastore_name,
                '',
                f'Imported {results["success"]} entries',
                True,
                0
            )

            return jsonify(results)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/analytics/dashboard', methods=['GET'])
    def get_analytics_dashboard():
        """Get dashboard analytics"""
        try:
            days = int(request.args.get('days', 7))
            stats = app.analytics_engine.get_dashboard_stats(
                universe_id=api_state['config'].get('universe_id'),
                days=days
            )
            return jsonify(stats)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/analytics/timeseries', methods=['GET'])
    def get_timeseries():
        """Get time series data"""
        try:
            days = int(request.args.get('days', 30))
            granularity = request.args.get('granularity', 'day')
            data = app.analytics_engine.get_time_series_data(
                universe_id=api_state['config'].get('universe_id'),
                days=days,
                granularity=granularity
            )
            return jsonify(data)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/analytics/top-datastores', methods=['GET'])
    def get_top_datastores():
        """Get top datastores"""
        try:
            days = int(request.args.get('days', 7))
            limit = int(request.args.get('limit', 10))
            data = app.analytics_engine.get_top_datastores(
                universe_id=api_state['config'].get('universe_id'),
                days=days,
                limit=limit
            )
            return jsonify({'datastores': data})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/analytics/errors', methods=['GET'])
    def get_error_analysis():
        """Get error analysis"""
        try:
            days = int(request.args.get('days', 7))
            data = app.analytics_engine.get_error_analysis(days=days)
            return jsonify(data)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/history', methods=['GET'])
    def get_history():
        """Get operation history"""
        try:
            limit = int(request.args.get('limit', 50))
            operations = OperationHistory.query.order_by(
                OperationHistory.timestamp.desc()
            ).limit(limit).all()

            history = []
            for op in operations:
                history.append({
                    'id': op.id,
                    'timestamp': op.timestamp.isoformat(),
                    'operation_type': op.operation_type,
                    'datastore_name': op.datastore_name or '',
                    'key_name': op.key_name or '',
                    'success': op.success,
                    'response_time_ms': op.response_time_ms or 0,
                    'error_message': op.error_message
                })

            return jsonify({'history': history})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/backups', methods=['GET'])
    def list_backups():
        """List backup history"""
        try:
            backups = Backup.query.order_by(Backup.created_at.desc()).limit(50).all()

            result = []
            for b in backups:
                result.append({
                    'id': b.id,
                    'timestamp': b.created_at.isoformat(),
                    'universe_id': b.universe_id,
                    'datastore_name': b.datastore_name,
                    'backup_file': b.backup_file,
                    'entry_count': b.entry_count,
                    'file_size_bytes': b.file_size_bytes,
                    'checksum': b.checksum
                })

            return jsonify({'backups': result})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/request-log', methods=['GET'])
    def get_request_log():
        """Get API request log"""
        if not api_state['client']:
            return jsonify({'log': [], 'rate_limit': {'remaining': 300, 'reset_in_seconds': 0}})

        return jsonify({
            'log': api_state['client'].get_request_log(),
            'rate_limit': api_state['client'].get_rate_limit_status()
        })

    @app.route('/api/stats', methods=['GET'])
    def get_stats():
        """Get quick stats"""
        try:
            stats = {
                'total_operations': OperationHistory.query.count(),
                'successful_operations': OperationHistory.query.filter_by(success=True).count(),
                'failed_operations': OperationHistory.query.filter_by(success=False).count(),
                'total_backups': Backup.query.count(),
                'total_bookmarks': Bookmark.query.count()
            }

            if api_state['client']:
                stats['rate_limit'] = api_state['client'].get_rate_limit_status()

            return jsonify(stats)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/health', methods=['GET'])
    def health_check():
        """Health check endpoint"""
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'connected',
            'api_configured': bool(api_state['client'])
        })

    # Helper functions
    def log_operation(op_type, datastore, key, details, success, response_time):
        """Log operation to database"""
        try:
            operation = OperationHistory(
                operation_type=op_type,
                datastore_name=datastore,
                key_name=key,
                request_data=details,
                success=success,
                response_time_ms=response_time,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent', '')[:255]
            )
            db.session.add(operation)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Failed to log operation: {e}")

    def cache_datastore_info(ds_info):
        """Cache datastore information"""
        try:
            universe_id = api_state['config'].get('universe_id', '')
            existing = DataStoreCache.query.filter_by(
                universe_id=universe_id,
                datastore_name=ds_info.get('name', '')
            ).first()

            if existing:
                existing.created_time = ds_info.get('createdTime', '')
                existing.cached_at = datetime.utcnow()
            else:
                cache_entry = DataStoreCache(
                    universe_id=universe_id,
                    datastore_name=ds_info.get('name', ''),
                    created_time=ds_info.get('createdTime', '')
                )
                db.session.add(cache_entry)

            db.session.commit()
        except Exception as e:
            db.session.rollback()

    return app


if __name__ == '__main__':
    app = create_app('development')
    app.run(host='127.0.0.1', port=5000, debug=True)
