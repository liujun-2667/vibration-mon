<script>
  import { onMount, onDestroy } from 'svelte';
  import { devices, currentDevice, unacknowledgedAlarmCount, deviceStatusCounts, selectDevice } from './store.js';
  import { devicesApi, systemApi } from './api.js';
  import Dashboard from './pages/Dashboard.svelte';
  import DeviceAnalysis from './pages/DeviceAnalysis.svelte';
  import SignalSimulator from './pages/SignalSimulator.svelte';
  import FeatureCalculator from './pages/FeatureCalculator.svelte';
  import TrendMonitor from './pages/TrendMonitor.svelte';
  import AlarmConfig from './pages/AlarmConfig.svelte';
  import DeviceManager from './pages/DeviceManager.svelte';
  import DataReplay from './pages/DataReplay.svelte';
  import ReportGenerator from './pages/ReportGenerator.svelte';

  let currentPage = 'dashboard';
  let sidebarCollapsed = false;
  let backendConnected = false;
  let ws = null;
  let selectedDeviceId = null;

  const menuItems = [
    { id: 'dashboard', name: '监控概览', icon: '📊' },
    { id: 'devices', name: '设备管理', icon: '📡' },
    { id: 'analysis', name: '数据分析', icon: '📈' },
    { id: 'trend', name: '趋势监测', icon: '📉' },
    { id: 'feature', name: '特征频率', icon: '🔢' },
    { id: 'simulator', name: '信号模拟', icon: '🎛️' },
    { id: 'replay', name: '数据回放', icon: '▶️' },
    { id: 'alarms', name: '报警中心', icon: '🔔' },
    { id: 'alarm-config', name: '报警规则', icon: '⚙️' },
    { id: 'reports', name: '报告生成', icon: '📄' },
  ];

  $: unacknowledged = $unacknowledgedAlarmCount;
  $: statusCounts = $deviceStatusCounts;

  function navigate(page, params = {}) {
    currentPage = page;
    if (params.deviceId) {
      selectedDeviceId = params.deviceId;
    }
    const hash = params.deviceId ? `${page}/${params.deviceId}` : page;
    window.location.hash = hash;
  }

  function handleHashChange() {
    const hash = window.location.hash.slice(1) || 'dashboard';
    const parts = hash.split('/');
    const page = parts[0];
    const deviceId = parts[1] ? parseInt(parts[1]) : null;
    
    if (menuItems.some(item => item.id === page)) {
      currentPage = page;
      if (deviceId) {
        selectedDeviceId = deviceId;
      }
    }
  }

  async function loadDevices() {
    try {
      const response = await devicesApi.getDevices({ page_size: 100 });
      if (response.success && response.data) {
        devices.set(response.data.items || response.data);
        if (response.data.items && response.data.items.length > 0 && !$currentDevice) {
          selectDevice(response.data.items[0]);
        }
      }
    } catch (error) {
      console.error('加载设备列表失败:', error);
    }
  }

  async function checkBackend() {
    try {
      await systemApi.healthCheck();
      backendConnected = true;
    } catch (error) {
      backendConnected = false;
      console.error('后端连接失败:', error);
    }
  }

  function handleDeviceClick(device) {
    selectDevice(device);
    navigate('analysis', { deviceId: device.id });
  }

  function handleNavigate(event) {
    const { page, deviceId } = event.detail;
    navigate(page, { deviceId });
  }

  onMount(() => {
    handleHashChange();
    window.addEventListener('hashchange', handleHashChange);
    window.addEventListener('navigate', handleNavigate);
    checkBackend();
    loadDevices();

    const healthCheckInterval = setInterval(checkBackend, 30000);

    onDestroy(() => {
      window.removeEventListener('hashchange', handleHashChange);
      window.removeEventListener('navigate', handleNavigate);
      clearInterval(healthCheckInterval);
      if (ws) {
        ws.close();
      }
    });
  });

  function getStatusClass(status) {
    switch (status) {
      case 'online': return 'status-online';
      case 'warning': return 'status-warning';
      case 'offline': return 'status-offline';
      default: return 'status-offline';
    }
  }

  function getStatusText(status) {
    switch (status) {
      case 'online': return '在线';
      case 'warning': return '警告';
      case 'offline': return '离线';
      default: return '未知';
    }
  }
</script>

<div class="app-container">
  <aside class="sidebar" class:collapsed={sidebarCollapsed}>
    <div class="sidebar-header">
      <div class="logo">
        <span class="logo-icon">📡</span>
        {#if !sidebarCollapsed}
          <span class="logo-text">振动监测系统</span>
        {/if}
      </div>
      <button class="toggle-btn" on:click={() => sidebarCollapsed = !sidebarCollapsed}>
        {sidebarCollapsed ? '→' : '←'}
      </button>
    </div>

    <nav class="nav-menu">
      {#each menuItems as item}
        <button
          class="nav-item"
          class:active={currentPage === item.id}
          on:click={() => navigate(item.id)}
          title={item.name}
        >
          <span class="nav-icon">{item.icon}</span>
          {#if !sidebarCollapsed}
            <span class="nav-text">{item.name}</span>
          {/if}
          {#if item.id === 'alarms' && unacknowledged > 0 && !sidebarCollapsed}
            <span class="badge">{unacknowledged > 99 ? '99+' : unacknowledged}</span>
          {/if}
        </button>
      {/each}
    </nav>

    {#if !sidebarCollapsed}
      <div class="sidebar-footer">
        <div class="device-list-header">
          <h4>设备列表</h4>
          <div class="device-status-summary">
            <span class="status-dot online"></span> {statusCounts.online}
            <span class="status-dot warning"></span> {statusCounts.warning}
            <span class="status-dot offline"></span> {statusCounts.offline}
          </div>
        </div>
        <div class="device-list">
          {#each $devices as device}
            <div
              class="device-item"
              class:selected={$currentDevice && $currentDevice.id === device.id}
              on:click={() => handleDeviceClick(device)}
            >
              <span class="device-status {getStatusClass(device.status)}"></span>
              <span class="device-name">{device.name}</span>
              {#if device.status === 'warning'}
                <span class="device-warning">⚠️</span>
              {/if}
            </div>
          {/each}
        </div>
      </div>
    {/if}

    <div class="sidebar-bottom">
      <div class="connection-status">
        <span class="status-dot {backendConnected ? 'online' : 'offline'}"></span>
        {#if !sidebarCollapsed}
          <span>{backendConnected ? '后端已连接' : '后端未连接'}</span>
        {/if}
      </div>
    </div>
  </aside>

  <main class="main-content">
    <header class="top-header">
      <div class="header-left">
        <h1>{menuItems.find(m => m.id === currentPage)?.name || '监控概览'}</h1>
      </div>
      <div class="header-right">
        {#if $currentDevice}
          <div class="current-device">
            <span class="status-dot {getStatusClass($currentDevice.status)}"></span>
            <span>{$currentDevice.name}</span>
            <span class="device-code">({$currentDevice.code})</span>
          </div>
        {/if}
        {#if unacknowledged > 0}
          <button class="alarm-btn" on:click={() => navigate('alarms')}>
            🔔 {unacknowledged} 条未处理报警
          </button>
        {/if}
      </div>
    </header>

    <div class="page-content">
      {#if currentPage === 'dashboard'}
        <Dashboard />
      {:else if currentPage === 'analysis'}
        <DeviceAnalysis deviceId={selectedDeviceId || $currentDevice?.id || 1} />
      {:else if currentPage === 'simulator'}
        <SignalSimulator />
      {:else if currentPage === 'feature'}
        <FeatureCalculator />
      {:else if currentPage === 'trend'}
        <TrendMonitor />
      {:else if currentPage === 'alarm-config'}
        <AlarmConfig />
      {:else if currentPage === 'devices'}
        <DeviceManager />
      {:else if currentPage === 'replay'}
        <DataReplay />
      {:else if currentPage === 'reports'}
        <ReportGenerator />
      {:else if currentPage === 'alarms'}
        <div class="placeholder-page">
          <div class="placeholder-icon">🔔</div>
          <h2>报警中心</h2>
          <p>查看和处理所有报警记录</p>
          <div class="card-grid">
            <div class="stat-card">
              <div class="stat-icon">📊</div>
              <div class="stat-content">
                <div class="stat-label">报警总数</div>
                <div class="stat-value text-primary">{statusCounts.total || 0}</div>
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-icon">⚠️</div>
              <div class="stat-content">
                <div class="stat-label">未处理</div>
                <div class="stat-value text-warning">{unacknowledged}</div>
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-icon">✅</div>
              <div class="stat-content">
                <div class="stat-label">已处理</div>
                <div class="stat-value text-success">{(statusCounts.total || 0) - unacknowledged}</div>
              </div>
            </div>
          </div>
        </div>
      {:else}
        <div class="placeholder-page">
          <div class="placeholder-icon">📋</div>
          <h2>页面开发中</h2>
          <p>该功能正在开发中，敬请期待</p>
        </div>
      {/if}
    </div>
  </main>
</div>

<style>
  .app-container {
    display: flex;
    height: 100vh;
    overflow: hidden;
    background: var(--color-gray-50);
    font-family: var(--font-family);
  }

  .sidebar {
    width: var(--sidebar-width);
    background: linear-gradient(180deg, var(--color-gray-800) 0%, var(--color-gray-900) 100%);
    color: var(--color-gray-200);
    display: flex;
    flex-direction: column;
    transition: width var(--transition-slow);
    flex-shrink: 0;
  }

  .sidebar.collapsed {
    width: var(--sidebar-width-collapsed);
  }

  .sidebar-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--spacing-4);
    border-bottom: var(--border-width) solid var(--color-gray-700);
  }

  .logo {
    display: flex;
    align-items: center;
    gap: var(--spacing-2);
    font-weight: 600;
    font-size: var(--font-size-lg);
  }

  .logo-icon {
    font-size: var(--font-size-2xl);
  }

  .toggle-btn {
    background: transparent;
    border: none;
    color: var(--color-gray-400);
    cursor: pointer;
    font-size: var(--font-size-base);
    padding: var(--spacing-1) var(--spacing-2);
    border-radius: var(--radius-sm);
    transition: all var(--transition-fast);
  }

  .toggle-btn:hover {
    background: var(--color-gray-700);
    color: var(--color-gray-200);
  }

  .nav-menu {
    flex: 1;
    padding: var(--spacing-3) var(--spacing-2);
    overflow-y: auto;
  }

  .nav-item {
    display: flex;
    align-items: center;
    gap: var(--spacing-3);
    width: 100%;
    padding: var(--spacing-3) var(--spacing-3);
    background: transparent;
    border: none;
    color: var(--color-gray-400);
    cursor: pointer;
    border-radius: var(--radius-md);
    margin-bottom: var(--spacing-1);
    transition: all var(--transition-fast);
    text-align: left;
  }

  .nav-item:hover {
    background: var(--color-gray-700);
    color: var(--color-gray-200);
  }

  .nav-item.active {
    background: linear-gradient(90deg, var(--color-primary) 0%, var(--color-primary-dark) 100%);
    color: white;
    box-shadow: var(--shadow-primary);
  }

  .nav-icon {
    font-size: var(--font-size-xl);
    width: 24px;
    text-align: center;
  }

  .nav-text {
    flex: 1;
    font-size: var(--font-size-base);
    font-weight: 500;
  }

  .badge {
    background: var(--color-danger);
    color: white;
    font-size: var(--font-size-xs);
    font-weight: 600;
    padding: 2px var(--spacing-2);
    border-radius: var(--radius-full);
    min-width: 20px;
    text-align: center;
  }

  .sidebar-footer {
    border-top: var(--border-width) solid var(--color-gray-700);
    padding: var(--spacing-3);
    max-height: 300px;
    display: flex;
    flex-direction: column;
  }

  .device-list-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--spacing-2);
  }

  .device-list-header h4 {
    margin: 0;
    font-size: var(--font-size-xs);
    color: var(--color-gray-400);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .device-status-summary {
    display: flex;
    align-items: center;
    gap: var(--spacing-2);
    font-size: var(--font-size-xs);
    color: var(--color-gray-400);
  }

  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    display: inline-block;
  }

  .status-dot.online {
    background: var(--color-success);
    box-shadow: 0 0 8px var(--color-success);
  }

  .status-dot.warning {
    background: var(--color-warning);
    box-shadow: 0 0 8px var(--color-warning);
  }

  .status-dot.offline {
    background: var(--color-gray-500);
  }

  .device-list {
    overflow-y: auto;
    flex: 1;
  }

  .device-item {
    display: flex;
    align-items: center;
    gap: var(--spacing-2);
    padding: var(--spacing-2) var(--spacing-2);
    border-radius: var(--radius-sm);
    cursor: pointer;
    transition: all var(--transition-fast);
    margin-bottom: 2px;
  }

  .device-item:hover {
    background: var(--color-gray-700);
  }

  .device-item.selected {
    background: var(--color-primary-dark);
    border-left: 3px solid var(--color-primary);
  }

  .device-status {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .status-online {
    background: var(--color-success);
    box-shadow: 0 0 6px var(--color-success);
  }

  .status-warning {
    background: var(--color-warning);
    box-shadow: 0 0 6px var(--color-warning);
  }

  .status-offline {
    background: var(--color-gray-500);
  }

  .device-name {
    flex: 1;
    font-size: var(--font-size-sm);
    color: var(--color-gray-300);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .device-warning {
    font-size: var(--font-size-sm);
  }

  .sidebar-bottom {
    padding: var(--spacing-3);
    border-top: var(--border-width) solid var(--color-gray-700);
  }

  .connection-status {
    display: flex;
    align-items: center;
    gap: var(--spacing-2);
    font-size: var(--font-size-xs);
    color: var(--color-gray-400);
  }

  .main-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .top-header {
    background: var(--color-white);
    padding: var(--spacing-4) var(--spacing-6);
    border-bottom: var(--border-width) solid var(--color-gray-200);
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: var(--shadow-sm);
  }

  .header-left h1 {
    margin: 0;
    font-size: var(--font-size-xl);
    font-weight: 600;
    color: var(--color-gray-900);
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: var(--spacing-4);
  }

  .current-device {
    display: flex;
    align-items: center;
    gap: var(--spacing-2);
    padding: var(--spacing-2) var(--spacing-4);
    background: var(--color-gray-100);
    border-radius: var(--radius-md);
    font-size: var(--font-size-base);
  }

  .device-code {
    color: var(--color-gray-500);
  }

  .alarm-btn {
    display: flex;
    align-items: center;
    gap: var(--spacing-2);
    padding: var(--spacing-2) var(--spacing-4);
    background: var(--color-danger-lighter);
    color: var(--color-danger-dark);
    border: 1px solid var(--color-danger-light);
    border-radius: var(--radius-md);
    cursor: pointer;
    font-size: var(--font-size-base);
    font-weight: 500;
    transition: all var(--transition-fast);
  }

  .alarm-btn:hover {
    background: var(--color-danger-lighter);
  }

  .page-content {
    flex: 1;
    overflow-y: auto;
  }

  .placeholder-page {
    padding: var(--spacing-6);
    min-height: calc(100vh - var(--header-height));
  }

  .placeholder-page .placeholder-icon {
    font-size: 64px;
    margin-bottom: var(--spacing-4);
    opacity: 0.5;
  }

  .placeholder-page h2 {
    margin: 0 0 var(--spacing-2) 0;
    font-size: var(--font-size-3xl);
    color: var(--color-gray-900);
  }

  .placeholder-page p {
    margin: 0 0 var(--spacing-8) 0;
    color: var(--color-gray-500);
    font-size: var(--font-size-lg);
  }

  .card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: var(--spacing-5);
    max-width: 900px;
    margin: 0 auto;
  }

  .stat-card {
    display: flex;
    align-items: center;
    gap: var(--spacing-4);
    padding: var(--spacing-6);
    background: var(--color-white);
    border-radius: var(--radius-lg);
    border: var(--border-width) solid var(--color-gray-200);
    box-shadow: var(--shadow-md);
    transition: all var(--transition-normal);
  }

  .stat-card:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-lg);
  }

  .stat-icon {
    font-size: var(--font-size-4xl);
  }

  .stat-content {
    text-align: left;
  }

  .stat-label {
    font-size: var(--font-size-sm);
    color: var(--color-gray-500);
    margin-bottom: var(--spacing-1);
  }

  .stat-value {
    font-size: var(--font-size-4xl);
    font-weight: 700;
    color: var(--color-gray-900);
    line-height: 1.2;
  }

  @media (max-width: 768px) {
    .sidebar {
      position: absolute;
      height: 100%;
      z-index: 100;
    }

    .top-header {
      padding: var(--spacing-3) var(--spacing-4);
    }

    .page-content {
      padding: var(--spacing-4);
    }

    .placeholder-page {
      padding: var(--spacing-4);
    }
  }
</style>
