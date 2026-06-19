<script>
  import { onMount } from 'svelte';
  import { Line, Pie } from 'svelte-chartjs';
  import { format, subDays, startOfDay, isSameDay } from 'date-fns';
  import { alarmsApi, devicesApi } from '../api.js';
  import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
    Filler,
    ArcElement
  } from 'chart.js';

  ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
    Filler,
    ArcElement
  );

  let loading = true;
  let allRecords = [];
  let devices = [];
  let selectedDay = null;
  let filterLevel = '';
  let acknowledgeFilter = '';

  let trendChartData = null;
  let pieChartData = null;
  let pieChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'right', labels: { font: { size: 12 }, padding: 12 } },
      tooltip: {
        callbacks: {
          label: (ctx) => {
            const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
            const pct = total > 0 ? ((ctx.parsed / total) * 100).toFixed(1) : 0;
            return `${ctx.label}: ${ctx.parsed} 条 (${pct}%)`;
          }
        }
      }
    }
  };

  const SEVERITY_COLORS = {
    critical: '#ef4444',
    warning: '#f59e0b',
    info: '#3b82f6'
  };

  const SEVERITY_LABELS = {
    critical: '严重',
    warning: '警告',
    info: '提示'
  };

  const trendChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: true, position: 'top', labels: { font: { size: 12 } } },
      tooltip: { mode: 'index', intersect: false }
    },
    scales: {
      x: { title: { display: true, text: '日期' }, grid: { color: 'rgba(0,0,0,0.05)' } },
      y: { title: { display: true, text: '报警次数' }, beginAtZero: true, grid: { color: 'rgba(0,0,0,0.05)' }, ticks: { precision: 0 } }
    },
    interaction: { mode: 'index', intersect: false },
    onClick: (evt, elements, chart) => {
      if (elements.length > 0) {
        const idx = elements[0].index;
        const days = getRecent7Days();
        selectedDay = days[idx];
        const el = document.getElementById('alarm-detail');
        if (el) el.scrollIntoView({ behavior: 'smooth' });
      }
    }
  };

  function getRecent7Days() {
    const days = [];
    const today = new Date();
    for (let i = 6; i >= 0; i--) {
      days.push(startOfDay(subDays(today, i)));
    }
    return days;
  }

  function normalizeLevel(level) {
    const l = String(level).toLowerCase();
    if (l.includes('crit') || l.includes('严重')) return 'critical';
    if (l.includes('warn') || l.includes('警告')) return 'warning';
    return 'info';
  }

  async function loadData() {
    loading = true;
    try {
      const sevenAgo = subDays(new Date(), 7).toISOString();
      const res = await alarmsApi.getAlarmRecords({ start_time: sevenAgo, page_size: 1000 });
      const items = res?.data?.items || res?.items || [];
      if (items.length > 0) {
        allRecords = items;
      } else {
        throw new Error('no records');
      }
    } catch (e) {
      allRecords = generateMockRecords();
    }

    try {
      const res = await devicesApi.getDevices();
      const items = res?.data?.items || res?.items || [];
      if (items.length > 0) {
        devices = items;
      } else {
        throw new Error('no devices');
      }
    } catch (e) {
      devices = [
        { id: 1, name: '电机-001' },
        { id: 2, name: '齿轮箱-001' },
        { id: 3, name: '泵组-001' },
        { id: 4, name: '风机-001' }
      ];
    }

    buildTrendChart();
    buildPieChart();
    loading = false;
  }

  function generateMockRecords() {
    const records = [];
    const types = ['振动超限', '温度异常', '峭度异常', '转速波动', '频谱异常'];
    let id = 5000;
    for (let d = 6; d >= 0; d--) {
      const day = startOfDay(subDays(new Date(), d));
      const count = 3 + Math.floor(Math.random() * 8);
      for (let j = 0; j < count; j++) {
        const r = Math.random();
        const level = r > 0.75 ? 'critical' : (r > 0.4 ? 'warning' : 'info');
        const ts = new Date(day.getTime() + Math.floor(Math.random() * 86400000));
        records.push({
          id: id++,
          device_id: 1 + Math.floor(Math.random() * 4),
          alarm_type: types[Math.floor(Math.random() * types.length)],
          alarm_level: level,
          message: `${types[Math.floor(Math.random() * types.length)]}触发`,
          actual_value: +(Math.random() * 5 + 1).toFixed(2),
          threshold: 3.0,
          acknowledged: Math.random() > 0.6,
          created_at: ts.toISOString()
        });
      }
    }
    return records;
  }

  function buildTrendChart() {
    const days = getRecent7Days();
    const labels = days.map(d => format(d, 'MM-dd'));
    const counts = { critical: [], warning: [], info: [] };

    for (const day of days) {
      let c = 0, w = 0, i = 0;
      for (const rec of allRecords) {
        const recDate = new Date(rec.created_at);
        if (isSameDay(recDate, day)) {
          const lvl = normalizeLevel(rec.alarm_level);
          if (lvl === 'critical') c++;
          else if (lvl === 'warning') w++;
          else i++;
        }
      }
      counts.critical.push(c);
      counts.warning.push(w);
      counts.info.push(i);
    }

    trendChartData = {
      labels,
      datasets: [
        {
          label: SEVERITY_LABELS.critical,
          data: counts.critical,
          borderColor: SEVERITY_COLORS.critical,
          backgroundColor: SEVERITY_COLORS.critical + '20',
          borderWidth: 2,
          tension: 0.3,
          pointRadius: 4,
          pointHoverRadius: 6,
          fill: false
        },
        {
          label: SEVERITY_LABELS.warning,
          data: counts.warning,
          borderColor: SEVERITY_COLORS.warning,
          backgroundColor: SEVERITY_COLORS.warning + '20',
          borderWidth: 2,
          tension: 0.3,
          pointRadius: 4,
          pointHoverRadius: 6,
          fill: false
        },
        {
          label: SEVERITY_LABELS.info,
          data: counts.info,
          borderColor: SEVERITY_COLORS.info,
          backgroundColor: SEVERITY_COLORS.info + '20',
          borderWidth: 2,
          tension: 0.3,
          pointRadius: 4,
          pointHoverRadius: 6,
          fill: false
        }
      ]
    };
  }

  function buildPieChart() {
    const deviceCounts = {};
    for (const rec of allRecords) {
      const key = rec.device_id;
      deviceCounts[key] = (deviceCounts[key] || 0) + 1;
    }
    const palette = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];
    const labels = [];
    const data = [];
    const colors = [];
    Object.keys(deviceCounts).forEach((id, idx) => {
      const dev = devices.find(d => String(d.id) === String(id));
      labels.push(dev ? dev.name : `设备 ${id}`);
      data.push(deviceCounts[id]);
      colors.push(palette[idx % palette.length]);
    });

    if (data.length === 0) {
      labels.push('暂无报警');
      data.push(1);
      colors.push('#d1d5db');
    }

    pieChartData = {
      labels,
      datasets: [{
        data,
        backgroundColor: colors,
        borderColor: '#fff',
        borderWidth: 2
      }]
    };
  }

  $: filteredRecords = allRecords.filter(rec => {
    if (selectedDay) {
      if (!isSameDay(new Date(rec.created_at), selectedDay)) return false;
    }
    if (filterLevel && normalizeLevel(rec.alarm_level) !== filterLevel) return false;
    if (acknowledgeFilter === 'unacked' && rec.acknowledged) return false;
    if (acknowledgeFilter === 'acked' && !rec.acknowledged) return false;
    return true;
  });

  $: summary = {
    total: allRecords.length,
    critical: allRecords.filter(r => normalizeLevel(r.alarm_level) === 'critical').length,
    warning: allRecords.filter(r => normalizeLevel(r.alarm_level) === 'warning').length,
    info: allRecords.filter(r => normalizeLevel(r.alarm_level) === 'info').length,
    unacked: allRecords.filter(r => !r.acknowledged).length
  };

  function clearDayFilter() {
    selectedDay = null;
  }

  async function acknowledge(recordId) {
    try {
      await alarmsApi.acknowledgeAlarm(recordId);
    } catch (e) {
      // ignore
    }
    allRecords = allRecords.map(r => r.id === recordId ? { ...r, acknowledged: true, acknowledged_at: new Date().toISOString() } : r);
  }

  onMount(() => {
    loadData();
  });
</script>

<div class="alarm-center-page">
  <div class="page-header">
    <h1 class="page-title">报警中心</h1>
    <p class="page-subtitle">最近 7 天报警趋势统计与详情</p>
  </div>

  {#if loading}
    <div class="loading">数据加载中...</div>
  {:else}
    <div class="summary-cards">
      <div class="summary-card">
        <div class="summary-icon">📊</div>
        <div class="summary-body">
          <div class="summary-label">报警总数</div>
          <div class="summary-value">{summary.total}</div>
        </div>
      </div>
      <div class="summary-card critical">
        <div class="summary-icon">🔴</div>
        <div class="summary-body">
          <div class="summary-label">严重</div>
          <div class="summary-value">{summary.critical}</div>
        </div>
      </div>
      <div class="summary-card warning">
        <div class="summary-icon">🟡</div>
        <div class="summary-body">
          <div class="summary-label">警告</div>
          <div class="summary-value">{summary.warning}</div>
        </div>
      </div>
      <div class="summary-card info">
        <div class="summary-icon">🔵</div>
        <div class="summary-body">
          <div class="summary-label">提示</div>
          <div class="summary-value">{summary.info}</div>
        </div>
      </div>
      <div class="summary-card unacked">
        <div class="summary-icon">⏳</div>
        <div class="summary-body">
          <div class="summary-label">未处理</div>
          <div class="summary-value">{summary.unacked}</div>
        </div>
      </div>
    </div>

    <div class="charts-row">
      <div class="chart-card trend-card">
        <div class="card-header">
          <h3 class="card-title">最近 7 天报警趋势</h3>
          <span class="card-hint">点击图中某一天可筛选当天报警</span>
        </div>
        <div class="chart-container">
          {#if trendChartData}
            <Line data={trendChartData} options={trendChartOptions} />
          {/if}
        </div>
        {#if selectedDay}
          <div class="day-filter-bar">
            <span>已筛选: {format(selectedDay, 'yyyy-MM-dd')} 当天报警 ({filteredRecords.length} 条)</span>
            <button class="clear-btn" on:click={clearDayFilter}>清除筛选</button>
          </div>
        {/if}
      </div>

      <div class="chart-card pie-card">
        <div class="card-header">
          <h3 class="card-title">各设备报警占比</h3>
        </div>
        <div class="chart-container">
          {#if pieChartData}
            <Pie data={pieChartData} options={pieChartOptions} />
          {/if}
        </div>
      </div>
    </div>

    <div class="detail-section" id="alarm-detail">
      <div class="detail-header">
        <h3 class="card-title">报警详情列表</h3>
        <div class="filter-controls">
          <select bind:value={filterLevel} class="filter-select">
            <option value="">全部级别</option>
            <option value="critical">严重</option>
            <option value="warning">警告</option>
            <option value="info">提示</option>
          </select>
          <select bind:value={acknowledgeFilter} class="filter-select">
            <option value="">全部状态</option>
            <option value="unacked">未处理</option>
            <option value="acked">已处理</option>
          </select>
        </div>
      </div>

      <div class="table-wrap">
        <table class="alarm-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>时间</th>
              <th>设备</th>
              <th>报警类型</th>
              <th>级别</th>
              <th>实际值</th>
              <th>阈值</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {#each filteredRecords.slice(0, 100) as rec}
              <tr>
                <td>{rec.id}</td>
                <td>{format(new Date(rec.created_at), 'MM-dd HH:mm:ss')}</td>
                <td>{devices.find(d => String(d.id) === String(rec.device_id))?.name || `设备${rec.device_id}`}</td>
                <td>{rec.alarm_type}</td>
                <td>
                  <span class="level-tag" style="background: {SEVERITY_COLORS[normalizeLevel(rec.alarm_level)]}20; color: {SEVERITY_COLORS[normalizeLevel(rec.alarm_level)]}">
                    {SEVERITY_LABELS[normalizeLevel(rec.alarm_level)]}
                  </span>
                </td>
                <td>{rec.actual_value?.toFixed?.(2) ?? rec.actual_value}</td>
                <td>{rec.threshold}</td>
                <td>
                  {#if rec.acknowledged}
                    <span class="status-tag acked">已处理</span>
                  {:else}
                    <span class="status-tag unacked">未处理</span>
                  {/if}
                </td>
                <td>
                  {#if !rec.acknowledged}
                    <button class="ack-btn" on:click={() => acknowledge(rec.id)}>处理</button>
                  {/if}
                </td>
              </tr>
            {:else}
              <tr>
                <td colspan="9" class="empty-row">暂无符合条件的报警记录</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
      {#if filteredRecords.length > 100}
        <div class="table-footer">仅显示前 100 条，共 {filteredRecords.length} 条</div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .alarm-center-page {
    padding: 24px;
    min-height: 100vh;
    background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
  }

  .page-header {
    margin-bottom: 20px;
  }

  .page-title {
    font-size: 26px;
    font-weight: 700;
    color: #1f2937;
    margin: 0 0 6px 0;
  }

  .page-subtitle {
    font-size: 14px;
    color: #6b7280;
    margin: 0;
  }

  .loading {
    text-align: center;
    padding: 60px;
    color: #6b7280;
    background: white;
    border-radius: 12px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  }

  .summary-cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 16px;
    margin-bottom: 20px;
  }

  .summary-card {
    background: white;
    border-radius: 12px;
    padding: 18px;
    display: flex;
    align-items: center;
    gap: 14px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    border-left: 4px solid #3b82f6;
  }

  .summary-card.critical { border-left-color: #ef4444; }
  .summary-card.warning { border-left-color: #f59e0b; }
  .summary-card.info { border-left-color: #3b82f6; }
  .summary-card.unacked { border-left-color: #8b5cf6; }

  .summary-icon {
    font-size: 28px;
  }

  .summary-label {
    font-size: 12px;
    color: #6b7280;
  }

  .summary-value {
    font-size: 26px;
    font-weight: 800;
    color: #1f2937;
    line-height: 1.1;
  }

  .charts-row {
    display: grid;
    grid-template-columns: 2fr 1fr;
    gap: 16px;
    margin-bottom: 20px;
  }

  .chart-card {
    background: white;
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 14px;
    flex-wrap: wrap;
    gap: 8px;
  }

  .card-title {
    font-size: 16px;
    font-weight: 600;
    color: #1f2937;
    margin: 0;
  }

  .card-hint {
    font-size: 12px;
    color: #6b7280;
  }

  .chart-container {
    height: 300px;
    position: relative;
  }

  .day-filter-bar {
    margin-top: 12px;
    padding: 8px 14px;
    background: #eff6ff;
    border-radius: 8px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 13px;
    color: #1e40af;
  }

  .clear-btn {
    padding: 4px 12px;
    background: white;
    border: 1px solid #93c5fd;
    border-radius: 6px;
    font-size: 12px;
    color: #1e40af;
    cursor: pointer;
  }

  .clear-btn:hover {
    background: #dbeafe;
  }

  .detail-section {
    background: white;
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  }

  .detail-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 14px;
    flex-wrap: wrap;
    gap: 10px;
  }

  .filter-controls {
    display: flex;
    gap: 10px;
  }

  .filter-select {
    padding: 6px 10px;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    font-size: 13px;
    background: white;
    cursor: pointer;
  }

  .table-wrap {
    overflow-x: auto;
  }

  .alarm-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }

  .alarm-table th,
  .alarm-table td {
    padding: 10px 12px;
    text-align: left;
    border-bottom: 1px solid #f3f4f6;
    white-space: nowrap;
  }

  .alarm-table th {
    background: #f9fafb;
    color: #6b7280;
    font-weight: 600;
    font-size: 12px;
    position: sticky;
    top: 0;
  }

  .alarm-table tbody tr:hover {
    background: #f9fafb;
  }

  .level-tag {
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 600;
  }

  .status-tag {
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 500;
  }

  .status-tag.acked {
    background: #d1fae5;
    color: #065f46;
  }

  .status-tag.unacked {
    background: #fee2e2;
    color: #991b1b;
  }

  .ack-btn {
    padding: 4px 12px;
    background: #3b82f6;
    color: white;
    border: none;
    border-radius: 6px;
    font-size: 12px;
    cursor: pointer;
  }

  .ack-btn:hover {
    background: #2563eb;
  }

  .empty-row {
    text-align: center;
    color: #9ca3af;
    padding: 30px;
  }

  .table-footer {
    text-align: center;
    padding: 12px;
    color: #6b7280;
    font-size: 12px;
  }

  @media (max-width: 900px) {
    .charts-row {
      grid-template-columns: 1fr;
    }
  }
</style>
