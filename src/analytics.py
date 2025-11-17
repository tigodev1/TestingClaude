"""
Advanced Analytics and Reporting
"""

from datetime import datetime, timedelta, date
from collections import defaultdict
import json


class AnalyticsEngine:
    """Process and aggregate analytics data"""

    def __init__(self, db_session):
        self.db = db_session

    def record_operation(self, operation_data):
        """Record an operation for analytics"""
        from .models import Analytics

        today = date.today()
        current_hour = datetime.utcnow().hour

        # Get or create analytics record for this hour
        analytics = Analytics.query.filter_by(
            date=today,
            hour=current_hour,
            universe_id=operation_data.get('universe_id'),
            datastore_name=operation_data.get('datastore_name')
        ).first()

        if not analytics:
            analytics = Analytics(
                date=today,
                hour=current_hour,
                universe_id=operation_data.get('universe_id'),
                datastore_name=operation_data.get('datastore_name')
            )
            self.db.add(analytics)

        # Update metrics
        analytics.total_operations += 1

        op_type = operation_data.get('operation_type', '').upper()
        if 'GET' in op_type or 'LIST' in op_type or 'READ' in op_type:
            analytics.read_operations += 1
        elif 'SET' in op_type or 'CREATE' in op_type or 'UPDATE' in op_type or 'IMPORT' in op_type:
            analytics.write_operations += 1
        elif 'DELETE' in op_type:
            analytics.delete_operations += 1

        if operation_data.get('success', True):
            analytics.successful_operations += 1
        else:
            analytics.failed_operations += 1

        # Response time tracking
        response_time = operation_data.get('response_time_ms', 0)
        if response_time > 0:
            if analytics.avg_response_time_ms is None:
                analytics.avg_response_time_ms = response_time
                analytics.max_response_time_ms = response_time
                analytics.min_response_time_ms = response_time
            else:
                # Running average
                n = analytics.total_operations
                analytics.avg_response_time_ms = (
                    (analytics.avg_response_time_ms * (n - 1) + response_time) / n
                )
                analytics.max_response_time_ms = max(
                    analytics.max_response_time_ms or 0, response_time
                )
                analytics.min_response_time_ms = min(
                    analytics.min_response_time_ms or float('inf'), response_time
                )

        self.db.commit()

    def get_dashboard_stats(self, universe_id=None, days=7):
        """Get statistics for dashboard"""
        from .models import Analytics, OperationHistory

        start_date = date.today() - timedelta(days=days)

        query = Analytics.query.filter(Analytics.date >= start_date)
        if universe_id:
            query = query.filter_by(universe_id=universe_id)

        analytics = query.all()

        stats = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'read_operations': 0,
            'write_operations': 0,
            'delete_operations': 0,
            'avg_response_time': 0,
            'max_response_time': 0,
            'operations_by_day': defaultdict(int),
            'operations_by_hour': defaultdict(int),
            'operations_by_datastore': defaultdict(int),
            'error_rate': 0,
            'success_rate': 0
        }

        total_response_time = 0
        response_time_count = 0

        for a in analytics:
            stats['total_operations'] += a.total_operations
            stats['successful_operations'] += a.successful_operations
            stats['failed_operations'] += a.failed_operations
            stats['read_operations'] += a.read_operations
            stats['write_operations'] += a.write_operations
            stats['delete_operations'] += a.delete_operations

            if a.avg_response_time_ms:
                total_response_time += a.avg_response_time_ms * a.total_operations
                response_time_count += a.total_operations

            if a.max_response_time_ms:
                stats['max_response_time'] = max(
                    stats['max_response_time'], a.max_response_time_ms
                )

            # Group by day
            day_str = a.date.isoformat()
            stats['operations_by_day'][day_str] += a.total_operations

            # Group by hour
            if a.hour is not None:
                stats['operations_by_hour'][a.hour] += a.total_operations

            # Group by datastore
            if a.datastore_name:
                stats['operations_by_datastore'][a.datastore_name] += a.total_operations

        # Calculate averages
        if response_time_count > 0:
            stats['avg_response_time'] = round(total_response_time / response_time_count, 2)

        if stats['total_operations'] > 0:
            stats['success_rate'] = round(
                (stats['successful_operations'] / stats['total_operations']) * 100, 2
            )
            stats['error_rate'] = round(
                (stats['failed_operations'] / stats['total_operations']) * 100, 2
            )

        # Convert defaultdicts to regular dicts for JSON serialization
        stats['operations_by_day'] = dict(stats['operations_by_day'])
        stats['operations_by_hour'] = dict(stats['operations_by_hour'])
        stats['operations_by_datastore'] = dict(stats['operations_by_datastore'])

        return stats

    def get_time_series_data(self, universe_id=None, days=30, granularity='day'):
        """Get time series data for charts"""
        from .models import Analytics

        start_date = date.today() - timedelta(days=days)

        query = Analytics.query.filter(Analytics.date >= start_date)
        if universe_id:
            query = query.filter_by(universe_id=universe_id)

        analytics = query.order_by(Analytics.date, Analytics.hour).all()

        if granularity == 'hour':
            data = defaultdict(lambda: {
                'operations': 0,
                'success': 0,
                'failed': 0,
                'avg_time': 0
            })

            for a in analytics:
                key = f"{a.date.isoformat()}T{a.hour:02d}:00"
                data[key]['operations'] += a.total_operations
                data[key]['success'] += a.successful_operations
                data[key]['failed'] += a.failed_operations
                if a.avg_response_time_ms:
                    data[key]['avg_time'] = a.avg_response_time_ms

        else:  # day
            data = defaultdict(lambda: {
                'operations': 0,
                'success': 0,
                'failed': 0,
                'avg_time': 0
            })

            for a in analytics:
                key = a.date.isoformat()
                data[key]['operations'] += a.total_operations
                data[key]['success'] += a.successful_operations
                data[key]['failed'] += a.failed_operations

        return dict(data)

    def get_top_datastores(self, universe_id=None, days=7, limit=10):
        """Get top datastores by operation count"""
        from .models import Analytics

        start_date = date.today() - timedelta(days=days)

        query = Analytics.query.filter(Analytics.date >= start_date)
        if universe_id:
            query = query.filter_by(universe_id=universe_id)

        analytics = query.all()

        datastore_stats = defaultdict(lambda: {
            'operations': 0,
            'reads': 0,
            'writes': 0,
            'deletes': 0,
            'errors': 0
        })

        for a in analytics:
            if a.datastore_name:
                ds = datastore_stats[a.datastore_name]
                ds['operations'] += a.total_operations
                ds['reads'] += a.read_operations
                ds['writes'] += a.write_operations
                ds['deletes'] += a.delete_operations
                ds['errors'] += a.failed_operations

        # Sort by operations
        sorted_ds = sorted(
            datastore_stats.items(),
            key=lambda x: x[1]['operations'],
            reverse=True
        )[:limit]

        return [
            {'name': name, **stats}
            for name, stats in sorted_ds
        ]

    def get_error_analysis(self, days=7):
        """Analyze errors and common failure patterns"""
        from .models import OperationHistory

        start_time = datetime.utcnow() - timedelta(days=days)

        failed_ops = OperationHistory.query.filter(
            OperationHistory.timestamp >= start_time,
            OperationHistory.success == False
        ).all()

        error_patterns = defaultdict(int)
        error_by_operation = defaultdict(int)
        error_by_datastore = defaultdict(int)

        for op in failed_ops:
            if op.error_message:
                # Extract error pattern
                error_msg = op.error_message[:100]
                error_patterns[error_msg] += 1

            error_by_operation[op.operation_type] += 1

            if op.datastore_name:
                error_by_datastore[op.datastore_name] += 1

        return {
            'total_errors': len(failed_ops),
            'error_patterns': dict(sorted(
                error_patterns.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]),
            'errors_by_operation': dict(error_by_operation),
            'errors_by_datastore': dict(sorted(
                error_by_datastore.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10])
        }
