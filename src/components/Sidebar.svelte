<script>
  export let items = [];
  export let activeKey = '';
  export let collapsed = false;
  export let width = 240;
  export let collapsedWidth = 64;

  function handleClick(item) {
    if (item.disabled) return;
    if (item.onClick) {
      item.onClick(item);
    }
    activeKey = item.key;
  }

  function toggleCollapse() {
    collapsed = !collapsed;
  }
</script>

<aside
  class="sidebar"
  style="--sidebar-width: {collapsed ? collapsedWidth : width}px;"
>
  <div class="sidebar-header">
    {#if !collapsed}
      <span class="logo-text">振动监测</span>
    {/if}
    <button class="collapse-btn" on:click={toggleCollapse}>
      {collapsed ? '→' : '←'}
    </button>
  </div>

  <nav class="sidebar-nav">
    <ul class="menu-list">
      {#each items as item (item.key)}
        <li
          class="menu-item {activeKey === item.key ? 'active' : ''} {item.disabled ? 'disabled' : ''}"
          on:click={() => handleClick(item)}
        >
          <span class="menu-icon">{item.icon || '•'}</span>
          {#if !collapsed}
            <span class="menu-label">{item.label}</span>
            {#if item.badge}
              <span class="menu-badge">{item.badge}</span>
            {/if}
          {/if}
        </li>
      {/each}
    </ul>
  </nav>

  <div class="sidebar-footer">
    {#if !collapsed}
      <span class="version">v1.0.0</span>
    {/if}
  </div>
</aside>

<style>
  .sidebar {
    width: var(--sidebar-width);
    height: 100vh;
    background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
    color: #e4e4e7;
    display: flex;
    flex-direction: column;
    transition: width 0.3s ease;
    position: fixed;
    left: 0;
    top: 0;
    z-index: 100;
    box-shadow: 2px 0 8px rgba(0, 0, 0, 0.3);
  }

  .sidebar-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    min-height: 60px;
  }

  .logo-text {
    font-size: 18px;
    font-weight: 600;
    background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  .collapse-btn {
    background: rgba(255, 255, 255, 0.1);
    border: none;
    color: #e4e4e7;
    width: 28px;
    height: 28px;
    border-radius: 6px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s ease;
  }

  .collapse-btn:hover {
    background: rgba(255, 255, 255, 0.2);
  }

  .sidebar-nav {
    flex: 1;
    overflow-y: auto;
    padding: 12px 8px;
  }

  .sidebar-nav::-webkit-scrollbar {
    width: 4px;
  }

  .sidebar-nav::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.2);
    border-radius: 2px;
  }

  .menu-list {
    list-style: none;
    margin: 0;
    padding: 0;
  }

  .menu-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 16px;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s ease;
    margin-bottom: 4px;
  }

  .menu-item:hover {
    background: rgba(255, 255, 255, 0.08);
  }

  .menu-item.active {
    background: linear-gradient(90deg, rgba(79, 172, 254, 0.2) 0%, rgba(0, 242, 254, 0.2) 100%);
    color: #4facfe;
  }

  .menu-item.disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .menu-icon {
    font-size: 18px;
    min-width: 20px;
    text-align: center;
  }

  .menu-label {
    flex: 1;
    font-size: 14px;
  }

  .menu-badge {
    background: #ef4444;
    color: white;
    font-size: 11px;
    padding: 2px 6px;
    border-radius: 10px;
    min-width: 18px;
    text-align: center;
  }

  .sidebar-footer {
    padding: 16px;
    border-top: 1px solid rgba(255, 255, 255, 0.1);
    text-align: center;
  }

  .version {
    font-size: 12px;
    color: rgba(255, 255, 255, 0.5);
  }
</style>
