<script>
  import { onMount, onDestroy } from 'svelte';
  import { format, parseISO } from 'date-fns';
  import { diagnosisApi } from '../api.js';

  export let taskId;

  let loading = true;
  let generatingReport = false;
  let task = null;
  let report = null;
  let showReport = false;
  let errorMessage = '';
  let refreshInterval = null;

  const STATUS_COLORS = {
    pending: '#f59e0b',
    completed: '#10b981',
    failed: '#ef4444'
  };

  const STATUS_LABELS = {
    pending: '待分析',
    completed: '已完成',
    failed: '失败'
  };

  const SEVERITY_COLORS = {
    low: '#3b82f6',
    medium: '#f59e0b',
    high: '#ef4444',
    critical: '#dc2626'
  };

  const SEVERITY_LABELS = {
    low: '低',
    medium: '中',
    high: '高',
    critical: '严重'
  };

  const URGENCY_LABELS = {
    immediate: '立即',
    planned: '计划内',
    observe: '观察'
  };

  const URGENCY_COLORS = {
    immediate: '#dc2626',
    planned: '#f59e0b',
    observe: '#3b82f6'
  };

  function formatDateTime(isoString) {
    if (!isoString) return '-';
    return format(parseISO(isoString), 'yyyy-MM-dd HH:mm:ss');
  }

  function formatTimeRange(start, end) {
    if (!start || !end) return '-';
    return `${format(parseISO(start), 'yyyy-MM-dd HH:mm')} ~ ${format(parseISO(end), 'yyyy-MM-dd HH:mm')}`;
  }

  function getConfidenceColor(confidence) {
    if (confidence >= 70) return '#dc2626';
    if (confidence >= 50) return '#f59e0b';
    if (confidence >= 30) return '#3b82f6';
    return '#6b7280';
  }

  async function loadTask() {
    try {
      const response = await diagnosisApi.getTask(taskId);
      if (response.success && response.data) {
        task = response.data;
        if (task.status === 'pending') {
          setTimeout(loadTask, 3000);
        }
      }
    } catch (error) {
      console.error('加载诊断任务失败:', error);
      errorMessage = '加载任务详情失败';
    } finally {
      loading = false;
    }
  }

  async function generateReport() {
    generatingReport = true;
    errorMessage = '';
    try {
      const response = await diagnosisApi.getReport(taskId);
      if (response.success && response.data) {
        report = response.data;
        showReport = true;
      } else {
        errorMessage = response.message || '生成报告失败';
      }
    } catch (error) {
      errorMessage = error.message || '生成报告失败';
    } finally {
      generatingReport = false;
    }
  }

  function downloadReport() {
    const url = diagnosisApi.downloadReport(taskId);
    const link = document.createElement('a');
    link.href = url;
    link.download = `diagnosis_report_${taskId}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  function goBack() {
    const event = new CustomEvent('navigate', {
      detail: { page: 'diagnosis' }
    });
    window.dispatchEvent(event);
  }

  function exportReportAsJSON() {
    if (!report) return;
    const dataStr = JSON.stringify(report, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `diagnosis_report_${taskId}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  onMount(() => {
    loadTask();
    refreshInterval = setInterval(() => {
      if (task && task.status === 'pending') {
        loadTask();
      }
    }, 5000);
  });

  onDestroy(() => {
    if (refreshInterval) {
      clearInterval(refreshInterval);
    }
  });
</script>

<div class="diagnosis-detail">
  <div class="page-header">
    <div class="header-left">
      <button class="back-btn" on:click={goBack}>
        ← 返回列表
      </button>
      <h2>诊断任务详情</h2>
    </div>
    {#if task && task.status === 'completed'}
      <button class="btn-primary" on:click={generateReport} disabled={generatingReport}>
        {#if generatingReport}
          <span class="spinner small"></span>
          生成中...
        {:else}
          <span class="btn-icon">📄</span>
          生成诊断报告
        {/if}
      </button>
    {/if}
  </div>

  {#if loading}
    <div class="loading-state">
      <div class="spinner"></div>
      <p>加载中...</p>
    </div>
  {:else if !task}
    <div class="error-state">
      <div class="error-icon">❌</div>
      <h3>任务不存在</h3>
      <p>{errorMessage || '无法找到该诊断任务'}</p>
      <button class="btn-primary" on:click={goBack}>返回列表</button>
    </div>
  {:else}
    <div class="detail-content">
      <div class="info-card">
        <div class="card-header">
          <h3>基本信息</h3>
          <span
            class="status-badge"
            style="background: {STATUS_COLORS[task.status]}20; color: {STATUS_COLORS[task.status]}"
          >
            {STATUS_LABELS[task.status]}
          </span>
        </div>
        <div class="info-grid">
          <div class="info-item">
            <span class="label">任务ID</span>
            <span class="value">#{task.id}</span>
          </div>
          <div class="info-item">
            <span class="label">设备名称</span>
            <span class="value">{task.device_name || `设备-${task.device_id}`}</span>
          </div>
          <div class="info-item">
            <span class="label">时间范围</span>
            <span class="value">{formatTimeRange(task.start_time, task.end_time)}</span>
          </div>
          <div class="info-item">
            <span class="label">创建时间</span>
            <span class="value">{formatDateTime(task.created_at)}</span>
          </div>
          {#if task.completed_at}
            <div class="info-item">
              <span class="label">完成时间</span>
              <span class="value">{formatDateTime(task.completed_at)}</span>
            </div>
          {/if}
        </div>
      </div>

      {#if task.status === 'pending'}
        <div class="pending-card">
          <div class="spinner"></div>
          <h3>正在分析中...</h3>
          <p>系统正在提取振动特征并进行故障模式匹配，请稍候</p>
        </div>
      {:else if task.status === 'failed'}
        <div class="error-card">
          <div class="error-icon">❌</div>
          <h3>诊断失败</h3>
          <p>诊断过程中出现错误，请检查数据是否存在后重试</p>
        </div>
      {:else if task.feature_snapshot}
        <div class="feature-card">
          <div class="card-header">
            <h3>📊 特征快照</h3>
            <span class="data-count">基于 {task.feature_snapshot.data_points_count} 条数据分析</span>
          </div>

          <div class="feature-main-grid">
            <div class="feature-main-item highlight">
              <div class="feature-icon">📈</div>
              <div class="feature-info">
                <span class="feature-label">RMS趋势斜率</span>
                <span class="feature-value large">{task.feature_snapshot.rms_trend_slope.toFixed(4)}</span>
                <span class="feature-desc">
                  {task.feature_snapshot.rms_trend_slope > 0.01 ? '呈明显上升趋势' :
                   task.feature_snapshot.rms_trend_slope < -0.01 ? '呈明显下降趋势' : '相对平稳'}
                </span>
              </div>
            </div>

            <div class="feature-main-item highlight">
              <div class="feature-icon">📊</div>
              <div class="feature-info">
                <span class="feature-label">峭度均值</span>
                <span class="feature-value large">{task.feature_snapshot.kurtosis_mean.toFixed(2)}</span>
                <span class="feature-desc">
                  {task.feature_snapshot.kurtosis_mean > 4.5 ? '偏高，可能存在冲击' :
                   task.feature_snapshot.kurtosis_mean < 2.5 ? '偏低，信号平稳' : '处于正常范围'}
                </span>
              </div>
            </div>

            <div class="feature-main-item highlight">
              <div class="feature-icon">🔄</div>
              <div class="feature-info">
                <span class="feature-label">主频偏移量</span>
                <span class="feature-value large">{task.feature_snapshot.dominant_frequency_offset.toFixed(2)} Hz</span>
                <span class="feature-desc">
                  {task.feature_snapshot.dominant_frequency_offset > 3 ? '偏移较大，频率不稳定' :
                   task.feature_snapshot.dominant_frequency_offset < 1 ? '偏移很小，频率稳定' : '有一定偏移'}
                </span>
              </div>
            </div>

            <div class="feature-main-item highlight">
              <div class="feature-icon">🎵</div>
              <div class="feature-info">
                <span class="feature-label">谐波比</span>
                <span class="feature-value large">{task.feature_snapshot.harmonic_ratio.toFixed(2)}</span>
                <span class="feature-desc">
                  {task.feature_snapshot.harmonic_ratio > 0.7 ? '谐波丰富，可能存在故障' :
                   task.feature_snapshot.harmonic_ratio < 0.3 ? '谐波较少' : '存在一定谐波'}
                </span>
              </div>
            </div>
          </div>

          <div class="feature-secondary-grid">
            <div class="feature-secondary-item">
              <span class="label">峰值</span>
              <span class="value">{task.feature_snapshot.peak_value.toFixed(2)} mm/s</span>
            </div>
            <div class="feature-secondary-item">
              <span class="label">波峰因数</span>
              <span class="value">{task.feature_snapshot.crest_factor.toFixed(2)}</span>
            </div>
            <div class="feature-secondary-item">
              <span class="label">频谱质心</span>
              <span class="value">{task.feature_snapshot.spectral_centroid.toFixed(1)} Hz</span>
            </div>
          </div>
        </div>

        {#if task.match_results && task.match_results.length > 0}
          <div class="match-card">
            <div class="card-header">
              <h3>🎯 故障模式匹配结果</h3>
              <span class="match-count">匹配到 {task.match_results.length} 种故障模式</span>
            </div>

            <div class="match-list">
              {#each task.match_results as result, index}
                <div class="match-item" class:top={index === 0}>
                  <div class="match-rank">#{index + 1}</div>
                  <div class="match-content">
                    <div class="match-header">
                      <h4>{result.fault_mode_name}</h4>
                      <div class="match-meta">
                        <span
                          class="severity-badge"
                          style="background: {SEVERITY_COLORS[result.severity_level]}20; color: {SEVERITY_COLORS[result.severity_level]}"
                        >
                          {SEVERITY_LABELS[result.severity_level]}
                        </span>
                        <div class="confidence-bar">
                          <div class="confidence-fill" style="width: {result.confidence}%; background: {getConfidenceColor(result.confidence)}"></div>
                          <span class="confidence-text" style="color: {getConfidenceColor(result.confidence)}">
                            {result.confidence}%
                          </span>
                        </div>
                      </div>
                    </div>

                    <div class="frequency-feature">
                      <span class="label">关键频率特征:</span>
                      <span class="value">{result.key_frequency_features}</span>
                    </div>

                    <div class="evidence-section">
                      <span class="evidence-label">关键证据:</span>
                      <ul class="evidence-list">
                        {#each result.evidence as item}
                          <li>✓ {item}</li>
                        {/each}
                      </ul>
                    </div>
                  </div>
                </div>
              {/each}
            </div>
          </div>
        {:else}
          <div class="no-match-card">
            <div class="no-match-icon">✅</div>
            <h3>未匹配到明显故障模式</h3>
            <p>当前特征数据未发现明显的故障模式特征，建议继续观察</p>
          </div>
        {/if}
      {/if}
    </div>
  {/if}

  {#if showReport && report}
    <div class="modal-overlay" on:click={() => showReport = false}>
      <div class="modal-content large" on:click|stopPropagation>
        <div class="modal-header">
          <h3>📄 诊断报告</h3>
          <button class="close-btn" on:click={() => showReport = false}>×</button>
        </div>

        <div class="modal-body report-body">
          <div class="report-section">
            <h4>设备信息</h4>
            <div class="report-info-grid">
              <div class="report-info-item">
                <span class="label">设备名称</span>
                <span class="value">{report.device_info.name || '-'}</span>
              </div>
              <div class="report-info-item">
                <span class="label">设备编码</span>
                <span class="value">{report.device_info.code || '-'}</span>
              </div>
              <div class="report-info-item">
                <span class="label">安装位置</span>
                <span class="value">{report.device_info.location || '-'}</span>
              </div>
              <div class="report-info-item">
                <span class="label">诊断时间</span>
                <span class="value">{formatDateTime(report.generated_at)}</span>
              </div>
            </div>
          </div>

          <div class="report-section">
            <h4>特征快照摘要</h4>
            <div class="report-feature-grid">
              <div class="report-feature-item">
                <span class="label">RMS趋势斜率</span>
                <span class="value">{report.feature_snapshot.rms_trend_slope.toFixed(4)}</span>
              </div>
              <div class="report-feature-item">
                <span class="label">峭度均值</span>
                <span class="value">{report.feature_snapshot.kurtosis_mean.toFixed(2)}</span>
              </div>
              <div class="report-feature-item">
                <span class="label">主频偏移</span>
                <span class="value">{report.feature_snapshot.dominant_frequency_offset.toFixed(2)} Hz</span>
              </div>
              <div class="report-feature-item">
                <span class="label">谐波比</span>
                <span class="value">{report.feature_snapshot.harmonic_ratio.toFixed(2)}</span>
              </div>
            </div>
          </div>

          {#if report.fault_match_results && report.fault_match_results.length > 0}
            <div class="report-section">
              <h4>故障匹配结果</h4>
              <div class="report-match-list">
                {#each report.fault_match_results as result, index}
                  <div class="report-match-item">
                    <div class="match-header">
                      <span class="match-rank">#{index + 1}</span>
                      <span class="match-name">{result.fault_mode_name}</span>
                      <span class="match-confidence" style="color: {getConfidenceColor(result.confidence)}">
                        {result.confidence}%
                      </span>
                    </div>
                  </div>
                {/each}
              </div>
            </div>
          {/if}

          <div class="report-section">
            <h4>🛠️ 维护建议</h4>
            <div class="suggestion-list">
              {#each report.maintenance_suggestions as suggestion, index}
                <div class="suggestion-item">
                  <div class="suggestion-header">
                    <span class="suggestion-action">{suggestion.action}</span>
                    <span
                      class="urgency-badge"
                      style="background: {URGENCY_COLORS[suggestion.urgency]}20; color: {URGENCY_COLORS[suggestion.urgency]}"
                    >
                      {URGENCY_LABELS[suggestion.urgency]}
                    </span>
                  </div>
                  <p class="suggestion-impact">{suggestion.expected_impact}</p>
                </div>
              {/each}
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn-secondary" on:click={() => showReport = false}>关闭</button>
          <button class="btn-primary" on:click={exportReportAsJSON}>
            <span class="btn-icon">⬇️</span>
            导出JSON
          </button>
          <button class="btn-primary" on:click={downloadReport}>
            <span class="btn-icon">📥</span>
            下载报告
          </button>
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  .diagnosis-detail {
    padding: var(--spacing-6);
    min-height: calc(100vh - var(--header-height));
  }

  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--spacing-6);
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: var(--spacing-4);
  }

  .back-btn {
    background: var(--color-gray-100);
    border: none;
    padding: var(--spacing-2) var(--spacing-4);
    border-radius: var(--radius-md);
    color: var(--color-gray-600);
    cursor: pointer;
    font-size: var(--font-size-sm);
    transition: all var(--transition-fast);
  }

  .back-btn:hover {
    background: var(--color-gray-200);
    color: var(--color-gray-800);
  }

  .header-left h2 {
    margin: 0;
    font-size: var(--font-size-2xl);
    color: var(--color-gray-900);
  }

  .loading-state,
  .pending-card,
  .error-state {
    text-align: center;
    padding: var(--spacing-12) var(--spacing-6);
    background: var(--color-white);
    border-radius: var(--radius-lg);
    border: var(--border-width) solid var(--color-gray-200);
  }

  .pending-card h3,
  .error-state h3 {
    margin: var(--spacing-4) 0 var(--spacing-2);
    color: var(--color-gray-900);
  }

  .pending-card p,
  .error-state p {
    margin: 0;
    color: var(--color-gray-500);
  }

  .error-card {
    text-align: center;
    padding: var(--spacing-8);
    background: var(--color-danger-lighter);
    border-radius: var(--radius-lg);
    border: var(--border-width) solid var(--color-danger-light);
  }

  .error-icon {
    font-size: 48px;
    margin-bottom: var(--spacing-4);
  }

  .spinner {
    width: 32px;
    height: 32px;
    border: 3px solid var(--color-gray-200);
    border-top-color: var(--color-primary);
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin: 0 auto var(--spacing-3);
  }

  .spinner.small {
    width: 16px;
    height: 16px;
    display: inline-block;
    margin: 0 var(--spacing-2) 0 0;
    vertical-align: middle;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .detail-content {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-6);
  }

  .info-card,
  .feature-card,
  .match-card,
  .no-match-card,
  .error-card {
    background: var(--color-white);
    border-radius: var(--radius-lg);
    border: var(--border-width) solid var(--color-gray-200);
    box-shadow: var(--shadow-sm);
    overflow: hidden;
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--spacing-5);
    border-bottom: var(--border-width) solid var(--color-gray-100);
  }

  .card-header h3 {
    margin: 0;
    font-size: var(--font-size-lg);
    color: var(--color-gray-900);
    font-weight: 600;
  }

  .status-badge {
    padding: 6px var(--spacing-3);
    border-radius: var(--radius-full);
    font-size: var(--font-size-xs);
    font-weight: 500;
  }

  .data-count,
  .match-count {
    font-size: var(--font-size-sm);
    color: var(--color-gray-500);
  }

  .info-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: var(--spacing-4);
    padding: var(--spacing-5);
  }

  .info-item {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .info-item .label {
    font-size: var(--font-size-xs);
    color: var(--color-gray-500);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .info-item .value {
    font-size: var(--font-size-base);
    font-weight: 500;
    color: var(--color-gray-900);
  }

  .feature-main-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: var(--spacing-4);
    padding: var(--spacing-5);
  }

  .feature-main-item {
    display: flex;
    gap: var(--spacing-4);
    padding: var(--spacing-4);
    background: var(--color-gray-50);
    border-radius: var(--radius-md);
  }

  .feature-main-item.highlight {
    background: linear-gradient(135deg, var(--color-primary-lighter) 0%, var(--color-primary-light) 100%);
  }

  .feature-icon {
    font-size: var(--font-size-3xl);
  }

  .feature-info {
    display: flex;
    flex-direction: column;
    gap: 2px;
    flex: 1;
  }

  .feature-label {
    font-size: var(--font-size-xs);
    color: var(--color-gray-600);
  }

  .feature-value {
    font-size: var(--font-size-xl);
    font-weight: 700;
    color: var(--color-gray-900);
  }

  .feature-value.large {
    font-size: var(--font-size-2xl);
  }

  .feature-desc {
    font-size: var(--font-size-xs);
    color: var(--color-gray-500);
    margin-top: 2px;
  }

  .feature-secondary-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: var(--spacing-4);
    padding: 0 var(--spacing-5) var(--spacing-5);
  }

  .feature-secondary-item {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: var(--spacing-3);
    background: var(--color-gray-50);
    border-radius: var(--radius-md);
  }

  .feature-secondary-item .label {
    font-size: var(--font-size-xs);
    color: var(--color-gray-500);
  }

  .feature-secondary-item .value {
    font-size: var(--font-size-base);
    font-weight: 600;
    color: var(--color-gray-900);
  }

  .match-list {
    padding: var(--spacing-5);
    display: flex;
    flex-direction: column;
    gap: var(--spacing-4);
  }

  .match-item {
    display: flex;
    gap: var(--spacing-4);
    padding: var(--spacing-4);
    background: var(--color-gray-50);
    border-radius: var(--radius-md);
    border-left: 4px solid var(--color-gray-300);
    transition: all var(--transition-fast);
  }

  .match-item.top {
    border-left-color: var(--color-danger);
    background: linear-gradient(90deg, var(--color-danger-lighter) 0%, var(--color-gray-50) 100%);
  }

  .match-rank {
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--color-primary);
    color: white;
    border-radius: 50%;
    font-weight: 700;
    font-size: var(--font-size-sm);
    flex-shrink: 0;
  }

  .match-item.top .match-rank {
    background: var(--color-danger);
  }

  .match-content {
    flex: 1;
  }

  .match-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: var(--spacing-3);
  }

  .match-header h4 {
    margin: 0;
    font-size: var(--font-size-lg);
    color: var(--color-gray-900);
  }

  .match-meta {
    display: flex;
    align-items: center;
    gap: var(--spacing-3);
  }

  .severity-badge {
    padding: 4px var(--spacing-2);
    border-radius: var(--radius-full);
    font-size: var(--font-size-xs);
    font-weight: 500;
  }

  .confidence-bar {
    display: flex;
    align-items: center;
    gap: var(--spacing-2);
    min-width: 120px;
  }

  .confidence-fill {
    height: 6px;
    border-radius: var(--radius-full);
    min-width: 30px;
    transition: width 0.5s ease;
  }

  .confidence-text {
    font-weight: 700;
    font-size: var(--font-size-sm);
    min-width: 50px;
  }

  .frequency-feature {
    display: flex;
    gap: var(--spacing-2);
    margin-bottom: var(--spacing-3);
    font-size: var(--font-size-sm);
  }

  .frequency-feature .label {
    color: var(--color-gray-500);
    flex-shrink: 0;
  }

  .frequency-feature .value {
    color: var(--color-gray-700);
  }

  .evidence-label {
    display: block;
    font-size: var(--font-size-sm);
    color: var(--color-gray-600);
    margin-bottom: var(--spacing-2);
    font-weight: 500;
  }

  .evidence-list {
    margin: 0;
    padding-left: var(--spacing-2);
    list-style: none;
  }

  .evidence-list li {
    font-size: var(--font-size-sm);
    color: var(--color-gray-700);
    padding: 4px 0;
  }

  .no-match-card {
    text-align: center;
    padding: var(--spacing-12);
  }

  .no-match-icon {
    font-size: 64px;
    margin-bottom: var(--spacing-4);
  }

  .no-match-card h3 {
    margin: 0 0 var(--spacing-2) 0;
    color: var(--color-gray-900);
  }

  .no-match-card p {
    margin: 0;
    color: var(--color-gray-500);
  }

  .modal-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
  }

  .modal-content {
    background: var(--color-white);
    border-radius: var(--radius-xl);
    width: 100%;
    max-width: 600px;
    max-height: 90vh;
    overflow-y: auto;
    box-shadow: var(--shadow-2xl);
  }

  .modal-content.large {
    max-width: 800px;
  }

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--spacing-5);
    border-bottom: var(--border-width) solid var(--color-gray-200);
  }

  .modal-header h3 {
    margin: 0;
    font-size: var(--font-size-xl);
    color: var(--color-gray-900);
  }

  .close-btn {
    background: none;
    border: none;
    font-size: var(--font-size-2xl);
    color: var(--color-gray-400);
    cursor: pointer;
    line-height: 1;
    padding: 0;
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: var(--radius-sm);
    transition: all var(--transition-fast);
  }

  .close-btn:hover {
    background: var(--color-gray-100);
    color: var(--color-gray-600);
  }

  .modal-body {
    padding: var(--spacing-5);
  }

  .report-body {
    max-height: 60vh;
    overflow-y: auto;
  }

  .report-section {
    margin-bottom: var(--spacing-6);
  }

  .report-section:last-child {
    margin-bottom: 0;
  }

  .report-section h4 {
    margin: 0 0 var(--spacing-3) 0;
    font-size: var(--font-size-base);
    color: var(--color-gray-900);
    font-weight: 600;
    padding-bottom: var(--spacing-2);
    border-bottom: var(--border-width) solid var(--color-gray-200);
  }

  .report-info-grid,
  .report-feature-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: var(--spacing-3);
  }

  .report-info-item,
  .report-feature-item {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .report-info-item .label,
  .report-feature-item .label {
    font-size: var(--font-size-xs);
    color: var(--color-gray-500);
  }

  .report-info-item .value,
  .report-feature-item .value {
    font-size: var(--font-size-sm);
    font-weight: 500;
    color: var(--color-gray-900);
  }

  .report-match-list {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-2);
  }

  .report-match-item {
    padding: var(--spacing-3);
    background: var(--color-gray-50);
    border-radius: var(--radius-md);
  }

  .report-match-item .match-header {
    display: flex;
    align-items: center;
    gap: var(--spacing-3);
  }

  .report-match-item .match-rank {
    width: 24px;
    height: 24px;
    font-size: var(--font-size-xs);
  }

  .report-match-item .match-name {
    flex: 1;
    font-weight: 500;
    color: var(--color-gray-900);
  }

  .report-match-item .match-confidence {
    font-weight: 700;
  }

  .suggestion-list {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-3);
  }

  .suggestion-item {
    padding: var(--spacing-4);
    background: var(--color-gray-50);
    border-radius: var(--radius-md);
    border-left: 4px solid var(--color-primary);
  }

  .suggestion-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--spacing-2);
  }

  .suggestion-action {
    font-weight: 600;
    color: var(--color-gray-900);
  }

  .urgency-badge {
    padding: 4px var(--spacing-2);
    border-radius: var(--radius-full);
    font-size: var(--font-size-xs);
    font-weight: 500;
  }

  .suggestion-impact {
    margin: 0;
    font-size: var(--font-size-sm);
    color: var(--color-gray-600);
    line-height: 1.5;
  }

  .modal-footer {
    display: flex;
    justify-content: flex-end;
    gap: var(--spacing-3);
    padding: var(--spacing-5);
    border-top: var(--border-width) solid var(--color-gray-200);
  }

  .btn-primary,
  .btn-secondary {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: var(--spacing-2);
    padding: var(--spacing-3) var(--spacing-5);
    border: none;
    border-radius: var(--radius-md);
    font-size: var(--font-size-base);
    font-weight: 500;
    cursor: pointer;
    transition: all var(--transition-fast);
  }

  .btn-primary {
    background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-dark) 100%);
    color: white;
    box-shadow: var(--shadow-primary);
  }

  .btn-primary:hover:not(:disabled) {
    transform: translateY(-1px);
    box-shadow: var(--shadow-primary-lg);
  }

  .btn-primary:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .btn-secondary {
    background: var(--color-gray-100);
    color: var(--color-gray-700);
  }

  .btn-secondary:hover {
    background: var(--color-gray-200);
  }

  .btn-icon {
    font-size: var(--font-size-lg);
  }
</style>
