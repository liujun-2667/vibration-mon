<script>
  import { onMount, onDestroy } from 'svelte';
  import { devices as devicesStore } from '../store.js';
  import { monitorApi, devicesApi } from '../api.js';
  import DeviceMonitorCard from '../components/DeviceMonitorCard.svelte';
  import HealthTrendSidebar from '../components/HealthTrendSidebar.svelte';
  import Toast from '../components/Toast.svelte';

  const MAX_SELECTED = 4;
  const TOAST_DURATION = 8000;

  const LAYOUT_OPTIONS = [
    { value: 'grid-2', label: '网格2列', icon: '⊞' },
    { value: 'grid-1', label: '网格1列', icon: '⬛' },
    { value: 'compact', label: '紧凑列表', icon: '≡' },
  ];

  let allDevices = [];
  let selectedIds = [];
  let summaryMap = {};
  let trendDeviceId = null;
  let toasts = [];
  let activeToastMap = {};
  let toastTimers = {};
  let toastSeq = 1;
  let layout = 'grid-2';

  $: trendDevice = allDevices.find((d) => d.id === trendDeviceId) || {};

  function toggleDevice(id) {
    id = Number(id);
    if (selectedIds.includes(id)) {
      selectedIds = selectedIds.filter((x) => x !== id);
      if (trendDeviceId === id) {
        trendDeviceId = selectedIds[0] != null ? selectedIds[0] : null;
      }
    } else {
      if (selectedIds.length >= MAX_SELECTED) return;
      selectedIds = [...selectedIds, id];
      if (trendDeviceId == null) trendDeviceId = id;
    }
  }

  $: selectedDevices = selectedIds.map((id) => {
    const base = allDevices.find((x) => x.id === id) || {};
    const sum = summaryMap[id] || {};
    return {
      id,
      name: base.name || sum.device_name || `设备${id}`,
      code: base.code || sum.device_code || '',
    };
  });

  function getChipStatus(id) {
    const sum = summaryMap[id];
    if (!sum) return 'unknown';
    if (!sum.online) return 'offline';
    if (sum.health_index != null && sum.health_index < 60) return 'alarm';
    return 'online';
  }

  async function loadSummary() {
    try {
      const resp = await monitorApi.getRealtimeSummary();
      if (resp && resp.success && resp.data && resp.data.devices) {
        const map = {};
        for (const d of resp.data.devices) {
          map[d.device_id] = d;
        }
        summaryMap = map;
      }
    } catch (e) {
      console.error('加载实时摘要失败:', e);
    }
  }

  async function loadDevices() {
    if (allDevices.length === 0) {
      try {
        const resp = await devicesApi.getDevices({ page_size: 100 });
        const list =
          (resp && (resp.items || (resp.data && (resp.data.items || resp.data)))) || [];
        allDevices = Array.isArray(list) ? list : [];
      } catch (e) {
        console.error('加载设备列表失败:', e);
      }
    } else {
      allDevices = $devicesStore;
    }
    if (selectedIds.length === 0 && allDevices.length > 0) {
      const defaults = allDevices.slice(0, 2).map((d) => d.id);
      selectedIds = defaults;
      trendDeviceId = defaults[0];
    }
  }

  function handleHealthDrop(event) {
    const { deviceId, deviceName, healthIndex } = event.detail;
    if (activeToastMap[deviceId]) return;
    const id = toastSeq++;
    toasts = [...toasts, { id, deviceId, deviceName, healthIndex }];
    activeToastMap = { ...activeToastMap, [deviceId]: true };
    const timer = setTimeout(() => removeToast(id, deviceId), TOAST_DURATION);
    toastTimers = { ...toastTimers, [id]: timer };
  }

  function removeToast(id, deviceId) {
    if (toastTimers[id]) {
      clearTimeout(toastTimers[id]);
      const nextTimers = { ...toastTimers };
      delete nextTimers[id];
      toastTimers = nextTimers;
    }
    toasts = toasts.filter((t) => t.id !== id);
    if (activeToastMap[deviceId]) {
      const next = { ...activeToastMap };
      delete next[deviceId];
      activeToastMap = next;
    }
  }

  function handleToastClose(event) {
    removeToast(event.detail.id, event.detail.deviceId);
  }

  function setTrendFocus(id) {
    trendDeviceId = id;
  }

  function handleCardKeydown(event, id) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      setTrendFocus(id);
    }
  }

  function setLayout(value) {
    layout = value;
  }

  onMount(async () => {
    await loadDevices();
    await loadSummary();
  });

  onDestroy(() => {
    for (const id of Object.keys(toastTimers)) {
      clearTimeout(toastTimers[id]);
    }
    toastTimers = {};
    toasts = [];
    activeToastMap = {};
  });
</script>

<div class="rt-page">
  <div class="rt-main">
    <section class="selection-bar">
      <div class="selection-title">
        <span>设备选择</span>
        <span class="selection-count">已选 {selectedIds.length}/{MAX_SELECTED}</span>
      </div>
      <div class="selection-row">
        <div class="device-chips">
          {#each allDevices as device (device.id)}
            <label
              class="device-chip"
              class:checked={selectedIds.includes(device.id)}
              class:disabled={!selectedIds.includes(device.id) && selectedIds.length >= MAX_SELECTED}
            >
              <input
                type="checkbox"
                checked={selectedIds.includes(device.id)}
                disabled={!selectedIds.includes(device.id) && selectedIds.length >= MAX_SELECTED}
                on:change={() => toggleDevice(device.id)}
              />
              <span class="chip-dot {getChipStatus(device.id)}"></span>
              <span class="chip-name">{device.name}</span>
              <span class="chip-code">{device.code}</span>
            </label>
          {/each}
          {#if allDevices.length === 0}
            <span class="empty-hint">暂无设备</span>
          {/if}
        </div>
        <div class="layout-switcher">
          <span class="layout-label">布局</span>
          <div class="layout-buttons">
            {#each LAYOUT_OPTIONS as opt (opt.value)}
              <button
                class="layout-btn"
                class:active={layout === opt.value}
                on:click={() => setLayout(opt.value)}
                title={opt.label}
              >
                <span class="layout-icon">{opt.icon}</span>
                <span class="layout-text">{opt.label}</span>
              </button>
            {/each}
          </div>
        </div>
      </div>
    </section>

    <section class="cards-area">
      {#if selectedDevices.length === 0}
        <div class="empty-cards">
          <div class="empty-icon">📡</div>
          <p>请在上方勾选需要监控的设备(最多 {MAX_SELECTED} 台)</p>
        </div>
      {:else}
        <div class="cards-grid" data-layout={layout}>
          {#each selectedDevices as device (device.id)}
            <div
              class="card-wrapper"
              class:focus={trendDeviceId === device.id}
              on:click={() => setTrendFocus(device.id)}
              on:keydown={(e) => handleCardKeydown(e, device.id)}
              role="button"
              tabindex="0"
            >
              <DeviceMonitorCard {device} summary={summaryMap[device.id] || null} {layout} on:healthdrop={handleHealthDrop} />
              {#if trendDeviceId === device.id && layout !== 'compact'}
                <span class="focus-badge">趋势焦点</span>
              {/if}
            </div>
          {/each}
        </div>
      {/if}
    </section>
  </div>

  <HealthTrendSidebar deviceId={trendDeviceId} deviceName={trendDevice.name || ''} />
</div>

<Toast {toasts} on:close={handleToastClose} />

<style>
  .rt-page {
    display: flex;
    height: 100%;
    min-height: 0;
  }

  .rt-main {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
    overflow: hidden;
  }

  .selection-bar {
    background: var(--color-white);
    padding: var(--spacing-3) var(--spacing-5);
    border-bottom: var(--border-width) solid var(--color-gray-200);
    box-shadow: var(--shadow-sm);
  }

  .selection-title {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: var(--spacing-2);
    font-size: var(--font-size-sm);
    color: var(--color-gray-600);
    font-weight: 600;
  }

  .selection-count {
    color: var(--color-primary);
    font-size: var(--font-size-xs);
  }

  .selection-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--spacing-4);
  }

  .device-chips {
    display: flex;
    flex-wrap: wrap;
    gap: var(--spacing-2);
    flex: 1;
    min-width: 0;
  }

  .device-chip {
    display: inline-flex;
    align-items: center;
    gap: var(--spacing-2);
    padding: var(--spacing-2) var(--spacing-3);
    background: var(--color-gray-50);
    border: 1px solid var(--color-gray-200);
    border-radius: var(--radius-md);
    cursor: pointer;
    transition: all var(--transition-fast);
    font-size: var(--font-size-sm);
    user-select: none;
  }

  .device-chip:hover {
    border-color: var(--color-primary-light);
    background: var(--color-primary-lighter);
  }

  .device-chip.checked {
    border-color: var(--color-primary);
    background: var(--color-primary-lighter);
    color: var(--color-primary-dark);
  }

  .device-chip.disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .device-chip input {
    margin: 0;
    cursor: pointer;
  }

  .chip-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .chip-dot.online { background: var(--color-success); }
  .chip-dot.alarm { background: var(--color-danger); }
  .chip-dot.offline { background: var(--color-gray-400); }
  .chip-dot.unknown { background: var(--color-gray-300); }

  .chip-name {
    font-weight: 500;
  }

  .chip-code {
    color: var(--color-gray-400);
    font-size: var(--font-size-xs);
  }

  .layout-switcher {
    display: flex;
    align-items: center;
    gap: var(--spacing-2);
    flex-shrink: 0;
  }

  .layout-label {
    font-size: var(--font-size-sm);
    color: var(--color-gray-500);
    font-weight: 500;
  }

  .layout-buttons {
    display: flex;
    background: var(--color-gray-100);
    border-radius: var(--radius-md);
    padding: 2px;
    gap: 2px;
  }

  .layout-btn {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 4px 10px;
    border: none;
    background: transparent;
    border-radius: var(--radius-sm);
    cursor: pointer;
    font-size: var(--font-size-xs);
    color: var(--color-gray-600);
    transition: all var(--transition-fast);
  }

  .layout-btn:hover {
    background: var(--color-gray-200);
  }

  .layout-btn.active {
    background: var(--color-white);
    color: var(--color-primary);
    box-shadow: var(--shadow-sm);
    font-weight: 600;
  }

  .layout-icon {
    font-size: 14px;
    line-height: 1;
  }

  .cards-area {
    flex: 1;
    overflow: auto;
    padding: var(--spacing-4);
  }

  .cards-grid {
    display: grid;
    gap: var(--spacing-4);
  }

  .cards-grid[data-layout='grid-2'] {
    grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
  }

  .cards-grid[data-layout='grid-1'] {
    grid-template-columns: 1fr;
  }

  .cards-grid[data-layout='compact'] {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-2);
  }

  .card-wrapper {
    position: relative;
    cursor: pointer;
    outline: none;
  }

  .card-wrapper.focus::after {
    content: '';
    position: absolute;
    inset: -2px;
    border: 2px solid var(--color-primary);
    border-radius: var(--radius-lg);
    pointer-events: none;
  }

  .cards-grid[data-layout='compact'] .card-wrapper.focus::after {
    border-radius: var(--radius-md);
  }

  .focus-badge {
    position: absolute;
    top: var(--spacing-2);
    right: var(--spacing-2);
    background: var(--color-primary);
    color: white;
    font-size: var(--font-size-xs);
    padding: 2px var(--spacing-2);
    border-radius: var(--radius-full);
    z-index: 2;
  }

  .empty-cards,
  .empty-hint {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: var(--color-gray-400);
    text-align: center;
    gap: var(--spacing-3);
  }

  .empty-icon {
    font-size: 56px;
    opacity: 0.6;
  }

  @media (max-width: 1200px) {
    .cards-grid[data-layout='grid-2'] {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 900px) {
    .selection-row {
      flex-direction: column;
      align-items: flex-start;
    }

    .layout-switcher {
      align-self: flex-end;
    }
  }
</style>
