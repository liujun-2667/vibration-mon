<script>
  import { onMount } from 'svelte';

  let selectedDevice = null;
  let devices = [];
  let rules = [];
  let showRuleForm = false;
  let editingRule = null;
  let loading = true;

  const ruleTypes = [
    {
      value: 'absolute_threshold',
      label: '绝对阈值',
      icon: '📏',
      desc: '当指标超过固定阈值时触发告警',
      color: '#3b82f6'
    },
    {
      value: 'relative_change',
      label: '相对变化',
      icon: '📈',
      desc: '当指标相比基线变化超过百分比时触发',
      color: '#8b5cf6'
    },
    {
      value: 'frequency_threshold',
      label: '频率阈值',
      icon: '📊',
      desc: '当特定频段的幅值超过阈值时触发',
      color: '#10b981'
    },
    {
      value: 'trend_rising',
      label: '趋势上升',
      icon: '↗️',
      desc: '当指标呈现持续上升趋势时触发',
      color: '#ef4444'
    }
  ];

  const operators = [
    { value: '>', label: '大于 (>)' },
    { value: '<', label: '小于 (<)' },
    { value: '>=', label: '大于等于 (>=)' },
    { value: '<=', label: '小于等于 (<=)' },
    { value: '==', label: '等于 (==)' },
    { value: '!=', label: '不等于 (!=)' }
  ];

  const logicalOperators = [
    { value: 'and', label: 'AND (全部满足)' },
    { value: 'or', label: 'OR (任意满足)' }
  ];

  const alarmLevels = [
    { value: 'info', label: '信息', color: '#3b82f6', bgColor: '#dbeafe' },
    { value: 'warning', label: '警告', color: '#f59e0b', bgColor: '#fef3c7' },
    { value: 'critical', label: '严重', color: '#ef4444', bgColor: '#fee2e2' }
  ];

  const parameters = [
    { value: 'rms', label: 'RMS (均方根)', unit: 'mm/s' },
    { value: 'peak', label: '峰值', unit: 'mm/s' },
    { value: 'peak_to_peak', label: '峰峰值', unit: 'mm/s' },
    { value: 'crest_factor', label: '波峰因数', unit: '' },
    { value: 'kurtosis', label: '峭度', unit: '' },
    { value: 'spectral_centroid', label: '频谱质心', unit: 'Hz' },
    { value: 'dominant_frequency', label: '主导频率', unit: 'Hz' }
  ];

  const timeRanges = [
    { value: '1h', label: '1小时', seconds: 3600 },
    { value: '8h', label: '8小时', seconds: 28800 },
    { value: '24h', label: '24小时', seconds: 86400 },
    { value: '7d', label: '7天', seconds: 604800 }
  ];

  let formData = {
    name: '',
    description: '',
    level: 'warning',
    logicalOperator: 'and',
    cooldownSeconds: 60,
    enabled: true,
    conditions: []
  };

  function generateId() {
    return 'rule_' + Math.random().toString(36).substr(2, 9);
  }

  function createEmptyCondition(ruleType = 'absolute_threshold') {
    const baseCondition = {
      id: generateId(),
      ruleType,
      parameter: 'rms',
      enabled: true,
      description: ''
    };

    switch (ruleType) {
      case 'absolute_threshold':
        return { ...baseCondition, threshold: 2.0, operator: '>' };
      case 'relative_change':
        return { ...baseCondition, relativeChangePercent: 50.0, baselineWindowSeconds: 3600 };
      case 'frequency_threshold':
        return { ...baseCondition, threshold: 1.0, operator: '>', frequencyBand: 'low', frequencyMin: 0, frequencyMax: 100 };
      case 'trend_rising':
        return { ...baseCondition, trendTimeRange: '1h', minRSquared: 0.7 };
      default:
        return baseCondition;
    }
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

  function loadMockRules() {
    rules = [
      {
        id: 'rule_001',
        name: 'RMS值过高告警',
        description: '当RMS值超过2.0 mm/s时触发告警',
        deviceId: 1,
        level: 'warning',
        logicalOperator: 'and',
        enabled: true,
        cooldownSeconds: 60,
        createdAt: Date.now() - 86400000,
        conditions: [
          {
            id: 'cond_001',
            ruleType: 'absolute_threshold',
            parameter: 'rms',
            threshold: 2.0,
            operator: '>',
            enabled: true,
            description: 'RMS > 2.0 mm/s'
          }
        ]
      },
      {
        id: 'rule_002',
        name: '峭度与峰值综合告警',
        description: '当峭度超过4.5且峰值超过8.0时触发严重告警',
        deviceId: 1,
        level: 'critical',
        logicalOperator: 'and',
        enabled: true,
        cooldownSeconds: 120,
        createdAt: Date.now() - 43200000,
        conditions: [
          {
            id: 'cond_002',
            ruleType: 'absolute_threshold',
            parameter: 'kurtosis',
            threshold: 4.5,
            operator: '>',
            enabled: true,
            description: '峭度 > 4.5'
          },
          {
            id: 'cond_003',
            ruleType: 'absolute_threshold',
            parameter: 'peak',
            threshold: 8.0,
            operator: '>',
            enabled: true,
            description: '峰值 > 8.0 mm/s'
          }
        ]
      },
      {
        id: 'rule_003',
        name: 'RMS快速上升告警',
        description: '当RMS在1小时内相对变化超过100%时触发',
        deviceId: 2,
        level: 'critical',
        logicalOperator: 'and',
        enabled: true,
        cooldownSeconds: 180,
        createdAt: Date.now() - 21600000,
        conditions: [
          {
            id: 'cond_004',
            ruleType: 'relative_change',
            parameter: 'rms',
            relativeChangePercent: 100.0,
            baselineWindowSeconds: 3600,
            enabled: true,
            description: 'RMS相对变化 > 100%'
          }
        ]
      },
      {
        id: 'rule_004',
        name: 'RMS持续上升趋势',
        description: '当RMS在8小时内呈现持续上升趋势时触发',
        deviceId: 1,
        level: 'warning',
        logicalOperator: 'and',
        enabled: true,
        cooldownSeconds: 300,
        createdAt: Date.now() - 3600000,
        conditions: [
          {
            id: 'cond_005',
            ruleType: 'trend_rising',
            parameter: 'rms',
            trendTimeRange: '8h',
            minRSquared: 0.7,
            enabled: true,
            description: 'RMS上升趋势 (R² ≥ 0.7)'
          }
        ]
      },
      {
        id: 'rule_005',
        name: '高频段幅值告警',
        description: '当1000-5000Hz频段幅值超过1.5时触发',
        deviceId: 2,
        level: 'warning',
        logicalOperator: 'and',
        enabled: false,
        cooldownSeconds: 60,
        createdAt: Date.now() - 7200000,
        conditions: [
          {
            id: 'cond_006',
            ruleType: 'frequency_threshold',
            parameter: 'amplitude',
            threshold: 1.5,
            operator: '>',
            frequencyBand: 'high',
            frequencyMin: 1000,
            frequencyMax: 5000,
            enabled: true,
            description: '高频段幅值 > 1.5'
          }
        ]
      }
    ];
  }

  function getRuleTypeInfo(type) {
    return ruleTypes.find(t => t.value === type) || ruleTypes[0];
  }

  function getParameterInfo(param) {
    return parameters.find(p => p.value === param) || { label: param, unit: '' };
  }

  function getAlarmLevelInfo(level) {
    return alarmLevels.find(l => l.value === level) || alarmLevels[1];
  }

  function getOperatorLabel(op) {
    const operator = operators.find(o => o.value === op);
    return operator ? operator.label : op;
  }

  function formatConditionDescription(condition) {
    const paramInfo = getParameterInfo(condition.parameter);
    const typeInfo = getRuleTypeInfo(condition.ruleType);

    switch (condition.ruleType) {
      case 'absolute_threshold':
        return `${paramInfo.label} ${condition.operator} ${condition.threshold} ${paramInfo.unit}`;
      case 'relative_change':
        return `${paramInfo.label} 变化 > ${condition.relativeChangePercent}% (${condition.baselineWindowSeconds / 3600}小时基线)`;
      case 'frequency_threshold':
        return `${condition.frequencyMin}-${condition.frequencyMax}Hz 频段 ${condition.operator} ${condition.threshold}`;
      case 'trend_rising':
        const tr = timeRanges.find(t => t.value === condition.trendTimeRange);
        return `${paramInfo.label} ${tr?.label || condition.trendTimeRange} 上升趋势 (R² ≥ ${condition.minRSquared})`;
      default:
        return condition.description || '';
    }
  }

  function openNewRuleForm() {
    editingRule = null;
    formData = {
      name: '',
      description: '',
      level: 'warning',
      logicalOperator: 'and',
      cooldownSeconds: 60,
      enabled: true,
      conditions: [createEmptyCondition('absolute_threshold')]
    };
    showRuleForm = true;
  }

  function editRule(rule) {
    editingRule = rule;
    formData = {
      name: rule.name,
      description: rule.description,
      level: rule.level,
      logicalOperator: rule.logicalOperator,
      cooldownSeconds: rule.cooldownSeconds,
      enabled: rule.enabled,
      conditions: JSON.parse(JSON.stringify(rule.conditions))
    };
    showRuleForm = true;
  }

  function closeForm() {
    showRuleForm = false;
    editingRule = null;
  }

  function addCondition() {
    formData.conditions.push(createEmptyCondition('absolute_threshold'));
  }

  function removeCondition(index) {
    if (formData.conditions.length > 1) {
      formData.conditions.splice(index, 1);
    }
  }

  function changeConditionType(index, newType) {
    formData.conditions[index] = createEmptyCondition(newType);
  }

  function toggleConditionEnabled(index) {
    formData.conditions[index].enabled = !formData.conditions[index].enabled;
  }

  function saveRule() {
    if (!formData.name.trim()) {
      alert('请输入规则名称');
      return;
    }
    if (formData.conditions.length === 0) {
      alert('至少需要一个条件');
      return;
    }

    const ruleData = {
      ...formData,
      conditions: formData.conditions.map(c => ({
        ...c,
        description: formatConditionDescription(c)
      }))
    };

    if (editingRule) {
      const index = rules.findIndex(r => r.id === editingRule.id);
      if (index !== -1) {
        rules[index] = {
          ...editingRule,
          ...ruleData,
          updatedAt: Date.now()
        };
      }
    } else {
      rules.unshift({
        id: generateId(),
        deviceId: selectedDevice,
        ...ruleData,
        createdAt: Date.now()
      });
    }

    closeForm();
  }

  function toggleRuleEnabled(ruleId) {
    const rule = rules.find(r => r.id === ruleId);
    if (rule) {
      rule.enabled = !rule.enabled;
    }
  }

  function deleteRule(ruleId) {
    if (confirm('确定要删除此规则吗？')) {
      rules = rules.filter(r => r.id !== ruleId);
    }
  }

  function formatDate(timestamp) {
    return new Date(timestamp).toLocaleString('zh-CN');
  }

  function formatValue(value, decimals = 2) {
    return value !== undefined && value !== null ? value.toFixed(decimals) : '-';
  }

  onMount(async () => {
    await fetchDevices();
    loadMockRules();
    loading = false;
  });

  $: filteredRules = rules.filter(r => r.deviceId === selectedDevice);
</script>

<div class="alarm-config-page">
  <div class="header">
    <div class="header-left">
      <h1 class="page-title">预警规则配置</h1>
      <p class="page-subtitle">管理设备的告警规则和触发条件</p>
    </div>
    <div class="header-right">
      <div class="device-selector">
        <label>选择设备</label>
        <select bind:value={selectedDevice}>
          {#each devices as device}
            <option value={device.id}>{device.name} ({device.code})</option>
          {/each}
        </select>
      </div>
      <button class="add-btn" on:click={openNewRuleForm}>
        ➕ 新建规则
      </button>
    </div>
  </div>

  {#if loading}
    <div class="loading">加载中...</div>
  {:else}
    <div class="stats-bar">
      <div class="stat-item">
        <span class="stat-icon">📋</span>
        <span class="stat-value">{filteredRules.length}</span>
        <span class="stat-label">总规则数</span>
      </div>
      <div class="stat-item">
        <span class="stat-icon">✅</span>
        <span class="stat-value">{filteredRules.filter(r => r.enabled).length}</span>
        <span class="stat-label">已启用</span>
      </div>
      <div class="stat-item">
        <span class="stat-icon">⚠️</span>
        <span class="stat-value">{filteredRules.filter(r => r.level === 'warning').length}</span>
        <span class="stat-label">警告级别</span>
      </div>
      <div class="stat-item">
        <span class="stat-icon">🚨</span>
        <span class="stat-value">{filteredRules.filter(r => r.level === 'critical').length}</span>
        <span class="stat-label">严重级别</span>
      </div>
    </div>

    {#if filteredRules.length === 0}
      <div class="empty-state">
        <div class="empty-icon">📋</div>
        <h3>暂无告警规则</h3>
        <p>点击"新建规则"按钮创建第一个告警规则</p>
      </div>
    {:else}
      <div class="rules-list">
        {#each filteredRules as rule}
          <div class="rule-card" class:disabled={!rule.enabled}>
            <div class="rule-header">
              <div class="rule-title">
                <span class="rule-icon" style="background: {getRuleTypeInfo(rule.conditions[0]?.ruleType)?.color}">
                  {getRuleTypeInfo(rule.conditions[0]?.ruleType)?.icon}
                </span>
                <div>
                  <h3 class="rule-name">{rule.name}</h3>
                  <p class="rule-desc">{rule.description}</p>
                </div>
              </div>
              <div class="rule-actions">
                <span class="level-badge" style="background: {getAlarmLevelInfo(rule.level).bgColor}; color: {getAlarmLevelInfo(rule.level).color}">
                  {getAlarmLevelInfo(rule.level).label}
                </span>
                <label class="toggle-switch">
                  <input type="checkbox" checked={rule.enabled} on:change={() => toggleRuleEnabled(rule.id)} />
                  <span class="toggle-slider"></span>
                </label>
              </div>
            </div>

            <div class="rule-conditions">
              <div class="conditions-header">
                <span class="conditions-title">触发条件</span>
                <span class="logic-badge">{rule.logicalOperator.toUpperCase()}</span>
              </div>
              <div class="conditions-list">
                {#each rule.conditions as condition}
                  <div class="condition-item" class:disabled={!condition.enabled}>
                    <span class="condition-type-icon" style="background: {getRuleTypeInfo(condition.ruleType).color}">
                      {getRuleTypeInfo(condition.ruleType).icon}
                    </span>
                    <div class="condition-content">
                      <span class="condition-type">{getRuleTypeInfo(condition.ruleType).label}</span>
                      <span class="condition-desc">{condition.description || formatConditionDescription(condition)}</span>
                    </div>
                    {#if !condition.enabled}
                      <span class="disabled-badge">已禁用</span>
                    {/if}
                  </div>
                {/each}
              </div>
            </div>

            <div class="rule-footer">
              <div class="rule-meta">
                <span class="meta-item">🕒 冷却时间: {rule.cooldownSeconds}秒</span>
                <span class="meta-item">📅 创建时间: {formatDate(rule.createdAt)}</span>
                {#if rule.updatedAt}
                  <span class="meta-item">✏️ 更新时间: {formatDate(rule.updatedAt)}</span>
                {/if}
              </div>
              <div class="rule-buttons">
                <button class="btn-secondary" on:click={() => editRule(rule)}>
                  ✏️ 编辑
                </button>
                <button class="btn-danger" on:click={() => deleteRule(rule.id)}>
                  🗑️ 删除
                </button>
              </div>
            </div>
          </div>
        {/each}
      </div>
    {/if}
  {/if}

  {#if showRuleForm}
    <div class="modal-overlay" on:click|self={closeForm}>
      <div class="modal">
        <div class="modal-header">
          <h2>{editingRule ? '编辑规则' : '新建规则'}</h2>
          <button class="close-btn" on:click={closeForm}>×</button>
        </div>

        <div class="modal-body">
          <div class="form-section">
            <h4 class="section-title">基本信息</h4>
            <div class="form-grid">
              <div class="form-group full-width">
                <label>规则名称 *</label>
                <input type="text" bind:value={formData.name} placeholder="输入规则名称" />
              </div>
              <div class="form-group full-width">
                <label>规则描述</label>
                <textarea bind:value={formData.description} placeholder="输入规则描述" rows="2"></textarea>
              </div>
              <div class="form-group">
                <label>告警级别</label>
                <div class="level-buttons">
                  {#each alarmLevels as level}
                    <button
                      class="level-btn {formData.level === level.value ? 'active' : ''}"
                      style="--level-color: {level.color}; --level-bg: {level.bgColor}"
                      on:click={() => formData.level = level.value}
                    >
                      {level.label}
                    </button>
                  {/each}
                </div>
              </div>
              <div class="form-group">
                <label>冷却时间 (秒)</label>
                <input type="number" bind:value={formData.cooldownSeconds} min="0" step="10" />
              </div>
              <div class="form-group">
                <label>条件逻辑</label>
                <div class="logic-buttons">
                  {#each logicalOperators as op}
                    <button
                      class="logic-btn {formData.logicalOperator === op.value ? 'active' : ''}"
                      on:click={() => formData.logicalOperator = op.value}
                    >
                      {op.label}
                    </button>
                  {/each}
                </div>
              </div>
              <div class="form-group">
                <label>启用状态</label>
                <label class="toggle-switch large">
                  <input type="checkbox" bind:checked={formData.enabled} />
                  <span class="toggle-slider"></span>
                </label>
              </div>
            </div>
          </div>

          <div class="form-section">
            <div class="section-header">
              <h4 class="section-title">触发条件</h4>
              <button class="add-condition-btn" on:click={addCondition}>
                ➕ 添加条件
              </button>
            </div>

            <div class="conditions-form-list">
              {#each formData.conditions as condition, index}
                <div class="condition-form-card">
                  <div class="condition-form-header">
                    <div class="condition-type-selector">
                      {#each ruleTypes as type}
                        <button
                          class="type-btn {condition.ruleType === type.value ? 'active' : ''}"
                          style="--type-color: {type.color}"
                          on:click={() => changeConditionType(index, type.value)}
                        >
                          <span class="type-icon">{type.icon}</span>
                          <span class="type-label">{type.label}</span>
                        </button>
                      {/each}
                    </div>
                    <div class="condition-form-actions">
                      <label class="toggle-switch">
                        <input type="checkbox" checked={condition.enabled} on:change={() => toggleConditionEnabled(index)} />
                        <span class="toggle-slider"></span>
                      </label>
                      {#if formData.conditions.length > 1}
                        <button class="remove-btn" on:click={() => removeCondition(index)}>✕</button>
                      {/if}
                    </div>
                  </div>

                  <div class="condition-form-body">
                    <div class="form-group">
                      <label>监测指标</label>
                      <select bind:value={condition.parameter}>
                        {#each parameters as param}
                          <option value={param.value}>{param.label} ({param.unit || '-'})</option>
                        {/each}
                      </select>
                    </div>

                    {#if condition.ruleType === 'absolute_threshold'}
                      <div class="form-row">
                        <div class="form-group">
                          <label>比较运算符</label>
                          <select bind:value={condition.operator}>
                            {#each operators as op}
                              <option value={op.value}>{op.label}</option>
                            {/each}
                          </select>
                        </div>
                        <div class="form-group">
                          <label>阈值</label>
                          <input type="number" bind:value={condition.threshold} step="0.1" />
                        </div>
                      </div>
                    {/if}

                    {#if condition.ruleType === 'relative_change'}
                      <div class="form-row">
                        <div class="form-group">
                          <label>变化阈值 (%)</label>
                          <input type="number" bind:value={condition.relativeChangePercent} min="0" step="1" />
                        </div>
                        <div class="form-group">
                          <label>基线窗口</label>
                          <select bind:value={condition.baselineWindowSeconds}>
                            {#each timeRanges as tr}
                              <option value={tr.seconds}>{tr.label}</option>
                            {/each}
                          </select>
                        </div>
                      </div>
                    {/if}

                    {#if condition.ruleType === 'frequency_threshold'}
                      <div class="form-row">
                        <div class="form-group">
                          <label>比较运算符</label>
                          <select bind:value={condition.operator}>
                            {#each operators as op}
                              <option value={op.value}>{op.label}</option>
                            {/each}
                          </select>
                        </div>
                        <div class="form-group">
                          <label>幅值阈值</label>
                          <input type="number" bind:value={condition.threshold} step="0.1" />
                        </div>
                      </div>
                      <div class="form-row">
                        <div class="form-group">
                          <label>频率下限 (Hz)</label>
                          <input type="number" bind:value={condition.frequencyMin} min="0" step="10" />
                        </div>
                        <div class="form-group">
                          <label>频率上限 (Hz)</label>
                          <input type="number" bind:value={condition.frequencyMax} min="0" step="10" />
                        </div>
                      </div>
                    {/if}

                    {#if condition.ruleType === 'trend_rising'}
                      <div class="form-row">
                        <div class="form-group">
                          <label>时间范围</label>
                          <select bind:value={condition.trendTimeRange}>
                            {#each timeRanges as tr}
                              <option value={tr.value}>{tr.label}</option>
                            {/each}
                          </select>
                        </div>
                        <div class="form-group">
                          <label>最小 R²</label>
                          <input type="number" bind:value={condition.minRSquared} min="0" max="1" step="0.05" />
                        </div>
                      </div>
                    {/if}
                  </div>
                </div>
              {/each}
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn-secondary" on:click={closeForm}>取消</button>
          <button class="btn-primary" on:click={saveRule}>
            {editingRule ? '保存修改' : '创建规则'}
          </button>
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  .alarm-config-page {
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

  .header-right {
    display: flex;
    align-items: flex-end;
    gap: 16px;
    flex-wrap: wrap;
  }

  .device-selector {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .device-selector label {
    font-size: 13px;
    font-weight: 500;
    color: #374151;
  }

  .device-selector select {
    padding: 10px 14px;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    font-size: 14px;
    outline: none;
    min-width: 180px;
    transition: border-color 0.2s, box-shadow 0.2s;
  }

  .device-selector select:focus {
    border-color: #3b82f6;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
  }

  .add-btn {
    padding: 10px 20px;
    background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
    box-shadow: 0 4px 14px rgba(59, 130, 246, 0.4);
  }

  .add-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(59, 130, 246, 0.5);
  }

  .loading {
    text-align: center;
    padding: 60px;
    color: #6b7280;
    background: white;
    border-radius: 12px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  }

  .stats-bar {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 16px;
    margin-bottom: 24px;
  }

  .stat-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 16px;
    background: white;
    border-radius: 12px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  }

  .stat-icon {
    font-size: 28px;
  }

  .stat-value {
    font-size: 24px;
    font-weight: 800;
    color: #1f2937;
  }

  .stat-label {
    font-size: 12px;
    color: #6b7280;
    margin-left: auto;
  }

  .empty-state {
    text-align: center;
    padding: 80px 40px;
    background: white;
    border-radius: 12px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  }

  .empty-icon {
    font-size: 64px;
    margin-bottom: 16px;
  }

  .empty-state h3 {
    font-size: 20px;
    color: #1f2937;
    margin: 0 0 8px 0;
  }

  .empty-state p {
    font-size: 14px;
    color: #6b7280;
    margin: 0;
  }

  .rules-list {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .rule-card {
    background: white;
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    transition: all 0.2s;
    border-left: 4px solid #3b82f6;
  }

  .rule-card:hover {
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
  }

  .rule-card.disabled {
    opacity: 0.6;
    border-left-color: #9ca3af;
  }

  .rule-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 16px;
    gap: 16px;
  }

  .rule-title {
    display: flex;
    gap: 12px;
    flex: 1;
  }

  .rule-icon {
    width: 48px;
    height: 48px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 24px;
    flex-shrink: 0;
  }

  .rule-name {
    font-size: 18px;
    font-weight: 600;
    color: #1f2937;
    margin: 0 0 4px 0;
  }

  .rule-desc {
    font-size: 13px;
    color: #6b7280;
    margin: 0;
  }

  .rule-actions {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .level-badge {
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
  }

  .toggle-switch {
    position: relative;
    display: inline-block;
    width: 44px;
    height: 22px;
  }

  .toggle-switch.large {
    width: 52px;
    height: 28px;
  }

  .toggle-switch input {
    opacity: 0;
    width: 0;
    height: 0;
  }

  .toggle-slider {
    position: absolute;
    cursor: pointer;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: #d1d5db;
    transition: 0.3s;
    border-radius: 22px;
  }

  .toggle-slider:before {
    position: absolute;
    content: "";
    height: 16px;
    width: 16px;
    left: 3px;
    bottom: 3px;
    background-color: white;
    transition: 0.3s;
    border-radius: 50%;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  }

  .toggle-switch.large .toggle-slider:before {
    height: 22px;
    width: 22px;
  }

  input:checked + .toggle-slider {
    background-color: #3b82f6;
  }

  input:checked + .toggle-slider:before {
    transform: translateX(22px);
  }

  .toggle-switch.large input:checked + .toggle-slider:before {
    transform: translateX(24px);
  }

  .rule-conditions {
    background: #f9fafb;
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 16px;
  }

  .conditions-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
  }

  .conditions-title {
    font-size: 14px;
    font-weight: 600;
    color: #374151;
  }

  .logic-badge {
    padding: 2px 10px;
    background: #e5e7eb;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 700;
    color: #374151;
    letter-spacing: 0.5px;
  }

  .conditions-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .condition-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 12px;
    background: white;
    border-radius: 6px;
    border-left: 3px solid #3b82f6;
  }

  .condition-item.disabled {
    opacity: 0.5;
    border-left-color: #9ca3af;
  }

  .condition-type-icon {
    width: 32px;
    height: 32px;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    flex-shrink: 0;
  }

  .condition-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .condition-type {
    font-size: 12px;
    font-weight: 600;
    color: #6b7280;
  }

  .condition-desc {
    font-size: 14px;
    color: #1f2937;
    font-weight: 500;
  }

  .disabled-badge {
    padding: 2px 8px;
    background: #f3f4f6;
    color: #6b7280;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 500;
  }

  .rule-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 12px;
    padding-top: 16px;
    border-top: 1px solid #f3f4f6;
  }

  .rule-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
  }

  .meta-item {
    font-size: 12px;
    color: #9ca3af;
  }

  .rule-buttons {
    display: flex;
    gap: 8px;
  }

  .btn-secondary, .btn-danger, .btn-primary {
    padding: 8px 16px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    border: none;
  }

  .btn-secondary {
    background: #f3f4f6;
    color: #374151;
  }

  .btn-secondary:hover {
    background: #e5e7eb;
  }

  .btn-danger {
    background: #fee2e2;
    color: #dc2626;
  }

  .btn-danger:hover {
    background: #fecaca;
  }

  .btn-primary {
    background: #3b82f6;
    color: white;
  }

  .btn-primary:hover {
    background: #2563eb;
  }

  .modal-overlay {
    position: fixed;
    inset: 0;
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
    width: 100%;
    max-width: 900px;
    max-height: 90vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  }

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 20px 24px;
    border-bottom: 1px solid #f3f4f6;
  }

  .modal-header h2 {
    font-size: 20px;
    font-weight: 700;
    color: #1f2937;
    margin: 0;
  }

  .close-btn {
    width: 36px;
    height: 36px;
    border: none;
    background: #f3f4f6;
    border-radius: 8px;
    font-size: 24px;
    cursor: pointer;
    color: #6b7280;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s;
  }

  .close-btn:hover {
    background: #e5e7eb;
    color: #374151;
  }

  .modal-body {
    flex: 1;
    overflow-y: auto;
    padding: 24px;
  }

  .form-section {
    margin-bottom: 24px;
  }

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
  }

  .section-title {
    font-size: 16px;
    font-weight: 600;
    color: #1f2937;
    margin: 0 0 16px 0;
  }

  .section-header .section-title {
    margin: 0;
  }

  .add-condition-btn {
    padding: 8px 14px;
    background: #ecfdf5;
    color: #059669;
    border: 1px solid #a7f3d0;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
  }

  .add-condition-btn:hover {
    background: #d1fae5;
  }

  .form-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }

  .form-group {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .form-group.full-width {
    grid-column: 1 / -1;
  }

  .form-group label {
    font-size: 13px;
    font-weight: 500;
    color: #374151;
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

  .form-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin-top: 12px;
  }

  .level-buttons, .logic-buttons {
    display: flex;
    gap: 8px;
  }

  .level-btn, .logic-btn {
    flex: 1;
    padding: 10px 12px;
    border: 2px solid #d1d5db;
    background: white;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
  }

  .level-btn:hover, .logic-btn:hover {
    border-color: #9ca3af;
  }

  .level-btn.active {
    border-color: var(--level-color);
    background: var(--level-bg);
    color: var(--level-color);
  }

  .logic-btn.active {
    border-color: #3b82f6;
    background: #eff6ff;
    color: #3b82f6;
  }

  .conditions-form-list {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .condition-form-card {
    border: 2px solid #e5e7eb;
    border-radius: 12px;
    overflow: hidden;
  }

  .condition-form-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    background: #f9fafb;
    border-bottom: 1px solid #e5e7eb;
    flex-wrap: wrap;
    gap: 12px;
  }

  .condition-type-selector {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }

  .type-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    border: 2px solid #e5e7eb;
    background: white;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    color: #374151;
  }

  .type-btn:hover {
    border-color: #d1d5db;
  }

  .type-btn.active {
    border-color: var(--type-color);
    background: var(--type-color) + '15';
    color: var(--type-color);
  }

  .type-icon {
    font-size: 14px;
  }

  .condition-form-actions {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .remove-btn {
    width: 28px;
    height: 28px;
    border: none;
    background: #fee2e2;
    color: #dc2626;
    border-radius: 6px;
    cursor: pointer;
    font-size: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s;
  }

  .remove-btn:hover {
    background: #fecaca;
  }

  .condition-form-body {
    padding: 16px;
  }

  .modal-footer {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
    padding: 20px 24px;
    border-top: 1px solid #f3f4f6;
    background: #fafafa;
  }

  @media (max-width: 768px) {
    .form-grid {
      grid-template-columns: 1fr;
    }

    .form-row {
      grid-template-columns: 1fr;
    }

    .condition-type-selector {
      flex-direction: column;
      align-items: stretch;
    }

    .rule-header {
      flex-direction: column;
    }

    .rule-actions {
      width: 100%;
      justify-content: space-between;
    }

    .rule-footer {
      flex-direction: column;
      align-items: stretch;
    }

    .rule-buttons {
      justify-content: flex-end;
    }
  }
</style>
