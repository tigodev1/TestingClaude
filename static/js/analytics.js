/**
 * Advanced Analytics and Charting Functions
 */

// Chart instances
let operationsChart = null;
let operationTypesChart = null;
let topDatastoresChart = null;

// Chart color palette
const chartColors = {
    primary: '#00d4ff',
    secondary: '#7c3aed',
    success: '#10b981',
    warning: '#f59e0b',
    danger: '#ef4444',
    info: '#3b82f6',
    gradient1: 'rgba(0, 212, 255, 0.5)',
    gradient2: 'rgba(124, 58, 237, 0.5)'
};

async function loadAnalyticsDashboard() {
    try {
        const days = document.getElementById('chartTimeRange')?.value || 30;
        const response = await fetch(`/api/analytics/dashboard?days=${days}`);
        const data = await response.json();

        if (data.error) {
            console.error('Analytics error:', data.error);
            return;
        }

        // Update stat cards
        document.getElementById('analyticsSuccessRate').textContent = `${data.success_rate || 0}%`;
        document.getElementById('analyticsAvgResponse').textContent = `${Math.round(data.avg_response_time || 0)}ms`;
        document.getElementById('analyticsReadOps').textContent = formatNumber(data.read_operations || 0);
        document.getElementById('analyticsWriteOps').textContent = formatNumber(data.write_operations || 0);

    } catch (error) {
        console.error('Failed to load analytics:', error);
    }
}

async function loadAnalyticsCharts() {
    await loadAnalyticsDashboard();
    await Promise.all([
        loadOperationsChart(),
        loadOperationTypesChart(),
        loadTopDatastoresChart()
    ]);
}

async function loadOperationsChart() {
    const days = document.getElementById('chartTimeRange')?.value || 30;

    try {
        const response = await fetch(`/api/analytics/timeseries?days=${days}&granularity=day`);
        const data = await response.json();

        if (data.error) {
            console.error('Timeseries error:', data.error);
            return;
        }

        // Prepare data
        const labels = Object.keys(data).sort();
        const operationsData = labels.map(key => data[key].operations);
        const successData = labels.map(key => data[key].success);
        const failedData = labels.map(key => data[key].failed);

        // Format labels
        const formattedLabels = labels.map(d => new Date(d).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric'
        }));

        const ctx = document.getElementById('operationsChart').getContext('2d');

        // Destroy old chart
        if (operationsChart) {
            operationsChart.destroy();
        }

        operationsChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: formattedLabels,
                datasets: [
                    {
                        label: 'Total Operations',
                        data: operationsData,
                        borderColor: chartColors.primary,
                        backgroundColor: chartColors.gradient1,
                        fill: true,
                        tension: 0.4,
                        pointRadius: 4,
                        pointHoverRadius: 6
                    },
                    {
                        label: 'Successful',
                        data: successData,
                        borderColor: chartColors.success,
                        backgroundColor: 'transparent',
                        borderDash: [5, 5],
                        tension: 0.4,
                        pointRadius: 3
                    },
                    {
                        label: 'Failed',
                        data: failedData,
                        borderColor: chartColors.danger,
                        backgroundColor: 'transparent',
                        borderDash: [5, 5],
                        tension: 0.4,
                        pointRadius: 3
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            color: '#b0b0b0',
                            usePointStyle: true
                        }
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        backgroundColor: 'rgba(26, 26, 26, 0.9)',
                        titleColor: '#ffffff',
                        bodyColor: '#b0b0b0',
                        borderColor: '#3a3a3a',
                        borderWidth: 1
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(58, 58, 58, 0.5)'
                        },
                        ticks: {
                            color: '#b0b0b0'
                        }
                    },
                    x: {
                        grid: {
                            color: 'rgba(58, 58, 58, 0.3)'
                        },
                        ticks: {
                            color: '#b0b0b0',
                            maxRotation: 45
                        }
                    }
                },
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                }
            }
        });

    } catch (error) {
        console.error('Failed to load operations chart:', error);
    }
}

async function loadOperationTypesChart() {
    const days = document.getElementById('chartTimeRange')?.value || 30;

    try {
        const response = await fetch(`/api/analytics/dashboard?days=${days}`);
        const data = await response.json();

        if (data.error) return;

        const ctx = document.getElementById('operationTypesChart').getContext('2d');

        if (operationTypesChart) {
            operationTypesChart.destroy();
        }

        operationTypesChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Read', 'Write', 'Delete'],
                datasets: [{
                    data: [
                        data.read_operations || 0,
                        data.write_operations || 0,
                        data.delete_operations || 0
                    ],
                    backgroundColor: [
                        chartColors.primary,
                        chartColors.success,
                        chartColors.danger
                    ],
                    borderColor: '#1a1a1a',
                    borderWidth: 2,
                    hoverOffset: 10
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: '#b0b0b0',
                            usePointStyle: true,
                            padding: 20
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(26, 26, 26, 0.9)',
                        titleColor: '#ffffff',
                        bodyColor: '#b0b0b0'
                    }
                },
                cutout: '60%'
            }
        });

    } catch (error) {
        console.error('Failed to load operation types chart:', error);
    }
}

async function loadTopDatastoresChart() {
    const days = document.getElementById('chartTimeRange')?.value || 30;

    try {
        const response = await fetch(`/api/analytics/top-datastores?days=${days}&limit=5`);
        const data = await response.json();

        if (data.error) return;

        const datastores = data.datastores || [];
        const labels = datastores.map(d => d.name || 'Unknown');
        const values = datastores.map(d => d.operations);

        const ctx = document.getElementById('topDatastoresChart').getContext('2d');

        if (topDatastoresChart) {
            topDatastoresChart.destroy();
        }

        topDatastoresChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Operations',
                    data: values,
                    backgroundColor: [
                        chartColors.primary,
                        chartColors.secondary,
                        chartColors.success,
                        chartColors.warning,
                        chartColors.info
                    ],
                    borderRadius: 8,
                    borderSkipped: false
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'rgba(26, 26, 26, 0.9)',
                        titleColor: '#ffffff',
                        bodyColor: '#b0b0b0'
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(58, 58, 58, 0.3)'
                        },
                        ticks: {
                            color: '#b0b0b0'
                        }
                    },
                    y: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            color: '#b0b0b0'
                        }
                    }
                }
            }
        });

    } catch (error) {
        console.error('Failed to load top datastores chart:', error);
    }
}

async function loadErrorAnalysis() {
    try {
        const response = await fetch('/api/analytics/errors?days=7');
        const data = await response.json();

        const container = document.getElementById('errorAnalysis');

        if (data.total_errors === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-check-circle" style="color: var(--success);"></i>
                    <p>No errors in the last 7 days!</p>
                </div>
            `;
            return;
        }

        let html = `
            <div style="margin-bottom: 16px;">
                <strong>Total Errors:</strong> <span class="badge badge-danger">${data.total_errors}</span>
            </div>
        `;

        // Error patterns
        if (Object.keys(data.error_patterns).length > 0) {
            html += `
                <h4 style="margin-bottom: 12px;">Common Error Patterns</h4>
                <div class="table-container" style="margin-bottom: 16px;">
                    <table>
                        <thead>
                            <tr>
                                <th>Error Message</th>
                                <th>Count</th>
                            </tr>
                        </thead>
                        <tbody>
            `;

            for (const [error, count] of Object.entries(data.error_patterns)) {
                html += `
                    <tr>
                        <td><small>${escapeHtml(error)}</small></td>
                        <td><span class="badge badge-danger">${count}</span></td>
                    </tr>
                `;
            }

            html += `
                        </tbody>
                    </table>
                </div>
            `;
        }

        // Errors by operation
        if (Object.keys(data.errors_by_operation).length > 0) {
            html += `
                <h4 style="margin-bottom: 12px;">Errors by Operation Type</h4>
                <div style="display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 16px;">
            `;

            for (const [op, count] of Object.entries(data.errors_by_operation)) {
                html += `
                    <div class="stat-card" style="flex: 1; min-width: 150px;">
                        <div class="stat-value" style="font-size: 24px;">${count}</div>
                        <div class="stat-label">${op}</div>
                    </div>
                `;
            }

            html += `</div>`;
        }

        container.innerHTML = html;

    } catch (error) {
        console.error('Failed to load error analysis:', error);
    }
}

function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
}

// Export functions
window.loadAnalyticsDashboard = loadAnalyticsDashboard;
window.loadAnalyticsCharts = loadAnalyticsCharts;
window.loadErrorAnalysis = loadErrorAnalysis;
