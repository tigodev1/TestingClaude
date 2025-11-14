import React from 'react';
import { Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js';
import './Charts.css';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

function PlatformChart({ universeData }) {
  if (!universeData) return null;

  const platforms = [
    { name: 'Desktop', enabled: universeData.desktopEnabled },
    { name: 'Mobile', enabled: universeData.mobileEnabled },
    { name: 'Tablet', enabled: universeData.tabletEnabled },
    { name: 'Console', enabled: universeData.consoleEnabled },
    { name: 'VR', enabled: universeData.vrEnabled }
  ];

  const data = {
    labels: platforms.map(p => p.name),
    datasets: [
      {
        label: 'Platform Support',
        data: platforms.map(p => p.enabled ? 1 : 0),
        backgroundColor: platforms.map(p =>
          p.enabled ? 'rgba(76, 175, 80, 0.8)' : 'rgba(244, 67, 54, 0.8)'
        ),
        borderColor: platforms.map(p =>
          p.enabled ? 'rgba(76, 175, 80, 1)' : 'rgba(244, 67, 54, 1)'
        ),
        borderWidth: 2,
        borderRadius: 10,
      }
    ]
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false
      },
      tooltip: {
        callbacks: {
          label: function(context) {
            return context.parsed.y === 1 ? 'Enabled' : 'Disabled';
          }
        },
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        titleColor: 'white',
        bodyColor: 'white',
        padding: 12,
        borderColor: 'rgba(255, 255, 255, 0.2)',
        borderWidth: 1
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        max: 1,
        ticks: {
          stepSize: 1,
          callback: function(value) {
            return value === 1 ? 'Enabled' : 'Disabled';
          },
          color: 'rgba(255, 255, 255, 0.7)'
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

  return (
    <div className="chart-container">
      <Bar data={data} options={options} />
    </div>
  );
}

export default PlatformChart;
