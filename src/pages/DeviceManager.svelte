<script>
  import { onMount } from 'svelte';
  import { devicesApi, samplingApi } from '../api.js';
  import StatusIndicator from '../components/StatusIndicator.svelte';

  let devices = [];
  let loading = true;
  let searchKeyword = '';
  let statusFilter = 'all';
  let activeTab = 'devices';

  let showDeviceModal = false;
  let showMonitorModal = false;
  let editingDevice = null;
  let selectedDevice = null;

  let monitorPoints = [];
  let editingMonitor = null;

  let deviceForm = {
    name: '',
    code: '',
    location: '',
    ip_address: '',
    description: '',
    manufacturer: '',
    model: '',
    install_date: ''
  };

  let monitorForm = {
    name: '',
    position: '',
    direction: 'x',
    sensor_type: 'acceleration',
    sensitivity: 100,
    sample_rate: 1000,
    range: 10,
    alarm_threshold: 5,
    warning_threshold: 3
  };

  const statusConfig = {
    online: { label: '在线', color: '#10b981', status: 'normal' },
    offline: { label: '离线', color: '#6b7280', status: 'offline' },
    warning: { label: '警告', color: '#f59e0b', status: 'warning' },
    error: { label: '异常', color: '#ef4444', status: 'danger' }
  };

  const directionOptions = [
    { value: 'x', label: 'X轴 (水平)' },
    { value: 'y', label: 'Y轴 (垂直)' },
    { value: 'z', label: 'Z轴 (轴向)' }
  ];

  const sensorTypeOptions = [
    { value: 'acceleration', label: '加速度传感器' },
    { value: 'velocity', label: '速度传感器' },
    { value: 'displacement', label: '位移传感器' }
  ];

  $: filteredDevices = devices.filter(d => {
    const matchesSearch = !searchKeyword ||
      d.name.toLowerCase().includes(searchKeyword.toLowerCase()) ||
      d.code.toLowerCase().includes(searchKeyword.toLowerCase()) ||
      d.location.toLowerCase().includes(searchKeyword.toLowerCase());
    const matchesStatus = statusFilter === 'all' || d.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  $: statusStats = {
    total: devices.length,
    online: devices.filter(d => d.status === 'online').length,
    offline: devices.filter(d => d.status === 'offline').length,
    warning: devices.filter(d => d.status === 'warning').length,
    error: devices.filter(d => d.status === 'error').length
  };

  async function fetchDevices() {
    loading = true;
    try {
      const response = await devicesApi.getDevices({ page_size: 100 });
      devices = response.data?.items || response.data || [];
    } catch (error) {
      console.error('加载设备列表失败:', error);
      devices = [
        { id: 1, name: '电机-001', code: 'MOT-001', location: 'A车间-1号线', status: 'online', ip_address: '192.168.1.101', manufacturer: '西门子', model: '1LE0001', install_date: '2023-01-15', monitor_count: 3, last_maintenance: '2024-05-10' },
        { id: 2, name: '齿轮箱-001', code: 'GEAR-001', location: 'A车间-1号线', status: 'online', ip_address: '192.168.1.102', manufacturer: 'SEW', model: 'R77', install_date: '2023-01-15', monitor_count: 4, last_maintenance: '2024-04-20' },
        { id: 3, name: '泵组-001', code: 'PUMP-001', location: 'B车间-2号线', status: 'warning', ip_address: '192.168.1.103', manufacturer: '格兰富', model: 'CR32', install_date: '2023-03-20', monitor_count: 2, last_maintenance: '2024-06-01' },
        { id: 4, name: '风机-001', code: 'FAN-001', location: 'C车间-3号线', status: 'offline', ip_address: null, manufacturer: '格林瀚克', model: 'BDB-710', install_date: '2023-05-10', monitor_count: 2, last_maintenance: '2024-03-15' },
        { id: 5, name: '压缩机-001', code: 'COMP-001', location: 'D车间-4号线', status: 'error', ip_address: '192.168.1.105', manufacturer: '阿特拉斯', model: 'GA37', install_date: '2023-06-01', monitor_count: 6, last_maintenance: '2024-05-01' }
      ];
    } finally {
      loading = false;
    }
  }

  async function fetchMonitorPoints(deviceId) {
    try {
      const response = await samplingApi.listSamplingParams({ device_id: deviceId });
      monitorPoints = response.data?.items || response.data || [];
    } catch (error) {
      console.error('加载监测点失败:', error);
      monitorPoints = [
        { id: 1, name: '前端轴承', position: '电机驱动端', direction: 'x', sensor_type: 'acceleration', sensitivity: 100, sample_rate: 1000, range: 10, alarm_threshold: 5, warning_threshold: 3, status: 'active' },
        { id: 2, name: '后端轴承', position: '电机非驱动端', direction: 'y', sensor_type: 'acceleration', sensitivity: 100, sample_rate: 1000, range: 10, alarm_threshold: 5, warning_threshold: 3, status: 'active' },
        { id: 3, name: '机壳振动', position: '电机中部', direction: 'z', sensor_type: 'acceleration', sensitivity: 100, sample_rate: 500, range: 10, alarm_threshold: 4, warning_threshold: 2.5, status: 'active' }
      ];
    }
  }

  function openAddDevice() {
    editingDevice = null;
    deviceForm = {
      name: '',
      code: '',
      location: '',
      ip_address: '',
      description: '',
      manufacturer: '',
      model: '',
      install_date: new Date().toISOString().split('T')[0]
    };
    showDeviceModal = true;
  }

  function openEditDevice(device) {
    editingDevice = device;
    deviceForm = { ...device };
    showDeviceModal = true;
  }

  async function saveDevice() {
    try {
      if (editingDevice) {
        await devicesApi.updateDevice(editingDevice.id, deviceForm);
        devices = devices.map(d => d.id === editingDevice.id ? { ...d, ...deviceForm } : d);
      } else {
        const response = await devicesApi.createDevice(deviceForm);
        const newDevice = response.data || { ...deviceForm, id: Date.now(), status: 'offline', monitor_count: 0 };
        devices = [...devices, newDevice];
      }
      showDeviceModal = false;
    } catch (error) {
      console.error('保存设备失败:', error);
      if (editingDevice) {
        devices = devices.map(d => d.id === editingDevice.id ? { ...d, ...deviceForm } : d);
      } else {
        const newDevice = { ...deviceForm, id: Date.now(), status: 'offline', monitor_count: 0 };
        devices = [...devices, newDevice];
      }
      showDeviceModal = false;
    }
  }

  async function deleteDevice(device) {
    if (!confirm(`确定要删除设备 "${device.name}" 吗？`)) return;
    try {
      await devicesApi.deleteDevice(device.id);
      devices = devices.filter(d => d.id !== device.id);
    } catch (error) {
      console.error('删除设备失败:', error);
      devices = devices.filter(d => d.id !== device.id);
    }
  }

  function openMonitorConfig(device) {
    selectedDevice = device;
    fetchMonitorPoints(device.id);
    activeTab = 'monitor';
  }

  function openAddMonitor() {
    editingMonitor = null;
    monitorForm = {
      name: '',
      position: '',
      direction: 'x',
      sensor_type: 'acceleration',
      sensitivity: 100,
      sample_rate: 1000,
      range: 10,
      alarm_threshold: 5,
      warning_threshold: 3
    };
    showMonitorModal = true;
  }

  function openEditMonitor(monitor) {
    editingMonitor = monitor;
    monitorForm = { ...monitor };
    showMonitorModal = true;
  }

  async function saveMonitor() {
    try {
      const data = { ...monitorForm, device_id: selectedDevice.id };
      if (editingMonitor) {
        await samplingApi.updateSamplingParams(editingMonitor.id, data);
        monitorPoints = monitorPoints.map(m => m.id === editingMonitor.id ? { ...m, ...data } : m);
      } else {
        const response = await samplingApi.createSamplingParams(data);
        const newMonitor = response.data || { ...data, id: Date.now(), status: 'active' };
        monitorPoints = [...monitorPoints, newMonitor];
      }
      showMonitorModal = false;
    } catch (error) {
      console.error('保存监测点失败:', error);
      if (editingMonitor) {
        monitorPoints = monitorPoints.map(m => m.id === editingMonitor.id ? { ...m, ...monitorForm } : m);
      } else {
        const newMonitor = { ...monitorForm, id: Date.now(), status: 'active' };
        monitorPoints = [...monitorPoints, newMonitor];
      }
      showMonitorModal = false;
    }
  }

  async function deleteMonitor(monitor) {
    if (!confirm(`确定要删除监测点 "${monitor.name}" 吗？`)) return;
    try {
      await samplingApi.deleteSamplingParams(monitor.id);
      monitorPoints = monitorPoints.filter(m => m.id !== monitor.id);
    } catch (error) {
      console.error('删除监测点失败:', error);
      monitorPoints = monitorPoints.filter(m => m.id !== monitor.id);
    }
  }

  function getStatusStyle(status) {
    return statusConfig[status] || statusConfig.offline;
  }

  function getDirectionLabel(value) {
    return directionOptions.find(d => d.value === value)?.label || value;
  }

  function getSensorTypeLabel(value) {
    return sensorTypeOptions.find(s => s.value === value)?.label || value;
  }

  onMount(() => {
    fetchDevices();
  });
</script>

<div class="device-manager">
  <div class="header">
    <div>
      <h1 class="page-title">设备管理</h1>
      <p class="page-subtitle">管理所有监测设备及监测点配置</p>
    </div>
    <div class="header-actions">
      <button class="btn btn-primary" on:click={openAddDevice}>
        + 新增设备
      </button>
    </div>
  </div>

  <div class="tabs">
    <button class="tab-btn {activeTab === 'devices' ? 'active' : ''}" on:click={() => activeTab = 'devices'}>
      📋 设备列表
    </button>
    <button class="tab-btn {activeTab === 'monitor' ? 'active' : ''}" on:click={() => activeTab = 'monitor'} disabled={!selectedDevice}>
      📍 监测点配置 {selectedDevice ? `(${selectedDevice.name})` : ''}
    </button>
    <button class="tab-btn {activeTab === 'status' ? 'active' : ''}" on:click={() => activeTab = 'status'}>
      📊 状态统计
    </button>
  </div>

  {#if activeTab === 'devices'}
    <div class="stats-grid">
      <div class="stat-card total">
        <div class="stat-icon">📊</div>
        <div class="stat-content">
          <div class="stat-value">{statusStats.total}</div>
          <div class="stat-label">设备总数</div>
        </div>
      </div>
      <div class="stat-card online">
        <div class="stat-icon">✅</div>
        <div class="stat-content">
          <div class="stat-value">{statusStats.online}</div>
          <div class="stat-label">在线设备</div>
        </div>
      </div>
      <div class="stat-card warning">
        <div class="stat-icon">⚠️</div>
        <div class="stat-content">
          <div class="stat-value">{statusStats.warning}</div>
          <div class="stat-label">警告设备</div>
        </div>
      </div>
      <div class="stat-card error">
        <div class="stat-icon">❌</div>
        <div class="stat-content">
          <div class="stat-value">{statusStats.error + statusStats.offline}</div>
          <div class="stat-label">离线/异常</div>
        </div>
      </div>
    </div>

    <div class="filter-bar">
      <div class="search-box">
        <input
          type="text"
          bind:value={searchKeyword}
          placeholder="搜索设备名称、编码或位置..."
        />
      </div>
      <div class="status-filter">
        <button
          class="filter-btn {statusFilter === 'all' ? 'active' : ''}"
          on:click={() => statusFilter = 'all'}
        >全部</button>
        <button
          class="filter-btn {statusFilter === 'online' ? 'active' : ''}"
          on:click={() => statusFilter = 'online'}
        >在线</button>
        <button
          class="filter-btn {statusFilter === 'warning' ? 'active' : ''}"
          on:click={() => statusFilter = 'warning'}
        >警告</button>
        <button
          class="filter-btn {statusFilter === 'offline' ? 'active' : ''}"
          on:click={() => statusFilter = 'offline'}
        >离线</button>
        <button
          class="filter-btn {statusFilter === 'error' ? 'active' : ''}"
          on:click={() => statusFilter = 'error'}
        >异常</button>
      </div>
    </div>

    <div class="content-section">
      {#if loading}
        <div class="loading">加载中...</div>
      {:else if filteredDevices.length === 0}
        <div class="empty">暂无设备数据</div>
      {:else}
        <div class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>设备名称</th>
                <th>设备编码</th>
                <th>安装位置</th>
                <th>IP地址</th>
                <th>监测点</th>
                <th>状态</th>
                <th>上次维护</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {#each filteredDevices as device (device.id)}
                <tr>
                  <td>
                    <div class="device-name-cell">
                      <span class="device-icon">🏭</span>
                      <div>
                        <div class="device-name">{device.name}</div>
                        <div class="device-model">{device.manufacturer} {device.model}</div>
                      </div>
                    </div>
                  </td>
                  <td class="monospace">{device.code}</td>
                  <td>{device.location}</td>
                  <td class="monospace">{device.ip_address || '-'}</td>
                  <td>
                    <span class="badge-count">{device.monitor_count || 0}</span>
                  </td>
                  <td>
                    <StatusIndicator status={getStatusStyle(device.status).status} showLabel={true} pulse={device.status === 'online'} />
                  </td>
                  <td>{device.last_maintenance || '-'}</td>
                  <td>
                    <div class="action-buttons">
                      <button class="btn btn-sm btn-secondary" on:click={() => openMonitorConfig(device)} title="监测点配置">
                        📍
                      </button>
                      <button class="btn btn-sm btn-secondary" on:click={() => openEditDevice(device)} title="编辑">
                        ✏️
                      </button>
                      <button class="btn btn-sm btn-danger" on:click={() => deleteDevice(device)} title="删除">
                        🗑️
                      </button>
                    </div>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </div>
  {:else if activeTab === 'monitor'}
    <div class="content-section">
      {#if !selectedDevice}
        <div class="empty">请先选择一个设备</div>
      {:else}
        <div class="monitor-header">
          <div>
            <h2 class="section-title">{selectedDevice.name} - 监测点配置</h2>
            <p class="section-subtitle">共 {monitorPoints.length} 个监测点</p>
          </div>
          <button class="btn btn-primary" on:click={openAddMonitor}>
            + 新增监测点
          </button>
        </div>

        {#if monitorPoints.length === 0}
          <div class="empty">暂无监测点配置</div>
        {:else}
          <div class="monitor-grid">
            {#each monitorPoints as monitor (monitor.id)}
              <div class="monitor-card">
                <div class="monitor-card-header">
                  <div>
                    <h3 class="monitor-name">{monitor.name}</h3>
                    <span class="monitor-position">{monitor.position}</span>
                  </div>
                  <span class="monitor-status active">● 启用</span>
                </div>
                <div class="monitor-details">
                  <div class="detail-row">
                    <span class="detail-label">测量方向</span>
                    <span class="detail-value">{getDirectionLabel(monitor.direction)}</span>
                  </div>
                  <div class="detail-row">
                    <span class="detail-label">传感器类型</span>
                    <span class="detail-value">{getSensorTypeLabel(monitor.sensor_type)}</span>
                  </div>
                  <div class="detail-row">
                    <span class="detail-label">灵敏度</span>
                    <span class="detail-value">{monitor.sensitivity} mV/g</span>
                  </div>
                  <div class="detail-row">
                    <span class="detail-label">采样率</span>
                    <span class="detail-value">{monitor.sample_rate} Hz</span>
                  </div>
                  <div class="detail-row">
                    <span class="detail-label">量程</span>
                    <span class="detail-value">±{monitor.range} g</span>
                  </div>
                  <div class="detail-row">
                    <span class="detail-label">警告阈值</span>
                    <span class="detail-value warning">{monitor.warning_threshold} mm/s</span>
                  </div>
                  <div class="detail-row">
                    <span class="detail-label">报警阈值</span>
                    <span class="detail-value danger">{monitor.alarm_threshold} mm/s</span>
                  </div>
                </div>
                <div class="monitor-card-footer">
                  <button class="btn btn-sm btn-secondary" on:click={() => openEditMonitor(monitor)}>编辑</button>
                  <button class="btn btn-sm btn-danger" on:click={() => deleteMonitor(monitor)}>删除</button>
                </div>
              </div>
            {/each}
          </div>
        {/if}
      {/if}
    </div>
  {:else if activeTab === 'status'}
    <div class="content-section">
      <h2 class="section-title">设备状态统计</h2>
      
      <div class="status-detail-grid">
        <div class="status-detail-card normal">
          <div class="status-detail-header">
            <span class="status-icon">✅</span>
            <span class="status-title">在线设备</span>
            <span class="status-count">{statusStats.online}</span>
          </div>
          <div class="status-detail-list">
            {#each devices.filter(d => d.status === 'online') as device}
              <div class="status-item">
                <span class="status-item-name">{device.name}</span>
                <span class="status-item-code">{device.code}</span>
              </div>
            {/each}
          </div>
        </div>

        <div class="status-detail-card warning">
          <div class="status-detail-header">
            <span class="status-icon">⚠️</span>
            <span class="status-title">警告设备</span>
            <span class="status-count">{statusStats.warning}</span>
          </div>
          <div class="status-detail-list">
            {#each devices.filter(d => d.status === 'warning') as device}
              <div class="status-item">
                <span class="status-item-name">{device.name}</span>
                <span class="status-item-code">{device.code}</span>
              </div>
            {/each}
          </div>
        </div>

        <div class="status-detail-card error">
          <div class="status-detail-header">
            <span class="status-icon">❌</span>
            <span class="status-title">异常设备</span>
            <span class="status-count">{statusStats.error}</span>
          </div>
          <div class="status-detail-list">
            {#each devices.filter(d => d.status === 'error') as device}
              <div class="status-item">
                <span class="status-item-name">{device.name}</span>
                <span class="status-item-code">{device.code}</span>
              </div>
            {/each}
          </div>
        </div>

        <div class="status-detail-card offline">
          <div class="status-detail-header">
            <span class="status-icon">⚫</span>
            <span class="status-title">离线设备</span>
            <span class="status-count">{statusStats.offline}</span>
          </div>
          <div class="status-detail-list">
            {#each devices.filter(d => d.status === 'offline') as device}
              <div class="status-item">
                <span class="status-item-name">{device.name}</span>
                <span class="status-item-code">{device.code}</span>
              </div>
            {/each}
          </div>
        </div>
      </div>
    </div>
  {/if}

  {#if showDeviceModal}
    <div class="modal-overlay" on:click|stopPropagation={() => showDeviceModal = false}>
      <div class="modal" on:click|stopPropagation>
        <div class="modal-header">
          <h2>{editingDevice ? '编辑设备' : '新增设备'}</h2>
          <button class="modal-close" on:click={() => showDeviceModal = false}>×</button>
        </div>
        <div class="modal-body">
          <div class="form-grid">
            <div class="form-group">
              <label>设备名称 *</label>
              <input type="text" bind:value={deviceForm.name} placeholder="请输入设备名称" />
            </div>
            <div class="form-group">
              <label>设备编码 *</label>
              <input type="text" bind:value={deviceForm.code} placeholder="请输入设备编码" />
            </div>
            <div class="form-group">
              <label>安装位置 *</label>
              <input type="text" bind:value={deviceForm.location} placeholder="请输入安装位置" />
            </div>
            <div class="form-group">
              <label>IP地址</label>
              <input type="text" bind:value={deviceForm.ip_address} placeholder="如: 192.168.1.100" />
            </div>
            <div class="form-group">
              <label>制造商</label>
              <input type="text" bind:value={deviceForm.manufacturer} placeholder="请输入制造商" />
            </div>
            <div class="form-group">
              <label>型号</label>
              <input type="text" bind:value={deviceForm.model} placeholder="请输入型号" />
            </div>
            <div class="form-group">
              <label>安装日期</label>
              <input type="date" bind:value={deviceForm.install_date} />
            </div>
            <div class="form-group full-width">
              <label>描述</label>
              <textarea bind:value={deviceForm.description} placeholder="请输入设备描述" rows="3"></textarea>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" on:click={() => showDeviceModal = false}>取消</button>
          <button class="btn btn-primary" on:click={saveDevice} disabled={!deviceForm.name || !deviceForm.code || !deviceForm.location}>
            {editingDevice ? '保存修改' : '创建设备'}
          </button>
        </div>
      </div>
    </div>
  {/if}

  {#if showMonitorModal}
    <div class="modal-overlay" on:click|stopPropagation={() => showMonitorModal = false}>
      <div class="modal" on:click|stopPropagation>
        <div class="modal-header">
          <h2>{editingMonitor ? '编辑监测点' : '新增监测点'}</h2>
          <button class="modal-close" on:click={() => showMonitorModal = false}>×</button>
        </div>
        <div class="modal-body">
          <div class="form-grid">
            <div class="form-group">
              <label>监测点名称 *</label>
              <input type="text" bind:value={monitorForm.name} placeholder="如: 前端轴承" />
            </div>
            <div class="form-group">
              <label>安装位置 *</label>
              <input type="text" bind:value={monitorForm.position} placeholder="如: 电机驱动端" />
            </div>
            <div class="form-group">
              <label>测量方向</label>
              <select bind:value={monitorForm.direction}>
                {#each directionOptions as opt}
                  <option value={opt.value}>{opt.label}</option>
                {/each}
              </select>
            </div>
            <div class="form-group">
              <label>传感器类型</label>
              <select bind:value={monitorForm.sensor_type}>
                {#each sensorTypeOptions as opt}
                  <option value={opt.value}>{opt.label}</option>
                {/each}
              </select>
            </div>
            <div class="form-group">
              <label>灵敏度 (mV/g)</label>
              <input type="number" bind:value={monitorForm.sensitivity} min="1" step="10" />
            </div>
            <div class="form-group">
              <label>采样率 (Hz)</label>
              <input type="number" bind:value={monitorForm.sample_rate} min="10" step="100" />
            </div>
            <div class="form-group">
              <label>量程 (±g)</label>
              <input type="number" bind:value={monitorForm.range} min="1" step="1" />
            </div>
            <div class="form-group">
              <label>警告阈值 (mm/s)</label>
              <input type="number" bind:value={monitorForm.warning_threshold} min="0" step="0.1" />
            </div>
            <div class="form-group">
              <label>报警阈值 (mm/s)</label>
              <input type="number" bind:value={monitorForm.alarm_threshold} min="0" step="0.1" />
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" on:click={() => showMonitorModal = false}>取消</button>
          <button class="btn btn-primary" on:click={saveMonitor} disabled={!monitorForm.name || !monitorForm.position}>
            {editingMonitor ? '保存修改' : '创建监测点'}
          </button>
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  .device-manager {
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
    font-size: 20px;
    font-weight: 600;
    color: #1f2937;
    margin: 0 0 4px 0;
  }

  .section-subtitle {
    font-size: 13px;
    color: #6b7280;
    margin: 0;
  }

  .header-actions {
    display: flex;
    gap: 12px;
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

  .tabs {
    display: flex;
    gap: 8px;
    margin-bottom: 24px;
    border-bottom: 2px solid #e5e7eb;
    padding-bottom: 0;
  }

  .tab-btn {
    padding: 12px 24px;
    background: none;
    border: none;
    border-bottom: 3px solid transparent;
    color: #6b7280;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    margin-bottom: -2px;
  }

  .tab-btn:hover:not(:disabled) {
    color: #3b82f6;
  }

  .tab-btn.active {
    color: #3b82f6;
    border-bottom-color: #3b82f6;
  }

  .tab-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px;
    margin-bottom: 24px;
  }

  .stat-card {
    display: flex;
    align-items: center;
    padding: 20px;
    background: white;
    border-radius: 12px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    transition: transform 0.2s, box-shadow 0.2s;
  }

  .stat-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
  }

  .stat-icon {
    font-size: 32px;
    margin-right: 16px;
  }

  .stat-content {
    flex: 1;
  }

  .stat-value {
    font-size: 28px;
    font-weight: 700;
    color: #1f2937;
    line-height: 1.2;
  }

  .stat-label {
    font-size: 13px;
    color: #6b7280;
    margin-top: 4px;
  }

  .stat-card.total .stat-value { color: #3b82f6; }
  .stat-card.online .stat-value { color: #10b981; }
  .stat-card.warning .stat-value { color: #f59e0b; }
  .stat-card.error .stat-value { color: #ef4444; }

  .filter-bar {
    display: flex;
    gap: 16px;
    margin-bottom: 20px;
    flex-wrap: wrap;
    align-items: center;
  }

  .search-box {
    flex: 1;
    min-width: 250px;
  }

  .search-box input {
    width: 100%;
    padding: 10px 16px;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    font-size: 14px;
    outline: none;
    transition: border-color 0.2s, box-shadow 0.2s;
  }

  .search-box input:focus {
    border-color: #3b82f6;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
  }

  .status-filter {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }

  .filter-btn {
    padding: 8px 16px;
    border: 1px solid #d1d5db;
    background: white;
    border-radius: 8px;
    font-size: 13px;
    cursor: pointer;
    transition: all 0.2s;
  }

  .filter-btn:hover {
    border-color: #3b82f6;
    color: #3b82f6;
  }

  .filter-btn.active {
    background: #3b82f6;
    color: white;
    border-color: #3b82f6;
  }

  .content-section {
    background: white;
    border-radius: 12px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    overflow: hidden;
  }

  .table-container {
    overflow-x: auto;
  }

  .data-table {
    width: 100%;
    border-collapse: collapse;
  }

  .data-table th,
  .data-table td {
    padding: 14px 16px;
    text-align: left;
    border-bottom: 1px solid #f3f4f6;
  }

  .data-table th {
    background: #f9fafb;
    font-weight: 600;
    font-size: 13px;
    color: #374151;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .data-table tr:hover {
    background: #f9fafb;
  }

  .device-name-cell {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .device-icon {
    font-size: 24px;
  }

  .device-name {
    font-weight: 600;
    color: #1f2937;
  }

  .device-model {
    font-size: 12px;
    color: #6b7280;
  }

  .monospace {
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
    font-size: 13px;
    color: #374151;
  }

  .badge-count {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 24px;
    height: 24px;
    padding: 0 8px;
    background: #eff6ff;
    color: #3b82f6;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 600;
  }

  .action-buttons {
    display: flex;
    gap: 8px;
  }

  .monitor-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    padding: 20px;
    border-bottom: 1px solid #f3f4f6;
    flex-wrap: wrap;
    gap: 12px;
  }

  .monitor-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 16px;
    padding: 20px;
  }

  .monitor-card {
    background: #f9fafb;
    border-radius: 12px;
    padding: 16px;
    border: 1px solid #e5e7eb;
    transition: all 0.2s;
  }

  .monitor-card:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    border-color: #3b82f6;
  }

  .monitor-card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 16px;
  }

  .monitor-name {
    font-size: 16px;
    font-weight: 600;
    color: #1f2937;
    margin: 0 0 4px 0;
  }

  .monitor-position {
    font-size: 12px;
    color: #6b7280;
  }

  .monitor-status {
    font-size: 12px;
    font-weight: 500;
  }

  .monitor-status.active {
    color: #10b981;
  }

  .monitor-details {
    margin-bottom: 16px;
  }

  .detail-row {
    display: flex;
    justify-content: space-between;
    padding: 6px 0;
    border-bottom: 1px dashed #e5e7eb;
  }

  .detail-row:last-child {
    border-bottom: none;
  }

  .detail-label {
    font-size: 12px;
    color: #6b7280;
  }

  .detail-value {
    font-size: 12px;
    font-weight: 500;
    color: #374151;
  }

  .detail-value.warning {
    color: #f59e0b;
  }

  .detail-value.danger {
    color: #ef4444;
  }

  .monitor-card-footer {
    display: flex;
    gap: 8px;
    padding-top: 12px;
    border-top: 1px solid #e5e7eb;
  }

  .monitor-card-footer .btn {
    flex: 1;
    justify-content: center;
  }

  .status-detail-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 16px;
    padding: 20px;
  }

  .status-detail-card {
    background: #f9fafb;
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid #e5e7eb;
  }

  .status-detail-card.normal {
    border-top: 4px solid #10b981;
  }

  .status-detail-card.warning {
    border-top: 4px solid #f59e0b;
  }

  .status-detail-card.error {
    border-top: 4px solid #ef4444;
  }

  .status-detail-card.offline {
    border-top: 4px solid #6b7280;
  }

  .status-detail-header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 16px;
    background: white;
    border-bottom: 1px solid #e5e7eb;
  }

  .status-icon {
    font-size: 20px;
  }

  .status-title {
    flex: 1;
    font-weight: 600;
    color: #1f2937;
  }

  .status-count {
    font-size: 24px;
    font-weight: 700;
    color: #1f2937;
  }

  .status-detail-list {
    max-height: 300px;
    overflow-y: auto;
  }

  .status-item {
    display: flex;
    justify-content: space-between;
    padding: 12px 16px;
    border-bottom: 1px solid #f3f4f6;
  }

  .status-item:last-child {
    border-bottom: none;
  }

  .status-item:hover {
    background: white;
  }

  .status-item-name {
    font-weight: 500;
    color: #374151;
  }

  .status-item-code {
    font-size: 12px;
    color: #6b7280;
    font-family: monospace;
  }

  .loading, .empty {
    text-align: center;
    padding: 60px;
    color: #6b7280;
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
    max-width: 600px;
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

  .form-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }

  .form-group {
    display: flex;
    flex-direction: column;
  }

  .form-group.full-width {
    grid-column: 1 / -1;
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
    .form-grid {
      grid-template-columns: 1fr;
    }

    .device-manager {
      padding: 16px;
    }

    .monitor-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
