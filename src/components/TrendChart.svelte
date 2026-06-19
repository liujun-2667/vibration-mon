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
  import { format } from 'date-fns';
  import { zhCN } from 'date-fns/locale';

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

  export let datasets = [];
  export let timestamps = [];
  export let title = '趋势分析';
  export let yAxisLabel = '数值';
  export let unit = '';
  export let height = 300;
  export let showGrid = true;
  export let showLegend = true;
  export let fillArea = true;
  export let smooth = true;
  export let warningThreshold = null;
  export let dangerThreshold = null;

  const defaultColors = [
    { border: '#4facfe', bg: 'rgba(79, 172, 254, 0.15)' },
    { border: '#a855f7', bg: 'rgba(168, 85, 247, 0.15)' },
    { border: '#22c55e', bg: 'rgba(34, 197, 94, 0.15)' },
    { border: '#f59e0b', bg: 'rgba(245, 158, 11, 0.15)' },
    { border: '#ef4444', bg: 'rgba(239, 68, 68, 0.15)' },
    { border: '#06b6d4', bg: 'rgba(6, 182, 212, 0.15)' }
  ];

  $: formattedLabels = timestamps.map(ts => {
    if (typeof ts === 'number') {
      return format(ts, 'MM-dd HH:mm', { locale: zhCN });
    }
    return ts;
  });

  $: chartDatasets = datasets.map((ds, idx) => {
    const colors = ds.colors || defaultColors[idx % defaultColors.length];
    return {
      label: ds.label,
      data: ds.data,
      borderColor: colors.border,
      backgroundColor: fillArea ? colors.bg : 'transparent',
      borderWidth: 2,
      fill: fillArea,
      tension: smooth ? 0.3 : 0,
      pointRadius: 0,
      pointHoverRadius: 6,
      pointHoverBackgroundColor: colors.border,
      pointHoverBorderColor: '#fff',
      pointHoverBorderWidth: 2,
      borderDash: ds.dashed ? [5, 5] : []
    };
  });

  $: thresholdAnnotations = {};

  $: if (warningThreshold !== null) {
    thresholdAnnotations.warningLine = {
      type: 'line',
      yMin: warningThreshold,
      yMax: warningThreshold,
      borderColor: '#eab308',
      borderWidth: 2,
      borderDash: [6, 6],
      label: {
        display: true,
        content: `警告阈值: ${warningThreshold}${unit}`,
        position: 'start',
        backgroundColor: 'rgba(234, 179, 8, 0.8)',
        color: '#000',
        font: { size: 11, weight: '500' },
        padding: 4
      }
    };
  }

  $: if (dangerThreshold !== null) {
    thresholdAnnotations.dangerLine = {
      type: 'line',
      yMin: dangerThreshold,
      yMax: dangerThreshold,
      borderColor: '#ef4444',
      borderWidth: 2,
      borderDash: [6, 6],
      label: {
        display: true,
        content: `危险阈值: ${dangerThreshold}${unit}`,
        position: 'start',
        backgroundColor: 'rgba(239, 68, 68, 0.8)',
        color: '#fff',
        font: { size: 11, weight: '500' },
        padding: 4
      }
    };
  }

  $: chartData = {
    labels: formattedLabels,
    datasets: chartDatasets
  };

  $: options = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 300 },
    interaction: { mode: 'index', intersect: false },
    plugins: {
      legend: {
        display: showLegend,
        position: 'top',
        labels: {
          color: '#e4e4e7',
          font: { size: 12 },
          usePointStyle: true,
          pointStyle: 'circle',
          padding: 15
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
        backgroundColor: 'rgba(0, 0, 0, 0.85)',
        titleColor: '#fff',
        bodyColor: '#fff',
        borderColor: '#4facfe',
        borderWidth: 1,
        padding: 12,
        callbacks: {
          label: function(context) {
            let label = context.dataset.label || '';
            if (label) label += ': ';
            label += context.parsed.y !== null
              ? context.parsed.y.toFixed(4) + (unit ? ` ${unit}` : '')
              : '';
            return label;
          }
        }
      },
      annotation: {
        annotations: thresholdAnnotations
      }
    },
    scales: {
      x: {
        display: true,
        grid: {
          display: showGrid,
          color: 'rgba(255, 255, 255, 0.05)'
        },
        ticks: {
          color: '#9ca3af',
          maxTicksLimit: 8,
          font: { size: 11 },
          maxRotation: 45,
          minRotation: 45
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
          text: yAxisLabel + (unit ? ` (${unit})` : ''),
          color: '#9ca3af',
          font: { size: 12 }
        }
      }
    }
  };
</script>

<div class="trend-chart" style="height: {height}px;">
  <Line data={chartData} {options} />
</div>

<style>
  .trend-chart {
    width: 100%;
    background: #1e1e2e;
    border-radius: 8px;
    padding: 8px;
    box-sizing: border-box;
  }
</style>
