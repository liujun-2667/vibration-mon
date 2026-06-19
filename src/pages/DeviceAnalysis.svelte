<script>
  import { onMount, onDestroy } from 'svelte';
  import { Line } from 'svelte-chartjs';
  import { format } from 'date-fns';
  import { dataApi } from '../api.js';
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

  export let deviceId = 1;

  let device = null;
  let analysisResult = null;
  let loading = true;
  let timeDomainData = { time: [], signal: [] };
  let frequencyData = { freq: [], amplitude: [] };

  let timeChartData = null;
  let freqChartData = null;

  let comparisonMode = false;
  let historicalRecords = [];
  let selectedBaselineId = null;
  let baselineLoading = false;
  let compareChartData = null;
  let topDiffs = [];

  const compareChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: true, position: 'top', labels: { font: { size: 12 } } },
      tooltip: { mode: 'index', intersect: false }
    },
    scales: {
      x: { title: { display: true, text: '频率 (Hz)' }, grid: { color: 'rgba(0, 0, 0, 0.05)' } },
      y: { title: { display: true, text: '幅值' }, grid: { color: 'rgba(0, 0, 0, 0.05)' } }
    },
    interaction: { mode: 'index', intersect: false }
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false
      }
    },
    scales: {
      x: {
        grid: {
          color: 'rgba(0, 0, 0, 0.05)'
        }
      },
      y: {
        grid: {
          color: 'rgba(0, 0, 0, 0.05)'
        }
      }
    },
    interaction: {
      intersect: false,
      mode: 'index'
    }
  };

  function generateMockSignal(duration = 1, sampleRate = 1000) {
    const n = duration * sampleRate;
    const time = [];
    const signal = [];
    const fRot = 50;

    for (let i = 0; i < n; i++) {
      const t = i / sampleRate;
      let s = 0.5 * Math.sin(2 * Math.PI * fRot * t)
        + 0.2 * Math.sin(2 * Math.PI * 2 * fRot * t)
        + 0.1 * Math.sin(2 * Math.PI * 3 * fRot * t);
      s += 0.1 * (Math.random() - 0.5);
      time.push(t.toFixed(4));
      signal.push(s);
    }

    return { time, signal };
  }

  function computeFFT(signal, sampleRate) {
    const n = signal.length;
    const freqs = [];
    const amplitudes = [];
    const nFFT = Math.pow(2, Math.floor(Math.log2(n)));
    const data = signal.slice(0, nFFT);

    for (let k = 0; k < nFFT / 2; k++) {
      let real = 0, imag = 0;
      for (let t = 0; t < nFFT; t++) {
        const angle = -2 * Math.PI * k * t / nFFT;
        real += data[t] * Math.cos(angle);
        imag += data[t] * Math.sin(angle);
      }
      const amplitude = 2 * Math.sqrt(real * real + imag * imag) / nFFT;
      freqs.push((k * sampleRate / nFFT).toFixed(1));
      amplitudes.push(amplitude);
    }

    return { freq: freqs, amplitude: amplitudes };
  }

  function prepareChartData() {
    timeChartData = {
      labels: timeDomainData.time.filter((_, i) => i % 10 === 0),
      datasets: [
        {
          label: '振动幅值',
          data: timeDomainData.signal.filter((_, i) => i % 10 === 0),
          borderColor: '#3b82f6',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          borderWidth: 2,
          fill: true,
          tension: 0.4,
          pointRadius: 0
        }
      ]
    };

    freqChartData = {
      labels: frequencyData.freq,
      datasets: [
        {
          label: '频谱幅值',
          data: frequencyData.amplitude,
          borderColor: '#10b981',
          backgroundColor: 'rgba(16, 185, 129, 0.1)',
          borderWidth: 2,
          fill: true,
          tension: 0.3,
          pointRadius: 0
        }
      ]
    };
  }

  async function loadHistoricalRecords() {
    baselineLoading = true;
    try {
      const res = await dataApi.getVibrationData({ device_id: deviceId, page_size: 50 });
      const items = res?.data?.items || res?.items || [];
      if (items.length > 0) {
        historicalRecords = items.map(r => ({
          id: r.id,
          timestamp: r.timestamp,
          data: Array.isArray(r.data) ? r.data : [],
          sample_rate: r.sample_rate || 1000
        }));
      } else {
        throw new Error('no records');
      }
    } catch (e) {
      historicalRecords = generateMockHistoricalRecords();
    } finally {
      baselineLoading = false;
    }
  }

  function generateMockHistoricalRecords() {
    const records = [];
    const now = Date.now();
    for (let i = 0; i < 6; i++) {
      const ts = now - i * 86400000 * 5;
      const n = 1000;
      const data = [];
      const healthFactor = i === 0 ? 1.0 : 1.0 + i * 0.12;
      for (let j = 0; j < n; j++) {
        const t = j / 1000;
        let s = 0.5 * healthFactor * Math.sin(2 * Math.PI * 50 * t)
          + 0.2 * healthFactor * Math.sin(2 * Math.PI * 100 * t)
          + 0.1 * healthFactor * Math.sin(2 * Math.PI * 150 * t);
        s += 0.08 * (Math.random() - 0.5);
        data.push(s);
      }
      records.push({
        id: 1000 - i,
        timestamp: new Date(ts).toISOString(),
        data,
        sample_rate: 1000
      });
    }
    return records;
  }

  function toggleComparisonMode() {
    comparisonMode = !comparisonMode;
    if (comparisonMode && historicalRecords.length === 0) {
      loadHistoricalRecords();
    }
    if (!comparisonMode) {
      compareChartData = null;
      topDiffs = [];
      selectedBaselineId = null;
    }
  }

  function selectBaseline(recordId) {
    selectedBaselineId = recordId;
    const record = historicalRecords.find(r => r.id === recordId);
    if (!record) return;

    const baselineSpectrum = computeFFT(record.data, record.sample_rate || 1000);
    const currentFreq = frequencyData.freq;
    const currentAmp = frequencyData.amplitude;

    const len = Math.min(baselineSpectrum.amplitude.length, currentAmp.length);

    let maxBase = 0;
    let maxCur = 0;
    for (let i = 0; i < len; i++) {
      if (baselineSpectrum.amplitude[i] > maxBase) maxBase = baselineSpectrum.amplitude[i];
      if (currentAmp[i] > maxCur) maxCur = currentAmp[i];
    }
    const threshold = Math.max(maxBase, maxCur) * 0.05;

    const diffs = [];
    for (let i = 0; i < len; i++) {
      const baseVal = baselineSpectrum.amplitude[i];
      const curVal = currentAmp[i];
      if (baseVal < threshold && curVal < threshold) continue;
      let change;
      if (baseVal >= threshold) {
        change = ((curVal - baseVal) / baseVal) * 100;
      } else {
        change = curVal > 0 ? Infinity : 0;
      }
      diffs.push({
        index: i,
        freq: currentFreq[i],
        baseline: baseVal,
        current: curVal,
        change: change
      });
    }

    diffs.sort((a, b) => {
      const aFin = isFinite(a.change);
      const bFin = isFinite(b.change);
      if (aFin && bFin) return Math.abs(b.change) - Math.abs(a.change);
      if (!aFin && !bFin) return b.current - a.current;
      return aFin ? 1 : -1;
    });

    topDiffs = diffs.slice(0, 5).map(d => ({
      ...d,
      changePct: isFinite(d.change) ? d.change : null,
      isNewPeak: !isFinite(d.change)
    }));

    compareChartData = {
      labels: currentFreq,
      datasets: [
        {
          label: '当前频谱',
          data: currentAmp,
          borderColor: '#3b82f6',
          backgroundColor: 'rgba(59, 130, 246, 0.08)',
          borderWidth: 2,
          fill: true,
          tension: 0.3,
          pointRadius: 0
        },
        {
          label: '基准频谱',
          data: baselineSpectrum.amplitude,
          borderColor: '#f59e0b',
          backgroundColor: 'rgba(245, 158, 11, 0.08)',
          borderWidth: 2,
          borderDash: [6, 4],
          fill: false,
          tension: 0.3,
          pointRadius: 0
        }
      ]
    };
  }

  async function fetchData() {
    loading = true;
    try {
      const deviceRes = await fetch(`/api/v1/devices/${deviceId}`);
      const deviceData = await deviceRes.json();
      device = deviceData.data;

      const analysisRes = await fetch(`/api/v1/analysis/${deviceId}/latest`);
      const analysisData = await analysisRes.json();
      analysisResult = analysisData.data;

      const signalData = generateMockSignal();
      timeDomainData = signalData;
      frequencyData = computeFFT(signalData.signal, 1000);

      if (!analysisResult) {
        analysisResult = {
          time_domain: {
            rms: 1.85,
            peak: 4.62,
            peak_to_peak: 8.87,
            crest_factor: 2.5,
            kurtosis: 3.2,
            skewness: 0.15,
            mean: 0.02,
            variance: 3.42,
            standard_deviation: 1.85
          },
          frequency_domain: {
            dominant_frequency: 50.0,
            dominant_amplitude: 0.85,
            spectral_centroid: 155.0,
            spectral_rolloff: 420.0,
            spectral_spread: 85.0
          },
          health_index: 85,
          status: '良好',
          anomalies: []
        };
      }

      prepareChartData();
    } catch (error) {
      device = { id: deviceId, name: '电机-001', code: 'MOT-001', location: 'A车间-1号线', status: 'online' };
      const signalData = generateMockSignal();
      timeDomainData = signalData;
      frequencyData = computeFFT(signalData.signal, 1000);
      analysisResult = {
        time_domain: {
          rms: 1.85,
          peak: 4.62,
          peak_to_peak: 8.87,
          crest_factor: 2.5,
          kurtosis: 3.2,
          skewness: 0.15,
          mean: 0.02,
          variance: 3.42,
          standard_deviation: 1.85
        },
        frequency_domain: {
          dominant_frequency: 50.0,
          dominant_amplitude: 0.85,
          spectral_centroid: 155.0,
          spectral_rolloff: 420.0,
          spectral_spread: 85.0
        },
        health_index: 85,
        status: '良好',
        anomalies: []
      };
      prepareChartData();
    } finally {
      loading = false;
    }
  }

  function getHealthColor(index) {
    if (index >= 80) return '#10b981';
    if (index >= 60) return '#f59e0b';
    if (index >= 40) return '#f97316';
    return '#ef4444';
  }

  function getStatusColor(status) {
    const colors = {
      '良好': '#10b981',
      '正常': '#3b82f6',
      '注意': '#f59e0b',
      '异常': '#ef4444'
    };
    return colors[status] || '#6b7280';
  }

  function formatValue(value, decimals = 2) {
    return value !== undefined && value !== null ? value.toFixed(decimals) : '-';
  }

  onMount(() => {
    fetchData();
  });
</script>

<div class="analysis-page">
  <div class="header">
    <div class="header-left">
      <button class="back-btn" on:click={() => window.dispatchEvent(new CustomEvent('navigate', { detail: { page: 'dashboard' } }))}>
        ← 返回
      </button>
      <div>
        <h1 class="page-title">{device?.name || '设备分析'}</h1>
        <p class="page-subtitle">{device?.code} · {device?.location}</p>
      </div>
    </div>
    <div class="header-right">
      <span class="device-status" style="background-color: {device?.status === 'online' ? '#10b98120' : '#6b728020'}; color: {device?.status === 'online' ? '#10b981' : '#6b7280'}">
        {device?.status === 'online' ? '在线' : '离线'}
      </span>
    </div>
  </div>

  {#if loading}
    <div class="loading">加载中...</div>
  {:else}
    <div class="health-section">
      <div class="health-card">
        <div class="health-label">健康指数</div>
        <div class="health-index" style="color: {getHealthColor(analysisResult?.health_index)}">
          {analysisResult?.health_index || 0}
        </div>
        <div class="health-status" style="color: {getStatusColor(analysisResult?.status)}">
          {analysisResult?.status || '未知'}
        </div>
      </div>
      {#if analysisResult?.anomalies?.length > 0}
        <div class="anomalies-card">
          <div class="anomalies-title">⚠️ 异常警告</div>
          <ul class="anomalies-list">
            {#each analysisResult.anomalies as anomaly, i}
              <li key={i}>{anomaly}</li>
            {/each}
          </ul>
        </div>
      {/if}
    </div>

    <div class="charts-section">
      <div class="chart-card">
        <div class="card-header">
          <h3 class="card-title">时域波形图</h3>
          <span class="card-subtitle">采样率: 1000 Hz</span>
        </div>
        <div class="chart-container">
          {#if timeChartData}
            <Line data={timeChartData} options={chartOptions} />
          {/if}
        </div>
      </div>

      <div class="chart-card">
        <div class="card-header">
          <h3 class="card-title">频谱图</h3>
          <div class="freq-header-right">
            {#if !comparisonMode}
              <span class="card-subtitle">主导频率: {formatValue(analysisResult?.frequency_domain?.dominant_frequency)} Hz</span>
            {/if}
            <button class="compare-toggle-btn" class:active={comparisonMode} on:click={toggleComparisonMode}>
              {comparisonMode ? '退出对比' : '对比模式'}
            </button>
          </div>
        </div>

        {#if comparisonMode}
          <div class="baseline-selector">
            <label class="baseline-label">选择基准频谱:</label>
            <select class="baseline-select" value={selectedBaselineId} on:change={(e) => selectBaseline(Number(e.target.value))}>
              <option value={null} disabled>请选择历史记录...</option>
              {#if baselineLoading}
                <option value={null} disabled>加载中...</option>
              {:else}
                {#each historicalRecords as record}
                  <option value={record.id}>
                    {format(new Date(record.timestamp), 'yyyy-MM-dd HH:mm')} · 记录 #{record.id}
                  </option>
                {/each}
              {/if}
            </select>
            <span class="baseline-hint">提示: 选择设备投运初期的健康状态频谱作为基准</span>
          </div>
        {/if}

        <div class="chart-container">
          {#if comparisonMode && compareChartData}
            <Line data={compareChartData} options={compareChartOptions} />
          {:else if freqChartData}
            <Line data={freqChartData} options={chartOptions} />
          {/if}
        </div>

        {#if comparisonMode && topDiffs.length > 0}
          <div class="diff-table-wrap">
            <div class="diff-table-title">差异最大的前 5 个频率点</div>
            <table class="diff-table">
              <thead>
                <tr>
                  <th>序号</th>
                  <th>频率值 (Hz)</th>
                  <th>基准幅值</th>
                  <th>当前幅值</th>
                  <th>变化百分比</th>
                </tr>
              </thead>
              <tbody>
                {#each topDiffs as diff, i}
                  <tr>
                    <td>{i + 1}</td>
                    <td>{diff.freq}</td>
                    <td>{formatValue(diff.baseline, 4)}</td>
                    <td>{formatValue(diff.current, 4)}</td>
                    <td class="change-cell" style="color: {diff.isNewPeak ? '#8b5cf6' : (diff.changePct > 0 ? '#ef4444' : (diff.changePct < 0 ? '#10b981' : '#6b7280'))}">
                      {#if diff.isNewPeak}
                        新增峰值
                      {:else}
                        {diff.changePct > 0 ? '+' : ''}{diff.changePct.toFixed(1)}%
                      {/if}
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {/if}
      </div>
    </div>

    <div class="stats-section">
      <div class="stats-card">
        <div class="card-header">
          <h3 class="card-title">时域统计量</h3>
        </div>
        <div class="stats-grid">
          <div class="stat-item">
            <span class="stat-label">RMS (均方根)</span>
            <span class="stat-value">{formatValue(analysisResult?.time_domain?.rms)}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">峰值</span>
            <span class="stat-value">{formatValue(analysisResult?.time_domain?.peak)}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">峰峰值</span>
            <span class="stat-value">{formatValue(analysisResult?.time_domain?.peak_to_peak)}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">波峰因数</span>
            <span class="stat-value">{formatValue(analysisResult?.time_domain?.crest_factor)}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">峭度</span>
            <span class="stat-value">{formatValue(analysisResult?.time_domain?.kurtosis)}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">偏度</span>
            <span class="stat-value">{formatValue(analysisResult?.time_domain?.skewness)}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">均值</span>
            <span class="stat-value">{formatValue(analysisResult?.time_domain?.mean, 4)}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">标准差</span>
            <span class="stat-value">{formatValue(analysisResult?.time_domain?.standard_deviation)}</span>
          </div>
        </div>
      </div>

      <div class="stats-card">
        <div class="card-header">
          <h3 class="card-title">频域统计量</h3>
        </div>
        <div class="stats-grid">
          <div class="stat-item">
            <span class="stat-label">主导频率 (Hz)</span>
            <span class="stat-value">{formatValue(analysisResult?.frequency_domain?.dominant_frequency)}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">主导幅值</span>
            <span class="stat-value">{formatValue(analysisResult?.frequency_domain?.dominant_amplitude)}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">频谱质心 (Hz)</span>
            <span class="stat-value">{formatValue(analysisResult?.frequency_domain?.spectral_centroid)}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">频谱滚降 (Hz)</span>
            <span class="stat-value">{formatValue(analysisResult?.frequency_domain?.spectral_rolloff)}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">频谱展宽</span>
            <span class="stat-value">{formatValue(analysisResult?.frequency_domain?.spectral_spread)}</span>
          </div>
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  .analysis-page {
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
    display: flex;
    align-items: center;
    gap: 16px;
    flex-wrap: wrap;
  }

  .back-btn {
    padding: 8px 16px;
    border: 1px solid #d1d5db;
    background: white;
    border-radius: 8px;
    font-size: 14px;
    cursor: pointer;
    transition: all 0.2s;
  }

  .back-btn:hover {
    border-color: #3b82f6;
    color: #3b82f6;
  }

  .page-title {
    font-size: 28px;
    font-weight: 700;
    color: #1f2937;
    margin: 0 0 4px 0;
  }

  .page-subtitle {
    font-size: 14px;
    color: #6b7280;
    margin: 0;
  }

  .device-status {
    padding: 6px 16px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 500;
  }

  .loading {
    text-align: center;
    padding: 60px;
    color: #6b7280;
    background: white;
    border-radius: 12px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  }

  .health-section {
    display: grid;
    grid-template-columns: 300px 1fr;
    gap: 16px;
    margin-bottom: 24px;
  }

  .health-card {
    background: white;
    border-radius: 12px;
    padding: 24px;
    text-align: center;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  }

  .health-label {
    font-size: 14px;
    color: #6b7280;
    margin-bottom: 8px;
  }

  .health-index {
    font-size: 56px;
    font-weight: 800;
    line-height: 1.1;
    margin-bottom: 8px;
  }

  .health-status {
    font-size: 16px;
    font-weight: 600;
  }

  .anomalies-card {
    background: white;
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    border-left: 4px solid #ef4444;
  }

  .anomalies-title {
    font-size: 16px;
    font-weight: 600;
    color: #1f2937;
    margin-bottom: 12px;
  }

  .anomalies-list {
    margin: 0;
    padding-left: 20px;
  }

  .anomalies-list li {
    color: #ef4444;
    font-size: 14px;
    margin-bottom: 6px;
  }

  .charts-section {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
    gap: 16px;
    margin-bottom: 24px;
  }

  .chart-card, .stats-card {
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
    height: 300px;
    position: relative;
  }

  .stats-section {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
    gap: 16px;
  }

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 12px;
  }

  .stat-item {
    display: flex;
    flex-direction: column;
    padding: 12px;
    background: #f9fafb;
    border-radius: 8px;
    transition: background 0.2s;
  }

  .stat-item:hover {
    background: #f3f4f6;
  }

  .stat-label {
    font-size: 12px;
    color: #6b7280;
    margin-bottom: 4px;
  }

  .stat-value {
    font-size: 20px;
    font-weight: 700;
    color: #1f2937;
  }

  .freq-header-right {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
  }

  .compare-toggle-btn {
    padding: 6px 14px;
    border: 1px solid #d1d5db;
    background: white;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 500;
    color: #374151;
    cursor: pointer;
    transition: all 0.2s;
  }

  .compare-toggle-btn:hover {
    border-color: #3b82f6;
    color: #3b82f6;
  }

  .compare-toggle-btn.active {
    background: #3b82f6;
    border-color: #3b82f6;
    color: white;
  }

  .baseline-selector {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
    padding: 12px;
    background: #f0f7ff;
    border-radius: 8px;
    margin-bottom: 12px;
    border: 1px solid #bfdbfe;
  }

  .baseline-label {
    font-size: 13px;
    font-weight: 600;
    color: #1f2937;
    white-space: nowrap;
  }

  .baseline-select {
    padding: 6px 10px;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    font-size: 13px;
    background: white;
    min-width: 260px;
    cursor: pointer;
  }

  .baseline-hint {
    font-size: 12px;
    color: #6b7280;
    flex: 1;
    min-width: 180px;
  }

  .diff-table-wrap {
    margin-top: 16px;
    border-top: 1px dashed #e5e7eb;
    padding-top: 14px;
  }

  .diff-table-title {
    font-size: 14px;
    font-weight: 600;
    color: #1f2937;
    margin-bottom: 10px;
  }

  .diff-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }

  .diff-table th,
  .diff-table td {
    padding: 8px 10px;
    text-align: left;
    border-bottom: 1px solid #f3f4f6;
  }

  .diff-table th {
    background: #f9fafb;
    color: #6b7280;
    font-weight: 600;
    font-size: 12px;
  }

  .diff-table tbody tr:hover {
    background: #f9fafb;
  }

  .change-cell {
    font-weight: 700;
  }

  @media (max-width: 768px) {
    .health-section {
      grid-template-columns: 1fr;
    }

    .charts-section {
      grid-template-columns: 1fr;
    }

    .stats-section {
      grid-template-columns: 1fr;
    }
  }
</style>
