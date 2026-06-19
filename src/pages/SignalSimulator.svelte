<script>
  import { onMount } from 'svelte';
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

  let faultType = 'normal';
  let severity = 'mild';
  let sampleRate = 10240;
  let rpm = 3000;
  let snrDb = 30;
  let duration = 1.0;

  let isGenerating = false;
  let generatedSignal = null;
  let signalStats = null;
  let chartData = null;

  const faultTypes = [
    { value: 'normal', label: '正常', icon: '✅', desc: '设备运行正常，无故障特征' },
    { value: 'misalignment', label: '不对中', icon: '⚙️', desc: '轴系不对中故障，2倍频特征明显' },
    { value: 'unbalance', label: '不平衡', icon: '⚖️', desc: '转子不平衡故障，1倍频特征明显' },
    { value: 'bearing_fault', label: '轴承故障', icon: '🔩', desc: '滚动轴承故障，包含冲击特征' },
    { value: 'gear_fault', label: '齿轮故障', icon: '⚙️', desc: '齿轮啮合故障，边频带特征明显' }
  ];

  const severities = [
    { value: 'mild', label: '轻微', color: '#10b981', factor: 1.5 },
    { value: 'moderate', label: '中等', color: '#f59e0b', factor: 3.0 },
    { value: 'severe', label: '严重', color: '#ef4444', factor: 6.0 }
  ];

  const sampleRates = [
    { value: 5120, label: '5120 Hz' },
    { value: 10240, label: '10240 Hz' },
    { value: 20480, label: '20480 Hz' },
    { value: 51200, label: '51200 Hz' }
  ];

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
        title: { display: true, text: '时间 (s)' },
        grid: { color: 'rgba(0, 0, 0, 0.05)' }
      },
      y: {
        title: { display: true, text: '幅值 (mm/s)' },
        grid: { color: 'rgba(0, 0, 0, 0.05)' }
      }
    },
    interaction: {
      intersect: false,
      mode: 'index'
    }
  };

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

  function generateSignal() {
    const fRot = rpm / 60;
    const n = Math.floor(sampleRate * duration);
    const t = [];
    const signal = [];

    function addNoise(s, snr) {
      const signalPower = s.reduce((sum, val) => sum + val * val, 0) / s.length;
      const noisePower = signalPower / Math.pow(10, snr / 10);
      return s.map(val => val + Math.sqrt(noisePower) * (Math.random() * 2 - 1));
    }

    function generateNormal(timeArr) {
      return timeArr.map(t =>
        0.5 * Math.sin(2 * Math.PI * fRot * t)
        + 0.2 * Math.sin(2 * Math.PI * 2 * fRot * t)
        + 0.1 * Math.sin(2 * Math.PI * 3 * fRot * t)
      );
    }

    function generateMisalignment(timeArr, factor) {
      const base = generateNormal(timeArr);
      return base.map((val, i) =>
        val + factor * (
          0.4 * Math.sin(2 * Math.PI * 2 * fRot * timeArr[i] + Math.PI / 4)
          + 0.2 * Math.sin(2 * Math.PI * 4 * fRot * timeArr[i] + Math.PI / 6)
          + 0.15 * Math.sin(2 * Math.PI * fRot * timeArr[i])
        )
      );
    }

    function generateUnbalance(timeArr, factor) {
      const base = generateNormal(timeArr);
      return base.map((val, i) =>
        val + factor * (
          0.6 * Math.sin(2 * Math.PI * fRot * timeArr[i] + Math.PI / 3)
          + 0.1 * Math.sin(2 * Math.PI * 2 * fRot * timeArr[i])
        )
      );
    }

    function generateBearingFault(timeArr, factor, sr) {
      const base = generateNormal(timeArr);
      const bpfo = 3.5 * fRot;
      const bpfi = 5.5 * fRot;
      const bsf = 2.8 * fRot;
      const ftf = 0.4 * fRot;

      const impulses = new Array(timeArr.length).fill(0);
      const impulseInterval = Math.floor(sr / bpfo);
      for (let i = 0; i < timeArr.length; i += impulseInterval) {
        if (i < timeArr.length) {
          const impulseLength = Math.min(20, timeArr.length - i);
          for (let j = 0; j < impulseLength; j++) {
            const decay = Math.exp(-j / 4);
            impulses[i + j] = decay * Math.sin(2 * Math.PI * 2000 * timeArr[i + j]);
          }
        }
      }

      return base.map((val, i) =>
        val + factor * (
          0.3 * Math.sin(2 * Math.PI * bpfo * timeArr[i])
          + 0.2 * Math.sin(2 * Math.PI * bpfi * timeArr[i])
          + 0.15 * Math.sin(2 * Math.PI * bsf * timeArr[i])
          + 0.1 * Math.sin(2 * Math.PI * ftf * timeArr[i])
          + 0.4 * impulses[i]
        )
      );
    }

    function generateGearFault(timeArr, factor) {
      const base = generateNormal(timeArr);
      const numTeeth = 24;
      const gearMeshFreq = numTeeth * fRot;

      let sidebands = new Array(timeArr.length).fill(0);
      for (let k = 1; k <= 3; k++) {
        sidebands = sidebands.map((val, i) =>
          val + 0.1 * Math.sin(2 * Math.PI * (gearMeshFreq - k * fRot) * timeArr[i])
          + 0.1 * Math.sin(2 * Math.PI * (gearMeshFreq + k * fRot) * timeArr[i])
        );
      }

      return base.map((val, i) =>
        val + factor * (
          0.4 * Math.sin(2 * Math.PI * gearMeshFreq * timeArr[i])
          + 0.2 * Math.sin(2 * Math.PI * gearMeshFreq * timeArr[i] + Math.PI / 4)
          * Math.sin(2 * Math.PI * fRot * timeArr[i])
          + 0.15 * Math.sin(2 * Math.PI * 2 * gearMeshFreq * timeArr[i])
          + 0.1 * Math.sin(2 * Math.PI * 3 * gearMeshFreq * timeArr[i])
          + 0.3 * sidebands[i]
        )
      );
    }

    for (let i = 0; i < n; i++) {
      t.push(i / sampleRate);
    }

    const severityFactor = severities.find(s => s.value === severity)?.factor || 1.5;
    let cleanSignal;

    switch (faultType) {
      case 'normal':
        cleanSignal = generateNormal(t);
        break;
      case 'misalignment':
        cleanSignal = generateMisalignment(t, severityFactor);
        break;
      case 'unbalance':
        cleanSignal = generateUnbalance(t, severityFactor);
        break;
      case 'bearing_fault':
        cleanSignal = generateBearingFault(t, severityFactor, sampleRate);
        break;
      case 'gear_fault':
        cleanSignal = generateGearFault(t, severityFactor);
        break;
      default:
        cleanSignal = generateNormal(t);
    }

    const noisySignal = addNoise(cleanSignal, snrDb);

    generatedSignal = {
      time: t,
      signal: noisySignal,
      faultType,
      severity,
      sampleRate,
      rpm,
      snrDb,
      duration
    };

    const rms = Math.sqrt(noisySignal.reduce((sum, val) => sum + val * val, 0) / noisySignal.length);
    const peak = Math.max(...noisySignal.map(Math.abs));
    const mean = noisySignal.reduce((sum, val) => sum + val, 0) / noisySignal.length;
    const variance = noisySignal.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / noisySignal.length;
    const std = Math.sqrt(variance);

    signalStats = {
      rms,
      peak,
      peakToPeak: Math.max(...noisySignal) - Math.min(...noisySignal),
      crestFactor: rms > 0 ? peak / rms : 0,
      mean,
      standardDeviation: std,
      sampleCount: noisySignal.length,
      sampleRate
    };

    const downsample = Math.max(1, Math.floor(n / 500));
    chartData = {
      labels: t.filter((_, i) => i % downsample === 0).map(v => v.toFixed(4)),
      datasets: [
        {
          label: '振动幅值',
          data: noisySignal.filter((_, i) => i % downsample === 0),
          borderColor: '#8b5cf6',
          backgroundColor: 'rgba(139, 92, 246, 0.1)',
          borderWidth: 2,
          fill: true,
          tension: 0.4,
          pointRadius: 0
        }
      ]
    };
  }

  async function generateAndSend() {
    isGenerating = true;
    try {
      generateSignal();

      if (selectedDevice && generatedSignal) {
        await fetch('/api/v1/analysis', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            device_id: selectedDevice,
            data: generatedSignal.signal,
            sample_rate: sampleRate,
            channel: 0,
            perform_hht: false
          })
        });
      }
    } catch (error) {
      console.error('发送信号失败:', error);
    } finally {
      isGenerating = false;
    }
  }

  function formatValue(value, decimals = 4) {
    return value !== undefined && value !== null ? value.toFixed(decimals) : '-';
  }

  $: currentFaultInfo = faultTypes.find(f => f.value === faultType);
  $: currentSeverityInfo = severities.find(s => s.value === severity);

  onMount(() => {
    fetchDevices();
  });
</script>

<div class="simulator-page">
  <div class="header">
    <div>
      <h1 class="page-title">信号模拟器</h1>
      <p class="page-subtitle">生成包含不同故障特征的振动信号用于测试分析</p>
    </div>
  </div>

  <div class="main-content">
    <div class="control-panel">
      <div class="panel-section">
        <h3 class="section-title">📡 目标设备</h3>
        <div class="form-group">
          <label>选择设备</label>
          <select bind:value={selectedDevice}>
            {#each devices as device}
              <option value={device.id}>{device.name} ({device.code})</option>
            {/each}
          </select>
        </div>
      </div>

      <div class="panel-section">
        <h3 class="section-title">🔧 故障类型</h3>
        <div class="fault-grid">
          {#each faultTypes as fault}
            <button
              class="fault-btn {faultType === fault.value ? 'active' : ''}"
              on:click={() => faultType = fault.value}
            >
              <span class="fault-icon">{fault.icon}</span>
              <span class="fault-label">{fault.label}</span>
            </button>
          {/each}
        </div>
        <p class="fault-desc">
          {currentFaultInfo?.desc}
        </p>
      </div>

      <div class="panel-section">
        <h3 class="section-title">📊 严重程度</h3>
        <div class="severity-grid">
          {#each severities as sev}
            <button
              class="severity-btn {severity === sev.value ? 'active' : ''}"
              on:click={() => severity = sev.value}
              style="{severity === sev.value ? `background-color: ${sev.color}; color: white; border-color: ${sev.color}` : ''}"
            >
              {sev.label}
            </button>
          {/each}
        </div>
        <p class="severity-info">
          故障幅值系数: <strong>{currentSeverityInfo?.factor}x</strong>
        </p>
      </div>

      <div class="panel-section">
        <h3 class="section-title">⚙️ 采样参数</h3>
        <div class="params-grid">
          <div class="form-group">
            <label>采样率</label>
            <select bind:value={sampleRate}>
              {#each sampleRates as rate}
                <option value={rate.value}>{rate.label}</option>
              {/each}
            </select>
          </div>
          <div class="form-group">
            <label>采样时长 (秒)</label>
            <input type="number" bind:value={duration} min="0.1" max="10" step="0.1" />
          </div>
          <div class="form-group">
            <label>转速 (RPM)</label>
            <input type="number" bind:value={rpm} min="100" max="10000" step="100" />
          </div>
          <div class="form-group">
            <label>信噪比 (dB)</label>
            <input type="number" bind:value={snrDb} min="0" max="60" step="1" />
          </div>
        </div>
      </div>

      <div class="panel-section">
        <button
          class="generate-btn"
          on:click={generateAndSend}
          disabled={isGenerating}
        >
          {isGenerating ? '生成中...' : '🎯 生成并发送信号'}
        </button>
      </div>
    </div>

    <div class="display-panel">
      {#if generatedSignal}
        <div class="waveform-card">
          <div class="card-header">
            <h3 class="card-title">生成的振动信号</h3>
            <div class="signal-tags">
              <span class="tag tag-fault">
                {faultTypes.find(f => f.value === generatedSignal.faultType)?.label}
              </span>
              <span class="tag tag-severity" style="background-color: {currentSeverityInfo?.color}20; color: {currentSeverityInfo?.color}">
                {currentSeverityInfo?.label}
              </span>
              <span class="tag tag-sr">{generatedSignal.sampleRate} Hz</span>
            </div>
          </div>
          <div class="chart-container">
            {#if chartData}
              <Line data={chartData} options={chartOptions} />
            {/if}
          </div>
        </div>

        {#if signalStats}
          <div class="stats-card">
            <div class="card-header">
              <h3 class="card-title">信号统计量</h3>
            </div>
            <div class="stats-grid">
              <div class="stat-item">
                <span class="stat-label">RMS</span>
                <span class="stat-value">{formatValue(signalStats.rms)}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">峰值</span>
                <span class="stat-value">{formatValue(signalStats.peak)}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">峰峰值</span>
                <span class="stat-value">{formatValue(signalStats.peakToPeak)}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">波峰因数</span>
                <span class="stat-value">{formatValue(signalStats.crestFactor, 3)}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">均值</span>
                <span class="stat-value">{formatValue(signalStats.mean, 5)}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">标准差</span>
                <span class="stat-value">{formatValue(signalStats.standardDeviation)}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">采样点数</span>
                <span class="stat-value">{signalStats.sampleCount}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">转速</span>
                <span class="stat-value">{rpm} RPM</span>
              </div>
            </div>
          </div>
        {/if}
      {:else}
        <div class="placeholder">
          <div class="placeholder-icon">📡</div>
          <h3>尚未生成信号</h3>
          <p>请在左侧配置参数后点击"生成并发送信号"按钮</p>
        </div>
      {/if}
    </div>
  </div>
</div>

<style>
  .simulator-page {
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

  .main-content {
    display: grid;
    grid-template-columns: 380px 1fr;
    gap: 20px;
  }

  .control-panel {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .panel-section {
    background: white;
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  }

  .section-title {
    font-size: 16px;
    font-weight: 600;
    color: #1f2937;
    margin: 0 0 16px 0;
  }

  .form-group {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .form-group label {
    font-size: 13px;
    color: #374151;
    font-weight: 500;
  }

  .form-group input,
  .form-group select {
    padding: 10px 12px;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    font-size: 14px;
    outline: none;
    transition: border-color 0.2s, box-shadow 0.2s;
  }

  .form-group input:focus,
  .form-group select:focus {
    border-color: #8b5cf6;
    box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.1);
  }

  .fault-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(90px, 1fr));
    gap: 8px;
    margin-bottom: 12px;
  }

  .fault-btn {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
    padding: 12px 8px;
    border: 2px solid #e5e7eb;
    background: white;
    border-radius: 10px;
    cursor: pointer;
    transition: all 0.2s;
  }

  .fault-btn:hover {
    border-color: #8b5cf6;
    background: #faf5ff;
  }

  .fault-btn.active {
    border-color: #8b5cf6;
    background: #faf5ff;
  }

  .fault-icon {
    font-size: 24px;
  }

  .fault-label {
    font-size: 12px;
    font-weight: 600;
    color: #374151;
  }

  .fault-desc {
    font-size: 13px;
    color: #6b7280;
    margin: 0;
    padding: 10px;
    background: #f9fafb;
    border-radius: 8px;
    border-left: 3px solid #8b5cf6;
  }

  .severity-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    margin-bottom: 12px;
  }

  .severity-btn {
    padding: 10px;
    border: 2px solid #e5e7eb;
    background: white;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 600;
    color: #374151;
    cursor: pointer;
    transition: all 0.2s;
  }

  .severity-btn:hover:not(.active) {
    border-color: #d1d5db;
    background: #f9fafb;
  }

  .severity-info {
    font-size: 13px;
    color: #6b7280;
    margin: 0;
  }

  .severity-info strong {
    color: #1f2937;
  }

  .params-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }

  .generate-btn {
    width: 100%;
    padding: 14px 20px;
    background: linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%);
    color: white;
    border: none;
    border-radius: 10px;
    font-size: 16px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
    box-shadow: 0 4px 14px rgba(139, 92, 246, 0.4);
  }

  .generate-btn:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(139, 92, 246, 0.5);
  }

  .generate-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .display-panel {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .waveform-card, .stats-card {
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
    gap: 12px;
  }

  .card-title {
    font-size: 18px;
    font-weight: 600;
    color: #1f2937;
    margin: 0;
  }

  .signal-tags {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }

  .tag {
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 500;
  }

  .tag-fault {
    background: #ede9fe;
    color: #7c3aed;
  }

  .tag-sr {
    background: #dbeafe;
    color: #2563eb;
  }

  .chart-container {
    height: 300px;
    position: relative;
  }

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
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
    font-size: 18px;
    font-weight: 700;
    color: #1f2937;
  }

  .placeholder {
    background: white;
    border-radius: 12px;
    padding: 60px 40px;
    text-align: center;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  }

  .placeholder-icon {
    font-size: 64px;
    margin-bottom: 16px;
  }

  .placeholder h3 {
    font-size: 20px;
    color: #1f2937;
    margin: 0 0 8px 0;
  }

  .placeholder p {
    font-size: 14px;
    color: #6b7280;
    margin: 0;
  }

  @media (max-width: 1024px) {
    .main-content {
      grid-template-columns: 1fr;
    }
  }
</style>
