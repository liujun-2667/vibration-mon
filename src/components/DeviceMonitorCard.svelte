<script>
  import { onMount, onDestroy, createEventDispatcher } from 'svelte';
  import { Line, Bar } from 'svelte-chartjs';
  import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    BarElement,
    Title,
    Tooltip,
    Filler,
  } from 'chart.js';
  import annotationPlugin from 'chartjs-plugin-annotation';
  import { createReconnectingWebSocket } from '../api.js';
  import { computeFFT, computeSpectrumBars, findDominantFrequency } from '../utils/fft.js';

  ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    BarElement,
    Title,
    Tooltip,
    Filler,
    annotationPlugin
  );

  export let device = {};
  export let summary = null;
  export let height = 200;
  export let layout = 'grid-2';

  const dispatch = createEventDispatcher();

  const MAX_BUFFER_MS = 30000;
  const TARGET_POINTS = 1500;
  const SPECTRUM_MAX_FREQ = 500;
  const SPECTRUM_BARS = 50;

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
  let spectrumLabels = [];
  let spectrumValues = [];
  let spectrumDominantFreq = null;
  let spectrumDominantIdx = null;

  let vibrationLevel = null;
  let lastAlertTime = null;
  let dataQuality = null;

  $: if (summary && !wsReceived) {
    healthIndex = summary.health_index ?? null;
    rms = summary.rms ?? null;
    dominantFrequency = summary.dominant_frequency ?? null;
    lastTimestamp = summary.last_updated ?? null;
    vibrationLevel = summary.vibration_level ?? null;
    lastAlertTime = summary.last_alert_time ?? null;
    dataQuality = summary.data_quality ?? null;
  }

  $: vibrationLevelClass = {
    '优': 'level-excellent',
    '良': 'level-good',
    '警': 'level-warning',
    '危': 'level-danger',
  }[vibrationLevel] || '';

  $: dataQualityWarn = dataQuality != null && dataQuality < 80;

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

  function updateSpectrum(data, sampleRate) {
    if (!data || data.length === 0) return;
    try {
      const fftResult = computeFFT(data, sampleRate);
      const barsResult = computeSpectrumBars(
        fftResult.frequencies,
        fftResult.amplitudes,
        SPECTRUM_MAX_FREQ,
        SPECTRUM_BARS
      );
      spectrumLabels = barsResult.labels;
      spectrumValues = barsResult.bars;

      const dominant = findDominantFrequency(
        fftResult.frequencies,
        fftResult.amplitudes,
        SPECTRUM_MAX_FREQ
      );
      spectrumDominantFreq = dominant.frequency;

      const barWidth = SPECTRUM_MAX_FREQ / SPECTRUM_BARS;
      spectrumDominantIdx = Math.floor(dominant.frequency / barWidth);
    } catch (e) {
      console.error('频谱计算失败:', e);
    }
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

    if (msg.vibration_level !== undefined) {
      vibrationLevel = msg.vibration_level;
    }
    if (msg.data_quality !== undefined) {
      dataQuality = msg.data_quality;
    }

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

    updateSpectrum(seg.data, seg.sampleRate);
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

  $: spectrumChartData = {
    labels: spectrumLabels,
    datasets: [
      {
        label: '幅值',
        data: spectrumValues,
        backgroundColor: 'rgba(139, 92, 246, 0.7)',
        borderColor: 'rgba(139, 92, 246, 1)',
        borderWidth: 1,
        borderRadius: 2,
      },
    ],
  };

  $: spectrumChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 0 },
    plugins: {
      legend: { display: false },
      title: { display: false },
      tooltip: {
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        callbacks: {
          title: (items) => `${items[0].label} Hz`,
          label: (ctx) => `幅值 ${ctx.parsed.y.toFixed(4)}`,
        },
      },
      annotation: spectrumDominantIdx != null
        ? {
            annotations: {
              dominantLine: {
                type: 'line',
                xMin: spectrumDominantIdx,
                xMax: spectrumDominantIdx,
                borderColor: 'rgba(239, 68, 68, 0.9)',
                borderWidth: 1.5,
                borderDash: [4, 3],
              },
            },
          }
        : { annotations: {} },
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: {
          color: '#9ca3af',
          maxTicksLimit: 6,
          font: { size: 9 },
          callback: function(value, index) {
            const label = this.getLabelForValue(index);
            if (index % 10 === 0) return label;
            return '';
          }
        },
        title: { display: true, text: '频率 (Hz)', color: '#9ca3af', font: { size: 10 } },
      },
      y: {
        grid: { display: true, color: 'rgba(255,255,255,0.08)' },
        ticks: { color: '#9ca3af', font: { size: 9 }, maxTicksLimit: 3 },
        title: { display: false },
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
    spectrumLabels = [];
    spectrumValues = [];
    spectrumDominantFreq = null;
    spectrumDominantIdx = null;
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

  function formatDateTime(iso) {
    if (!iso) return '--';
    try {
      const d = new Date(iso);
      return d.toLocaleString('zh-CN', { hour12: false, month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
    } catch (e) {
      return '--';
    }
  }
</script>

<div class="monitor-card" data-status={cardStatus} data-layout={layout}>
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

  {#if layout !== 'compact'}
    <div class="chart-panel" style="height: {height}px;">
      {#if chartValues.length > 0}
        <Line data={chartData} options={chartOptions} />
      {:else}
        <div class="chart-placeholder">等待采集数据…</div>
      {/if}
    </div>

    <div class="spectrum-panel">
      <div class="spectrum-header">
        <span class="spectrum-title">频谱缩略图</span>
        {#if spectrumDominantFreq != null}
          <span class="spectrum-dominant">主频: {spectrumDominantFreq.toFixed(1)} Hz</span>
        {/if}
      </div>
      <div class="spectrum-chart">
        {#if spectrumValues.length > 0}
          <Bar data={spectrumChartData} options={spectrumChartOptions} />
        {:else}
          <div class="chart-placeholder small">等待频谱数据…</div>
        {/if}
      </div>
    </div>
  {/if}

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
    <div class="metric metric-vibration {vibrationLevelClass}">
      <span class="metric-label">振动烈度</span>
      <span class="metric-value">{vibrationLevel || '--'}</span>
    </div>
    {#if layout !== 'compact'}
      <div class="metric metric-data-quality" class:warn={dataQualityWarn}>
        <span class="metric-label">数据质量</span>
        <span class="metric-value">{dataQuality != null ? dataQuality.toFixed(1) + '%' : '--'}</span>
      </div>
      <div class="metric metric-alert-time">
        <span class="metric-label">最近告警</span>
        <span class="metric-value metric-time">{formatDateTime(lastAlertTime)}</span>
      </div>
      <div class="metric metric-last-update">
        <span class="metric-label">最后更新</span>
        <span class="metric-value metric-time">{formatTime(lastTimestamp)}</span>
      </div>
      <div class="metric metric-spacer"></div>
    {/if}
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

  .monitor-card[data-layout='compact'] {
    padding: var(--spacing-2) var(--spacing-4);
    border-radius: var(--radius-md);
  }

  .monitor-card[data-layout='compact'] .card-header {
    padding: 0;
    border-bottom: none;
  }

  .monitor-card[data-layout='compact'] .metrics {
    grid-template-columns: 2fr 1fr 1fr 1fr;
    padding: var(--spacing-2) 0 0;
    gap: var(--spacing-3);
  }

  .monitor-card[data-layout='compact'] .device-text {
    flex-direction: row;
    align-items: center;
    gap: var(--spacing-2);
  }

  .monitor-card[data-layout='compact'] .device-code {
    font-size: var(--font-size-xs);
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

  .spectrum-panel {
    background: #1e1e2e;
    padding: 0 var(--spacing-2) var(--spacing-2);
    box-sizing: border-box;
    border-top: 1px solid rgba(255, 255, 255, 0.05);
  }

  .spectrum-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 4px 2px;
    margin-bottom: 2px;
  }

  .spectrum-title {
    font-size: 11px;
    color: #9ca3af;
    font-weight: 500;
  }

  .spectrum-dominant {
    font-size: 11px;
    color: #f87171;
    font-weight: 500;
  }

  .spectrum-chart {
    height: 80px;
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

  .chart-placeholder.small {
    font-size: 11px;
  }

  .metrics {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: var(--spacing-2);
    padding: var(--spacing-3) var(--spacing-4);
  }

  .monitor-card:not([data-layout='compact']) .metrics {
    grid-template-columns: repeat(4, 1fr);
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

  .metric-vibration .metric-value {
    color: var(--color-gray-900);
  }

  .metric-vibration.level-excellent .metric-value {
    color: #10b981;
  }

  .metric-vibration.level-good .metric-value {
    color: #3b82f6;
  }

  .metric-vibration.level-warning .metric-value {
    color: #f97316;
  }

  .metric-vibration.level-danger .metric-value {
    color: #ef4444;
  }

  .metric-data-quality .metric-value {
    color: var(--color-gray-900);
  }

  .metric-data-quality.warn .metric-value {
    color: #eab308;
  }

  .metric-time {
    font-size: var(--font-size-sm);
    font-weight: 500;
    color: var(--color-gray-700);
  }

  .metric-spacer {
    visibility: hidden;
  }

  @media (max-width: 1100px) {
    .metrics { grid-template-columns: repeat(2, 1fr); }
  }
</style>
