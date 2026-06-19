<script>
  import { onMount, onDestroy, createEventDispatcher } from 'svelte';
  import { Line } from 'svelte-chartjs';
  import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Filler,
  } from 'chart.js';
  import { createReconnectingWebSocket } from '../api.js';

  ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Filler
  );

  export let device = {};
  export let summary = null;
  export let height = 200;

  const dispatch = createEventDispatcher();

  const MAX_BUFFER_MS = 30000;
  const TARGET_POINTS = 1500;

  let wsManager = null;
  let wsStatus = 'connecting';
  let segments = [];
  let chartLabels = [];
  let chartValues = [];
  let healthIndex = null;
  let rms = null;
  let dominantFrequency = null;
  let lastTimestamp = null;
  let wsReceived = false;

  $: if (summary && !wsReceived) {
    healthIndex = summary.health_index ?? null;
    rms = summary.rms ?? null;
    dominantFrequency = summary.dominant_frequency ?? null;
    lastTimestamp = summary.last_updated ?? null;
  }

  function buildWaveform(segs) {
    if (!segs || segs.length === 0) return { labels: [], values: [] };
    let total = 0;
    for (const s of segs) total += s.data.length;
    const stride = Math.max(1, Math.floor(total / TARGET_POINTS));
    const startTime = segs[0].timestampMs;
    const labels = [];
    const values = [];
    let idx = 0;
    for (const seg of segs) {
      const sr = seg.sampleRate;
      const baseT = (seg.timestampMs - startTime) / 1000;
      for (let i = 0; i < seg.data.length; i++) {
        if (idx % stride === 0) {
          labels.push((baseT + i / sr).toFixed(3));
          values.push(seg.data[i]);
        }
        idx++;
      }
    }
    return { labels, values };
  }

  function handleMessage(msg) {
    if (!msg || msg.type !== 'vibration_data') return;
    wsReceived = true;
    const ts = new Date(msg.timestamp).getTime();
    if (isNaN(ts)) return;
    const seg = {
      timestampMs: ts,
      data: msg.data || [],
      sampleRate: msg.sample_rate || 10240,
    };
    segments.push(seg);
    const cutoff = ts - MAX_BUFFER_MS;
    while (segments.length && segments[0].timestampMs < cutoff) {
      segments.shift();
    }
    segments = segments;

    const prev = healthIndex;
    healthIndex = msg.health_index;
    rms = msg.rms;
    dominantFrequency = msg.dominant_frequency;
    lastTimestamp = msg.timestamp;

    if (prev != null && prev >= 60 && healthIndex != null && healthIndex < 60) {
      dispatch('healthdrop', {
        deviceId: device.id,
        deviceName: device.name,
        healthIndex,
      });
    }

    const built = buildWaveform(segments);
    chartLabels = built.labels;
    chartValues = built.values;
  }

  function handleStatusChange(status) {
    wsStatus = status;
  }

  $: chartData = {
    labels: chartLabels,
    datasets: [
      {
        label: '振幅',
        data: chartValues,
        borderColor: '#4facfe',
        backgroundColor: 'rgba(79, 172, 254, 0.12)',
        borderWidth: 1.2,
        fill: true,
        tension: 0.1,
        pointRadius: 0,
        pointHoverRadius: 3,
      },
    ],
  };

  $: chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 0 },
    interaction: { mode: 'index', intersect: false },
    plugins: {
      legend: { display: false },
      title: { display: false },
      tooltip: {
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        callbacks: {
          title: (items) => `t=${items[0].label}s`,
          label: (ctx) => `振幅 ${ctx.parsed.y.toFixed(4)}`,
        },
      },
    },
    scales: {
      x: {
        grid: { display: true, color: 'rgba(255,255,255,0.08)' },
        ticks: { color: '#9ca3af', maxTicksLimit: 6, font: { size: 10 } },
        title: { display: true, text: '时间 (s)', color: '#9ca3af', font: { size: 11 } },
      },
      y: {
        grid: { display: true, color: 'rgba(255,255,255,0.08)' },
        ticks: { color: '#9ca3af', font: { size: 10 } },
        title: { display: true, text: '振幅', color: '#9ca3af', font: { size: 11 } },
      },
    },
  };

  $: cardStatus =
    wsStatus === 'disconnected'
      ? 'offline'
      : healthIndex != null && healthIndex < 60
        ? 'alarm'
        : 'online';

  $: statusText =
    {
      connected: '已连接',
      connecting: '重连中',
      reconnecting: '重连中',
      disconnected: '已断开',
    }[wsStatus] || '已断开';

  $: statusClass =
    {
      connected: 'ws-connected',
      connecting: 'ws-reconnecting',
      reconnecting: 'ws-reconnecting',
      disconnected: 'ws-disconnected',
    }[wsStatus] || 'ws-disconnected';

  onMount(() => {
    wsManager = createReconnectingWebSocket(device.id, {
      onMessage: handleMessage,
      onStatusChange: handleStatusChange,
    });
  });

  onDestroy(() => {
    if (wsManager && typeof wsManager.disconnect === 'function') {
      wsManager.disconnect();
    }
    wsManager = null;
    segments = [];
    chartLabels = [];
    chartValues = [];
    healthIndex = null;
    rms = null;
    dominantFrequency = null;
    lastTimestamp = null;
  });

  function formatTime(iso) {
    if (!iso) return '--';
    try {
      const d = new Date(iso);
      return d.toLocaleTimeString('zh-CN', { hour12: false });
    } catch (e) {
      return '--';
    }
  }
</script>

<div class="monitor-card" data-status={cardStatus}>
  <div class="card-header">
    <div class="device-info">
      <span class="status-dot {cardStatus}"></span>
      <div class="device-text">
        <span class="device-name">{device.name || `设备${device.id}`}</span>
        <span class="device-code">{device.code || ''}</span>
      </div>
    </div>
    <div class="ws-status {statusClass}">
      <span class="ws-dot"></span>
      <span class="ws-text">{statusText}</span>
    </div>
  </div>

  <div class="chart-panel" style="height: {height}px;">
    {#if chartValues.length > 0}
      <Line data={chartData} options={chartOptions} />
    {:else}
      <div class="chart-placeholder">等待采集数据…</div>
    {/if}
  </div>

  <div class="metrics">
    <div class="metric metric-health" class:danger={healthIndex != null && healthIndex < 60}>
      <span class="metric-label">健康指数</span>
      <span class="metric-value">
        {healthIndex != null ? healthIndex.toFixed(1) : '--'}
      </span>
    </div>
    <div class="metric">
      <span class="metric-label">主频 (Hz)</span>
      <span class="metric-value">{dominantFrequency != null ? dominantFrequency.toFixed(2) : '--'}</span>
    </div>
    <div class="metric">
      <span class="metric-label">RMS</span>
      <span class="metric-value">{rms != null ? rms.toFixed(4) : '--'}</span>
    </div>
    <div class="metric">
      <span class="metric-label">最后更新</span>
      <span class="metric-value metric-time">{formatTime(lastTimestamp)}</span>
    </div>
  </div>
</div>

<style>
  .monitor-card {
    display: flex;
    flex-direction: column;
    background: var(--color-white);
    border-radius: var(--radius-lg);
    border: var(--border-width) solid var(--color-gray-200);
    box-shadow: var(--shadow-md);
    overflow: hidden;
    transition: box-shadow var(--transition-normal);
  }

  .monitor-card[data-status='alarm'] {
    border-color: var(--color-danger);
    box-shadow: 0 0 0 1px var(--color-danger-light), var(--shadow-md);
  }

  .monitor-card[data-status='offline'] {
    opacity: 0.85;
  }

  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--spacing-3) var(--spacing-4);
    border-bottom: var(--border-width) solid var(--color-gray-100);
  }

  .device-info {
    display: flex;
    align-items: center;
    gap: var(--spacing-3);
    min-width: 0;
  }

  .status-dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .status-dot.online {
    background: var(--color-success);
    box-shadow: 0 0 8px var(--color-success);
  }

  .status-dot.alarm {
    background: var(--color-danger);
    box-shadow: 0 0 8px var(--color-danger);
    animation: pulse 1.4s infinite;
  }

  .status-dot.offline {
    background: var(--color-gray-400);
  }

  @keyframes pulse {
    0% { box-shadow: 0 0 4px var(--color-danger); }
    50% { box-shadow: 0 0 14px var(--color-danger); }
    100% { box-shadow: 0 0 4px var(--color-danger); }
  }

  .device-text {
    display: flex;
    flex-direction: column;
    min-width: 0;
  }

  .device-name {
    font-size: var(--font-size-base);
    font-weight: 600;
    color: var(--color-gray-900);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .device-code {
    font-size: var(--font-size-xs);
    color: var(--color-gray-500);
  }

  .ws-status {
    display: flex;
    align-items: center;
    gap: var(--spacing-2);
    font-size: var(--font-size-xs);
    padding: 2px var(--spacing-2);
    border-radius: var(--radius-full);
  }

  .ws-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
  }

  .ws-connected { color: var(--color-success-dark); background: var(--color-success-lighter); }
  .ws-connected .ws-dot { background: var(--color-success); }

  .ws-reconnecting { color: var(--color-warning-dark); background: var(--color-warning-lighter); }
  .ws-reconnecting .ws-dot { background: var(--color-warning); animation: blink 1s infinite; }

  .ws-disconnected { color: var(--color-gray-600); background: var(--color-gray-100); }
  .ws-disconnected .ws-dot { background: var(--color-gray-400); }

  @keyframes blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
  }

  .chart-panel {
    width: 100%;
    background: #1e1e2e;
    padding: var(--spacing-2);
    box-sizing: border-box;
    position: relative;
  }

  .chart-placeholder {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--color-gray-400);
    font-size: var(--font-size-sm);
  }

  .metrics {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: var(--spacing-2);
    padding: var(--spacing-3) var(--spacing-4);
  }

  .metric {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
  }

  .metric-label {
    font-size: var(--font-size-xs);
    color: var(--color-gray-500);
  }

  .metric-value {
    font-size: var(--font-size-lg);
    font-weight: 600;
    color: var(--color-gray-900);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .metric-health .metric-value {
    color: var(--color-success-dark);
  }

  .metric-health.danger .metric-value {
    color: var(--color-danger);
  }

  .metric-time {
    font-size: var(--font-size-sm);
    font-weight: 500;
    color: var(--color-gray-700);
  }

  @media (max-width: 1100px) {
    .metrics { grid-template-columns: repeat(2, 1fr); }
  }
</style>
