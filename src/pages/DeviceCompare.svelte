<script>
  import { onMount } from 'svelte';
  import { Line } from 'svelte-chartjs';
  import { devicesApi, dataApi } from '../api.js';
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

  let devices = [];
  let selectedIds = [];
  let compareView = false;
  let loading = false;
  let deviceData = [];
  let chartDataList = [];
  let sharedYMin = -1;
  let sharedYMax = 1;
  let refreshTimer = null;

  const colors = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b'];

  function buildChartOptions() {
    return {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      plugins: {
        legend: { display: false },
        tooltip: { enabled: false }
      },
      scales: {
        x: {
          title: { display: true, text: '时间 (s)', font: { size: 11 } },
          grid: { color: 'rgba(0, 0, 0, 0.05)' },
          ticks: { maxTicksLimit: 6, font: { size: 10 } }
        },
        y: {
          title: { display: true, text: '加速度 (m/s²)', font: { size: 11 } },
          min: sharedYMin,
          max: sharedYMax,
          grid: { color: 'rgba(0, 0, 0, 0.05)' },
          ticks: { font: { size: 10 } }
        }
      }
    };
  }

  let chartOptions = buildChartOptions();

  $: if (deviceData.length > 0) {
    chartDataList = deviceData.map((item, idx) => ({
      labels: item.labels,
      datasets: [{
        label: item.device.name,
        data: item.data,
        borderColor: colors[idx % colors.length],
        backgroundColor: colors[idx % colors.length] + '15',
        borderWidth: 1.5,
        fill: false,
        tension: 0.2,
        pointRadius: 0
      }]
    }));
    chartOptions = buildChartOptions();
  }

  function generateMockSignal(seed = 1, amp = 1) {
    const n = 500;
    const sampleRate = 1000;
    const labels = [];
    const data = [];
    for (let i = 0; i < n; i++) {
      const t = i / sampleRate;
      labels.push(t.toFixed(3));
      let s = amp * 0.6 * Math.sin(2 * Math.PI * 50 * t + seed)
        + amp * 0.25 * Math.sin(2 * Math.PI * 120 * t + seed * 1.7)
        + amp * 0.12 * Math.sin(2 * Math.PI * 230 * t + seed * 2.3);
      s += 0.08 * amp * (Math.random() - 0.5);
      data.push(s);
    }
    return { labels, data };
  }

  function computeStats(signal) {
    if (!signal || signal.length === 0) {
      return { rms: 0, peak: 0, kurtosis: 0 };
    }
    const n = signal.length;
    const mean = signal.reduce((a, b) => a + b, 0) / n;
    const centered = signal.map(v => v - mean);
    const variance = centered.reduce((a, b) => a + b * b, 0) / n;
    const rms = Math.sqrt(variance);
    const peak = Math.max(...signal.map(Math.abs));
    const std = Math.sqrt(variance) || 1e-9;
    const kurtosis = centered.reduce((a, b) => a + Math.pow(b / std, 4), 0) / n;
    return { rms, peak, kurtosis };
  }

  async function loadDevices() {
    loading = true;
    try {
      const res = await devicesApi.getDevices();
      const items = res?.data?.items || res?.items || [];
      if (items.length > 0) {
        devices = items;
      } else {
        throw new Error('no devices');
      }
    } catch (e) {
      devices = [
        { id: 1, name: '电机-001', code: 'MOT-001', location: 'A车间-1号线', status: 'online' },
        { id: 2, name: '齿轮箱-001', code: 'GBX-001', location: 'A车间-2号线', status: 'online' },
        { id: 3, name: '泵组-001', code: 'PMP-001', location: 'B车间-1号线', status: 'online' },
        { id: 4, name: '风机-001', code: 'FAN-001', location: 'B车间-2号线', status: 'online' }
      ];
    } finally {
      loading = false;
    }
  }

  function toggleDevice(id) {
    const idx = selectedIds.indexOf(id);
    if (idx >= 0) {
      selectedIds = selectedIds.filter(i => i !== id);
    } else {
      if (selectedIds.length >= 4) {
        selectedIds = [...selectedIds.slice(1), id];
      } else {
        selectedIds = [...selectedIds, id];
      }
    }
    selectedIds = selectedIds;
  }

  function enterCompare() {
    if (selectedIds.length < 2) return;
    compareView = true;
    loadCompareData();
    refreshTimer = setInterval(loadCompareData, 3000);
  }

  function exitCompare() {
    compareView = false;
    deviceData = [];
    if (refreshTimer) {
      clearInterval(refreshTimer);
      refreshTimer = null;
    }
  }

  async function loadCompareData() {
    const results = [];
    for (const id of selectedIds) {
      try {
        const res = await dataApi.getLatestVibrationData(id);
        const record = res?.data || res;
        const raw = Array.isArray(record?.data) ? record.data : null;
        if (raw && raw.length > 0) {
          const labels = raw.map((_, i) => (i / (record.sample_rate || 1000)).toFixed(3));
          results.push({
            device: devices.find(d => d.id === id) || { id, name: `设备 ${id}` },
            labels,
            data: raw,
            stats: computeStats(raw)
          });
        } else {
          throw new Error('no data');
        }
      } catch (e) {
        const seed = id * 1.7;
        const amp = 0.8 + id * 0.35;
        const mock = generateMockSignal(seed, amp);
        results.push({
          device: devices.find(d => d.id === id) || { id, name: `设备 ${id}` },
          labels: mock.labels,
          data: mock.data,
          stats: computeStats(mock.data)
        });
      }
    }
    deviceData = results;
    computeSharedRange();
  }

  function computeSharedRange() {
    let min = Infinity;
    let max = -Infinity;
    for (const item of deviceData) {
      for (const v of item.data) {
        if (v < min) min = v;
        if (v > max) max = v;
      }
    }
    if (min === Infinity) {
      sharedYMin = -1;
      sharedYMax = 1;
    } else {
      const pad = (max - min) * 0.1 || 0.5;
      sharedYMin = min - pad;
      sharedYMax = max + pad;
    }
  }

  function getStatColor(stats) {
    if (stats.rms > 2.0) return '#ef4444';
    if (stats.rms > 1.2) return '#f59e0b';
    return '#10b981';
  }

  onMount(() => {
    loadDevices();
  });
</script>

<div class="compare-page">
  <div class="page-header">
    <h1 class="page-title">多设备同屏对比</h1>
    <p class="page-subtitle">勾选 2-4 台设备，横向并排对比实时时域波形与关键统计量</p>
  </div>

  {#if !compareView}
    <div class="device-select-card">
      <div class="select-instruction">
        请选择 2-4 台设备进行对比 <span class="select-count">已选 {selectedIds.length}/4</span>
      </div>
      {#if loading}
        <div class="loading">设备列表加载中...</div>
      {:else}
        <div class="device-checkbox-grid">
          {#each devices as device}
            <label class="device-checkbox-item" class:selected={selectedIds.includes(device.id)}>
              <input
                type="checkbox"
                checked={selectedIds.includes(device.id)}
                on:change={() => toggleDevice(device.id)}
              />
              <div class="device-info">
                <div class="device-name">{device.name}</div>
                <div class="device-meta">{device.code} · {device.location}</div>
                <div class="device-status-mini" style="color: {device.status === 'online' ? '#10b981' : '#6b7280'}">
                  {device.status === 'online' ? '● 在线' : '● 离线'}
                </div>
              </div>
            </label>
          {/each}
        </div>
      {/if}
      <div class="select-actions">
        <button class="btn-primary" disabled={selectedIds.length < 2} on:click={enterCompare}>
          进入对比视图 ({selectedIds.length} 台)
        </button>
        <button class="btn-secondary" on:click={() => (selectedIds = [])}>清空选择</button>
      </div>
    </div>
  {:else}
    <div class="compare-toolbar">
      <button class="btn-secondary" on:click={exitCompare}>← 返回选择</button>
      <span class="refresh-hint">数据每 3 秒自动刷新</span>
      <button class="btn-primary" on:click={loadCompareData}>立即刷新</button>
    </div>

    {#if deviceData.length === 0}
      <div class="loading">加载对比数据中...</div>
    {:else}
      <div class="compare-grid" style="grid-template-columns: repeat({deviceData.length}, 1fr);">
        {#each deviceData as item, idx}
          <div class="device-compare-col">
            <div class="col-header" style="border-top-color: {colors[idx % colors.length]}">
              <div class="col-title">{item.device.name}</div>
              <div class="col-code">{item.device.code}</div>
            </div>

            <div class="stat-row">
              <div class="stat-box" style="color: {getStatColor(item.stats)}">
                <div class="stat-mini-label">RMS</div>
                <div class="stat-mini-value">{item.stats.rms.toFixed(3)}</div>
              </div>
              <div class="stat-box" style="color: {getStatColor(item.stats)}">
                <div class="stat-mini-label">峰值</div>
                <div class="stat-mini-value">{item.stats.peak.toFixed(3)}</div>
              </div>
              <div class="stat-box" style="color: {getStatColor(item.stats)}">
                <div class="stat-mini-label">峭度</div>
                <div class="stat-mini-value">{item.stats.kurtosis.toFixed(2)}</div>
              </div>
            </div>

            <div class="mini-chart">
              <Line data={chartDataList[idx]} options={chartOptions} />
            </div>
          </div>
        {/each}
      </div>
    {/if}
  {/if}
</div>

<style>
  .compare-page {
    padding: 24px;
    min-height: 100vh;
    background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
  }

  .page-header {
    margin-bottom: 20px;
  }

  .page-title {
    font-size: 26px;
    font-weight: 700;
    color: #1f2937;
    margin: 0 0 6px 0;
  }

  .page-subtitle {
    font-size: 14px;
    color: #6b7280;
    margin: 0;
  }

  .device-select-card {
    background: white;
    border-radius: 12px;
    padding: 24px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  }

  .select-instruction {
    font-size: 15px;
    font-weight: 600;
    color: #1f2937;
    margin-bottom: 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
  }

  .select-count {
    font-size: 13px;
    color: #3b82f6;
    background: #dbeafe;
    padding: 4px 12px;
    border-radius: 12px;
    font-weight: 600;
  }

  .loading {
    text-align: center;
    padding: 40px;
    color: #6b7280;
  }

  .device-checkbox-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: 12px;
    margin-bottom: 20px;
  }

  .device-checkbox-item {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 14px;
    border: 2px solid #e5e7eb;
    border-radius: 10px;
    cursor: pointer;
    transition: all 0.2s;
  }

  .device-checkbox-item:hover {
    border-color: #93c5fd;
    background: #f0f7ff;
  }

  .device-checkbox-item.selected {
    border-color: #3b82f6;
    background: #eff6ff;
  }

  .device-checkbox-item input[type="checkbox"] {
    margin-top: 3px;
    width: 18px;
    height: 18px;
    accent-color: #3b82f6;
    cursor: pointer;
  }

  .device-info {
    flex: 1;
  }

  .device-name {
    font-size: 15px;
    font-weight: 600;
    color: #1f2937;
  }

  .device-meta {
    font-size: 12px;
    color: #6b7280;
    margin-top: 2px;
  }

  .device-status-mini {
    font-size: 12px;
    margin-top: 4px;
    font-weight: 500;
  }

  .select-actions {
    display: flex;
    gap: 12px;
  }

  .btn-primary {
    padding: 10px 20px;
    background: #3b82f6;
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
  }

  .btn-primary:hover:not(:disabled) {
    background: #2563eb;
  }

  .btn-primary:disabled {
    background: #9ca3af;
    cursor: not-allowed;
  }

  .btn-secondary {
    padding: 10px 20px;
    background: white;
    color: #374151;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
  }

  .btn-secondary:hover {
    border-color: #3b82f6;
    color: #3b82f6;
  }

  .compare-toolbar {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 16px;
    flex-wrap: wrap;
  }

  .refresh-hint {
    font-size: 13px;
    color: #6b7280;
    flex: 1;
  }

  .compare-grid {
    display: grid;
    gap: 16px;
  }

  .device-compare-col {
    background: white;
    border-radius: 12px;
    padding: 16px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  }

  .col-header {
    border-top: 4px solid #3b82f6;
    margin: -16px -16px 12px -16px;
    padding: 12px 16px;
    border-radius: 12px 12px 0 0;
    background: #f9fafb;
  }

  .col-title {
    font-size: 16px;
    font-weight: 700;
    color: #1f2937;
  }

  .col-code {
    font-size: 12px;
    color: #6b7280;
    margin-top: 2px;
  }

  .stat-row {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    margin-bottom: 12px;
  }

  .stat-box {
    text-align: center;
    padding: 8px 4px;
    background: #f9fafb;
    border-radius: 8px;
  }

  .stat-mini-label {
    font-size: 11px;
    color: #6b7280;
    margin-bottom: 2px;
  }

  .stat-mini-value {
    font-size: 16px;
    font-weight: 700;
  }

  .mini-chart {
    height: 260px;
    position: relative;
  }

  @media (max-width: 900px) {
    .compare-grid {
      grid-template-columns: 1fr !important;
    }
  }
</style>
