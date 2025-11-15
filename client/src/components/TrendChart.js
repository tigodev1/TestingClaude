import React from 'react';
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

function TrendChart({ data }) {
  if (!data || data.length === 0) {
    return (
      <div className="no-data">
        <p>No trend data available yet. Data will accumulate over time.</p>
      </div>
    );
  }

  const labels = data.map(item => {
    const date = new Date(item.timestamp);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  });

  const chartData = {
    labels,
    datasets: [
      {
        label: 'Players Online',
        data: data.map(item => item.playing || 0),
        borderColor: 'rgba(76, 175, 80, 1)',
        backgroundColor: 'rgba(76, 175, 80, 0.2)',
        fill: true,
        tension: 0.4,
        pointRadius: 4,
        pointHoverRadius: 6,
        pointBackgroundColor: 'rgba(76, 175, 80, 1)',
        pointBorderColor: '#fff',
        pointBorderWidth: 2
      },
      {
        label: 'Favorites',
        data: data.map(item => item.favorites || 0),
        borderColor: 'rgba(255, 152, 0, 1)',
        backgroundColor: 'rgba(255, 152, 0, 0.2)',
        fill: true,
        tension: 0.4,
        pointRadius: 4,
        pointHoverRadius: 6,
        pointBackgroundColor: 'rgba(255, 152, 0, 1)',
        pointBorderColor: '#fff',
        pointBorderWidth: 2
      },
      {
        label: 'Likes',
        data: data.map(item => item.up_votes || 0),
        borderColor: 'rgba(33, 150, 243, 1)',
        backgroundColor: 'rgba(33, 150, 243, 0.2)',
        fill: true,
        tension: 0.4,
        pointRadius: 4,
        pointHoverRadius: 6,
        pointBackgroundColor: 'rgba(33, 150, 243, 1)',
        pointBorderColor: '#fff',
        pointBorderWidth: 2
      }
    ]
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index',
      intersect: false,
    },
    plugins: {
      legend: {
        display: true,
        labels: {
          color: 'rgba(255, 255, 255, 0.9)',
          font: {
            size: 14,
            weight: 'bold'
          },
          usePointStyle: true,
          padding: 20
        }
      },
      tooltip: {
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        titleColor: 'white',
        bodyColor: 'white',
        padding: 12,
        borderColor: 'rgba(255, 255, 255, 0.2)',
        borderWidth: 1,
        displayColors: true,
        callbacks: {
          label: function(context) {
            let label = context.dataset.label || '';
            if (label) {
              label += ': ';
            }
            label += context.parsed.y.toLocaleString();
            return label;
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
          },
          callback: function(value) {
            return value.toLocaleString();
          }
        },
        grid: {
          color: 'rgba(255, 255, 255, 0.1)'
        },
        title: {
          display: true,
          text: 'Count',
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
        <p>Tracking player activity, favorites, and likes over time. Updates every 5 minutes.</p>
      </div>
      <div className="chart-container" style={{ height: '400px' }}>
        <Line data={chartData} options={options} />
      </div>
    </div>
  );
}

export default React.memo(TrendChart);
