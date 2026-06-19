<script>
  import { onMount } from 'svelte';

  let devices = [];
  let loading = true;
  let searchKeyword = '';
  let statusFilter = 'all';

  const statusConfig = {
    online: { label: '在线', color: '#10b981', bgColor: 'bg-green-500' },
    offline: { label: '离线', color: '#6b7280', bgColor: 'bg-gray-500' },
    warning: { label: '警告', color: '#f59e0b', bgColor: 'bg-yellow-500' },
    error: { label: '异常', color: '#ef4444', bgColor: 'bg-red-500' }
  };

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
      const response = await fetch('/api/v1/devices?page_size=100');
      const data = await response.json();
      devices = data.items || [];
    } catch (error) {
      devices = [
        { id: 1, name: '电机-001', code: 'MOT-001', location: 'A车间-1号线', status: 'online', sensor_count: 2, ip_address: '192.168.1.101' },
        { id: 2, name: '齿轮箱-001', code: 'GEAR-001', location: 'A车间-1号线', status: 'online', sensor_count: 3, ip_address: '192.168.1.102' },
        { id: 3, name: '泵组-001', code: 'PUMP-001', location: 'B车间-2号线', status: 'warning', sensor_count: 1, ip_address: '192.168.1.103' },
        { id: 4, name: '风机-001', code: 'FAN-001', location: 'C车间-3号线', status: 'offline', sensor_count: 2, ip_address: null }
      ];
    } finally {
      loading = false;
    }
  }

  function getStatusStyle(status) {
    return statusConfig[status] || statusConfig.offline;
  }

  function viewDevice(device) {
    window.dispatchEvent(new CustomEvent('navigate', { detail: { page: 'analysis', deviceId: device.id } }));
  }

  onMount(() => {
    fetchDevices();
  });
</script>

<div class="dashboard">
  <div class="header">
    <h1 class="page-title">设备总览</h1>
    <p class="page-subtitle">实时监控所有设备的运行状态</p>
  </div>

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
        <div class="stat-value">{statusStats.offline + statusStats.error}</div>
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

  <div class="device-list">
    {#if loading}
      <div class="loading">加载中...</div>
    {:else if filteredDevices.length === 0}
      <div class="empty">暂无设备数据</div>
    {:else}
      <div class="device-grid">
        {#each filteredDevices as device (device.id)}
          <div class="device-card" on:click={() => viewDevice(device)}>
            <div class="device-header">
              <div class="device-name">{device.name}</div>
              <span class="status-badge" style="background-color: {getStatusStyle(device.status).color}20; color: {getStatusStyle(device.status).color}">
                {getStatusStyle(device.status).label}
              </span>
            </div>
            <div class="device-info">
              <div class="info-row">
                <span class="info-label">设备编码:</span>
                <span class="info-value">{device.code}</span>
              </div>
              <div class="info-row">
                <span class="info-label">安装位置:</span>
                <span class="info-value">{device.location}</span>
              </div>
              <div class="info-row">
                <span class="info-label">IP地址:</span>
                <span class="info-value">{device.ip_address || '-'}</span>
              </div>
              <div class="info-row">
                <span class="info-label">传感器:</span>
                <span class="info-value">{device.sensor_count} 个</span>
              </div>
            </div>
            <div class="device-footer">
              <span class="view-detail">查看详情 →</span>
            </div>
          </div>
        {/each}
      </div>
    {/if}
  </div>
</div>

<style>
  .dashboard {
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
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
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

  .device-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 16px;
  }

  .device-card {
    background: white;
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    cursor: pointer;
    transition: transform 0.2s, box-shadow 0.2s;
    border: 2px solid transparent;
  }

  .device-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
    border-color: #3b82f6;
  }

  .device-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
  }

  .device-name {
    font-size: 18px;
    font-weight: 600;
    color: #1f2937;
  }

  .status-badge {
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 500;
  }

  .device-info {
    margin-bottom: 16px;
  }

  .info-row {
    display: flex;
    justify-content: space-between;
    padding: 6px 0;
    border-bottom: 1px solid #f3f4f6;
  }

  .info-row:last-child {
    border-bottom: none;
  }

  .info-label {
    font-size: 13px;
    color: #6b7280;
  }

  .info-value {
    font-size: 13px;
    color: #374151;
    font-weight: 500;
  }

  .device-footer {
    padding-top: 12px;
    border-top: 1px solid #f3f4f6;
  }

  .view-detail {
    font-size: 13px;
    color: #3b82f6;
    font-weight: 500;
  }

  .loading, .empty {
    text-align: center;
    padding: 40px;
    color: #6b7280;
    background: white;
    border-radius: 12px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  }
</style>
