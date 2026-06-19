<script>
  import { onMount, onDestroy } from 'svelte';
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
    Filler,
  } from 'chart.js';
  import annotationPlugin from 'chartjs-plugin-annotation';
  import { analysisApi } from '../api.js';

  ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
    Filler,
    annotationPlugin
  );

  export let deviceId = null;
  export let deviceName = '';

  let collapsed = false;
  let loading = false;
  let errorMsg = '';
  let labels = [];
  let values = [];
  let stats = { min: null, max: null, avg: null };

  function pad(n) {
    return String(n).padStart(2, '0');
  }

  function aggregateByHour(timestamps, rawValues) {
    const buckets = new Map();
    for (let i = 0; i < timestamps.length; i++) {
      const d = new Date(timestamps[i]);
      if (isNaN(d.getTime())) continue;
      const key = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}`;
      if (!buckets.has(key)) buckets.set(key, []);
      buckets.get(key).push(rawValues[i]);
    }
    const sortedKeys = [...buckets.keys()].sort();
    const outLabels = [];
    const outValues = [];
    for (const key of sortedKeys) {
      const arr = buckets.get(key);
      const avg = arr.reduce((a, b) => a + b, 0) / arr.length;
      outLabels.push(key.slice(5) + ':00');
      outValues.push(Number(avg.toFixed(1)));
    }
    return { labels: outLabels, values: outValues };
  }

  function buildDangerBoxes(vals) {
    const boxes = {};
    let start = -1;
    for (let i = 0; i <= vals.length; i++) {
      const below = i < vals.length && vals[i] < 60;
      if (below && start < 0) start = i;
      if (!below && start >= 0) {
        boxes[`danger${i}`] = {
          type: 'box',
          xMin: start - 0.5,
          xMax: i - 1 + 0.5,
          yMin: 0,
          yMax: 60,
          backgroundColor: 'rgba(239, 68, 68, 0.15)',
          borderColor: 'transparent',
          drawTime: 'beforeDatasetsDraw',
        };
        start = -1;
      }
    }
    return boxes;
  }

  async function loadData() {
    if (deviceId == null) return;
    loading = true;
    errorMsg = '';
    try {
      const resp = await analysisApi.getAnalysisTrend(deviceId, {
        hours: 24,
        metric: 'health_index',
      });
      if (resp && resp.success && resp.data) {
        const agg = aggregateByHour(resp.data.timestamps || [], resp.data.values || []);
        labels = agg.labels;
        values = agg.values;
        if (values.length > 0) {
          stats = {
            min: Math.min(...values),
            max: Math.max(...values),
            avg: Number((values.reduce((a, b) => a + b, 0) / values.length).toFixed(1)),
          };
        } else {
          stats = { min: null, max: null, avg: null };
        }
      } else {
        labels = [];
        values = [];
      }
    } catch (e) {
      errorMsg = e.message || '加载趋势失败';
      labels = [];
      values = [];
    } finally {
      loading = false;
    }
  }

  $: chartData = {
    labels,
    datasets: [
      {
        label: '健康指数',
        data: values,
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59, 130, 246, 0.12)',
        borderWidth: 2,
        fill: false,
        tension: 0.3,
        pointRadius: 2,
        pointHoverRadius: 5,
        pointBackgroundColor: '#3b82f6',
      },
    ],
  };

  $: dangerBoxes = buildDangerBoxes(values);

  $: chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 300 },
    interaction: { mode: 'index', intersect: false },
    plugins: {
      legend: { display: false },
      title: { display: false },
      tooltip: {
        backgroundColor: 'rgba(0,0,0,0.8)',
        callbacks: {
          label: (ctx) => `健康指数 ${ctx.parsed.y.toFixed(1)}`,
        },
      },
      annotation: {
        annotations: {
          thresholdLine: {
            type: 'line',
            yMin: 60,
            yMax: 60,
            borderColor: 'rgba(239, 68, 68, 0.7)',
            borderWidth: 1.5,
            borderDash: [6, 4],
            label: {
              display: true,
              content: '阈值 60',
              position: 'end',
              color: 'rgba(239, 68, 68, 0.9)',
              font: { size: 10 },
              backgroundColor: 'transparent',
            },
          },
          ...dangerBoxes,
        },
      },
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: { color: '#64748b', font: { size: 10 }, maxRotation: 60, minRotation: 45 },
      },
      y: {
        min: 0,
        max: 100,
        grid: { color: 'rgba(148, 163, 184, 0.15)' },
        ticks: { color: '#64748b', font: { size: 10 }, stepSize: 20 },
        title: { display: true, text: '健康指数', color: '#64748b', font: { size: 11 } },
      },
    },
  };

  let fetchToken = 0;
  $: if (deviceId != null) {
    const token = ++fetchToken;
    fetchToken = token;
    loadData().then(() => {
      if (token !== fetchToken) return;
    });
  }
</script>

<aside class="trend-sidebar" class:collapsed>
  <div class="sidebar-header">
    {#if !collapsed}
      <div class="header-title">
        <span class="header-icon">📈</span>
        <span>健康趋势</span>
        {#if deviceName}<span class="header-device">· {deviceName}</span>{/if}
      </div>
    {:else}
      <span class="header-icon">📈</span>
    {/if}
    <button class="collapse-btn" on:click={() => (collapsed = !collapsed)} title={collapsed ? '展开' : '收起'}>
      {collapsed ? '⯈' : '⯆'}
    </button>
  </div>

  {#if !collapsed}
    <div class="sidebar-body">
      <div class="stat-row">
        <div class="stat">
          <span class="stat-label">最低</span>
          <span class="stat-value" class:danger={stats.min != null && stats.min < 60}>
            {stats.min != null ? stats.min.toFixed(1) : '--'}
          </span>
        </div>
        <div class="stat">
          <span class="stat-label">平均</span>
          <span class="stat-value" class:danger={stats.avg != null && stats.avg < 60}>
            {stats.avg != null ? stats.avg.toFixed(1) : '--'}
          </span>
        </div>
        <div class="stat">
          <span class="stat-label">最高</span>
          <span class="stat-value">{stats.max != null ? stats.max.toFixed(1) : '--'}</span>
        </div>
      </div>

      <div class="chart-wrap">
        {#if loading}
          <div class="state-text">加载中…</div>
        {:else if errorMsg}
          <div class="state-text error">{errorMsg}</div>
        {:else if values.length === 0}
          <div class="state-text">暂无趋势数据</div>
        {:else}
          <Line data={chartData} options={chartOptions} />
        {/if}
      </div>

      <div class="legend-row">
        <span class="legend-item"><span class="legend-swatch danger"></span>健康指数 &lt; 60 区间</span>
        <span class="legend-hint">近24小时·按小时聚合</span>
      </div>
    </div>
  {/if}
</aside>

<style>
  .trend-sidebar {
    width: 360px;
    flex-shrink: 0;
    background: var(--color-white);
    border-left: var(--border-width) solid var(--color-gray-200);
    display: flex;
    flex-direction: column;
    transition: width var(--transition-slow);
    overflow: hidden;
  }

  .trend-sidebar.collapsed {
    width: 48px;
  }

  .sidebar-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--spacing-3) var(--spacing-4);
    border-bottom: var(--border-width) solid var(--color-gray-100);
  }

  .header-title {
    display: flex;
    align-items: center;
    gap: var(--spacing-2);
    font-size: var(--font-size-base);
    font-weight: 600;
    color: var(--color-gray-800);
  }

  .header-device {
    color: var(--color-gray-500);
    font-weight: 500;
  }

  .header-icon {
    font-size: var(--font-size-lg);
  }

  .collapse-btn {
    background: transparent;
    border: none;
    color: var(--color-gray-500);
    cursor: pointer;
    font-size: var(--font-size-sm);
    padding: var(--spacing-1) var(--spacing-2);
    border-radius: var(--radius-sm);
  }

  .collapse-btn:hover {
    background: var(--color-gray-100);
    color: var(--color-gray-700);
  }

  .sidebar-body {
    flex: 1;
    display: flex;
    flex-direction: column;
    padding: var(--spacing-3) var(--spacing-4);
    gap: var(--spacing-3);
    overflow: hidden;
  }

  .stat-row {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: var(--spacing-2);
  }

  .stat {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: var(--spacing-2);
    background: var(--color-gray-50);
    border-radius: var(--radius-md);
  }

  .stat-label {
    font-size: var(--font-size-xs);
    color: var(--color-gray-500);
  }

  .stat-value {
    font-size: var(--font-size-xl);
    font-weight: 700;
    color: var(--color-gray-900);
  }

  .stat-value.danger {
    color: var(--color-danger);
  }

  .chart-wrap {
    flex: 1;
    min-height: 280px;
    position: relative;
  }

  .state-text {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--color-gray-400);
    font-size: var(--font-size-sm);
  }

  .state-text.error {
    color: var(--color-danger);
  }

  .legend-row {
    display: flex;
    flex-direction: column;
    gap: 2px;
    font-size: var(--font-size-xs);
    color: var(--color-gray-500);
  }

  .legend-item {
    display: flex;
    align-items: center;
    gap: var(--spacing-2);
  }

  .legend-swatch {
    width: 14px;
    height: 10px;
    border-radius: 2px;
    display: inline-block;
  }

  .legend-swatch.danger {
    background: rgba(239, 68, 68, 0.35);
    border: 1px solid var(--color-danger);
  }

  .legend-hint {
    color: var(--color-gray-400);
  }
</style>
