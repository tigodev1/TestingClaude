"""
Roblox API Proxy Server
Full proxy for all Roblox APIs with analytics, rate limiting, and caching
"""

import os
import json
import time
import sqlite3
import requests
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from functools import wraps
import hashlib

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'proxy-secret-key-change-this')
CORS(app)

# Database for analytics
PROXY_DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'proxy.db')

# Cache for responses (in-memory with TTL)
response_cache = {}
CACHE_TTL = 60  # seconds

# Rate limiting per IP
rate_limits = {}
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX = 100  # requests per window


def init_proxy_db():
    """Initialize proxy analytics database"""
    os.makedirs(os.path.dirname(PROXY_DB_PATH), exist_ok=True)
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

    # Initialize stats row
    c.execute('INSERT OR IGNORE INTO proxy_stats (id, total_requests, last_updated) VALUES (1, 0, ?)',
              (datetime.now().isoformat(),))

    conn.commit()
    conn.close()


def log_proxy_request(client_ip, endpoint, roblox_api, method, status_code, response_time_ms, cached=False, error=''):
    """Log proxy request for analytics"""
    try:
        conn = sqlite3.connect(PROXY_DB_PATH)
        c = conn.cursor()
        c.execute('''INSERT INTO proxy_requests
                     (timestamp, client_ip, endpoint, roblox_api, method, status_code, response_time_ms, cached, error)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (datetime.now().isoformat(), client_ip, endpoint, roblox_api, method, status_code, response_time_ms, int(cached), error))

        # Update stats
        c.execute('UPDATE proxy_stats SET total_requests = total_requests + 1, last_updated = ? WHERE id = 1',
                  (datetime.now().isoformat(),))
        if cached:
            c.execute('UPDATE proxy_stats SET cached_requests = cached_requests + 1 WHERE id = 1')
        if status_code >= 400:
            c.execute('UPDATE proxy_stats SET failed_requests = failed_requests + 1 WHERE id = 1')

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Log error: {e}")


def check_rate_limit(client_ip):
    """Check if client is within rate limit"""
    now = time.time()

    if client_ip not in rate_limits:
        rate_limits[client_ip] = {'count': 0, 'window_start': now}

    client_rate = rate_limits[client_ip]

    # Reset window if expired
    if now - client_rate['window_start'] > RATE_LIMIT_WINDOW:
        client_rate['count'] = 0
        client_rate['window_start'] = now

    # Check limit
    if client_rate['count'] >= RATE_LIMIT_MAX:
        return False

    client_rate['count'] += 1
    return True


def get_cache_key(url, params=None):
    """Generate cache key for request"""
    key_data = url + json.dumps(params or {}, sort_keys=True)
    return hashlib.md5(key_data.encode()).hexdigest()


def get_cached_response(cache_key):
    """Get cached response if valid"""
    if cache_key in response_cache:
        cached = response_cache[cache_key]
        if time.time() - cached['time'] < CACHE_TTL:
            return cached['data']
        else:
            del response_cache[cache_key]
    return None


def set_cached_response(cache_key, data):
    """Cache response"""
    response_cache[cache_key] = {
        'data': data,
        'time': time.time()
    }
    # Clean old cache entries
    now = time.time()
    expired = [k for k, v in response_cache.items() if now - v['time'] > CACHE_TTL * 2]
    for k in expired:
        del response_cache[k]


def proxy_request(roblox_url, method='GET', params=None, json_data=None, headers=None):
    """Make proxied request to Roblox API"""
    start_time = time.time()

    req_headers = {
        'User-Agent': 'RobloxProxy/1.0',
        'Accept': 'application/json'
    }
    if headers:
        req_headers.update(headers)

    try:
        if method == 'GET':
            response = requests.get(roblox_url, params=params, headers=req_headers, timeout=30)
        elif method == 'POST':
            response = requests.post(roblox_url, params=params, json=json_data, headers=req_headers, timeout=30)
        else:
            response = requests.request(method, roblox_url, params=params, json=json_data, headers=req_headers, timeout=30)

        response_time = int((time.time() - start_time) * 1000)

        try:
            data = response.json()
        except:
            data = {'raw': response.text}

        return data, response.status_code, response_time

    except requests.exceptions.Timeout:
        return {'error': 'Request timeout'}, 504, int((time.time() - start_time) * 1000)
    except Exception as e:
        return {'error': str(e)}, 500, int((time.time() - start_time) * 1000)


# Initialize database
init_proxy_db()


# ===== PROXY ENDPOINTS =====

@app.route('/proxy/users/<user_id>')
def proxy_user_info(user_id):
    """Proxy user info endpoint"""
    client_ip = request.remote_addr
    if not check_rate_limit(client_ip):
        return jsonify({'error': 'Rate limit exceeded'}), 429

    roblox_url = f"https://users.roblox.com/v1/users/{user_id}"
    cache_key = get_cache_key(roblox_url)

    cached = get_cached_response(cache_key)
    if cached:
        log_proxy_request(client_ip, f'/proxy/users/{user_id}', roblox_url, 'GET', 200, 0, cached=True)
        return jsonify(cached)

    data, status, response_time = proxy_request(roblox_url)
    log_proxy_request(client_ip, f'/proxy/users/{user_id}', roblox_url, 'GET', status, response_time)

    if status == 200:
        set_cached_response(cache_key, data)

    return jsonify(data), status


@app.route('/proxy/users/username', methods=['POST'])
def proxy_username_lookup():
    """Proxy username to user ID lookup"""
    client_ip = request.remote_addr
    if not check_rate_limit(client_ip):
        return jsonify({'error': 'Rate limit exceeded'}), 429

    req_data = request.get_json()
    usernames = req_data.get('usernames', [])

    roblox_url = "https://users.roblox.com/v1/usernames/users"
    cache_key = get_cache_key(roblox_url, {'usernames': usernames})

    cached = get_cached_response(cache_key)
    if cached:
        log_proxy_request(client_ip, '/proxy/users/username', roblox_url, 'POST', 200, 0, cached=True)
        return jsonify(cached)

    data, status, response_time = proxy_request(roblox_url, method='POST', json_data={
        'usernames': usernames,
        'excludeBannedUsers': False
    })
    log_proxy_request(client_ip, '/proxy/users/username', roblox_url, 'POST', status, response_time)

    if status == 200:
        set_cached_response(cache_key, data)

    return jsonify(data), status


@app.route('/proxy/users/<user_id>/games')
def proxy_user_games(user_id):
    """Proxy user games endpoint"""
    client_ip = request.remote_addr
    if not check_rate_limit(client_ip):
        return jsonify({'error': 'Rate limit exceeded'}), 429

    limit = request.args.get('limit', 50)
    access_filter = request.args.get('accessFilter', 2)
    sort_order = request.args.get('sortOrder', 'Asc')

    roblox_url = f"https://games.roblox.com/v2/users/{user_id}/games"
    params = {'accessFilter': access_filter, 'limit': limit, 'sortOrder': sort_order}

    cache_key = get_cache_key(roblox_url, params)
    cached = get_cached_response(cache_key)
    if cached:
        log_proxy_request(client_ip, f'/proxy/users/{user_id}/games', roblox_url, 'GET', 200, 0, cached=True)
        return jsonify(cached)

    data, status, response_time = proxy_request(roblox_url, params=params)
    log_proxy_request(client_ip, f'/proxy/users/{user_id}/games', roblox_url, 'GET', status, response_time)

    if status == 200:
        set_cached_response(cache_key, data)

    return jsonify(data), status


@app.route('/proxy/users/<user_id>/groups')
def proxy_user_groups(user_id):
    """Proxy user groups endpoint"""
    client_ip = request.remote_addr
    if not check_rate_limit(client_ip):
        return jsonify({'error': 'Rate limit exceeded'}), 429

    roblox_url = f"https://groups.roblox.com/v1/users/{user_id}/groups/roles"
    cache_key = get_cache_key(roblox_url)

    cached = get_cached_response(cache_key)
    if cached:
        log_proxy_request(client_ip, f'/proxy/users/{user_id}/groups', roblox_url, 'GET', 200, 0, cached=True)
        return jsonify(cached)

    data, status, response_time = proxy_request(roblox_url)
    log_proxy_request(client_ip, f'/proxy/users/{user_id}/groups', roblox_url, 'GET', status, response_time)

    if status == 200:
        set_cached_response(cache_key, data)

    return jsonify(data), status


@app.route('/proxy/users/<user_id>/friends/count')
def proxy_friends_count(user_id):
    """Proxy friends count endpoint"""
    client_ip = request.remote_addr
    if not check_rate_limit(client_ip):
        return jsonify({'error': 'Rate limit exceeded'}), 429

    roblox_url = f"https://friends.roblox.com/v1/users/{user_id}/friends/count"
    cache_key = get_cache_key(roblox_url)

    cached = get_cached_response(cache_key)
    if cached:
        log_proxy_request(client_ip, f'/proxy/users/{user_id}/friends/count', roblox_url, 'GET', 200, 0, cached=True)
        return jsonify(cached)

    data, status, response_time = proxy_request(roblox_url)
    log_proxy_request(client_ip, f'/proxy/users/{user_id}/friends/count', roblox_url, 'GET', status, response_time)

    if status == 200:
        set_cached_response(cache_key, data)

    return jsonify(data), status


@app.route('/proxy/users/<user_id>/followers/count')
def proxy_followers_count(user_id):
    """Proxy followers count endpoint"""
    client_ip = request.remote_addr
    if not check_rate_limit(client_ip):
        return jsonify({'error': 'Rate limit exceeded'}), 429

    roblox_url = f"https://friends.roblox.com/v1/users/{user_id}/followers/count"
    cache_key = get_cache_key(roblox_url)

    cached = get_cached_response(cache_key)
    if cached:
        log_proxy_request(client_ip, f'/proxy/users/{user_id}/followers/count', roblox_url, 'GET', 200, 0, cached=True)
        return jsonify(cached)

    data, status, response_time = proxy_request(roblox_url)
    log_proxy_request(client_ip, f'/proxy/users/{user_id}/followers/count', roblox_url, 'GET', status, response_time)

    if status == 200:
        set_cached_response(cache_key, data)

    return jsonify(data), status


@app.route('/proxy/groups/<group_id>')
def proxy_group_info(group_id):
    """Proxy group info endpoint"""
    client_ip = request.remote_addr
    if not check_rate_limit(client_ip):
        return jsonify({'error': 'Rate limit exceeded'}), 429

    roblox_url = f"https://groups.roblox.com/v1/groups/{group_id}"
    cache_key = get_cache_key(roblox_url)

    cached = get_cached_response(cache_key)
    if cached:
        log_proxy_request(client_ip, f'/proxy/groups/{group_id}', roblox_url, 'GET', 200, 0, cached=True)
        return jsonify(cached)

    data, status, response_time = proxy_request(roblox_url)
    log_proxy_request(client_ip, f'/proxy/groups/{group_id}', roblox_url, 'GET', status, response_time)

    if status == 200:
        set_cached_response(cache_key, data)

    return jsonify(data), status


@app.route('/proxy/groups/<group_id>/games')
def proxy_group_games(group_id):
    """Proxy group games endpoint"""
    client_ip = request.remote_addr
    if not check_rate_limit(client_ip):
        return jsonify({'error': 'Rate limit exceeded'}), 429

    limit = request.args.get('limit', 50)
    access_filter = request.args.get('accessFilter', 2)
    sort_order = request.args.get('sortOrder', 'Asc')

    roblox_url = f"https://games.roblox.com/v2/groups/{group_id}/games"
    params = {'accessFilter': access_filter, 'limit': limit, 'sortOrder': sort_order}

    cache_key = get_cache_key(roblox_url, params)
    cached = get_cached_response(cache_key)
    if cached:
        log_proxy_request(client_ip, f'/proxy/groups/{group_id}/games', roblox_url, 'GET', 200, 0, cached=True)
        return jsonify(cached)

    data, status, response_time = proxy_request(roblox_url, params=params)
    log_proxy_request(client_ip, f'/proxy/groups/{group_id}/games', roblox_url, 'GET', status, response_time)

    if status == 200:
        set_cached_response(cache_key, data)

    return jsonify(data), status


@app.route('/proxy/games')
def proxy_game_info():
    """Proxy game info endpoint"""
    client_ip = request.remote_addr
    if not check_rate_limit(client_ip):
        return jsonify({'error': 'Rate limit exceeded'}), 429

    universe_ids = request.args.get('universeIds', '')
    if not universe_ids:
        return jsonify({'error': 'universeIds required'}), 400

    roblox_url = f"https://games.roblox.com/v1/games"
    params = {'universeIds': universe_ids}

    cache_key = get_cache_key(roblox_url, params)
    cached = get_cached_response(cache_key)
    if cached:
        log_proxy_request(client_ip, '/proxy/games', roblox_url, 'GET', 200, 0, cached=True)
        return jsonify(cached)

    data, status, response_time = proxy_request(roblox_url, params=params)
    log_proxy_request(client_ip, '/proxy/games', roblox_url, 'GET', status, response_time)

    if status == 200:
        set_cached_response(cache_key, data)

    return jsonify(data), status


@app.route('/proxy/games/votes')
def proxy_game_votes():
    """Proxy game votes endpoint"""
    client_ip = request.remote_addr
    if not check_rate_limit(client_ip):
        return jsonify({'error': 'Rate limit exceeded'}), 429

    universe_ids = request.args.get('universeIds', '')
    if not universe_ids:
        return jsonify({'error': 'universeIds required'}), 400

    roblox_url = f"https://games.roblox.com/v1/games/votes"
    params = {'universeIds': universe_ids}

    cache_key = get_cache_key(roblox_url, params)
    cached = get_cached_response(cache_key)
    if cached:
        log_proxy_request(client_ip, '/proxy/games/votes', roblox_url, 'GET', 200, 0, cached=True)
        return jsonify(cached)

    data, status, response_time = proxy_request(roblox_url, params=params)
    log_proxy_request(client_ip, '/proxy/games/votes', roblox_url, 'GET', status, response_time)

    if status == 200:
        set_cached_response(cache_key, data)

    return jsonify(data), status


@app.route('/proxy/thumbnails/users')
def proxy_user_thumbnails():
    """Proxy user thumbnails endpoint"""
    client_ip = request.remote_addr
    if not check_rate_limit(client_ip):
        return jsonify({'error': 'Rate limit exceeded'}), 429

    user_ids = request.args.get('userIds', '')
    size = request.args.get('size', '420x420')
    format_type = request.args.get('format', 'Png')

    roblox_url = "https://thumbnails.roblox.com/v1/users/avatar-headshot"
    params = {'userIds': user_ids, 'size': size, 'format': format_type}

    cache_key = get_cache_key(roblox_url, params)
    cached = get_cached_response(cache_key)
    if cached:
        log_proxy_request(client_ip, '/proxy/thumbnails/users', roblox_url, 'GET', 200, 0, cached=True)
        return jsonify(cached)

    data, status, response_time = proxy_request(roblox_url, params=params)
    log_proxy_request(client_ip, '/proxy/thumbnails/users', roblox_url, 'GET', status, response_time)

    if status == 200:
        set_cached_response(cache_key, data)

    return jsonify(data), status


@app.route('/proxy/thumbnails/games')
def proxy_game_thumbnails():
    """Proxy game thumbnails endpoint"""
    client_ip = request.remote_addr
    if not check_rate_limit(client_ip):
        return jsonify({'error': 'Rate limit exceeded'}), 429

    universe_ids = request.args.get('universeIds', '')
    size = request.args.get('size', '512x512')
    format_type = request.args.get('format', 'Png')

    roblox_url = "https://thumbnails.roblox.com/v1/games/icons"
    params = {'universeIds': universe_ids, 'size': size, 'format': format_type, 'isCircular': 'false'}

    cache_key = get_cache_key(roblox_url, params)
    cached = get_cached_response(cache_key)
    if cached:
        log_proxy_request(client_ip, '/proxy/thumbnails/games', roblox_url, 'GET', 200, 0, cached=True)
        return jsonify(cached)

    data, status, response_time = proxy_request(roblox_url, params=params)
    log_proxy_request(client_ip, '/proxy/thumbnails/games', roblox_url, 'GET', status, response_time)

    if status == 200:
        set_cached_response(cache_key, data)

    return jsonify(data), status


@app.route('/proxy/thumbnails/groups')
def proxy_group_thumbnails():
    """Proxy group thumbnails endpoint"""
    client_ip = request.remote_addr
    if not check_rate_limit(client_ip):
        return jsonify({'error': 'Rate limit exceeded'}), 429

    group_ids = request.args.get('groupIds', '')
    size = request.args.get('size', '150x150')
    format_type = request.args.get('format', 'Png')

    roblox_url = "https://thumbnails.roblox.com/v1/groups/icons"
    params = {'groupIds': group_ids, 'size': size, 'format': format_type, 'isCircular': 'false'}

    cache_key = get_cache_key(roblox_url, params)
    cached = get_cached_response(cache_key)
    if cached:
        log_proxy_request(client_ip, '/proxy/thumbnails/groups', roblox_url, 'GET', 200, 0, cached=True)
        return jsonify(cached)

    data, status, response_time = proxy_request(roblox_url, params=params)
    log_proxy_request(client_ip, '/proxy/thumbnails/groups', roblox_url, 'GET', status, response_time)

    if status == 200:
        set_cached_response(cache_key, data)

    return jsonify(data), status


# ===== ANALYTICS ENDPOINTS =====

@app.route('/proxy/analytics/stats')
def proxy_analytics_stats():
    """Get proxy analytics stats"""
    try:
        conn = sqlite3.connect(PROXY_DB_PATH)
        c = conn.cursor()
        c.execute('SELECT total_requests, cached_requests, failed_requests, total_bandwidth_kb FROM proxy_stats WHERE id = 1')
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
                'success_rate': round(success_rate, 1),
                'bandwidth_kb': row[3]
            })
        return jsonify({'error': 'No stats found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/proxy/analytics/recent')
def proxy_analytics_recent():
    """Get recent proxy requests"""
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
                'timestamp': row[0],
                'client_ip': row[1],
                'endpoint': row[2],
                'roblox_api': row[3],
                'method': row[4],
                'status_code': row[5],
                'response_time_ms': row[6],
                'cached': bool(row[7]),
                'error': row[8]
            })

        return jsonify({'requests': requests_list})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/proxy/analytics/top-endpoints')
def proxy_analytics_top_endpoints():
    """Get top requested endpoints"""
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
        return jsonify({'error': str(e)}), 500


@app.route('/proxy/analytics/top-clients')
def proxy_analytics_top_clients():
    """Get top clients by usage"""
    try:
        days = int(request.args.get('days', 7))
        limit = int(request.args.get('limit', 10))
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        conn = sqlite3.connect(PROXY_DB_PATH)
        c = conn.cursor()
        c.execute('''SELECT client_ip, COUNT(*) as count
                     FROM proxy_requests WHERE timestamp > ?
                     GROUP BY client_ip ORDER BY count DESC LIMIT ?''', (cutoff, limit))
        rows = c.fetchall()
        conn.close()

        clients = [{'ip': row[0], 'requests': row[1]} for row in rows]
        return jsonify({'clients': clients})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/proxy/analytics/errors')
def proxy_analytics_errors():
    """Get error breakdown"""
    try:
        days = int(request.args.get('days', 7))
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        conn = sqlite3.connect(PROXY_DB_PATH)
        c = conn.cursor()
        c.execute('''SELECT status_code, COUNT(*) as count
                     FROM proxy_requests WHERE timestamp > ? AND status_code >= 400
                     GROUP BY status_code ORDER BY count DESC''', (cutoff,))
        rows = c.fetchall()
        conn.close()

        errors = {str(row[0]): row[1] for row in rows}
        return jsonify({'errors_by_status': errors})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/proxy/health')
def proxy_health():
    """Proxy health check"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'cache_size': len(response_cache),
        'active_rate_limits': len(rate_limits)
    })


@app.route('/proxy/docs')
def proxy_docs():
    """API documentation"""
    return jsonify({
        'name': 'Roblox API Proxy',
        'version': '1.0.0',
        'description': 'Full proxy for Roblox APIs with caching, rate limiting, and analytics',
        'endpoints': {
            '/proxy/users/<user_id>': 'Get user info',
            '/proxy/users/username': 'POST - Resolve usernames to IDs',
            '/proxy/users/<user_id>/games': 'Get user games',
            '/proxy/users/<user_id>/groups': 'Get user groups',
            '/proxy/users/<user_id>/friends/count': 'Get friends count',
            '/proxy/users/<user_id>/followers/count': 'Get followers count',
            '/proxy/groups/<group_id>': 'Get group info',
            '/proxy/groups/<group_id>/games': 'Get group games',
            '/proxy/games?universeIds=<ids>': 'Get game info',
            '/proxy/games/votes?universeIds=<ids>': 'Get game votes',
            '/proxy/thumbnails/users?userIds=<ids>': 'Get user thumbnails',
            '/proxy/thumbnails/games?universeIds=<ids>': 'Get game thumbnails',
            '/proxy/thumbnails/groups?groupIds=<ids>': 'Get group thumbnails',
            '/proxy/analytics/stats': 'Get proxy stats',
            '/proxy/analytics/recent': 'Get recent requests',
            '/proxy/analytics/top-endpoints': 'Get top endpoints',
            '/proxy/analytics/top-clients': 'Get top clients',
            '/proxy/analytics/errors': 'Get error breakdown',
            '/proxy/health': 'Health check',
            '/proxy/docs': 'This documentation'
        },
        'rate_limits': {
            'requests_per_minute': RATE_LIMIT_MAX,
            'cache_ttl_seconds': CACHE_TTL
        }
    })


if __name__ == '__main__':
    print('\n' + '='*60)
    print('  Roblox API Proxy Server')
    print('='*60)
    print(f'\n  Running on http://127.0.0.1:8001\n')
    print('  Features:')
    print('  - Caching (60s TTL)')
    print('  - Rate Limiting (100 req/min)')
    print('  - Analytics Dashboard')
    print('  - All major Roblox APIs')
    print('\n' + '='*60 + '\n')

    from waitress import serve
    serve(app, host='127.0.0.1', port=8001)
