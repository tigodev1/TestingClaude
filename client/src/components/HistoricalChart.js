import React, { useState } from 'react';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';
import './Charts.css';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

function HistoricalChart({ data }) {
  const [metric, setMetric] = useState('snapshots');

  if (!data || data.length === 0) {
    return (
      <div className="no-data">
        <p>No historical data available yet. Data will accumulate over time.</p>
      </div>
    );
  }

  const labels = data.map(item => {
    const date = new Date(item.timestamp);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
  });

  const chartData = {
    labels,
    datasets: [
      {
        label: 'Data Snapshots Over Time',
        data: data.map((_, index) => index + 1),
        borderColor: 'rgba(75, 192, 192, 1)',
        backgroundColor: 'rgba(75, 192, 192, 0.2)',
        fill: true,
        tension: 0.4,
        pointRadius: 5,
        pointHoverRadius: 7,
        pointBackgroundColor: 'rgba(75, 192, 192, 1)',
        pointBorderColor: '#fff',
        pointBorderWidth: 2
      }
    ]
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: true,
        labels: {
          color: 'rgba(255, 255, 255, 0.9)',
          font: {
            size: 14,
            weight: 'bold'
          }
        }
      },
      tooltip: {
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        titleColor: 'white',
        bodyColor: 'white',
        padding: 12,
        borderColor: 'rgba(255, 255, 255, 0.2)',
        borderWidth: 1,
        callbacks: {
          afterBody: function(context) {
            const index = context[0].dataIndex;
            const item = data[index];
            return [
              '',
              `Game: ${item.display_name || 'N/A'}`,
              `Voice Chat: ${item.voice_chat_enabled ? 'On' : 'Off'}`,
              `Platforms: ${[
                item.desktop_enabled && 'Desktop',
                item.mobile_enabled && 'Mobile',
                item.tablet_enabled && 'Tablet',
                item.console_enabled && 'Console',
                item.vr_enabled && 'VR'
              ].filter(Boolean).join(', ')}`
            ];
          }
        }
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: {
          color: 'rgba(255, 255, 255, 0.7)',
          font: {
            size: 12
          }
        },
        grid: {
          color: 'rgba(255, 255, 255, 0.1)'
        },
        title: {
          display: true,
          text: 'Number of Snapshots',
          color: 'rgba(255, 255, 255, 0.9)',
          font: {
            size: 14,
            weight: 'bold'
          }
        }
      },
      x: {
        ticks: {
          color: 'rgba(255, 255, 255, 0.7)',
          maxRotation: 45,
          minRotation: 45,
          font: {
            size: 10
          }
        },
        grid: {
          color: 'rgba(255, 255, 255, 0.05)'
        }
      }
    }
  };

  return (
    <div>
      <div className="chart-info">
        <p>Tracking {data.length} data points over time. The system automatically collects snapshots every hour.</p>
      </div>
      <div className="chart-container" style={{ height: '400px' }}>
        <Line data={chartData} options={options} />
      </div>
    </div>
  );
}

export default HistoricalChart;
