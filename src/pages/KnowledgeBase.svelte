<script>
  import { onMount } from 'svelte';
  import { format, parseISO } from 'date-fns';
  import { diagnosisApi } from '../api.js';

  let loading = true;
  let knowledgeList = [];
  let showAddModal = false;
  let newName = '';
  let newDescription = '';
  let newKeyFeatures = '';
  let newSeverity = 'medium';
  let newAction = '';
  let errorMessage = '';
  let adding = false;
  let deletingId = null;

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

  function formatDateTime(isoString) {
    if (!isoString) return '-';
    return format(parseISO(isoString), 'yyyy-MM-dd HH:mm');
  }

  async function loadKnowledge() {
    loading = true;
    try {
      const response = await diagnosisApi.getKnowledge({ page_size: 100 });
      if (response.success && response.data) {
        knowledgeList = response.data.items || response.data;
      }
    } catch (error) {
      console.error('加载知识库失败:', error);
    } finally {
      loading = false;
    }
  }

  function openAddModal() {
    newName = '';
    newDescription = '';
    newKeyFeatures = '';
    newSeverity = 'medium';
    newAction = '';
    errorMessage = '';
    showAddModal = true;
  }

  function closeAddModal() {
    showAddModal = false;
    errorMessage = '';
  }

  async function addKnowledge() {
    if (!newName.trim()) {
      errorMessage = '请输入故障模式名称';
      return;
    }
    if (!newDescription.trim()) {
      errorMessage = '请输入判定条件描述';
      return;
    }

    adding = true;
    errorMessage = '';

    try {
      const response = await diagnosisApi.createKnowledge({
        name: newName.trim(),
        description: newDescription.trim(),
        key_frequency_features: newKeyFeatures.trim(),
        severity_level: newSeverity,
        maintenance_action: newAction.trim() || '专业检查'
      });

      if (response.success) {
        closeAddModal();
        loadKnowledge();
      } else {
        errorMessage = response.message || '添加规则失败';
      }
    } catch (error) {
      errorMessage = error.message || '添加规则失败';
    } finally {
      adding = false;
    }
  }

  async function deleteKnowledge(id) {
    if (!confirm('确定要删除这条故障模式规则吗？删除后无法恢复。')) {
      return;
    }

    deletingId = id;
    try {
      const response = await diagnosisApi.deleteKnowledge(id);
      if (response.success) {
        loadKnowledge();
      }
    } catch (error) {
      console.error('删除规则失败:', error);
    } finally {
      deletingId = null;
    }
  }

  onMount(() => {
    loadKnowledge();
  });
</script>

<div class="knowledge-base">
  <div class="page-header">
    <div class="header-left">
      <h2>知识库管理</h2>
      <p class="subtitle">管理故障模式判定规则，支持新增和删除操作</p>
    </div>
    <button class="btn-primary" on:click={openAddModal}>
      <span class="btn-icon">➕</span>
      新增规则
    </button>
  </div>

  <div class="stats-row">
    <div class="stat-card critical">
      <div class="stat-icon">🔴</div>
      <div class="stat-content">
        <div class="stat-value">{knowledgeList.filter(k => k.severity_level === 'critical').length}</div>
        <div class="stat-label">严重等级</div>
      </div>
    </div>
    <div class="stat-card high">
      <div class="stat-icon">🟠</div>
      <div class="stat-content">
        <div class="stat-value">{knowledgeList.filter(k => k.severity_level === 'high').length}</div>
        <div class="stat-label">高等级</div>
      </div>
    </div>
    <div class="stat-card medium">
      <div class="stat-icon">🟡</div>
      <div class="stat-content">
        <div class="stat-value">{knowledgeList.filter(k => k.severity_level === 'medium').length}</div>
        <div class="stat-label">中等级</div>
      </div>
    </div>
    <div class="stat-card low">
      <div class="stat-icon">🔵</div>
      <div class="stat-content">
        <div class="stat-value">{knowledgeList.filter(k => k.severity_level === 'low').length}</div>
        <div class="stat-label">低等级</div>
      </div>
    </div>
  </div>

  {#if loading}
    <div class="loading-state">
      <div class="spinner"></div>
      <p>加载中...</p>
    </div>
  {:else}
    <div class="table-card">
      <div class="table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th style="width: 60px;">序号</th>
              <th style="width: 150px;">故障模式名称</th>
              <th>判定条件描述</th>
              <th style="width: 200px;">关键频率特征</th>
              <th style="width: 100px;">严重等级</th>
              <th style="width: 150px;">创建时间</th>
              <th style="width: 80px;">操作</th>
            </tr>
          </thead>
          <tbody>
            {#if knowledgeList.length === 0}
              <tr>
                <td colspan="7" class="empty-cell">
                  <div class="empty-content">
                    <div class="empty-icon">📚</div>
                    <p>暂无故障模式规则</p>
                  </div>
                </td>
              </tr>
            {:else}
              {#each knowledgeList as knowledge, index}
                <tr>
                  <td class="text-center">{index + 1}</td>
                  <td class="font-medium">{knowledge.name}</td>
                  <td class="description-cell">
                    <div class="description-text">{knowledge.description}</div>
                  </td>
                  <td class="text-sm text-gray-600">{knowledge.key_frequency_features || '-'}</td>
                  <td>
                    <span
                      class="severity-badge"
                      style="background: {SEVERITY_COLORS[knowledge.severity_level]}20; color: {SEVERITY_COLORS[knowledge.severity_level]}"
                    >
                      {SEVERITY_LABELS[knowledge.severity_level]}
                    </span>
                  </td>
                  <td class="text-sm text-gray-500">{formatDateTime(knowledge.created_at)}</td>
                  <td class="text-center">
                    <button
                      class="btn-delete"
                      on:click={() => deleteKnowledge(knowledge.id)}
                      disabled={deletingId === knowledge.id}
                      title="删除规则"
                    >
                      {#if deletingId === knowledge.id}
                        <div class="spinner tiny"></div>
                      {:else}
                        🗑️
                      {/if}
                    </button>
                  </td>
                </tr>
              {/each}
            {/if}
          </tbody>
        </table>
      </div>
    </div>
  {/if}

  {#if showAddModal}
    <div class="modal-overlay" on:click={closeAddModal}>
      <div class="modal-content" on:click|stopPropagation>
        <div class="modal-header">
          <h3>新增故障模式规则</h3>
          <button class="close-btn" on:click={closeAddModal}>×</button>
        </div>

        <div class="modal-body">
          <div class="form-group">
            <label>故障模式名称 <span class="required">*</span></label>
            <input
              type="text"
              bind:value={newName}
              class="form-input"
              placeholder="如：轴承磨损、齿轮啮合不良等"
            />
          </div>

          <div class="form-group">
            <label>判定条件描述 <span class="required">*</span></label>
            <textarea
              bind:value={newDescription}
              class="form-textarea"
              rows="3"
              placeholder="请详细描述该故障模式的判定条件和特征表现"
            ></textarea>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>关键频率特征</label>
              <input
                type="text"
                bind:value={newKeyFeatures}
                class="form-input"
                placeholder="如：BPFO频率及其倍频、1X转频等"
              />
            </div>
            <div class="form-group">
              <label>严重等级</label>
              <select bind:value={newSeverity} class="form-select">
                <option value="low">低</option>
                <option value="medium">中</option>
                <option value="high">高</option>
                <option value="critical">严重</option>
              </select>
            </div>
          </div>

          <div class="form-group">
            <label>建议维护动作</label>
            <input
              type="text"
              bind:value={newAction}
              class="form-input"
              placeholder="如：更换轴承、动平衡校正等"
            />
          </div>

          {#if errorMessage}
            <div class="error-message">
              ⚠️ {errorMessage}
            </div>
          {/if}

          <div class="info-hint">
            💡 新增规则后将立即生效，下次故障诊断时将使用更新后的知识库进行匹配
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn-secondary" on:click={closeAddModal}>取消</button>
          <button class="btn-primary" on:click={addKnowledge} disabled={adding}>
            {#if adding}
              <span class="spinner small"></span>
              添加中...
            {:else}
              添加规则
            {/if}
          </button>
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  .knowledge-base {
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

  .stat-card.critical .stat-value { color: var(--color-danger); }
  .stat-card.high .stat-value { color: #f97316; }
  .stat-card.medium .stat-value { color: var(--color-warning); }
  .stat-card.low .stat-value { color: var(--color-primary); }

  .stat-icon {
    font-size: var(--font-size-2xl);
  }

  .stat-value {
    font-size: var(--font-size-2xl);
    font-weight: 700;
    line-height: 1.2;
  }

  .stat-label {
    font-size: var(--font-size-sm);
    color: var(--color-gray-500);
  }

  .loading-state {
    text-align: center;
    padding: var(--spacing-12) var(--spacing-6);
    background: var(--color-white);
    border-radius: var(--radius-lg);
    border: var(--border-width) solid var(--color-gray-200);
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

  .spinner.tiny {
    width: 14px;
    height: 14px;
    border-width: 2px;
    margin: 0;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .table-card {
    background: var(--color-white);
    border-radius: var(--radius-lg);
    border: var(--border-width) solid var(--color-gray-200);
    box-shadow: var(--shadow-sm);
    overflow: hidden;
  }

  .table-container {
    overflow-x: auto;
  }

  .data-table {
    width: 100%;
    border-collapse: collapse;
  }

  .data-table thead {
    background: var(--color-gray-50);
    border-bottom: var(--border-width) solid var(--color-gray-200);
  }

  .data-table th {
    padding: var(--spacing-3) var(--spacing-4);
    text-align: left;
    font-size: var(--font-size-xs);
    font-weight: 600;
    color: var(--color-gray-500);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    white-space: nowrap;
  }

  .data-table td {
    padding: var(--spacing-4);
    border-bottom: var(--border-width) solid var(--color-gray-100);
    font-size: var(--font-size-sm);
    color: var(--color-gray-700);
  }

  .data-table tbody tr:hover {
    background: var(--color-gray-50);
  }

  .data-table tbody tr:last-child td {
    border-bottom: none;
  }

  .text-center {
    text-align: center;
  }

  .font-medium {
    font-weight: 500;
    color: var(--color-gray-900);
  }

  .text-sm {
    font-size: var(--font-size-xs);
  }

  .text-gray-500 {
    color: var(--color-gray-500);
  }

  .text-gray-600 {
    color: var(--color-gray-600);
  }

  .description-cell {
    max-width: 400px;
  }

  .description-text {
    line-height: 1.5;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .severity-badge {
    display: inline-block;
    padding: 4px var(--spacing-2);
    border-radius: var(--radius-full);
    font-size: var(--font-size-xs);
    font-weight: 500;
    text-align: center;
    min-width: 50px;
  }

  .empty-cell {
    padding: var(--spacing-12);
    text-align: center;
  }

  .empty-content {
    text-align: center;
  }

  .empty-icon {
    font-size: 48px;
    margin-bottom: var(--spacing-3);
    opacity: 0.5;
  }

  .empty-content p {
    margin: 0;
    color: var(--color-gray-500);
  }

  .btn-delete {
    background: none;
    border: none;
    font-size: var(--font-size-lg);
    cursor: pointer;
    padding: var(--spacing-1) var(--spacing-2);
    border-radius: var(--radius-sm);
    transition: all var(--transition-fast);
    opacity: 0.7;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    margin: 0 auto;
  }

  .btn-delete:hover:not(:disabled) {
    background: var(--color-danger-lighter);
    opacity: 1;
  }

  .btn-delete:disabled {
    cursor: not-allowed;
    opacity: 0.5;
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
    max-width: 550px;
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

  .form-input,
  .form-select,
  .form-textarea {
    width: 100%;
    padding: var(--spacing-3) var(--spacing-3);
    border: var(--border-width) solid var(--color-gray-300);
    border-radius: var(--radius-md);
    font-size: var(--font-size-base);
    color: var(--color-gray-900);
    background: var(--color-white);
    transition: all var(--transition-fast);
    font-family: inherit;
  }

  .form-input:focus,
  .form-select:focus,
  .form-textarea:focus {
    outline: none;
    border-color: var(--color-primary);
    box-shadow: 0 0 0 3px var(--color-primary-lighter);
  }

  .form-textarea {
    resize: vertical;
    min-height: 80px;
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
