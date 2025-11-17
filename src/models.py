"""
Advanced Database Models for Production
Using SQLAlchemy ORM with MySQL support
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Index

db = SQLAlchemy()


class User(db.Model):
    """User accounts for multi-user support"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)

    # Relationships
    api_configs = db.relationship('APIConfig', backref='user', lazy='dynamic')
    operations = db.relationship('OperationHistory', backref='user', lazy='dynamic')

    def __repr__(self):
        return f'<User {self.username}>'


class APIConfig(db.Model):
    """Encrypted API configurations per user"""
    __tablename__ = 'api_configs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    universe_id = db.Column(db.String(50), nullable=False)
    api_key_encrypted = db.Column(db.Text, nullable=False)  # Encrypted storage
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)

    # Statistics
    total_requests = db.Column(db.Integer, default=0)
    successful_requests = db.Column(db.Integer, default=0)
    failed_requests = db.Column(db.Integer, default=0)

    __table_args__ = (
        Index('idx_user_universe', 'user_id', 'universe_id'),
    )


class OperationHistory(db.Model):
    """Comprehensive operation audit log"""
    __tablename__ = 'operation_history'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    api_config_id = db.Column(db.Integer, db.ForeignKey('api_configs.id'), nullable=True)

    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    operation_type = db.Column(db.String(50), nullable=False, index=True)
    datastore_name = db.Column(db.String(100), index=True)
    key_name = db.Column(db.String(255))
    scope = db.Column(db.String(50), default='global')

    request_data = db.Column(db.Text)  # JSON of request
    response_data = db.Column(db.Text)  # JSON of response

    success = db.Column(db.Boolean, default=True)
    error_message = db.Column(db.Text)
    response_time_ms = db.Column(db.Float)

    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))

    __table_args__ = (
        Index('idx_timestamp_operation', 'timestamp', 'operation_type'),
        Index('idx_datastore_key', 'datastore_name', 'key_name'),
    )


class DataStoreCache(db.Model):
    """Cache for datastore metadata and frequently accessed data"""
    __tablename__ = 'datastore_cache'

    id = db.Column(db.Integer, primary_key=True)
    universe_id = db.Column(db.String(50), nullable=False)
    datastore_name = db.Column(db.String(100), nullable=False)

    # Metadata
    entry_count = db.Column(db.Integer, default=0)
    last_modified = db.Column(db.DateTime)
    created_time = db.Column(db.String(100))

    # Cache info
    cached_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)

    __table_args__ = (
        Index('idx_universe_datastore', 'universe_id', 'datastore_name', unique=True),
    )


class EntrySnapshot(db.Model):
    """Snapshots of entry values for comparison and recovery"""
    __tablename__ = 'entry_snapshots'

    id = db.Column(db.Integer, primary_key=True)
    universe_id = db.Column(db.String(50), nullable=False)
    datastore_name = db.Column(db.String(100), nullable=False)
    key_name = db.Column(db.String(255), nullable=False)
    scope = db.Column(db.String(50), default='global')

    value_json = db.Column(db.Text)  # JSON stringified value
    value_hash = db.Column(db.String(64))  # SHA256 hash for change detection
    version_id = db.Column(db.String(100))

    user_ids = db.Column(db.Text)  # JSON array
    attributes = db.Column(db.Text)  # JSON object

    snapshot_at = db.Column(db.DateTime, default=datetime.utcnow)
    snapshot_type = db.Column(db.String(20))  # 'auto', 'manual', 'backup'

    __table_args__ = (
        Index('idx_snapshot_lookup', 'universe_id', 'datastore_name', 'key_name', 'scope'),
    )


class Backup(db.Model):
    """Backup history with metadata"""
    __tablename__ = 'backups'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    universe_id = db.Column(db.String(50), nullable=False)
    datastore_name = db.Column(db.String(100), nullable=False)
    scope = db.Column(db.String(50), default='global')

    backup_file = db.Column(db.String(255), nullable=False)
    file_size_bytes = db.Column(db.Integer)
    entry_count = db.Column(db.Integer)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)  # Optional auto-cleanup

    compression = db.Column(db.String(20))  # 'none', 'gzip', 'zstd'
    checksum = db.Column(db.String(64))  # SHA256 of file

    notes = db.Column(db.Text)
    tags = db.Column(db.String(255))  # Comma-separated tags


class Bookmark(db.Model):
    """Bookmarked keys for quick access"""
    __tablename__ = 'bookmarks'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    universe_id = db.Column(db.String(50), nullable=False)
    datastore_name = db.Column(db.String(100), nullable=False)
    key_name = db.Column(db.String(255), nullable=False)
    scope = db.Column(db.String(50), default='global')

    nickname = db.Column(db.String(100))
    notes = db.Column(db.Text)
    color = db.Column(db.String(20))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_accessed = db.Column(db.DateTime)
    access_count = db.Column(db.Integer, default=0)

    __table_args__ = (
        Index('idx_bookmark_lookup', 'user_id', 'universe_id', 'datastore_name'),
    )


class ScheduledTask(db.Model):
    """Scheduled tasks for automation"""
    __tablename__ = 'scheduled_tasks'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    task_type = db.Column(db.String(50), nullable=False)  # 'backup', 'cleanup', 'sync'
    task_config = db.Column(db.Text)  # JSON configuration

    schedule = db.Column(db.String(100))  # Cron expression
    is_active = db.Column(db.Boolean, default=True)

    last_run = db.Column(db.DateTime)
    next_run = db.Column(db.DateTime)
    last_status = db.Column(db.String(20))
    last_error = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Analytics(db.Model):
    """Aggregated analytics data"""
    __tablename__ = 'analytics'

    id = db.Column(db.Integer, primary_key=True)

    date = db.Column(db.Date, nullable=False, index=True)
    hour = db.Column(db.Integer)  # 0-23, null for daily aggregates

    universe_id = db.Column(db.String(50))
    datastore_name = db.Column(db.String(100))

    # Metrics
    total_operations = db.Column(db.Integer, default=0)
    read_operations = db.Column(db.Integer, default=0)
    write_operations = db.Column(db.Integer, default=0)
    delete_operations = db.Column(db.Integer, default=0)

    successful_operations = db.Column(db.Integer, default=0)
    failed_operations = db.Column(db.Integer, default=0)

    avg_response_time_ms = db.Column(db.Float)
    max_response_time_ms = db.Column(db.Float)
    min_response_time_ms = db.Column(db.Float)

    total_data_read_bytes = db.Column(db.BigInteger, default=0)
    total_data_written_bytes = db.Column(db.BigInteger, default=0)

    __table_args__ = (
        Index('idx_analytics_date', 'date', 'universe_id', 'datastore_name'),
    )
