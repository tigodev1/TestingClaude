/**
 * Enhanced Analytics Functions
 */

// ===== HOURLY HEATMAP =====
async function loadHourlyHeatmap() {
    const container = document.getElementById('hourlyHeatmap');
    if (!container) return;

    try {
        const response = await fetch('/api/analytics/comprehensive');
        const data = await response.json();

        // Create 24-hour heatmap
        let html = '';
        const hourlyData = data.hourly_distribution || {};
        const maxOps = Math.max(...Object.values(hourlyData), 1);

        for (let hour = 0; hour < 24; hour++) {
            const ops = hourlyData[hour] || 0;
            const intensity = ops / maxOps;
            const color = getHeatmapColor(intensity);
            const formattedHour = hour === 0 ? '12 AM' : hour < 12 ? hour + ' AM' : hour === 12 ? '12 PM' : (hour - 12) + ' PM';

            html += `
                <div style="height: 40px; background: ${color}; border-radius: 4px; display: flex; align-items: center; justify-content: center; font-size: 10px; color: ${intensity > 0.5 ? 'white' : 'var(--text-secondary)'}; cursor: pointer;" title="${formattedHour}: ${ops} operations">
                    ${ops > 0 ? ops : ''}
                </div>
            `;
        }

        container.innerHTML = html;
    } catch (error) {
        console.error('Failed to load hourly heatmap:', error);
        container.innerHTML = '<div style="text-align: center; color: var(--text-secondary);">No data available</div>';
    }
}

function getHeatmapColor(intensity) {
    if (intensity === 0) return 'var(--bg-tertiary)';
    if (intensity < 0.25) return 'rgba(67, 233, 123, 0.3)';
    if (intensity < 0.5) return 'rgba(67, 233, 123, 0.5)';
    if (intensity < 0.75) return 'rgba(67, 233, 123, 0.7)';
    return 'rgba(67, 233, 123, 0.9)';
}

async function loadPerformanceInsights() {
    try {
        const response = await fetch('/api/analytics/comprehensive');
        const data = await response.json();

        // Peak hours
        const hourlyData = data.hourly_distribution || {};
        let peakHour = 0;
        let maxOps = 0;
        for (const [hour, ops] of Object.entries(hourlyData)) {
            if (ops > maxOps) {
                maxOps = ops;
                peakHour = parseInt(hour);
            }
        }
        const peakFormatted = peakHour === 0 ? '12 AM' : peakHour < 12 ? peakHour + ' AM' : peakHour === 12 ? '12 PM' : (peakHour - 12) + ' PM';
        document.getElementById('insightPeakHours').textContent = maxOps > 0 ? peakFormatted + ' with ' + maxOps + ' operations' : 'No data yet';

        // Top datastore
        const topStores = data.top_datastores || [];
        if (topStores.length > 0) {
            document.getElementById('insightTopStore').textContent = topStores[0].datastore + ' (' + topStores[0].count + ' ops)';
        } else {
            document.getElementById('insightTopStore').textContent = 'No data yet';
        }

        // Trend calculation
        const timeline = data.operations_timeline || [];
        if (timeline.length >= 2) {
            const recent = timeline.slice(-7).reduce((sum, d) => sum + d.count, 0);
            const older = timeline.slice(-14, -7).reduce((sum, d) => sum + d.count, 0);
            const change = older > 0 ? ((recent - older) / older * 100).toFixed(1) : 0;
            const trend = change > 0 ? '↑ ' + change + '% increase' : change < 0 ? '↓ ' + Math.abs(change) + '% decrease' : 'Stable';
            document.getElementById('insightTrend').textContent = trend + ' vs last week';
        } else {
            document.getElementById('insightTrend').textContent = 'Not enough data';
        }

        // Update additional stat cards
        if (document.getElementById('analyticsDeleteOps')) {
            const deleteOps = (data.operations_by_type || []).find(op => op.operation === 'delete');
            document.getElementById('analyticsDeleteOps').textContent = deleteOps ? deleteOps.count : '0';
        }
        if (document.getElementById('analyticsErrorCount')) {
            const totalErrors = (data.operations_by_type || []).reduce((sum, op) => sum + (op.count - op.successful), 0);
            document.getElementById('analyticsErrorCount').textContent = totalErrors;
        }

    } catch (error) {
        console.error('Failed to load performance insights:', error);
    }
}

// Override the original loadAnalyticsCharts to include new features
const originalLoadAnalyticsCharts = window.loadAnalyticsCharts;
if (originalLoadAnalyticsCharts) {
    window.loadAnalyticsCharts = async function() {
        await originalLoadAnalyticsCharts();
        await loadHourlyHeatmap();
        await loadPerformanceInsights();
    };
}

// Export new functions
window.loadHourlyHeatmap = loadHourlyHeatmap;
window.loadPerformanceInsights = loadPerformanceInsights;
window.getHeatmapColor = getHeatmapColor;
