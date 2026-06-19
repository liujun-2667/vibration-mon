<script>
  export let status = 'normal';
  export let size = 12;
  export let showLabel = false;
  export let pulse = false;

  const statusConfig = {
    normal: {
      color: '#22c55e',
      label: '正常',
      bgColor: 'rgba(34, 197, 94, 0.15)'
    },
    warning: {
      color: '#eab308',
      label: '警告',
      bgColor: 'rgba(234, 179, 8, 0.15)'
    },
    danger: {
      color: '#ef4444',
      label: '危险',
      bgColor: 'rgba(239, 68, 68, 0.15)'
    },
    offline: {
      color: '#9ca3af',
      label: '离线',
      bgColor: 'rgba(156, 163, 175, 0.15)'
    }
  };

  $: config = statusConfig[status] || statusConfig.offline;
</script>

<div class="status-indicator" style="gap: {showLabel ? '8px' : '0'};">
  <div
    class="status-dot {pulse ? 'pulse' : ''}"
    style="
      width: {size}px;
      height: {size}px;
      background-color: {config.color};
      box-shadow: 0 0 0 {size / 4}px {config.bgColor};
    "
  >
    {#if pulse}
      <span
        class="pulse-ring"
        style="
          width: {size}px;
          height: {size}px;
          background-color: {config.color};
        "
      ></span>
    {/if}
  </div>
  {#if showLabel}
    <span class="status-label" style="color: {config.color};">
      {config.label}
    </span>
  {/if}
</div>

<style>
  .status-indicator {
    display: inline-flex;
    align-items: center;
  }

  .status-dot {
    position: relative;
    border-radius: 50%;
    display: inline-block;
  }

  .pulse-ring {
    position: absolute;
    top: 0;
    left: 0;
    border-radius: 50%;
    opacity: 0.75;
    animation: pulse 1.5s cubic-bezier(0.4, 0, 0.6, 1) infinite;
  }

  @keyframes pulse {
    0% {
      transform: scale(1);
      opacity: 0.75;
    }
    100% {
      transform: scale(2.5);
      opacity: 0;
    }
  }

  .status-label {
    font-size: 13px;
    font-weight: 500;
  }
</style>
