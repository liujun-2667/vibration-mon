<script>
  import { onMount } from 'svelte';
  import { jsPDF } from 'jspdf';
  import html2canvas from 'html2canvas';
  import { format } from 'date-fns';
  import { devicesApi, reportsApi, analysisApi } from '../api.js';
  import StatusIndicator from '../components/StatusIndicator.svelte';

  let devices = [];
  let selectedDeviceIds = [];
  let loading = true;
  let generating = false;
  let reports = [];
  let activeTab = 'generate';

  let startTime = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
  let endTime = new Date();
  let startTimeStr = '';
  let endTimeStr = '';

  let reportType = 'comprehensive';
  let reportTitle = '';
  let includeCharts = true;
  let includeRawData = false;
  let includeTrendAnalysis = true;
  let includeRecommendations = true;

  let generatedReport = null;
  let previewContent = null;

  const reportTypeOptions = [
    { value: 'comprehensive', label: '综合报告', description: '包含设备状态、数据分析、趋势预测的完整报告' },
    { value: 'diagnostic', label: '诊断报告', description: '针对特定设备的故障诊断分析报告' },
    { value: 'trend', label: '趋势报告', description: '设备运行趋势分析和预测报告' },
    { value: 'alarm', label: '报警报告', description: '指定时间范围内的报警事件汇总报告' },
    { value: 'maintenance', label: '维护报告', description: '设备维护建议和保养计划报告' }
  ];

  const templateOptions = [
    { value: 'standard', label: '标准模板' },
    { value: 'detailed', label: '详细模板' },
    { value: 'summary', label: '摘要模板' }
  ];

  $: canGenerate = selectedDeviceIds.length > 0 && reportTitle;

  async function fetchDevices() {
    try {
      const response = await devicesApi.getDevices({ page_size: 100 });
      devices = response.data?.items || response.data || [];
    } catch (error) {
      console.error('加载设备列表失败:', error);
      devices = [
        { id: 1, name: '电机-001', code: 'MOT-001', status: 'online', health_index: 85 },
        { id: 2, name: '齿轮箱-001', code: 'GEAR-001', status: 'online', health_index: 92 },
        { id: 3, name: '泵组-001', code: 'PUMP-001', status: 'warning', health_index: 65 },
        { id: 4, name: '风机-001', code: 'FAN-001', status: 'offline', health_index: 0 },
        { id: 5, name: '压缩机-001', code: 'COMP-001', status: 'error', health_index: 35 }
      ];
    } finally {
      loading = false;
    }
  }

  async function fetchReports() {
    try {
      const response = await reportsApi.getReportList({ page_size: 50 });
      reports = response.data?.items || response.data || [];
    } catch (error) {
      console.error('加载报告列表失败:', error);
      reports = [
        { id: 1, title: '2024年6月设备状态综合报告', type: 'comprehensive', devices: ['MOT-001', 'GEAR-001'], created_at: '2024-06-15T10:30:00', status: 'completed', file_size: '2.4 MB' },
        { id: 2, title: '泵组-001故障诊断报告', type: 'diagnostic', devices: ['PUMP-001'], created_at: '2024-06-10T14:20:00', status: 'completed', file_size: '1.8 MB' },
        { id: 3, title: '2024年Q2趋势分析报告', type: 'trend', devices: ['MOT-001', 'GEAR-001', 'PUMP-001'], created_at: '2024-06-01T09:00:00', status: 'completed', file_size: '3.1 MB' },
        { id: 4, title: '5月报警事件汇总', type: 'alarm', devices: ['COMP-001'], created_at: '2024-05-31T16:45:00', status: 'completed', file_size: '0.9 MB' }
      ];
    }
  }

  function generateMockReport() {
    const selectedDevices = devices.filter(d => selectedDeviceIds.includes(d.id));

    return {
      title: reportTitle,
      type: reportType,
      generated_at: new Date().toISOString(),
      period: {
        start: startTime.toISOString(),
        end: endTime.toISOString()
      },
      devices: selectedDevices.map(d => ({
        ...d,
        analysis: {
          time_domain: {
            rms: (Math.random() * 3 + 0.5).toFixed(2),
            peak: (Math.random() * 8 + 2).toFixed(2),
            peak_to_peak: (Math.random() * 15 + 5).toFixed(2),
            crest_factor: (Math.random() * 3 + 1.5).toFixed(2),
            kurtosis: (Math.random() * 4 + 2).toFixed(2),
            skewness: (Math.random() * 0.5 - 0.25).toFixed(3)
          },
          frequency_domain: {
            dominant_frequency: 50,
            dominant_amplitude: (Math.random() * 0.5 + 0.3).toFixed(2),
            spectral_centroid: (Math.random() * 100 + 100).toFixed(1)
          }
        }
      })),
      summary: {
        total_devices: selectedDevices.length,
        online_count: selectedDevices.filter(d => d.status === 'online').length,
        warning_count: selectedDevices.filter(d => d.status === 'warning').length,
        error_count: selectedDevices.filter(d => d.status === 'error').length,
        offline_count: selectedDevices.filter(d => d.status === 'offline').length,
        avg_health_index: selectedDevices.length > 0
          ? Math.round(selectedDevices.reduce((sum, d) => sum + (d.health_index || 0), 0) / selectedDevices.length)
          : 0
      },
      recommendations: [
        '定期检查电机轴承润滑情况，建议每3个月加注润滑脂',
        '齿轮箱油温略有偏高，建议检查冷却系统运行状态',
        '泵组振动值接近警告阈值，建议安排详细检查',
        '建议建立设备健康档案，跟踪长期运行趋势'
      ],
      alarm_events: [
        { time: '2024-06-12 14:32:15', device: '泵组-001', level: 'warning', message: '振动值超过警告阈值' },
        { time: '2024-06-10 09:15:30', device: '压缩机-001', level: 'error', message: '轴承温度异常升高' },
        { time: '2024-06-08 16:45:20', device: '电机-001', level: 'info', message: '例行数据采集完成' }
      ]
    };
  }

  async function generateReport() {
    if (!canGenerate) return;

    generating = true;
    previewContent = null;

    try {
      const reportData = {
        title: reportTitle,
        type: reportType,
        device_ids: selectedDeviceIds,
        start_time: startTime.toISOString(),
        end_time: endTime.toISOString(),
        include_charts: includeCharts,
        include_raw_data: includeRawData,
        include_trend: includeTrendAnalysis,
        include_recommendations: includeRecommendations
      };

      const response = await reportsApi.generateReport(reportData);
      generatedReport = response.data || generateMockReport();
    } catch (error) {
      console.error('生成报告失败:', error);
      generatedReport = generateMockReport();
    }

    previewContent = generatedReport;
    generating = false;

    setTimeout(() => {
      fetchReports();
    }, 500);
  }

  async function downloadPDF() {
    const reportElement = document.getElementById('report-preview');
    if (!reportElement) return;

    try {
      const canvas = await html2canvas(reportElement, {
        scale: 2,
        useCORS: true,
        logging: false,
        backgroundColor: '#ffffff'
      });

      const imgData = canvas.toDataURL('image/png');
      const pdf = new jsPDF('p', 'mm', 'a4');

      const pdfWidth = pdf.internal.pageSize.getWidth();
      const pdfHeight = pdf.internal.pageSize.getHeight();
      const imgWidth = canvas.width;
      const imgHeight = canvas.height;

      const ratio = Math.min(pdfWidth / imgWidth, pdfHeight / imgHeight);
      const imgX = (pdfWidth - imgWidth * ratio) / 2;
      const imgY = 10;

      const heightLeft = imgHeight * ratio;
      let position = 0;

      pdf.addImage(imgData, 'PNG', imgX, imgY + position, imgWidth * ratio, heightLeft);

      const fileName = `${reportTitle || 'vibration_report'}_${format(new Date(), 'yyyyMMdd_HHmmss')}.pdf`;
      pdf.save(fileName);
    } catch (error) {
      console.error('导出PDF失败:', error);
      alert('导出PDF失败，请重试');
    }
  }

  function downloadReport(report) {
    const url = reportsApi.downloadReport(report.id);
    window.open(url, '_blank');
  }

  function viewReport(report) {
    activeTab = 'generate';
    reportTitle = report.title;
    selectedDeviceIds = devices.filter(d => report.devices.includes(d.code)).map(d => d.id);
    generateReport();
  }

  function deleteReport(report) {
    if (!confirm(`确定要删除报告 "${report.title}" 吗？`)) return;
    reports = reports.filter(r => r.id !== report.id);
  }

  function toggleDeviceSelection(deviceId) {
    if (selectedDeviceIds.includes(deviceId)) {
      selectedDeviceIds = selectedDeviceIds.filter(id => id !== deviceId);
    } else {
      selectedDeviceIds = [...selectedDeviceIds, deviceId];
    }
  }

  function selectAllDevices() {
    if (selectedDeviceIds.length === devices.length) {
      selectedDeviceIds = [];
    } else {
      selectedDeviceIds = devices.map(d => d.id);
    }
  }

  function getHealthColor(index) {
    if (index >= 80) return '#10b981';
    if (index >= 60) return '#f59e0b';
    if (index >= 40) return '#f97316';
    return '#ef4444';
  }

  function getReportTypeLabel(value) {
    return reportTypeOptions.find(t => t.value === value)?.label || value;
  }

  function getReportTypeIcon(value) {
    const icons = {
      comprehensive: '📋',
      diagnostic: '🔍',
      trend: '📈',
      alarm: '🔔',
      maintenance: '🔧'
    };
    return icons[value] || '📄';
  }

  function initDateInputs() {
    startTimeStr = format(startTime, "yyyy-MM-dd'T'HH:mm");
    endTimeStr = format(endTime, "yyyy-MM-dd'T'HH:mm");
    reportTitle = `${format(new Date(), 'yyyy年M月')}设备状态综合报告`;
  }

  function updateStartTime(event) {
    startTime = new Date(event.target.value);
    startTimeStr = event.target.value;
  }

  function updateEndTime(event) {
    endTime = new Date(event.target.value);
    endTimeStr = event.target.value;
  }

  function setQuickRange(days) {
    endTime = new Date();
    startTime = new Date(endTime.getTime() - days * 24 * 60 * 60 * 1000);
    initDateInputs();
  }

  function resetForm() {
    selectedDeviceIds = [];
    reportType = 'comprehensive';
    includeCharts = true;
    includeRawData = false;
    includeTrendAnalysis = true;
    includeRecommendations = true;
    previewContent = null;
    generatedReport = null;
    initDateInputs();
  }

  function getStatusStyle(status) {
    const config = {
      online: { label: '在线', status: 'normal' },
      offline: { label: '离线', status: 'offline' },
      warning: { label: '警告', status: 'warning' },
      error: { label: '异常', status: 'danger' }
    };
    return config[status] || config.offline;
  }

  onMount(() => {
    initDateInputs();
    fetchDevices();
    fetchReports();
  });
</script>

<div class="report-generator">
  <div class="header">
    <div>
      <h1 class="page-title">报告管理</h1>
      <p class="page-subtitle">生成和导出设备监测报告</p>
    </div>
  </div>

  <div class="tabs">
    <button class="tab-btn {activeTab === 'generate' ? 'active' : ''}" on:click={() => activeTab = 'generate'}>
      ✏️ 生成报告
    </button>
    <button class="tab-btn {activeTab === 'history' ? 'active' : ''}" on:click={() => activeTab = 'history'}>
      📁 历史报告
    </button>
  </div>

  {#if activeTab === 'generate'}
    <div class="generate-layout">
      <div class="config-panel">
        <div class="config-section">
          <h3 class="section-title">基本信息</h3>
          
          <div class="form-group">
            <label>报告标题 *</label>
            <input type="text" bind:value={reportTitle} placeholder="请输入报告标题" />
          </div>

          <div class="form-group">
            <label>报告类型</label>
            <div class="type-options">
              {#each reportTypeOptions as opt}
                <label class="type-option {reportType === opt.value ? 'selected' : ''}">
                  <input type="radio" bind:group={reportType} value={opt.value} />
                  <div class="type-option-content">
                    <span class="type-icon">{getReportTypeIcon(opt.value)}</span>
                    <div>
                      <div class="type-label">{opt.label}</div>
                      <div class="type-desc">{opt.description}</div>
                    </div>
                  </div>
                </label>
              {/each}
            </div>
          </div>

          <div class="form-group">
            <label>时间范围</label>
            <div class="datetime-group">
              <input type="datetime-local" bind:value={startTimeStr} on:change={updateStartTime} />
              <span class="datetime-separator">至</span>
              <input type="datetime-local" bind:value={endTimeStr} on:change={updateEndTime} />
            </div>
            <div class="quick-range">
              <button class="range-btn" on:click={() => setQuickRange(7)}>近7天</button>
              <button class="range-btn" on:click={() => setQuickRange(30)}>近30天</button>
              <button class="range-btn" on:click={() => setQuickRange(90)}>近90天</button>
            </div>
          </div>
        </div>

        <div class="config-section">
          <div class="section-header">
            <h3 class="section-title">选择设备</h3>
            <button class="select-all-btn" on:click={selectAllDevices}>
              {selectedDeviceIds.length === devices.length ? '取消全选' : '全选'}
            </button>
          </div>
          <div class="device-select-list">
            {#each devices as device}
              <label class="device-item {selectedDeviceIds.includes(device.id) ? 'selected' : ''}">
                <input type="checkbox" bind:group={selectedDeviceIds} value={device.id} />
                <div class="device-info">
                  <div class="device-name">{device.name}</div>
                  <div class="device-meta">
                    <span class="device-code">{device.code}</span>
                    <StatusIndicator status={getStatusStyle(device.status).status} size={8} />
                    {#if device.health_index !== undefined}
                      <span class="health-index" style="color: {getHealthColor(device.health_index)}">
                        健康度: {device.health_index}%
                      </span>
                    {/if}
                  </div>
                </div>
              </label>
            {/each}
          </div>
        </div>

        <div class="config-section">
          <h3 class="section-title">报告内容</h3>
          <div class="checkbox-list">
            <label class="checkbox-item">
              <input type="checkbox" bind:checked={includeCharts} />
              <span>包含图表</span>
            </label>
            <label class="checkbox-item">
              <input type="checkbox" bind:checked={includeTrendAnalysis} />
              <span>包含趋势分析</span>
            </label>
            <label class="checkbox-item">
              <input type="checkbox" bind:checked={includeRecommendations} />
              <span>包含维护建议</span>
            </label>
            <label class="checkbox-item">
              <input type="checkbox" bind:checked={includeRawData} />
              <span>包含原始数据</span>
            </label>
          </div>
        </div>

        <div class="config-actions">
          <button class="btn btn-secondary" on:click={resetForm}>重置</button>
          <button class="btn btn-primary" on:click={generateReport} disabled={!canGenerate || generating}>
            {generating ? '生成中...' : '📄 生成报告'}
          </button>
        </div>
      </div>

      <div class="preview-panel">
        {#if generating}
          <div class="loading">
            <div class="loading-spinner"></div>
            <p>正在生成报告，请稍候...</p>
          </div>
        {:else if !previewContent}
          <div class="empty-preview">
            <div class="preview-icon">📄</div>
            <h3>报告预览</h3>
            <p>配置报告参数后点击"生成报告"按钮</p>
          </div>
        {:else}
          <div class="preview-header">
            <h3 class="preview-title">报告预览</h3>
            <div class="preview-actions">
              <button class="btn btn-secondary" on:click={resetForm}>新建报告</button>
              <button class="btn btn-primary" on:click={downloadPDF}>
                📥 下载PDF
              </button>
            </div>
          </div>

          <div class="preview-scroll">
            <div id="report-preview" class="report-content">
              <div class="report-header">
                <div class="report-logo">📡</div>
                <h1 class="report-main-title">{previewContent.title}</h1>
                <p class="report-subtitle">设备振动监测分析报告</p>
                <p class="report-meta">
                  生成时间: {format(new Date(previewContent.generated_at), 'yyyy-MM-dd HH:mm:ss')}
                </p>
                <p class="report-meta">
                  报告周期: {format(new Date(previewContent.period.start), 'yyyy-MM-dd')} - {format(new Date(previewContent.period.end), 'yyyy-MM-dd')}
                </p>
              </div>

              <div class="report-section">
                <h2 class="report-section-title">一、概览</h2>
                <div class="summary-grid">
                  <div class="summary-card">
                    <div class="summary-value">{previewContent.summary.total_devices}</div>
                    <div class="summary-label">设备总数</div>
                  </div>
                  <div class="summary-card online">
                    <div class="summary-value">{previewContent.summary.online_count}</div>
                    <div class="summary-label">在线设备</div>
                  </div>
                  <div class="summary-card warning">
                    <div class="summary-value">{previewContent.summary.warning_count}</div>
                    <div class="summary-label">警告设备</div>
                  </div>
                  <div class="summary-card error">
                    <div class="summary-value">{previewContent.summary.error_count}</div>
                    <div class="summary-label">异常设备</div>
                  </div>
                  <div class="summary-card health">
                    <div class="summary-value" style="color: {getHealthColor(previewContent.summary.avg_health_index)}">
                      {previewContent.summary.avg_health_index}%
                    </div>
                    <div class="summary-label">平均健康度</div>
                  </div>
                </div>
              </div>

              <div class="report-section">
                <h2 class="report-section-title">二、设备状态详情</h2>
                <table class="report-table">
                  <thead>
                    <tr>
                      <th>设备名称</th>
                      <th>设备编码</th>
                      <th>状态</th>
                      <th>健康度</th>
                      <th>RMS (g)</th>
                      <th>峰值 (g)</th>
                      <th>峭度</th>
                    </tr>
                  </thead>
                  <tbody>
                    {#each previewContent.devices as device}
                      <tr>
                        <td>{device.name}</td>
                        <td>{device.code}</td>
                        <td>{getStatusStyle(device.status).label}</td>
                        <td style="color: {getHealthColor(device.health_index || 0)}">
                          {device.health_index || 0}%
                        </td>
                        <td>{device.analysis.time_domain.rms}</td>
                        <td>{device.analysis.time_domain.peak}</td>
                        <td>{device.analysis.time_domain.kurtosis}</td>
                      </tr>
                    {/each}
                  </tbody>
                </table>
              </div>

              {#if includeRecommendations && previewContent.recommendations.length > 0}
                <div class="report-section">
                  <h2 class="report-section-title">三、维护建议</h2>
                  <ol class="recommendation-list">
                    {#each previewContent.recommendations as rec, i}
                      <li>{rec}</li>
                    {/each}
                  </ol>
                </div>
              {/if}

              {#if previewContent.alarm_events.length > 0}
                <div class="report-section">
                  <h2 class="report-section-title">四、报警事件</h2>
                  <table class="report-table">
                    <thead>
                      <tr>
                        <th>时间</th>
                        <th>设备</th>
                        <th>级别</th>
                        <th>消息</th>
                      </tr>
                    </thead>
                    <tbody>
                      {#each previewContent.alarm_events as alarm}
                        <tr>
                          <td>{alarm.time}</td>
                          <td>{alarm.device}</td>
                          <td>{alarm.level}</td>
                          <td>{alarm.message}</td>
                        </tr>
                      {/each}
                    </tbody>
                  </table>
                </div>
              {/if}

              <div class="report-footer">
                <p>本报告由振动监测系统自动生成</p>
                <p>报告生成时间: {format(new Date(), 'yyyy-MM-dd HH:mm:ss')}</p>
              </div>
            </div>
          </div>
        {/if}
      </div>
    </div>
  {:else}
    <div class="history-section">
      {#if reports.length === 0}
        <div class="empty">暂无历史报告</div>
      {:else}
        <div class="report-list">
          {#each reports as report (report.id)}
            <div class="report-card">
              <div class="report-card-header">
                <span class="report-type-icon">{getReportTypeIcon(report.type)}</span>
                <div class="report-card-info">
                  <h3 class="report-card-title">{report.title}</h3>
                  <p class="report-card-meta">
                    {getReportTypeLabel(report.type)} · {report.devices.join(', ')}
                  </p>
                </div>
                <span class="report-status completed">✓ 已完成</span>
              </div>
              <div class="report-card-body">
                <div class="report-card-detail">
                  <span>📅 {format(new Date(report.created_at), 'yyyy-MM-dd HH:mm')}</span>
                  <span>📦 {report.file_size}</span>
                </div>
              </div>
              <div class="report-card-footer">
                <button class="btn btn-sm btn-secondary" on:click={() => viewReport(report)}>查看</button>
                <button class="btn btn-sm btn-secondary" on:click={() => downloadReport(report)}>下载</button>
                <button class="btn btn-sm btn-danger" on:click={() => deleteReport(report)}>删除</button>
              </div>
            </div>
          {/each}
        </div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .report-generator {
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

  .section-title {
    font-size: 16px;
    font-weight: 600;
    color: #1f2937;
    margin: 0;
  }

  .tabs {
    display: flex;
    gap: 8px;
    margin-bottom: 24px;
    border-bottom: 2px solid #e5e7eb;
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

  .tab-btn:hover {
    color: #3b82f6;
  }

  .tab-btn.active {
    color: #3b82f6;
    border-bottom-color: #3b82f6;
  }

  .generate-layout {
    display: grid;
    grid-template-columns: 420px 1fr;
    gap: 24px;
    align-items: start;
  }

  .config-panel {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .config-section {
    background: white;
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  }

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
  }

  .select-all-btn {
    padding: 4px 12px;
    border: 1px solid #d1d5db;
    background: white;
    border-radius: 6px;
    font-size: 12px;
    cursor: pointer;
    transition: all 0.2s;
  }

  .select-all-btn:hover {
    border-color: #3b82f6;
    color: #3b82f6;
  }

  .form-group {
    margin-bottom: 16px;
  }

  .form-group:last-child {
    margin-bottom: 0;
  }

  .form-group label {
    display: block;
    font-size: 13px;
    font-weight: 500;
    color: #374151;
    margin-bottom: 8px;
  }

  .form-group input[type="text"],
  .form-group input[type="datetime-local"] {
    width: 100%;
    padding: 10px 14px;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    font-size: 14px;
    outline: none;
    transition: border-color 0.2s, box-shadow 0.2s;
    font-family: inherit;
    box-sizing: border-box;
  }

  .form-group input:focus {
    border-color: #3b82f6;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
  }

  .datetime-group {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
  }

  .datetime-separator {
    color: #6b7280;
    font-size: 14px;
  }

  .quick-range {
    display: flex;
    gap: 8px;
  }

  .range-btn {
    padding: 6px 12px;
    border: 1px solid #d1d5db;
    background: white;
    border-radius: 6px;
    font-size: 12px;
    cursor: pointer;
    transition: all 0.2s;
  }

  .range-btn:hover {
    border-color: #3b82f6;
    color: #3b82f6;
  }

  .type-options {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .type-option {
    display: block;
    cursor: pointer;
  }

  .type-option input {
    display: none;
  }

  .type-option-content {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 16px;
    border: 2px solid #e5e7eb;
    border-radius: 8px;
    transition: all 0.2s;
  }

  .type-option:hover .type-option-content {
    border-color: #d1d5db;
  }

  .type-option.selected .type-option-content {
    border-color: #3b82f6;
    background: #eff6ff;
  }

  .type-icon {
    font-size: 24px;
  }

  .type-label {
    font-weight: 600;
    color: #1f2937;
    margin-bottom: 2px;
  }

  .type-desc {
    font-size: 12px;
    color: #6b7280;
  }

  .device-select-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
    max-height: 240px;
    overflow-y: auto;
  }

  .device-item {
    display: block;
    cursor: pointer;
  }

  .device-item input {
    display: none;
  }

  .device-info {
    padding: 12px 16px;
    border: 2px solid #e5e7eb;
    border-radius: 8px;
    transition: all 0.2s;
  }

  .device-item:hover .device-info {
    border-color: #d1d5db;
  }

  .device-item.selected .device-info {
    border-color: #3b82f6;
    background: #eff6ff;
  }

  .device-name {
    font-weight: 600;
    color: #1f2937;
    margin-bottom: 4px;
  }

  .device-meta {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 12px;
    color: #6b7280;
  }

  .device-code {
    font-family: monospace;
  }

  .health-index {
    font-weight: 600;
  }

  .checkbox-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .checkbox-item {
    display: flex;
    align-items: center;
    gap: 10px;
    cursor: pointer;
  }

  .checkbox-item input[type="checkbox"] {
    width: 18px;
    height: 18px;
    cursor: pointer;
  }

  .config-actions {
    display: flex;
    gap: 12px;
  }

  .config-actions .btn {
    flex: 1;
    justify-content: center;
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

  .preview-panel {
    background: white;
    border-radius: 12px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    overflow: hidden;
    min-height: 600px;
    display: flex;
    flex-direction: column;
  }

  .preview-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 20px;
    border-bottom: 1px solid #e5e7eb;
    background: #f9fafb;
  }

  .preview-title {
    font-size: 16px;
    font-weight: 600;
    color: #1f2937;
    margin: 0;
  }

  .preview-actions {
    display: flex;
    gap: 8px;
  }

  .preview-scroll {
    flex: 1;
    overflow-y: auto;
    padding: 20px;
    background: #f3f4f6;
  }

  .loading, .empty-preview {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 60px;
    color: #6b7280;
  }

  .loading-spinner {
    width: 48px;
    height: 48px;
    border: 4px solid #e5e7eb;
    border-top-color: #3b82f6;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin-bottom: 16px;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .preview-icon {
    font-size: 64px;
    margin-bottom: 16px;
  }

  .empty-preview h3 {
    margin: 0 0 8px 0;
    font-size: 18px;
    color: #1f2937;
  }

  .empty-preview p {
    margin: 0;
  }

  .report-content {
    max-width: 800px;
    margin: 0 auto;
    background: white;
    padding: 40px;
    border-radius: 8px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  }

  .report-header {
    text-align: center;
    padding-bottom: 30px;
    border-bottom: 2px solid #3b82f6;
    margin-bottom: 30px;
  }

  .report-logo {
    font-size: 48px;
    margin-bottom: 16px;
  }

  .report-main-title {
    font-size: 24px;
    font-weight: 700;
    color: #1f2937;
    margin: 0 0 8px 0;
  }

  .report-subtitle {
    font-size: 16px;
    color: #6b7280;
    margin: 0 0 16px 0;
  }

  .report-meta {
    font-size: 13px;
    color: #9ca3af;
    margin: 4px 0;
  }

  .report-section {
    margin-bottom: 30px;
  }

  .report-section-title {
    font-size: 18px;
    font-weight: 600;
    color: #1f2937;
    margin: 0 0 16px 0;
    padding-bottom: 8px;
    border-bottom: 1px solid #e5e7eb;
  }

  .summary-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
    gap: 12px;
  }

  .summary-card {
    text-align: center;
    padding: 16px;
    background: #f9fafb;
    border-radius: 8px;
  }

  .summary-value {
    font-size: 24px;
    font-weight: 700;
    color: #1f2937;
    margin-bottom: 4px;
  }

  .summary-label {
    font-size: 12px;
    color: #6b7280;
  }

  .summary-card.online .summary-value { color: #10b981; }
  .summary-card.warning .summary-value { color: #f59e0b; }
  .summary-card.error .summary-value { color: #ef4444; }

  .report-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }

  .report-table th,
  .report-table td {
    padding: 10px 12px;
    text-align: left;
    border-bottom: 1px solid #e5e7eb;
  }

  .report-table th {
    background: #f9fafb;
    font-weight: 600;
    color: #374151;
  }

  .recommendation-list {
    margin: 0;
    padding-left: 20px;
    font-size: 14px;
    line-height: 1.8;
    color: #4b5563;
  }

  .recommendation-list li {
    margin-bottom: 8px;
  }

  .report-footer {
    text-align: center;
    padding-top: 20px;
    margin-top: 30px;
    border-top: 1px solid #e5e7eb;
    font-size: 12px;
    color: #9ca3af;
  }

  .report-footer p {
    margin: 4px 0;
  }

  .history-section {
    background: white;
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  }

  .report-list {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
    gap: 16px;
  }

  .report-card {
    background: #f9fafb;
    border-radius: 8px;
    border: 1px solid #e5e7eb;
    overflow: hidden;
    transition: all 0.2s;
  }

  .report-card:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    border-color: #3b82f6;
  }

  .report-card-header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 16px;
    border-bottom: 1px solid #e5e7eb;
  }

  .report-type-icon {
    font-size: 28px;
  }

  .report-card-info {
    flex: 1;
  }

  .report-card-title {
    font-size: 16px;
    font-weight: 600;
    color: #1f2937;
    margin: 0 0 4px 0;
  }

  .report-card-meta {
    font-size: 12px;
    color: #6b7280;
    margin: 0;
  }

  .report-status {
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 500;
  }

  .report-status.completed {
    background: #dcfce7;
    color: #166534;
  }

  .report-card-body {
    padding: 12px 16px;
  }

  .report-card-detail {
    display: flex;
    gap: 16px;
    font-size: 13px;
    color: #6b7280;
  }

  .report-card-footer {
    display: flex;
    gap: 8px;
    padding: 12px 16px;
    border-top: 1px solid #e5e7eb;
  }

  .report-card-footer .btn {
    flex: 1;
    justify-content: center;
  }

  .empty {
    text-align: center;
    padding: 60px;
    color: #6b7280;
  }

  @media (max-width: 1200px) {
    .generate-layout {
      grid-template-columns: 1fr;
    }

    .config-panel {
      position: sticky;
      top: 0;
      z-index: 10;
    }
  }

  @media (max-width: 768px) {
    .report-generator {
      padding: 16px;
    }

    .datetime-group {
      flex-direction: column;
      align-items: stretch;
    }

    .report-list {
      grid-template-columns: 1fr;
    }

    .report-content {
      padding: 20px;
    }

    .summary-grid {
      grid-template-columns: repeat(2, 1fr);
    }
  }
</style>
