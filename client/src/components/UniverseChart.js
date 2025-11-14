import React from 'react';
import { Doughnut } from 'react-chartjs-2';
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js';
import './Charts.css';

ChartJS.register(ArcElement, Tooltip, Legend);

function UniverseChart({ universeData }) {
  if (!universeData) return null;

  const enabledCount = [
    universeData.desktopEnabled,
    universeData.mobileEnabled,
    universeData.tabletEnabled,
    universeData.consoleEnabled,
    universeData.vrEnabled
  ].filter(Boolean).length;

  const data = {
    labels: ['Enabled', 'Disabled'],
    datasets: [
      {
        data: [enabledCount, 5 - enabledCount],
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
            size: 14
          }
        }
      },
      tooltip: {
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        titleColor: 'white',
        bodyColor: 'white',
        padding: 12
      }
    }
  };

  return (
    <div className="chart-container" style={{ maxWidth: '400px', margin: '0 auto' }}>
      <h4 style={{ color: 'white', textAlign: 'center', marginBottom: '20px' }}>
        Platform Distribution
      </h4>
      <Doughnut data={data} options={options} />
    </div>
  );
}

export default UniverseChart;
