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

  let selectedDevice = null;
  let devices = [];
  let selectedTimeRange = '1h';
  let selectedMetrics = ['rms', 'peak', 'peak_to_peak'];
  let loading = true;
  let trendData = null;
  let trendSummary = null;
  let warnings = [];

  const timeRanges = [
    { value: '1h', label: '最近1小时', seconds: 3600 },
    { value: '8h', label: '最近8小时', seconds: 28800 },
    { value: '24h', label: '最近24小时', seconds: 86400 },
    { value: '7d', label: '最近7天', seconds: 604800 }
  ];

  const metricsConfig = {
    rms: { label: 'RMS', color: '#3b82f6', unit: 'mm/s' },
    peak: { label: '峰值', color: '#ef4444', unit: 'mm/s' },
    peak_to_peak: { label: '峰峰值', color: '#f59e0b', unit: 'mm/s' },
    crest_factor: { label: '波峰因数', color: '#8b5cf6', unit: '' },
    kurtosis: { label: '峭度', color: '#10b981', unit: '' }
  };

  const referenceLines = {
    rms: { baseline: 1.0, warning: 2.0, alarm: 5.0 },
    peak: { baseline: 2.5, warning: 5.0, alarm: 12.0 },
    peak_to_peak: { baseline: 4.5, warning: 9.0, alarm: 20.0 },
    crest_factor: { baseline: 2.5, warning: 4.0, alarm: 6.0 },
    kurtosis: { baseline: 3.0, warning: 4.5, alarm: 7.0 }
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      intersect: false,
      mode: 'index'
    },
    plugins: {
      legend: {
        position: 'top',
        labels: {
          usePointStyle: true,
          padding: 20
        }
      },
      tooltip: {
        backgroundColor: 'rgba(255, 255, 255, 0.95)',
        titleColor: '#1f2937',
        bodyColor: '#374151',
        borderColor: '#e5e7eb',
        borderWidth: 1,
        padding: 12,
        displayColors: true
      }
    },
    scales: {
      x: {
        grid: {
          color: 'rgba(0, 0, 0, 0.05)'
        },
        ticks: {
          maxTicksLimit: 10
        }
      },
      y: {
        grid: {
          color: 'rgba(0, 0, 0, 0.05)'
        },
        beginAtZero: true
      }
    }
  };

  let chartData = null;

  function generateMockTrendData(timeRange, metric) {
    const config = timeRanges.find(t => t.value === timeRange);
    const now = Date.now();
    const points = Math.min(120, Math.floor(config.seconds / 60));
    const timestamps = [];
    const values = [];
    const regressionLine = [];

    const ref = referenceLines[metric];
    const baseValue = ref.baseline;
    const noise = ref.warning * 0.1;

    let slope = 0;
    const random = Math.random();
    if (random > 0.7) {
      slope = (ref.warning - baseValue) / points * 0.8;
    } else if (random < 0.3) {
      slope = -(ref.baseline * 0.3) / points;
    }

    for (let i = 0; i < points; i++) {
      const t = now - (points - i) * (config.seconds / points) * 1000;
      const date = new Date(t);
      let timeLabel;
      if (config.seconds <= 3600) {
        timeLabel = date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
      } else if (config.seconds <= 86400) {
        timeLabel = date.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit' });
      } else {
        timeLabel = date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' });
      }
      timestamps.push(timeLabel);

      const trendValue = baseValue + slope * i;
      const randomNoise = (Math.random() - 0.5) * noise;
      const value = Math.max(0.1, trendValue + randomNoise);
      values.push(value);
      regressionLine.push(baseValue + slope * i);
    }

    const xNorm = Array.from({ length: points }, (_, i) => i);
    const meanX = xNorm.reduce((a, b) => a + b, 0) / points;
    const meanY = values.reduce((a, b) => a + b, 0) / points;
    let numerator = 0, denominator = 0;
    for (let i = 0; i < points; i++) {
      numerator += (xNorm[i] - meanX) * (values[i] - meanY);
      denominator += Math.pow(xNorm[i] - meanX, 2);
    }
    const regSlope = denominator !== 0 ? numerator / denominator : 0;
    const regIntercept = meanY - regSlope * meanX;

    let ssTotal = 0, ssResidual = 0;
    for (let i = 0; i < points; i++) {
      const predicted = regSlope * xNorm[i] + regIntercept;
      ssTotal += Math.pow(values[i] - meanY, 2);
      ssResidual += Math.pow(values[i] - predicted, 2);
    }
    const rSquared = ssTotal !== 0 ? 1 - (ssResidual / ssTotal) : 0;

    let status = 'stable';
    let isRising = false;
    if (rSquared >= 0.7) {
      if (regSlope > 0.001) {
        status = 'rising';
        isRising = true;
      } else if (regSlope < -0.001) {
        status = 'falling';
      }
    } else {
      status = 'unknown';
    }

    return {
      timestamps,
      values,
      regressionLine,
      statistics: {
        slope: regSlope,
        intercept: regIntercept,
        r_squared: rSquared,
        mean: meanY,
        min: Math.min(...values),
        max: Math.max(...values),
        latest: values[values.length - 1]
      },
      status,
      isRising,
      reference_lines: ref
    };
  }

  function toggleMetric(metric) {
    if (selectedMetrics.includes(metric)) {
      if (selectedMetrics.length > 1) {
        selectedMetrics = selectedMetrics.filter(m => m !== metric);
      }
    } else {
      selectedMetrics = [...selectedMetrics, metric];
    }
    updateChartData();
  }

  function updateChartData() {
    if (!trendData) return;

    const datasets = [];
    const firstMetric = selectedMetrics[0];
    const labels = trendData[firstMetric]?.timestamps || [];

    selectedMetrics.forEach(metric => {
      const data = trendData[metric];
      const config = metricsConfig[metric];
      if (data) {
        datasets.push({
          label: `${config.label} (${config.unit})`,
          data: data.values,
          borderColor: config.color,
          backgroundColor: config.color + '20',
          borderWidth: 2,
          fill: false,
          tension: 0.3,
          pointRadius: 0,
          pointHoverRadius: 4,
          yAxisID: selectedMetrics.length > 1 ? `y${selectedMetrics.indexOf(metric)}` : 'y'
        });

        datasets.push({
          label: `${config.label} 趋势线`,
          data: data.regressionLine,
          borderColor: config.color,
          borderWidth: 2,
          borderDash: [5, 5],
          fill: false,
          tension: 0,
          pointRadius: 0,
          yAxisID: selectedMetrics.length > 1 ? `y${selectedMetrics.indexOf(metric)}` : 'y'
        });
      }
    });

    const scales = { ...chartOptions.scales };
    if (selectedMetrics.length > 1) {
      selectedMetrics.forEach((metric, idx) => {
        const config = metricsConfig[metric];
        scales[`y${idx}`] = {
          type: 'linear',
          display: true,
          position: idx === 0 ? 'left' : 'right',
          grid: { color: 'rgba(0, 0, 0, 0.05)' },
          title: {
            display: true,
            text: `${config.label} (${config.unit})`,
            color: config.color
          },
          ticks: { color: config.color }
        };
      });
      delete scales.y;
    }

    chartData = {
      labels,
      datasets,
      options: {
        ...chartOptions,
        scales
      }
    };
  }

  async function fetchDevices() {
    try {
      const response = await fetch('/api/v1/devices?page_size=100');
      const data = await response.json();
      devices = data.items || [];
      if (devices.length > 0) {
        selectedDevice = devices[0].id;
      }
    } catch (error) {
      devices = [
        { id: 1, name: '电机-001', code: 'MOT-001' },
        { id: 2, name: '齿轮箱-001', code: 'GEAR-001' },
        { id: 3, name: '泵组-001', code: 'PUMP-001' }
      ];
      selectedDevice = 1;
    }
  }

  async function fetchTrendData() {
    loading = true;
    try {
      const metrics = ['rms', 'peak', 'peak_to_peak', 'crest_factor', 'kurtosis'];
      trendData = {};
      trendSummary = {};
      warnings = [];

      for (const metric of metrics) {
        const result = generateMockTrendData(selectedTimeRange, metric);
        trendData[metric] = result;
        trendSummary[metric] = {
          ...result.statistics,
          status: result.status,
          isRising: result.isRising
        };

        if (result.isRising) {
          warnings.push({
            metric,
            label: metricsConfig[metric].label,
            severity: result.statistics.latest > referenceLines[metric].warning ? 'high' : 'medium',
            message: `${metricsConfig[metric].label}呈现持续上升趋势`,
            rSquared: result.statistics.r_squared,
            slope: result.statistics.slope
          });
        }

        if (result.statistics.latest > referenceLines[metric].alarm) {
          warnings.push({
            metric,
            label: metricsConfig[metric].label,
            severity: 'critical',
            message: `${metricsConfig[metric].label}超过报警阈值`,
            value: result.statistics.latest,
            threshold: referenceLines[metric].alarm
          });
        } else if (result.statistics.latest > referenceLines[metric].warning) {
          warnings.push({
            metric,
            label: metricsConfig[metric].label,
            severity: 'warning',
            message: `${metricsConfig[metric].label}超过警告阈值`,
            value: result.statistics.latest,
            threshold: referenceLines[metric].warning
          });
        }
      }

      warnings.sort((a, b) => {
        const severityOrder = { critical: 0, high: 1, warning: 2, medium: 3 };
        return severityOrder[a.severity] - severityOrder[b.severity];
      });

      updateChartData();
    } catch (error) {
      console.error('获取趋势数据失败:', error);
    } finally {
      loading = false;
    }
  }

  function formatValue(value, decimals = 3) {
    return value !== undefined && value !== null ? value.toFixed(decimals) : '-';
  }

  function getStatusStyle(status) {
    const styles = {
      rising: { color: '#ef4444', bgColor: '#fef2f2', label: '上升' },
      falling: { color: '#10b981', bgColor: '#ecfdf5', label: '下降' },
      stable: { color: '#3b82f6', bgColor: '#eff6ff', label: '稳定' },
      unknown: { color: '#6b7280', bgColor: '#f9fafb', label: '未知' }
    };
    return styles[status] || styles.unknown;
  }

  function getSeverityStyle(severity) {
    const styles = {
      critical: { color: '#fff', bgColor: '#ef4444', label: '严重' },
      high: { color: '#fff', bgColor: '#f97316', label: '高' },
      warning: { color: '#92400e', bgColor: '#fbbf24', label: '警告' },
      medium: { color: '#fff', bgColor: '#f59e0b', label: '中' }
    };
    return styles[severity] || styles.warning;
  }

  function getDeviceName(id) {
    const device = devices.find(d => d.id === id);
    return device ? device.name : `设备-${id}`;
  }

  let refreshInterval;

  onMount(async () => {
    await fetchDevices();
    await fetchTrendData();
    refreshInterval = setInterval(fetchTrendData, 30000);
  });

  onDestroy(() => {
    if (refreshInterval) {
      clearInterval(refreshInterval);
    }
  });

  $: if (selectedDevice && selectedTimeRange) {
    fetchTrendData();
  }
</script>

<div class="trend-monitor-page">
  <div class="header">
    <div class="header-left">
      <h1 class="page-title">趋势监测</h1>
      <p class="page-subtitle">实时监控设备振动指标的变化趋势</p>
    </div>
    <div class="header-right">
      <button class="refresh-btn" on:click={fetchTrendData}>
        🔄 刷新数据
      </button>
    </div>
  </div>

  <div class="filter-bar">
    <div class="filter-group">
      <label>选择设备</label>
      <select bind:value={selectedDevice}>
        {#each devices as device}
          <option value={device.id}>{device.name} ({device.code})</option>
        {/each}
      </select>
    </div>

    <div class="filter-group">
      <label>时间范围</label>
      <div class="time-range-buttons">
        {#each timeRanges as range}
          <button
            class="range-btn {selectedTimeRange === range.value ? 'active' : ''}"
            on:click={() => selectedTimeRange = range.value}
          >
            {range.label}
          </button>
        {/each}
      </div>
    </div>

    <div class="filter-group">
      <label>显示指标</label>
      <div class="metric-buttons">
        {#each Object.entries(metricsConfig) as [key, config]}
          <button
            class="metric-btn {selectedMetrics.includes(key) ? 'active' : ''}"
            style="--metric-color: {config.color}"
            on:click={() => toggleMetric(key)}
          >
            {config.label}
          </button>
        {/each}
      </div>
    </div>
  </div>

  {#if loading}
    <div class="loading">加载中...</div>
  {:else}
    {#if warnings.length > 0}
      <div class="warnings-section">
        <div class="warnings-header">
          <span class="warnings-icon">⚠️</span>
          <span class="warnings-title">趋势警告 ({warnings.length})</span>
        </div>
        <div class="warnings-list">
          {#each warnings as warning, i}
            <div class="warning-card" style="border-left-color: {getSeverityStyle(warning.severity).bgColor}">
              <span class="warning-badge" style="background: {getSeverityStyle(warning.severity).bgColor}; color: {getSeverityStyle(warning.severity).color}">
                {getSeverityStyle(warning.severity).label}
              </span>
              <div class="warning-content">
                <span class="warning-message">{warning.message}</span>
                <span class="warning-details">
                  {#if warning.value !== undefined}
                    当前值: {formatValue(warning.value)}, 阈值: {formatValue(warning.threshold)}
                  {/if}
                  {#if warning.rSquared !== undefined}
                    R² = {formatValue(warning.rSquared, 3)}, 斜率 = {formatValue(warning.slope, 5)}
                  {/if}
                </span>
              </div>
            </div>
          {/each}
        </div>
      </div>
    {/if}

    <div class="chart-section">
      <div class="chart-card">
        <div class="card-header">
          <h3 class="card-title">趋势图表</h3>
          <span class="card-subtitle">{getDeviceName(selectedDevice)} · {timeRanges.find(t => t.value === selectedTimeRange)?.label}</span>
        </div>
        <div class="chart-container">
          {#if chartData}
            <Line data={chartData} options={chartData.options || chartOptions} />
          {/if}
        </div>
      </div>
    </div>

    <div class="summary-section">
      <div class="summary-card">
        <div class="card-header">
          <h3 class="card-title">指标概览</h3>
        </div>
        <div class="summary-grid">
          {#each Object.entries(metricsConfig) as [key, config]}
            {#if trendSummary[key]}
              <div class="summary-item" style="border-top-color: {config.color}">
                <div class="summary-header">
                  <span class="summary-label" style="color: {config.color}">{config.label}</span>
                  <span class="summary-badge" style="background: {getStatusStyle(trendSummary[key].status).bgColor}; color: {getStatusStyle(trendSummary[key].status).color}">
                    {getStatusStyle(trendSummary[key].status).label}
                  </span>
                </div>
                <div class="summary-value">
                  {formatValue(trendSummary[key].latest)}
                  <span class="summary-unit">{config.unit}</span>
                </div>
                <div class="summary-stats">
                  <div class="stat-row">
                    <span class="stat-label">均值</span>
                    <span class="stat-val">{formatValue(trendSummary[key].mean)}</span>
                  </div>
                  <div class="stat-row">
                    <span class="stat-label">最小值</span>
                    <span class="stat-val">{formatValue(trendSummary[key].min)}</span>
                  </div>
                  <div class="stat-row">
                    <span class="stat-label">最大值</span>
                    <span class="stat-val">{formatValue(trendSummary[key].max)}</span>
                  </div>
                  <div class="stat-row">
                    <span class="stat-label">R²</span>
                    <span class="stat-val">{formatValue(trendSummary[key].r_squared, 3)}</span>
                  </div>
                </div>
                {#if trendSummary[key].isRising}
                  <div class="trend-alert">
                    <span class="trend-icon">📈</span>
                    <span class="trend-text">检测到上升趋势</span>
                  </div>
                {/if}
                <div class="reference-bars">
                  <div class="bar-container">
                    <div class="bar-label">参考阈值</div>
                    <div class="bar-track">
                      <div class="bar-segment baseline" style="width: {referenceLines[key].baseline / referenceLines[key].alarm * 33.33}%"></div>
                      <div class="bar-segment warning" style="width: {(referenceLines[key].warning - referenceLines[key].baseline) / referenceLines[key].alarm * 33.33}%"></div>
                      <div class="bar-segment alarm" style="width: {(referenceLines[key].alarm - referenceLines[key].warning) / referenceLines[key].alarm * 33.33}%"></div>
                    </div>
                    <div class="bar-markers">
                      <span class="marker">0</span>
                      <span class="marker">{formatValue(referenceLines[key].baseline)}</span>
                      <span class="marker">{formatValue(referenceLines[key].warning)}</span>
                      <span class="marker">{formatValue(referenceLines[key].alarm)}+</span>
                    </div>
                    <div class="current-indicator" style="left: {Math.min(100, trendSummary[key].latest / referenceLines[key].alarm * 100)}%">
                      <div class="indicator-dot" style="background: {config.color}"></div>
                      <span class="indicator-label">{formatValue(trendSummary[key].latest)}</span>
                    </div>
                  </div>
                </div>
              </div>
            {/if}
          {/each}
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  .trend-monitor-page {
    padding: 24px;
    min-height: 100vh;
    background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
  }

  .header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 24px;
    flex-wrap: wrap;
    gap: 16px;
  }

  .header-left {
    flex: 1;
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

  .refresh-btn {
    padding: 10px 20px;
    background: white;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    font-size: 14px;
    cursor: pointer;
    transition: all 0.2s;
  }

  .refresh-btn:hover {
    border-color: #3b82f6;
    color: #3b82f6;
    background: #eff6ff;
  }

  .filter-bar {
    display: flex;
    gap: 24px;
    margin-bottom: 20px;
    flex-wrap: wrap;
    align-items: flex-end;
    background: white;
    padding: 20px;
    border-radius: 12px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  }

  .filter-group {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .filter-group label {
    font-size: 13px;
    font-weight: 500;
    color: #374151;
  }

  .filter-group select {
    padding: 10px 14px;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    font-size: 14px;
    outline: none;
    min-width: 180px;
    transition: border-color 0.2s, box-shadow 0.2s;
  }

  .filter-group select:focus {
    border-color: #3b82f6;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
  }

  .time-range-buttons, .metric-buttons {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }

  .range-btn, .metric-btn {
    padding: 8px 16px;
    border: 1px solid #d1d5db;
    background: white;
    border-radius: 8px;
    font-size: 13px;
    cursor: pointer;
    transition: all 0.2s;
  }

  .range-btn:hover, .metric-btn:hover {
    border-color: #3b82f6;
    color: #3b82f6;
  }

  .range-btn.active {
    background: #3b82f6;
    color: white;
    border-color: #3b82f6;
  }

  .metric-btn.active {
    background: var(--metric-color);
    color: white;
    border-color: var(--metric-color);
  }

  .loading {
    text-align: center;
    padding: 60px;
    color: #6b7280;
    background: white;
    border-radius: 12px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  }

  .warnings-section {
    background: white;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    border-left: 4px solid #f59e0b;
  }

  .warnings-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 16px;
  }

  .warnings-icon {
    font-size: 20px;
  }

  .warnings-title {
    font-size: 16px;
    font-weight: 600;
    color: #1f2937;
  }

  .warnings-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .warning-card {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 12px 16px;
    background: #fefce8;
    border-radius: 8px;
    border-left: 3px solid;
  }

  .warning-badge {
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
    white-space: nowrap;
  }

  .warning-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .warning-message {
    font-size: 14px;
    font-weight: 500;
    color: #374151;
  }

  .warning-details {
    font-size: 12px;
    color: #6b7280;
  }

  .chart-section {
    margin-bottom: 20px;
  }

  .chart-card, .summary-card {
    background: white;
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    flex-wrap: wrap;
    gap: 8px;
  }

  .card-title {
    font-size: 18px;
    font-weight: 600;
    color: #1f2937;
    margin: 0;
  }

  .card-subtitle {
    font-size: 13px;
    color: #6b7280;
  }

  .chart-container {
    height: 400px;
    position: relative;
  }

  .summary-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 16px;
  }

  .summary-item {
    padding: 16px;
    background: #f9fafb;
    border-radius: 10px;
    border-top: 3px solid;
  }

  .summary-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
  }

  .summary-label {
    font-size: 14px;
    font-weight: 600;
  }

  .summary-badge {
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
  }

  .summary-value {
    font-size: 32px;
    font-weight: 800;
    color: #1f2937;
    margin-bottom: 12px;
  }

  .summary-unit {
    font-size: 14px;
    font-weight: 500;
    color: #6b7280;
    margin-left: 4px;
  }

  .summary-stats {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    margin-bottom: 12px;
  }

  .stat-row {
    display: flex;
    justify-content: space-between;
    font-size: 12px;
  }

  .stat-label {
    color: #6b7280;
  }

  .stat-val {
    font-weight: 600;
    color: #374151;
  }

  .trend-alert {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 12px;
    background: #fef2f2;
    border-radius: 6px;
    margin-bottom: 12px;
  }

  .trend-icon {
    font-size: 14px;
  }

  .trend-text {
    font-size: 12px;
    font-weight: 600;
    color: #dc2626;
  }

  .reference-bars {
    padding-top: 12px;
    border-top: 1px solid #e5e7eb;
  }

  .bar-container {
    position: relative;
    padding-top: 20px;
  }

  .bar-label {
    font-size: 11px;
    color: #6b7280;
    margin-bottom: 6px;
  }

  .bar-track {
    display: flex;
    height: 8px;
    border-radius: 4px;
    overflow: hidden;
  }

  .bar-segment {
    height: 100%;
  }

  .bar-segment.baseline {
    background: #10b981;
  }

  .bar-segment.warning {
    background: #f59e0b;
  }

  .bar-segment.alarm {
    background: #ef4444;
  }

  .bar-markers {
    display: flex;
    justify-content: space-between;
    margin-top: 4px;
  }

  .marker {
    font-size: 10px;
    color: #9ca3af;
  }

  .current-indicator {
    position: absolute;
    top: 0;
    transform: translateX(-50%);
    display: flex;
    flex-direction: column;
    align-items: center;
  }

  .indicator-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    border: 2px solid white;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  }

  .indicator-label {
    font-size: 10px;
    font-weight: 600;
    color: #1f2937;
    margin-top: 2px;
    white-space: nowrap;
  }

  @media (max-width: 768px) {
    .filter-bar {
      flex-direction: column;
      align-items: stretch;
    }

    .chart-container {
      height: 300px;
    }

    .summary-value {
      font-size: 24px;
    }
  }
</style>
