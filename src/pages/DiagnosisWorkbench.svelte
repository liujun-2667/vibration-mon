<script>
  import { onMount, onDestroy } from 'svelte';
  import { format, parseISO } from 'date-fns';
  import { diagnosisApi, devicesApi } from '../api.js';

  let loading = true;
  let creating = false;
  let tasks = [];
  let devices = [];
  let showCreateModal = false;
  let selectedDevice = null;
  let startTime = '';
  let endTime = '';
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

  function formatDateTime(isoString) {
    if (!isoString) return '-';
    return format(parseISO(isoString), 'yyyy-MM-dd HH:mm:ss');
  }

  function formatTimeRange(start, end) {
    if (!start || !end) return '-';
    return `${format(parseISO(start), 'MM-dd HH:mm')} ~ ${format(parseISO(end), 'MM-dd HH:mm')}`;
  }

  async function loadDevices() {
    try {
      const response = await devicesApi.getDevices({ page_size: 100 });
      if (response.success && response.data) {
        devices = response.data.items || response.data;
      }
    } catch (error) {
      console.error('加载设备列表失败:', error);
    }
  }

  async function loadTasks() {
    try {
      const response = await diagnosisApi.getTasks({ page_size: 50 });
      if (response.success && response.data) {
        tasks = response.data.items || response.data;
      }
    } catch (error) {
      console.error('加载诊断任务失败:', error);
    } finally {
      loading = false;
    }
  }

  function openCreateModal() {
    errorMessage = '';
    const now = new Date();
    const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);
    startTime = yesterday.toISOString().slice(0, 16);
    endTime = now.toISOString().slice(0, 16);
    showCreateModal = true;
  }

  function closeCreateModal() {
    showCreateModal = false;
    errorMessage = '';
  }

  async function createTask() {
    if (!selectedDevice) {
      errorMessage = '请选择目标设备';
      return;
    }
    if (!startTime || !endTime) {
      errorMessage = '请选择时间范围';
      return;
    }
    if (new Date(startTime) >= new Date(endTime)) {
      errorMessage = '开始时间必须早于结束时间';
      return;
    }

    creating = true;
    errorMessage = '';

    try {
      const response = await diagnosisApi.createTask({
        device_id: selectedDevice,
        start_time: new Date(startTime).toISOString(),
        end_time: new Date(endTime).toISOString()
      });

      if (response.success) {
        closeCreateModal();
        loadTasks();
      } else {
        errorMessage = response.message || '创建任务失败';
      }
    } catch (error) {
      errorMessage = error.message || '创建任务失败';
    } finally {
      creating = false;
    }
  }

  function goToDetail(task) {
    if (task.status !== 'pending') {
      const event = new CustomEvent('navigate', {
        detail: { page: 'diagnosis', taskId: task.id }
      });
      window.dispatchEvent(event);
    }
  }

  async function runTask(task) {
    try {
      await diagnosisApi.runTask(task.id);
      loadTasks();
    } catch (error) {
      console.error('运行诊断任务失败:', error);
    }
  }

  onMount(() => {
    loadDevices();
    loadTasks();
    refreshInterval = setInterval(() => {
      const pendingTasks = tasks.filter(t => t.status === 'pending');
      if (pendingTasks.length > 0) {
        loadTasks();
      }
    }, 3000);
  });

  onDestroy(() => {
    if (refreshInterval) {
      clearInterval(refreshInterval);
    }
  });
</script>

<div class="diagnosis-workbench">
  <div class="page-header">
    <div class="header-left">
      <h2>智能诊断工作台</h2>
      <p class="subtitle">基于振动特征的智能故障诊断与决策支持</p>
    </div>
    <button class="btn-primary" on:click={openCreateModal}>
      <span class="btn-icon">➕</span>
      新建诊断任务
    </button>
  </div>

  <div class="stats-row">
    <div class="stat-card">
      <div class="stat-icon">📋</div>
      <div class="stat-content">
        <div class="stat-value">{tasks.length}</div>
        <div class="stat-label">总任务数</div>
      </div>
    </div>
    <div class="stat-card pending">
      <div class="stat-icon">⏳</div>
      <div class="stat-content">
        <div class="stat-value">{tasks.filter(t => t.status === 'pending').length}</div>
        <div class="stat-label">待分析</div>
      </div>
    </div>
    <div class="stat-card completed">
      <div class="stat-icon">✅</div>
      <div class="stat-content">
        <div class="stat-value">{tasks.filter(t => t.status === 'completed').length}</div>
        <div class="stat-label">已完成</div>
      </div>
    </div>
    <div class="stat-card failed">
      <div class="stat-icon">❌</div>
      <div class="stat-content">
        <div class="stat-value">{tasks.filter(t => t.status === 'failed').length}</div>
        <div class="stat-label">失败</div>
      </div>
    </div>
  </div>

  <div class="section-title">
    <h3>诊断任务列表</h3>
  </div>

  {#if loading}
    <div class="loading-state">
      <div class="spinner"></div>
      <p>加载中...</p>
    </div>
  {:else if tasks.length === 0}
    <div class="empty-state">
      <div class="empty-icon">🔍</div>
      <h3>暂无诊断任务</h3>
      <p>点击上方按钮创建您的第一个诊断任务</p>
    </div>
  {:else}
    <div class="task-grid">
      {#each tasks as task (task.id)}
        <div
          class="task-card"
          class:clickable={task.status !== 'pending'}
          on:click={() => goToDetail(task)}
        >
          <div class="task-header">
            <div class="task-device">
              <span class="device-icon">📡</span>
              <span class="device-name">{task.device_name || `设备-${task.device_id}`}</span>
            </div>
            <span
              class="status-badge"
              style="background: {STATUS_COLORS[task.status]}20; color: {STATUS_COLORS[task.status]}"
            >
              {STATUS_LABELS[task.status]}
            </span>
          </div>

          <div class="task-body">
            <div class="time-range">
              <span class="label">时间范围:</span>
              <span class="value">{formatTimeRange(task.start_time, task.end_time)}</span>
            </div>

            {#if task.feature_snapshot && task.status === 'completed'}
              <div class="feature-preview">
                <div class="feature-item">
                  <span class="feature-label">RMS斜率</span>
                  <span class="feature-value">{task.feature_snapshot.rms_trend_slope.toFixed(4)}</span>
                </div>
                <div class="feature-item">
                  <span class="feature-label">峭度均值</span>
                  <span class="feature-value">{task.feature_snapshot.kurtosis_mean.toFixed(2)}</span>
                </div>
                <div class="feature-item">
                  <span class="feature-label">主频偏移</span>
                  <span class="feature-value">{task.feature_snapshot.dominant_frequency_offset.toFixed(2)} Hz</span>
                </div>
                <div class="feature-item">
                  <span class="feature-label">谐波比</span>
                  <span class="feature-value">{task.feature_snapshot.harmonic_ratio.toFixed(2)}</span>
                </div>
              </div>

              {#if task.match_results && task.match_results.length > 0}
                <div class="match-preview">
                  <span class="match-label">匹配故障:</span>
                  <span class="match-value">
                    {task.match_results[0].fault_mode_name} ({task.match_results[0].confidence}%)
                  </span>
                </div>
              {/if}
            {/if}

            {#if task.status === 'pending'}
              <div class="pending-info">
                <div class="spinner small"></div>
                <span>正在分析中...</span>
              </div>
            {/if}

            {#if task.status === 'failed'}
              <button
                class="btn-small btn-primary"
                on:click|stopPropagation={() => runTask(task)}
              >
                重新运行
              </button>
            {/if}
          </div>

          <div class="task-footer">
            <span class="create-time">创建于 {formatDateTime(task.created_at)}</span>
            {#if task.status !== 'pending'}
              <span class="view-detail">查看详情 →</span>
            {/if}
          </div>
        </div>
      {/each}
    </div>
  {/if}

  {#if showCreateModal}
    <div class="modal-overlay" on:click={closeCreateModal}>
      <div class="modal-content" on:click|stopPropagation>
        <div class="modal-header">
          <h3>新建诊断任务</h3>
          <button class="close-btn" on:click={closeCreateModal}>×</button>
        </div>

        <div class="modal-body">
          <div class="form-group">
            <label>目标设备 <span class="required">*</span></label>
            <select bind:value={selectedDevice} class="form-select">
              <option value={null}>请选择设备</option>
              {#each devices as device}
                <option value={device.id}>{device.name} ({device.code})</option>
              {/each}
            </select>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>开始时间 <span class="required">*</span></label>
              <input
                type="datetime-local"
                bind:value={startTime}
                class="form-input"
              />
            </div>
            <div class="form-group">
              <label>结束时间 <span class="required">*</span></label>
              <input
                type="datetime-local"
                bind:value={endTime}
                class="form-input"
              />
            </div>
          </div>

          {#if errorMessage}
            <div class="error-message">
              ⚠️ {errorMessage}
            </div>
          {/if}

          <div class="info-hint">
            💡 系统将自动从指定时间范围的历史振动数据中提取特征并进行故障模式匹配
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn-secondary" on:click={closeCreateModal}>取消</button>
          <button class="btn-primary" on:click={createTask} disabled={creating}>
            {#if creating}
              <span class="spinner small"></span>
              创建中...
            {:else}
              创建任务
            {/if}
          </button>
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  .diagnosis-workbench {
    padding: var(--spacing-6);
    min-height: calc(100vh - var(--header-height));
  }

  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: var(--spacing-6);
  }

  .header-left h2 {
    margin: 0 0 var(--spacing-2) 0;
    font-size: var(--font-size-2xl);
    color: var(--color-gray-900);
  }

  .subtitle {
    margin: 0;
    color: var(--color-gray-500);
    font-size: var(--font-size-base);
  }

  .stats-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: var(--spacing-4);
    margin-bottom: var(--spacing-6);
  }

  .stat-card {
    display: flex;
    align-items: center;
    gap: var(--spacing-4);
    padding: var(--spacing-5);
    background: var(--color-white);
    border-radius: var(--radius-lg);
    border: var(--border-width) solid var(--color-gray-200);
    box-shadow: var(--shadow-sm);
  }

  .stat-icon {
    font-size: var(--font-size-3xl);
  }

  .stat-value {
    font-size: var(--font-size-2xl);
    font-weight: 700;
    color: var(--color-gray-900);
    line-height: 1.2;
  }

  .stat-label {
    font-size: var(--font-size-sm);
    color: var(--color-gray-500);
  }

  .stat-card.pending .stat-value { color: var(--color-warning); }
  .stat-card.completed .stat-value { color: var(--color-success); }
  .stat-card.failed .stat-value { color: var(--color-danger); }

  .section-title {
    margin: var(--spacing-6) 0 var(--spacing-4);
  }

  .section-title h3 {
    margin: 0;
    font-size: var(--font-size-lg);
    color: var(--color-gray-900);
    font-weight: 600;
  }

  .loading-state,
  .empty-state {
    text-align: center;
    padding: var(--spacing-12) var(--spacing-6);
    background: var(--color-white);
    border-radius: var(--radius-lg);
    border: var(--border-width) solid var(--color-gray-200);
  }

  .empty-icon {
    font-size: 64px;
    margin-bottom: var(--spacing-4);
    opacity: 0.5;
  }

  .empty-state h3 {
    margin: 0 0 var(--spacing-2) 0;
    color: var(--color-gray-700);
  }

  .empty-state p {
    margin: 0;
    color: var(--color-gray-500);
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

  .task-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: var(--spacing-4);
  }

  .task-card {
    background: var(--color-white);
    border-radius: var(--radius-lg);
    border: var(--border-width) solid var(--color-gray-200);
    overflow: hidden;
    transition: all var(--transition-normal);
    display: flex;
    flex-direction: column;
  }

  .task-card.clickable {
    cursor: pointer;
  }

  .task-card.clickable:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-lg);
    border-color: var(--color-primary-light);
  }

  .task-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--spacing-4);
    border-bottom: var(--border-width) solid var(--color-gray-100);
  }

  .task-device {
    display: flex;
    align-items: center;
    gap: var(--spacing-2);
  }

  .device-icon {
    font-size: var(--font-size-lg);
  }

  .device-name {
    font-weight: 600;
    color: var(--color-gray-900);
  }

  .status-badge {
    padding: 4px var(--spacing-2);
    border-radius: var(--radius-full);
    font-size: var(--font-size-xs);
    font-weight: 500;
  }

  .task-body {
    padding: var(--spacing-4);
    flex: 1;
  }

  .time-range {
    display: flex;
    gap: var(--spacing-2);
    margin-bottom: var(--spacing-3);
    font-size: var(--font-size-sm);
  }

  .time-range .label {
    color: var(--color-gray-500);
    flex-shrink: 0;
  }

  .time-range .value {
    color: var(--color-gray-700);
    font-weight: 500;
  }

  .feature-preview {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: var(--spacing-2);
    padding: var(--spacing-3);
    background: var(--color-gray-50);
    border-radius: var(--radius-md);
    margin-bottom: var(--spacing-3);
  }

  .feature-item {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .feature-label {
    font-size: var(--font-size-xs);
    color: var(--color-gray-500);
  }

  .feature-value {
    font-size: var(--font-size-sm);
    font-weight: 600;
    color: var(--color-gray-900);
  }

  .match-preview {
    display: flex;
    gap: var(--spacing-2);
    align-items: center;
    padding: var(--spacing-2) var(--spacing-3);
    background: var(--color-danger-lighter);
    border-radius: var(--radius-md);
    font-size: var(--font-size-sm);
  }

  .match-label {
    color: var(--color-gray-600);
  }

  .match-value {
    color: var(--color-danger-dark);
    font-weight: 600;
  }

  .pending-info {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: var(--spacing-2);
    padding: var(--spacing-4);
    background: var(--color-warning-lighter);
    border-radius: var(--radius-md);
    color: var(--color-warning-dark);
  }

  .task-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--spacing-3) var(--spacing-4);
    background: var(--color-gray-50);
    font-size: var(--font-size-xs);
    color: var(--color-gray-500);
  }

  .view-detail {
    color: var(--color-primary);
    font-weight: 500;
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
    max-width: 500px;
    max-height: 90vh;
    overflow-y: auto;
    box-shadow: var(--shadow-2xl);
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

  .form-group {
    margin-bottom: var(--spacing-4);
  }

  .form-group label {
    display: block;
    margin-bottom: var(--spacing-2);
    font-size: var(--font-size-sm);
    font-weight: 500;
    color: var(--color-gray-700);
  }

  .required {
    color: var(--color-danger);
  }

  .form-select,
  .form-input {
    width: 100%;
    padding: var(--spacing-3) var(--spacing-3);
    border: var(--border-width) solid var(--color-gray-300);
    border-radius: var(--radius-md);
    font-size: var(--font-size-base);
    color: var(--color-gray-900);
    background: var(--color-white);
    transition: all var(--transition-fast);
  }

  .form-select:focus,
  .form-input:focus {
    outline: none;
    border-color: var(--color-primary);
    box-shadow: 0 0 0 3px var(--color-primary-lighter);
  }

  .form-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--spacing-4);
  }

  .error-message {
    padding: var(--spacing-3);
    background: var(--color-danger-lighter);
    color: var(--color-danger-dark);
    border-radius: var(--radius-md);
    font-size: var(--font-size-sm);
    margin-bottom: var(--spacing-4);
  }

  .info-hint {
    padding: var(--spacing-3);
    background: var(--color-primary-lighter);
    color: var(--color-primary-dark);
    border-radius: var(--radius-md);
    font-size: var(--font-size-sm);
  }

  .modal-footer {
    display: flex;
    justify-content: flex-end;
    gap: var(--spacing-3);
    padding: var(--spacing-5);
    border-top: var(--border-width) solid var(--color-gray-200);
  }

  .btn-primary,
  .btn-secondary,
  .btn-small {
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

  .btn-small {
    padding: var(--spacing-2) var(--spacing-4);
    font-size: var(--font-size-sm);
  }

  .btn-icon {
    font-size: var(--font-size-lg);
  }
</style>
