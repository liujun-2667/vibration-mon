<script>
  import { Line } from 'svelte-chartjs';
  import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    LogarithmicScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
    Filler,
    Annotation
  } from 'chart.js';
  import annotationPlugin from 'chartjs-plugin-annotation';

  ChartJS.register(
    CategoryScale,
    LinearScale,
    LogarithmicScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
    Filler,
    annotationPlugin
  );

  export let data = [];
  export let frequencies = [];
  export let title = '频谱图';
  export let unit = 'm/s²';
  export let color = '#a855f7';
  export let height = 350;
  export let showGrid = true;
  export let showLegend = false;
  export let yAxisType = 'linear';
  export let showPeaks = true;
  export let peakCount = 5;
  export let showCursor = true;
  export let cursorPosition = null;
  export let maxFrequency = null;

  let chartInstance = null;

  $: freqLabels = frequencies.length > 0
    ? frequencies.map(f => maxFrequency ? Math.min(f, maxFrequency).toFixed(1) : f.toFixed(1))
    : data.map((_, i) => (i * (maxFrequency || 1000) / data.length).toFixed(1));

  $: displayData = maxFrequency
    ? data.slice(0, Math.min(data.length, Math.floor(data.length * maxFrequency / (frequencies.length ? frequencies[frequencies.length - 1] : 1000))))
    : data;

  $: displayLabels = maxFrequency
    ? freqLabels.slice(0, displayData.length)
    : freqLabels;

  $: peaks = showPeaks ? findPeaks(displayData, peakCount) : [];

  $: peakAnnotations = peaks.reduce((acc, peak, idx) => {
    acc[`peakLine${idx}`] = {
      type: 'line',
      xMin: peak.index,
      xMax: peak.index,
      borderColor: '#ef4444',
      borderWidth: 1,
      borderDash: [4, 4],
      label: {
        display: true,
        content: `${displayLabels[peak.index]}Hz: ${peak.value.toFixed(4)}`,
        position: 'start',
        backgroundColor: 'rgba(239, 68, 68, 0.8)',
        color: '#fff',
        font: { size: 10 },
        padding: 4
      }
    };
    acc[`peakPoint${idx}`] = {
      type: 'point',
      xValue: peak.index,
      yValue: peak.value,
      backgroundColor: '#ef4444',
      borderColor: '#fff',
      borderWidth: 2,
      radius: 5
    };
    return acc;
  }, {});

  $: cursorAnnotation = showCursor && cursorPosition !== null
    ? {
        cursorLine: {
          type: 'line',
          xMin: cursorPosition,
          xMax: cursorPosition,
          borderColor: '#22d3ee',
          borderWidth: 2,
          label: {
            display: true,
            content: `${displayLabels[cursorPosition] || '0'}Hz`,
            position: 'end',
            backgroundColor: 'rgba(34, 211, 238, 0.9)',
            color: '#000',
            font: { size: 11, weight: 'bold' },
            padding: 6
          }
        }
      }
    : {};

  $: chartData = {
    labels: displayLabels,
    datasets: [
      {
        label: title,
        data: displayData,
        borderColor: color,
        backgroundColor: `${color}20`,
        borderWidth: 1.5,
        fill: true,
        tension: 0.1,
        pointRadius: 0,
        pointHoverRadius: 5,
        pointHoverBackgroundColor: color,
        pointHoverBorderColor: '#fff',
        pointHoverBorderWidth: 2
      }
    ]
  };

  $: options = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 0 },
    interaction: { mode: 'index', intersect: false },
    onHover: (event, elements) => {
      if (showCursor && elements.length > 0) {
        cursorPosition = elements[0].index;
      }
    },
    plugins: {
      legend: {
        display: showLegend,
        position: 'top',
        labels: { color: '#e4e4e7', font: { size: 12 } }
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
        borderColor: color,
        borderWidth: 1,
        padding: 10,
        callbacks: {
          title: (items) => `${items[0].label} Hz`,
          label: (context) => `${context.parsed.y.toFixed(4)} ${unit}`
        }
      },
      annotation: {
        annotations: { ...peakAnnotations, ...cursorAnnotation }
      }
    },
    scales: {
      x: {
        display: true,
        grid: { display: showGrid, color: 'rgba(255, 255, 255, 0.1)' },
        ticks: { color: '#9ca3af', maxTicksLimit: 12, font: { size: 11 } },
        title: {
          display: true,
          text: '频率 (Hz)',
          color: '#9ca3af',
          font: { size: 12 }
        }
      },
      y: {
        display: true,
        type: yAxisType === 'log' ? 'logarithmic' : 'linear',
        grid: { display: showGrid, color: 'rgba(255, 255, 255, 0.1)' },
        ticks: {
          color: '#9ca3af',
          font: { size: 11 },
          callback: (value) => {
            if (yAxisType === 'log') {
              return Number(value).toExponential(1);
            }
            return Number(value).toFixed(2);
          }
        },
        title: {
          display: true,
          text: `幅值 (${unit})`,
          color: '#9ca3af',
          font: { size: 12 }
        },
        min: yAxisType === 'log' ? 0.0001 : undefined
      }
    }
  };

  function findPeaks(arr, count) {
    const peaks = [];
    const threshold = Math.max(...arr) * 0.1;

    for (let i = 1; i < arr.length - 1; i++) {
      if (arr[i] > arr[i - 1] && arr[i] > arr[i + 1] && arr[i] > threshold) {
        peaks.push({ index: i, value: arr[i] });
      }
    }

    peaks.sort((a, b) => b.value - a.value);
    return peaks.slice(0, count);
  }

  function toggleYAxis() {
    yAxisType = yAxisType === 'linear' ? 'log' : 'linear';
  }

  function getChartRef(node) {
    if (node && node.chart) {
      chartInstance = node.chart;
    }
  }
</script>

<div class="frequency-chart">
  <div class="chart-toolbar">
    <button
      class="toolbar-btn {yAxisType === 'log' ? 'active' : ''}"
      on:click={toggleYAxis}
      title="切换纵轴坐标"
    >
      {yAxisType === 'log' ? '对数' : '线性'}
    </button>
    {#if peaks.length > 0}
      <div class="peak-info">
        <span class="peak-label">峰值:</span>
        {#each peaks as peak (peak.index)}
          <span class="peak-tag">
            {displayLabels[peak.index]}Hz
          </span>
        {/each}
      </div>
    {/if}
  </div>

  <div class="chart-container" style="height: {height - 40}px;">
    <Line use:chartRef data={chartData} {options} />
  </div>
</div>

<style>
  .frequency-chart {
    width: 100%;
    background: #1e1e2e;
    border-radius: 8px;
    padding: 8px;
    box-sizing: border-box;
  }

  .chart-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 4px 8px 8px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    margin-bottom: 8px;
  }

  .toolbar-btn {
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.2);
    color: #e4e4e7;
    padding: 4px 12px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 12px;
    transition: all 0.2s ease;
  }

  .toolbar-btn:hover {
    background: rgba(255, 255, 255, 0.15);
  }

  .toolbar-btn.active {
    background: rgba(168, 85, 247, 0.3);
    border-color: #a855f7;
    color: #a855f7;
  }

  .peak-info {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
  }

  .peak-label {
    font-size: 11px;
    color: #9ca3af;
  }

  .peak-tag {
    background: rgba(239, 68, 68, 0.2);
    color: #ef4444;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 500;
  }

  .chart-container {
    width: 100%;
  }
</style>
