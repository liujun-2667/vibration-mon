<script>
  import { Line } from 'svelte-chartjs';
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

  export let data = [];
  export let labels = [];
  export let title = '时域波形';
  export let unit = 'm/s²';
  export let color = '#4facfe';
  export let showGrid = true;
  export let showLegend = false;
  export let height = 300;
  export let samplingRate = 1000;

  $: chartData = {
    labels: labels.length > 0 ? labels : generateTimeLabels(),
    datasets: [
      {
        label: title,
        data: data,
        borderColor: color,
        backgroundColor: `${color}20`,
        borderWidth: 1.5,
        fill: true,
        tension: 0.1,
        pointRadius: 0,
        pointHoverRadius: 4,
        pointHoverBackgroundColor: color
      }
    ]
  };

  $: options = {
    responsive: true,
    maintainAspectRatio: false,
    animation: {
      duration: 0
    },
    interaction: {
      mode: 'index',
      intersect: false
    },
    plugins: {
      legend: {
        display: showLegend,
        position: 'top',
        labels: {
          color: '#e4e4e7',
          font: { size: 12 }
        }
      },
      title: {
        display: !!title,
        text: title,
        color: '#e4e4e7',
        font: { size: 14, weight: '600' },
        padding: { top: 10, bottom: 10 }
      },
      tooltip: {
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        titleColor: '#fff',
        bodyColor: '#fff',
        borderColor: '#4facfe',
        borderWidth: 1,
        padding: 10,
        callbacks: {
          label: function(context) {
            return `${context.parsed.y.toFixed(4)} ${unit}`;
          }
        }
      }
    },
    scales: {
      x: {
        display: true,
        grid: {
          display: showGrid,
          color: 'rgba(255, 255, 255, 0.1)'
        },
        ticks: {
          color: '#9ca3af',
          maxTicksLimit: 10,
          font: { size: 11 }
        },
        title: {
          display: true,
          text: '时间 (s)',
          color: '#9ca3af',
          font: { size: 12 }
        }
      },
      y: {
        display: true,
        grid: {
          display: showGrid,
          color: 'rgba(255, 255, 255, 0.1)'
        },
        ticks: {
          color: '#9ca3af',
          font: { size: 11 }
        },
        title: {
          display: true,
          text: `振幅 (${unit})`,
          color: '#9ca3af',
          font: { size: 12 }
        }
      }
    }
  };

  function generateTimeLabels() {
    const count = data.length;
    const interval = 1 / samplingRate;
    return data.map((_, i) => (i * interval).toFixed(3));
  }
</script>

<div class="chart-container" style="height: {height}px;">
  <Line data={chartData} {options} />
</div>

<style>
  .chart-container {
    width: 100%;
    background: #1e1e2e;
    border-radius: 8px;
    padding: 8px;
    box-sizing: border-box;
  }
</style>
