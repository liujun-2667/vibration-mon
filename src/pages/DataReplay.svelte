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
    Filler
  } from 'chart.js';
  import annotationPlugin from 'chartjs-plugin-annotation';
  import { format } from 'date-fns';
  import { devicesApi, dataApi } from '../api.js';
  import StatusIndicator from '../components/StatusIndicator.svelte';

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

  let devices = [];
  let selectedDevice = null;
  let loading = true;
  let dataLoading = false;

  let startTime = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
  let endTime = new Date();
  let startTimeStr = '';
  let endTimeStr = '';

  let playbackSpeed = 1;
  let isPlaying = false;
  let currentIndex = 0;
  let playbackTimer = null;

  let vibrationData = [];
  let displayData = [];
  let chartData = null;

  let faultMarkers = [];
  let showMarkerModal = false;
  let markerForm = {
    start_index: 0,
    end_index: 0,
    fault_type: 'bearing',
    severity: 'medium',
    description: ''
  };

  const faultTypeOptions = [
    { value: 'bearing', label: '轴承故障', color: '#ef4444' },
    { value: 'gear', label: '齿轮故障', color: '#f59e0b' },
    { value: 'imbalance', label: '不平衡', color: '#f97316' },
    { value: 'misalignment', label: '不对中', color: '#8b5cf6' },
    { value: 'looseness', label: '松动', color: '#06b6d4' },
    { value: 'electrical', label: '电气故障', color: '#10b981' },
    { value: 'other', label: '其他', color: '#6b7280' }
  ];

  const severityOptions = [
    { value: 'low', label: '轻微', color: '#f59e0b' },
    { value: 'medium', label: '中等', color: '#f97316' },
    { value: 'high', label: '严重', color: '#ef4444' },
    { value: 'critical', label: '危急', color: '#991b1b' }
  ];

  const speedOptions = [0.5, 1, 2, 4, 8, 16];

  $: playbackProgress = vibrationData.length > 0 ? (currentIndex / vibrationData.length) * 100 : 0;

  $: annotations = {
    ...Object.fromEntries(
      faultMarkers.map((marker, i) => [
        `marker${i}`,
        {
          type: 'box',
          xMin: marker.start_index,
          xMax: marker.end_index,
          backgroundColor: getFaultTypeColor(marker.fault_type) + '30',
          borderColor: getFaultTypeColor(marker.fault_type),
          borderWidth: 2,
          label: {
            display: true,
            content: `${getFaultTypeLabel(marker.fault_type)} - ${getSeverityLabel(marker.severity)}`,
            position: 'start'
          }
        }
      ])
    )
  };

  $: chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    plugins: {
      legend: {
        display: false
      },
      tooltip: {
        mode: 'index',
        intersect: false,
        callbacks: {
          title: (items) => {
            if (items.length > 0 && vibrationData[items[0].dataIndex]) {
              return format(new Date(vibrationData[items[0].dataIndex].timestamp), 'yyyy-MM-dd HH:mm:ss.SSS');
            }
            return '';
          }
        }
      },
      annotation: {
        annotations: annotations
      }
    },
    scales: {
      x: {
        grid: {
          color: 'rgba(0, 0, 0, 0.05)'
        },
        ticks: {
          maxTicksLimit: 10,
          callback: (value, index, ticks) => {
            if (vibrationData[value]) {
              return format(new Date(vibrationData[value].timestamp), 'HH:mm:ss');
            }
            return '';
          }
        }
      },
      y: {
        grid: {
          color: 'rgba(0, 0, 0, 0.05)'
        },
        title: {
          display: true,
          text: '振动幅值 (g)'
        }
      }
    },
    interaction: {
      intersect: false,
      mode: 'index'
    }
  };

  async function fetchDevices() {
    try {
      const response = await devicesApi.getDevices({ page_size: 100 });
      devices = response.data?.items || response.data || [];
    } catch (error) {
      console.error('加载设备列表失败:', error);
      devices = [
        { id: 1, name: '电机-001', code: 'MOT-001', status: 'online' },
        { id: 2, name: '齿轮箱-001', code: 'GEAR-001', status: 'online' },
        { id: 3, name: '泵组-001', code: 'PUMP-001', status: 'warning' }
      ];
    } finally {
      loading = false;
    }
  }

  function generateMockVibrationData(start, end) {
    const data = [];
    const duration = end.getTime() - start.getTime();
    const sampleRate = 100;
    const count = Math.min(Math.floor(duration / 1000 * sampleRate), 10000);
    const step = duration / count;

    const fRot = 50;
    const bearingFaultFreq = fRot * 5.4;
    const gearFaultFreq = fRot * 12.7;

    for (let i = 0; i < count; i++) {
      const t = i / sampleRate;
      const timestamp = start.getTime() + i * step;

      let signal = 0.5 * Math.sin(2 * Math.PI * fRot * t)
        + 0.2 * Math.sin(2 * Math.PI * 2 * fRot * t)
        + 0.1 * Math.sin(2 * Math.PI * 3 * fRot * t);

      const progress = i / count;
      if (progress > 0.3 && progress < 0.4) {
        var expArg = Math.pow((progress - 0.35) * 50, 2);
        signal += 0.3 * Math.sin(2 * Math.PI * bearingFaultFreq * t) * Math.exp(-expArg);
      }
      if (progress > 0.6 && progress < 0.7) {
        signal += 0.4 * Math.sin(2 * Math.PI * gearFaultFreq * t);
      }

      signal += 0.15 * (Math.random() - 0.5);

      data.push({
        timestamp,
        value: signal,
        rms: Math.abs(signal) * 0.707,
        peak: Math.abs(signal)
      });
    }

    return data;
  }

  async function fetchVibrationData() {
    if (!selectedDevice) return;

    dataLoading = true;
    stopPlayback();
    currentIndex = 0;

    try {
      const params = {
        device_id: selectedDevice.id,
        start_time: startTime.toISOString(),
        end_time: endTime.toISOString()
      };
      const response = await dataApi.getVibrationData(params);
      vibrationData = response.data?.items || response.data || [];
    } catch (error) {
      console.error('加载振动数据失败:', error);
      vibrationData = generateMockVibrationData(startTime, endTime);
    }

    if (vibrationData.length === 0) {
      vibrationData = generateMockVibrationData(startTime, endTime);
    }

    faultMarkers = [
      {
        id: 1,
        start_index: Math.floor(vibrationData.length * 0.3),
        end_index: Math.floor(vibrationData.length * 0.4),
        fault_type: 'bearing',
        severity: 'medium',
        description: '轴承外圈故障特征频率明显，建议安排检修',
        created_at: new Date().toISOString()
      },
      {
        id: 2,
        start_index: Math.floor(vibrationData.length * 0.6),
        end_index: Math.floor(vibrationData.length * 0.7),
        fault_type: 'gear',
        severity: 'high',
        description: '齿轮啮合频率幅值异常升高，可能存在齿面磨损',
        created_at: new Date().toISOString()
      }
    ];

    updateDisplayData();
    dataLoading = false;
  }

  function updateDisplayData() {
    const displayCount = Math.min(vibrationData.length, 1000);
    const step = Math.max(1, Math.floor(vibrationData.length / displayCount));

    displayData = [];
    for (let i = 0; i < vibrationData.length; i += step) {
      displayData.push(vibrationData[i]);
    }

    const currentData = displayData.slice(0, Math.ceil(currentIndex / step));

    chartData = {
      labels: currentData.map((_, i) => i * step),
      datasets: [
        {
          label: '振动幅值',
          data: currentData.map(d => d.value),
          borderColor: '#3b82f6',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          borderWidth: 2,
          fill: true,
          tension: 0.4,
          pointRadius: 0
        }
      ]
    };
  }

  function togglePlayback() {
    if (isPlaying) {
      stopPlayback();
    } else {
      startPlayback();
    }
  }

  function startPlayback() {
    if (currentIndex >= vibrationData.length - 1) {
      currentIndex = 0;
    }
    isPlaying = true;
    const interval = 100 / playbackSpeed;
    playbackTimer = setInterval(() => {
      currentIndex = Math.min(currentIndex + Math.ceil(10 * playbackSpeed), vibrationData.length - 1);
      updateDisplayData();
      if (currentIndex >= vibrationData.length - 1) {
        stopPlayback();
      }
    }, interval);
  }

  function stopPlayback() {
    isPlaying = false;
    if (playbackTimer) {
      clearInterval(playbackTimer);
      playbackTimer = null;
    }
  }

  function setPlaybackSpeed(speed) {
    playbackSpeed = speed;
    if (isPlaying) {
      stopPlayback();
      startPlayback();
    }
  }

  function seekToPosition(event) {
    const rect = event.currentTarget.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const percentage = x / rect.width;
    currentIndex = Math.floor(percentage * vibrationData.length);
    updateDisplayData();
  }

  function jumpToStart() {
    currentIndex = 0;
    updateDisplayData();
  }

  function jumpToEnd() {
    currentIndex = vibrationData.length - 1;
    updateDisplayData();
  }

  function stepBackward() {
    currentIndex = Math.max(0, currentIndex - 100);
    updateDisplayData();
  }

  function stepForward() {
    currentIndex = Math.min(vibrationData.length - 1, currentIndex + 100);
    updateDisplayData();
  }

  function openAddMarker() {
    stopPlayback();
    markerForm = {
      start_index: Math.max(0, currentIndex - 100),
      end_index: Math.min(vibrationData.length - 1, currentIndex + 100),
      fault_type: 'bearing',
      severity: 'medium',
      description: ''
    };
    showMarkerModal = true;
  }

  function saveMarker() {
    const newMarker = {
      id: Date.now(),
      ...markerForm,
      created_at: new Date().toISOString()
    };
    faultMarkers = [...faultMarkers, newMarker].sort((a, b) => a.start_index - b.start_index);
    showMarkerModal = false;
    updateDisplayData();
  }

  function deleteMarker(markerId) {
    if (!confirm('确定要删除这个故障标记吗？')) return;
    faultMarkers = faultMarkers.filter(m => m.id !== markerId);
    updateDisplayData();
  }

  function jumpToMarker(marker) {
    stopPlayback();
    currentIndex = marker.start_index;
    updateDisplayData();
  }

  function getFaultTypeLabel(value) {
    return faultTypeOptions.find(f => f.value === value)?.label || value;
  }

  function getFaultTypeColor(value) {
    return faultTypeOptions.find(f => f.value === value)?.color || '#6b7280';
  }

  function getSeverityLabel(value) {
    return severityOptions.find(s => s.value === value)?.label || value;
  }

  function getSeverityColor(value) {
    return severityOptions.find(s => s.value === value)?.color || '#6b7280';
  }

  function formatTime(date) {
    return format(date, 'yyyy-MM-dd HH:mm');
  }

  function initDateInputs() {
    startTimeStr = format(startTime, "yyyy-MM-dd'T'HH:mm");
    endTimeStr = format(endTime, "yyyy-MM-dd'T'HH:mm");
  }

  function updateStartTime(event) {
    startTime = new Date(event.target.value);
    startTimeStr = event.target.value;
  }

  function updateEndTime(event) {
    endTime = new Date(event.target.value);
    endTimeStr = event.target.value;
  }

  function setQuickRange(hours) {
    endTime = new Date();
    startTime = new Date(endTime.getTime() - hours * 60 * 60 * 1000);
    initDateInputs();
  }

  function exportMarkerData(marker) {
    const markerData = vibrationData.slice(marker.start_index, marker.end_index + 1);
    const json = JSON.stringify({
      marker_info: marker,
      data: markerData
    }, null, 2);
    
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `fault_${marker.fault_type}_${format(new Date(), 'yyyyMMdd_HHmmss')}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  onMount(() => {
    initDateInputs();
    fetchDevices();
  });

  onDestroy(() => {
    stopPlayback();
  });
</script>

<div class="data-replay">
  <div class="header">
    <div>
      <h1 class="page-title">历史数据回放</h1>
      <p class="page-subtitle">回放历史振动数据，标记故障样本</p>
    </div>
  </div>

  <div class="control-panel">
    <div class="control-section">
      <label class="control-label">选择设备</label>
      <select bind:value={selectedDevice} on:change={fetchVibrationData} disabled={loading}>
        <option value={null}>请选择设备</option>
        {#each devices as device}
          <option value={device}>{device.name} ({device.code})</option>
        {/each}
      </select>
    </div>

    <div class="control-section">
      <label class="control-label">时间范围</label>
      <div class="datetime-group">
        <input type="datetime-local" bind:value={startTimeStr} on:change={updateStartTime} />
        <span class="datetime-separator">至</span>
        <input type="datetime-local" bind:value={endTimeStr} on:change={updateEndTime} />
      </div>
      <div class="quick-range">
        <button class="range-btn" on:click={() => setQuickRange(1)}>1小时</button>
        <button class="range-btn" on:click={() => setQuickRange(6)}>6小时</button>
        <button class="range-btn" on:click={() => setQuickRange(24)}>1天</button>
        <button class="range-btn" on:click={() => setQuickRange(168)}>1周</button>
      </div>
    </div>

    <div class="control-section">
      <button class="btn btn-primary load-btn" on:click={fetchVibrationData} disabled={!selectedDevice || dataLoading}>
        {dataLoading ? '加载中...' : '🔍 加载数据'}
      </button>
    </div>
  </div>

  {#if dataLoading}
    <div class="loading">数据加载中...</div>
  {:else if vibrationData.length === 0}
    <div class="empty">
      <div class="empty-icon">📈</div>
      <p>请选择设备和时间范围，然后点击"加载数据"</p>
    </div>
  {:else}
    <div class="chart-section">
      <div class="chart-card">
        <div class="chart-header">
          <div>
            <h2 class="chart-title">时域波形回放</h2>
            <p class="chart-subtitle">
              {selectedDevice?.name} · {formatTime(startTime)} - {formatTime(endTime)}
              <span class="data-count">共 {vibrationData.length} 个采样点</span>
            </p>
          </div>
          <div class="chart-actions">
            <button class="btn btn-secondary" on:click={openAddMarker}>
              📍 标记故障
            </button>
          </div>
        </div>

        <div class="waveform-container">
          <div class="progress-bar" on:click={seekToPosition}>
            <div class="progress-fill" style="width: {playbackProgress}%"></div>
            <div class="progress-indicator" style="left: {playbackProgress}%"></div>
          </div>

          <div class="chart-container">
            {#if chartData}
              <Line data={chartData} options={chartOptions} />
            {/if}
          </div>
        </div>

        <div class="playback-controls">
          <div class="control-buttons">
            <button class="ctrl-btn" on:click={jumpToStart} title="跳到开始">⏮️</button>
            <button class="ctrl-btn" on:click={stepBackward} title="后退">⏪</button>
            <button class="ctrl-btn play-btn" on:click={togglePlayback}>
              {isPlaying ? '⏸️' : '▶️'}
            </button>
            <button class="ctrl-btn" on:click={stepForward} title="前进">⏩</button>
            <button class="ctrl-btn" on:click={jumpToEnd} title="跳到结束">⏭️</button>
          </div>

          <div class="speed-control">
            <span class="speed-label">倍速:</span>
            <div class="speed-buttons">
              {#each speedOptions as speed}
                <button
                  class="speed-btn {playbackSpeed === speed ? 'active' : ''}"
                  on:click={() => setPlaybackSpeed(speed)}
                >
                  {speed}x
                </button>
              {/each}
            </div>
          </div>

          <div class="current-time">
            {vibrationData[currentIndex] ? format(new Date(vibrationData[currentIndex].timestamp), 'yyyy-MM-dd HH:mm:ss.SSS') : '-'}
          </div>
        </div>
      </div>
    </div>

    <div class="markers-section">
      <div class="markers-header">
        <h2 class="section-title">故障标记列表</h2>
        <span class="markers-count">{faultMarkers.length} 个标记</span>
      </div>

      {#if faultMarkers.length === 0}
        <div class="empty small">暂无故障标记</div>
      {:else}
        <div class="markers-list">
          {#each faultMarkers as marker (marker.id)}
            <div class="marker-card" style="border-left: 4px solid {getFaultTypeColor(marker.fault_type)}">
              <div class="marker-header">
                <div class="marker-type">
                  <span class="marker-dot" style="background: {getFaultTypeColor(marker.fault_type)}"></span>
                  <span class="marker-type-label">{getFaultTypeLabel(marker.fault_type)}</span>
                </div>
                <span class="marker-severity" style="background: {getSeverityColor(marker.severity)}20; color: {getSeverityColor(marker.severity)}">
                  {getSeverityLabel(marker.severity)}
                </span>
              </div>
              <div class="marker-content">
                <p class="marker-description">{marker.description}</p>
                <div class="marker-meta">
                  <span>时间范围: {format(new Date(vibrationData[marker.start_index]?.timestamp), 'HH:mm:ss')} - {format(new Date(vibrationData[marker.end_index]?.timestamp), 'HH:mm:ss')}</span>
                  <span>采样点: {marker.start_index} - {marker.end_index}</span>
                </div>
              </div>
              <div class="marker-actions">
                <button class="btn btn-sm btn-secondary" on:click={() => jumpToMarker(marker)}>
                  定位
                </button>
                <button class="btn btn-sm btn-secondary" on:click={() => exportMarkerData(marker)}>
                  导出数据
                </button>
                <button class="btn btn-sm btn-danger" on:click={() => deleteMarker(marker.id)}>
                  删除
                </button>
              </div>
            </div>
          {/each}
        </div>
      {/if}
    </div>

    <div class="stats-section">
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-label">当前值</div>
          <div class="stat-value">{vibrationData[currentIndex]?.value?.toFixed(4) || '-'}</div>
          <div class="stat-unit">g</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">峰值</div>
          <div class="stat-value">{vibrationData[currentIndex]?.peak?.toFixed(4) || '-'}</div>
          <div class="stat-unit">g</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">RMS</div>
          <div class="stat-value">{vibrationData[currentIndex]?.rms?.toFixed(4) || '-'}</div>
          <div class="stat-unit">g</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">回放进度</div>
          <div class="stat-value">{playbackProgress.toFixed(1)}</div>
          <div class="stat-unit">%</div>
        </div>
      </div>
    </div>
  {/if}

  {#if showMarkerModal}
    <div class="modal-overlay" on:click|stopPropagation={() => showMarkerModal = false}>
      <div class="modal" on:click|stopPropagation>
        <div class="modal-header">
          <h2>添加故障标记</h2>
          <button class="modal-close" on:click={() => showMarkerModal = false}>×</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>故障类型</label>
            <select bind:value={markerForm.fault_type}>
              {#each faultTypeOptions as opt}
                <option value={opt.value}>{opt.label}</option>
              {/each}
            </select>
          </div>
          <div class="form-group">
            <label>严重程度</label>
            <select bind:value={markerForm.severity}>
              {#each severityOptions as opt}
                <option value={opt.value}>{opt.label}</option>
              {/each}
            </select>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>起始采样点</label>
              <input type="number" bind:value={markerForm.start_index} min="0" max={vibrationData.length - 1} />
            </div>
            <div class="form-group">
              <label>结束采样点</label>
              <input type="number" bind:value={markerForm.end_index} min="0" max={vibrationData.length - 1} />
            </div>
          </div>
          <div class="form-group">
            <label>故障描述</label>
            <textarea bind:value={markerForm.description} rows="3" placeholder="请输入故障特征描述..."></textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" on:click={() => showMarkerModal = false}>取消</button>
          <button class="btn btn-primary" on:click={saveMarker} disabled={markerForm.start_index >= markerForm.end_index}>
            保存标记
          </button>
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  .data-replay {
    padding: 24px;
    min-height: 100vh;
    background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
  }

  .header {
    margin-bottom: 24px;
  }

  .page-title {
    font-size: 28px;
    font-weight: 700;
    color: #1f2937;
    margin: 0 0 8px 0;
  }

  .page-subtitle {
    font-size: 14px;
    color: #6b7280;
    margin: 0;
  }

  .section-title {
    font-size: 18px;
    font-weight: 600;
    color: #1f2937;
    margin: 0;
  }

  .control-panel {
    background: white;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    display: flex;
    gap: 24px;
    flex-wrap: wrap;
    align-items: flex-end;
  }

  .control-section {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .control-label {
    font-size: 13px;
    font-weight: 500;
    color: #374151;
  }

  .control-section select,
  .control-section input {
    padding: 10px 14px;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    font-size: 14px;
    outline: none;
    transition: border-color 0.2s, box-shadow 0.2s;
    font-family: inherit;
    min-width: 200px;
  }

  .control-section select:focus,
  .control-section input:focus {
    border-color: #3b82f6;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
  }

  .datetime-group {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .datetime-separator {
    color: #6b7280;
    font-size: 14px;
  }

  .quick-range {
    display: flex;
    gap: 8px;
  }

  .range-btn {
    padding: 6px 12px;
    border: 1px solid #d1d5db;
    background: white;
    border-radius: 6px;
    font-size: 12px;
    cursor: pointer;
    transition: all 0.2s;
  }

  .range-btn:hover {
    border-color: #3b82f6;
    color: #3b82f6;
  }

  .btn {
    padding: 10px 20px;
    border: none;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    display: inline-flex;
    align-items: center;
    gap: 8px;
  }

  .btn-sm {
    padding: 6px 12px;
    font-size: 13px;
  }

  .btn-primary {
    background: linear-gradient(90deg, #3b82f6 0%, #2563eb 100%);
    color: white;
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
  }

  .btn-primary:hover:not(:disabled) {
    transform: translateY(-1px);
    box-shadow: 0 6px 16px rgba(59, 130, 246, 0.4);
  }

  .btn-primary:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .btn-secondary {
    background: white;
    color: #4b5563;
    border: 1px solid #d1d5db;
  }

  .btn-secondary:hover {
    border-color: #3b82f6;
    color: #3b82f6;
  }

  .btn-danger {
    background: #fef2f2;
    color: #dc2626;
    border: 1px solid #fecaca;
  }

  .btn-danger:hover {
    background: #fee2e2;
  }

  .load-btn {
    height: 42px;
  }

  .chart-section {
    margin-bottom: 20px;
  }

  .chart-card {
    background: white;
    border-radius: 12px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    overflow: hidden;
  }

  .chart-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    padding: 20px;
    border-bottom: 1px solid #f3f4f6;
    flex-wrap: wrap;
    gap: 12px;
  }

  .chart-title {
    font-size: 18px;
    font-weight: 600;
    color: #1f2937;
    margin: 0 0 4px 0;
  }

  .chart-subtitle {
    font-size: 13px;
    color: #6b7280;
    margin: 0;
  }

  .data-count {
    margin-left: 12px;
    padding: 2px 8px;
    background: #eff6ff;
    color: #3b82f6;
    border-radius: 10px;
    font-size: 12px;
  }

  .chart-actions {
    display: flex;
    gap: 8px;
  }

  .waveform-container {
    padding: 16px 20px;
  }

  .progress-bar {
    position: relative;
    height: 8px;
    background: #e5e7eb;
    border-radius: 4px;
    cursor: pointer;
    margin-bottom: 12px;
  }

  .progress-fill {
    position: absolute;
    left: 0;
    top: 0;
    height: 100%;
    background: linear-gradient(90deg, #3b82f6 0%, #2563eb 100%);
    border-radius: 4px;
    transition: width 0.05s linear;
  }

  .progress-indicator {
    position: absolute;
    top: 50%;
    transform: translate(-50%, -50%);
    width: 16px;
    height: 16px;
    background: white;
    border: 3px solid #3b82f6;
    border-radius: 50%;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
    transition: left 0.05s linear;
  }

  .chart-container {
    height: 350px;
    position: relative;
  }

  .playback-controls {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 20px;
    background: #f9fafb;
    border-top: 1px solid #e5e7eb;
    flex-wrap: wrap;
    gap: 16px;
  }

  .control-buttons {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .ctrl-btn {
    width: 40px;
    height: 40px;
    border: 1px solid #d1d5db;
    background: white;
    border-radius: 8px;
    font-size: 16px;
    cursor: pointer;
    transition: all 0.2s;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .ctrl-btn:hover {
    border-color: #3b82f6;
    color: #3b82f6;
  }

  .play-btn {
    width: 56px;
    height: 56px;
    background: linear-gradient(90deg, #3b82f6 0%, #2563eb 100%);
    color: white;
    border: none;
    font-size: 24px;
  }

  .play-btn:hover {
    transform: scale(1.05);
    color: white;
  }

  .speed-control {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .speed-label {
    font-size: 13px;
    color: #6b7280;
  }

  .speed-buttons {
    display: flex;
    gap: 4px;
    background: #e5e7eb;
    padding: 4px;
    border-radius: 8px;
  }

  .speed-btn {
    padding: 6px 12px;
    border: none;
    background: transparent;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    color: #4b5563;
  }

  .speed-btn:hover {
    background: white;
  }

  .speed-btn.active {
    background: white;
    color: #3b82f6;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  }

  .current-time {
    font-family: 'Monaco', 'Menlo', monospace;
    font-size: 13px;
    color: #374151;
    background: white;
    padding: 8px 16px;
    border-radius: 8px;
    border: 1px solid #e5e7eb;
  }

  .markers-section {
    background: white;
    border-radius: 12px;
    margin-bottom: 20px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    overflow: hidden;
  }

  .markers-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 20px;
    border-bottom: 1px solid #f3f4f6;
  }

  .markers-count {
    padding: 4px 12px;
    background: #eff6ff;
    color: #3b82f6;
    border-radius: 12px;
    font-size: 13px;
    font-weight: 500;
  }

  .markers-list {
    padding: 16px;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
    gap: 12px;
  }

  .marker-card {
    background: #f9fafb;
    border-radius: 8px;
    padding: 16px;
    border: 1px solid #e5e7eb;
  }

  .marker-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
  }

  .marker-type {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .marker-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
  }

  .marker-type-label {
    font-weight: 600;
    color: #1f2937;
  }

  .marker-severity {
    padding: 3px 10px;
    border-radius: 10px;
    font-size: 12px;
    font-weight: 500;
  }

  .marker-content {
    margin-bottom: 12px;
  }

  .marker-description {
    margin: 0 0 8px 0;
    font-size: 14px;
    color: #4b5563;
    line-height: 1.5;
  }

  .marker-meta {
    display: flex;
    flex-direction: column;
    gap: 4px;
    font-size: 12px;
    color: #6b7280;
  }

  .marker-actions {
    display: flex;
    gap: 8px;
    padding-top: 12px;
    border-top: 1px solid #e5e7eb;
  }

  .marker-actions .btn {
    flex: 1;
    justify-content: center;
  }

  .stats-section {
    margin-bottom: 20px;
  }

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 16px;
  }

  .stat-card {
    background: white;
    border-radius: 12px;
    padding: 20px;
    text-align: center;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  }

  .stat-label {
    font-size: 13px;
    color: #6b7280;
    margin-bottom: 8px;
  }

  .stat-value {
    font-size: 28px;
    font-weight: 700;
    color: #1f2937;
    font-family: 'Monaco', 'Menlo', monospace;
  }

  .stat-unit {
    font-size: 12px;
    color: #9ca3af;
    margin-top: 4px;
  }

  .loading, .empty {
    background: white;
    border-radius: 12px;
    padding: 60px;
    text-align: center;
    color: #6b7280;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  }

  .empty.small {
    padding: 40px;
    box-shadow: none;
    background: transparent;
  }

  .empty-icon {
    font-size: 48px;
    margin-bottom: 16px;
  }

  .modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    padding: 20px;
  }

  .modal {
    background: white;
    border-radius: 16px;
    max-width: 500px;
    width: 100%;
    max-height: 90vh;
    overflow-y: auto;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  }

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 20px 24px;
    border-bottom: 1px solid #e5e7eb;
  }

  .modal-header h2 {
    margin: 0;
    font-size: 20px;
    font-weight: 600;
    color: #1f2937;
  }

  .modal-close {
    background: none;
    border: none;
    font-size: 28px;
    color: #6b7280;
    cursor: pointer;
    padding: 0;
    line-height: 1;
  }

  .modal-close:hover {
    color: #ef4444;
  }

  .modal-body {
    padding: 24px;
  }

  .form-group {
    display: flex;
    flex-direction: column;
    margin-bottom: 16px;
  }

  .form-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }

  .form-group label {
    font-size: 13px;
    font-weight: 500;
    color: #374151;
    margin-bottom: 6px;
  }

  .form-group input,
  .form-group select,
  .form-group textarea {
    padding: 10px 12px;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    font-size: 14px;
    outline: none;
    transition: border-color 0.2s, box-shadow 0.2s;
    font-family: inherit;
  }

  .form-group input:focus,
  .form-group select:focus,
  .form-group textarea:focus {
    border-color: #3b82f6;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
  }

  .modal-footer {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
    padding: 20px 24px;
    border-top: 1px solid #e5e7eb;
    background: #f9fafb;
    border-radius: 0 0 16px 16px;
  }

  @media (max-width: 768px) {
    .data-replay {
      padding: 16px;
    }

    .control-panel {
      flex-direction: column;
      align-items: stretch;
    }

    .datetime-group {
      flex-direction: column;
      align-items: stretch;
    }

    .playback-controls {
      flex-direction: column;
      align-items: center;
    }

    .markers-list {
      grid-template-columns: 1fr;
    }

    .form-row {
      grid-template-columns: 1fr;
    }
  }
</style>
