import React from 'react';
import { Doughnut, Bar } from 'react-chartjs-2';
import { Chart as ChartJS, ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement } from 'chart.js';
import './Charts.css';

ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement);

function StatsChart({ gameStats }) {
  if (!gameStats) return null;

  const totalVotes = (gameStats.upVotes || 0) + (gameStats.downVotes || 0);

  const doughnutData = {
    labels: ['👍 Likes', '👎 Dislikes'],
    datasets: [
      {
        data: [gameStats.upVotes || 0, gameStats.downVotes || 0],
        backgroundColor: [
          'rgba(76, 175, 80, 0.8)',
          'rgba(244, 67, 54, 0.8)'
        ],
        borderColor: [
          'rgba(76, 175, 80, 1)',
          'rgba(244, 67, 54, 1)'
        ],
        borderWidth: 2
      }
    ]
  };

  const barData = {
    labels: ['Likes', 'Dislikes'],
    datasets: [
      {
        label: 'Vote Count',
        data: [gameStats.upVotes || 0, gameStats.downVotes || 0],
        backgroundColor: [
          'rgba(76, 175, 80, 0.8)',
          'rgba(244, 67, 54, 0.8)'
        ],
        borderColor: [
          'rgba(76, 175, 80, 1)',
          'rgba(244, 67, 54, 1)'
        ],
        borderWidth: 2,
        borderRadius: 10
      }
    ]
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom',
        labels: {
          color: 'rgba(255, 255, 255, 0.9)',
          padding: 20,
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
        callbacks: {
          label: function(context) {
            const label = context.label || '';
            const value = context.parsed || context.parsed.y || 0;
            const percentage = totalVotes > 0 ? ((value / totalVotes) * 100).toFixed(1) : 0;
            return `${label}: ${value.toLocaleString()} (${percentage}%)`;
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
        }
      },
      x: {
        ticks: {
          color: 'rgba(255, 255, 255, 0.7)',
          font: {
            size: 14,
            weight: 'bold'
          }
        },
        grid: {
          display: false
        }
      }
    }
  };

  const likePercentage = totalVotes > 0 ? ((gameStats.upVotes / totalVotes) * 100).toFixed(1) : 0;

  return (
    <div className="stats-chart-container">
      <div className="chart-info">
        <p>
          <strong>{likePercentage}%</strong> positive rating from {totalVotes.toLocaleString()} total votes
        </p>
      </div>
      <div className="chart-row">
        <div className="chart-box" style={{ height: '300px' }}>
          <h4 style={{ color: 'white', textAlign: 'center', marginBottom: '15px' }}>
            Distribution
          </h4>
          <Doughnut data={doughnutData} options={options} />
        </div>
        <div className="chart-box" style={{ height: '300px' }}>
          <h4 style={{ color: 'white', textAlign: 'center', marginBottom: '15px' }}>
            Comparison
          </h4>
          <Bar data={barData} options={options} />
        </div>
      </div>
    </div>
  );
}

export default React.memo(StatsChart);
