<script>
  import { createEventDispatcher } from 'svelte';

  export let toasts = [];

  const dispatch = createEventDispatcher();

  function close(toast) {
    dispatch('close', { id: toast.id, deviceId: toast.deviceId });
  }
</script>

<div class="toast-container">
  {#each toasts as toast (toast.id)}
    <div class="toast" role="alert">
      <div class="toast-icon">⚠️</div>
      <div class="toast-body">
        <div class="toast-title">设备健康指数异常</div>
        <div class="toast-message">
          设备 {toast.deviceName} 健康指数异常,当前值:{toast.healthIndex != null ? toast.healthIndex.toFixed(1) : '--'}
        </div>
      </div>
      <button class="toast-close" on:click={() => close(toast)} aria-label="关闭">×</button>
    </div>
  {/each}
</div>

<style>
  .toast-container {
    position: fixed;
    right: var(--spacing-6);
    bottom: var(--spacing-6);
    z-index: 9999;
    display: flex;
    flex-direction: column;
    gap: var(--spacing-3);
    pointer-events: none;
  }

  .toast {
    pointer-events: auto;
    display: flex;
    align-items: flex-start;
    gap: var(--spacing-3);
    min-width: 320px;
    max-width: 420px;
    padding: var(--spacing-3) var(--spacing-4);
    background: var(--color-white);
    border-left: 4px solid var(--color-danger);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-xl);
    animation: toast-in 0.25s ease;
  }

  @keyframes toast-in {
    from { transform: translateX(120%); opacity: 0; }
    to { transform: translateX(0); opacity: 1; }
  }

  .toast-icon {
    font-size: var(--font-size-2xl);
    line-height: 1;
  }

  .toast-body {
    flex: 1;
    min-width: 0;
  }

  .toast-title {
    font-size: var(--font-size-base);
    font-weight: 600;
    color: var(--color-danger-dark);
    margin-bottom: 2px;
  }

  .toast-message {
    font-size: var(--font-size-sm);
    color: var(--color-gray-700);
    line-height: 1.4;
    word-break: break-all;
  }

  .toast-close {
    background: transparent;
    border: none;
    color: var(--color-gray-400);
    font-size: 20px;
    line-height: 1;
    cursor: pointer;
    padding: 0 var(--spacing-1);
    border-radius: var(--radius-sm);
    transition: color var(--transition-fast);
  }

  .toast-close:hover {
    color: var(--color-gray-700);
  }
</style>
