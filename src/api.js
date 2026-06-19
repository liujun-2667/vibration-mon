const BASE_URL = 'http://localhost:8000/api/v1';

async function request(url, options = {}) {
  const defaultHeaders = {
    'Content-Type': 'application/json',
  };

  const config = {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
  };

  try {
    const response = await fetch(`${BASE_URL}${url}`, config);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.message || data.detail || `HTTP error! status: ${response.status}`);
    }

    return data;
  } catch (error) {
    console.error(`API request failed: ${url}`, error);
    throw error;
  }
}

export const devicesApi = {
  getDevices: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/devices${query ? `?${query}` : ''}`);
  },

  getDevice: (deviceId) => request(`/devices/${deviceId}`),

  createDevice: (deviceData) =>
    request('/devices', {
      method: 'POST',
      body: JSON.stringify(deviceData),
    }),

  updateDevice: (deviceId, deviceData) =>
    request(`/devices/${deviceId}`, {
      method: 'PUT',
      body: JSON.stringify(deviceData),
    }),

  deleteDevice: (deviceId) =>
    request(`/devices/${deviceId}`, {
      method: 'DELETE',
    }),

  updateDeviceStatus: (deviceId, status) =>
    request(`/devices/${deviceId}/status?new_status=${status}`, {
      method: 'PATCH',
    }),

  getDeviceSummary: (deviceId) => request(`/devices/${deviceId}/summary`),
};

export const samplingApi = {
  getSamplingParams: (deviceId) => request(`/sampling/${deviceId}`),

  listSamplingParams: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/sampling${query ? `?${query}` : ''}`);
  },

  createSamplingParams: (paramsData) =>
    request('/sampling', {
      method: 'POST',
      body: JSON.stringify(paramsData),
    }),

  updateSamplingParams: (paramsId, paramsData) =>
    request(`/sampling/${paramsId}`, {
      method: 'PUT',
      body: JSON.stringify(paramsData),
    }),

  deleteSamplingParams: (paramsId) =>
    request(`/sampling/${paramsId}`, {
      method: 'DELETE',
    }),

  applySamplingParams: (deviceId) =>
    request(`/sampling/${deviceId}/apply`, {
      method: 'POST',
    }),

  getSupportedSampleRates: () => request('/sampling/supported-rates'),
};

export const alarmsApi = {
  getAlarmRules: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/alarms/rules${query ? `?${query}` : ''}`);
  },

  getAlarmRule: (ruleId) => request(`/alarms/rules/${ruleId}`),

  createAlarmRule: (ruleData) =>
    request('/alarms/rules', {
      method: 'POST',
      body: JSON.stringify(ruleData),
    }),

  updateAlarmRule: (ruleId, ruleData) =>
    request(`/alarms/rules/${ruleId}`, {
      method: 'PUT',
      body: JSON.stringify(ruleData),
    }),

  deleteAlarmRule: (ruleId) =>
    request(`/alarms/rules/${ruleId}`, {
      method: 'DELETE',
    }),

  toggleAlarmRule: (ruleId, enabled) => {
    const url = enabled !== undefined
      ? `/alarms/rules/${ruleId}/toggle?enabled=${enabled}`
      : `/alarms/rules/${ruleId}/toggle`;
    return request(url, {
      method: 'PATCH',
    });
  },

  getAlarmRecords: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/alarms/records${query ? `?${query}` : ''}`);
  },

  getAlarmRecord: (recordId) => request(`/alarms/records/${recordId}`),

  acknowledgeAlarm: (recordId) =>
    request(`/alarms/records/${recordId}/acknowledge`, {
      method: 'PUT',
    }),

  batchAcknowledgeAlarms: (recordIds) => {
    const query = recordIds.map(id => `record_ids=${id}`).join('&');
    return request(`/alarms/records/batch-acknowledge?${query}`, {
      method: 'POST',
    });
  },

  getAlarmSummary: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/alarms/records/summary${query ? `?${query}` : ''}`);
  },
};

export const dataApi = {
  getVibrationData: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/data${query ? `?${query}` : ''}`);
  },

  getVibrationDataDetail: (dataId) => request(`/data/${dataId}`),

  uploadVibrationData: (data) =>
    request('/data', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  deleteVibrationData: (dataId) =>
    request(`/data/${dataId}`, {
      method: 'DELETE',
    }),

  getLatestVibrationData: (deviceId, params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/data/${deviceId}/latest${query ? `?${query}` : ''}`);
  },

  batchUploadData: (dataList) =>
    request('/data/batch', {
      method: 'POST',
      body: JSON.stringify(dataList),
    }),

  exportData: (deviceId, params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/data/${deviceId}/export${query ? `?${query}` : ''}`);
  },

  getDataStatistics: (deviceId, params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/data/${deviceId}/statistics${query ? `?${query}` : ''}`);
  },

  cleanupOldData: (deviceId, daysToKeep) =>
    request(`/data/${deviceId}/cleanup?days_to_keep=${daysToKeep}`, {
      method: 'DELETE',
    }),

  getTimeDomainFeatures: (params = {}) => {
    console.warn('getTimeDomainFeatures is deprecated, use analysisApi.analyzeVibration instead');
    return Promise.resolve({ success: true, data: null, message: 'Deprecated API' });
  },

  getFrequencyDomainFeatures: (params = {}) => {
    console.warn('getFrequencyDomainFeatures is deprecated, use analysisApi.analyzeVibration instead');
    return Promise.resolve({ success: true, data: null, message: 'Deprecated API' });
  },

  getTrendData: (params = {}) => {
    console.warn('getTrendData is deprecated, use analysisApi.getAnalysisTrend instead');
    return analysisApi.getAnalysisTrend(params.device_id, params);
  },
};

export const analysisApi = {
  analyzeVibration: (analysisRequest) =>
    request('/analysis', {
      method: 'POST',
      body: JSON.stringify(analysisRequest),
    }),

  getAnalysisResults: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/analysis/results${query ? `?${query}` : ''}`);
  },

  getAnalysisResult: (resultId) => request(`/analysis/results/${resultId}`),

  getLatestAnalysis: (deviceId) => request(`/analysis/${deviceId}/latest`),

  getAnalysisTrend: (deviceId, params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/analysis/${deviceId}/trend${query ? `?${query}` : ''}`);
  },

  batchAnalyze: (requests) =>
    request('/analysis/batch', {
      method: 'POST',
      body: JSON.stringify(requests),
    }),

  compareFeatures: (deviceIds, params = {}) => {
    const idParams = deviceIds.map(id => `device_ids=${id}`).join('&');
    const otherParams = new URLSearchParams(params).toString();
    const query = [idParams, otherParams].filter(Boolean).join('&');
    return request(`/analysis/features/compare${query ? `?${query}` : ''}`);
  },

  analyzeTimeDomain: (deviceId, data) => {
    console.warn('analyzeTimeDomain is deprecated, use analyzeVibration instead');
    return analysisApi.analyzeVibration({
      device_id: deviceId,
      data: data.data,
      sample_rate: data.sample_rate || 10000,
      channel: data.channel || 0,
    });
  },

  analyzeFrequencyDomain: (deviceId, data) => {
    console.warn('analyzeFrequencyDomain is deprecated, use analyzeVibration instead');
    return analysisApi.analyzeVibration({
      device_id: deviceId,
      data: data.data,
      sample_rate: data.sample_rate || 10000,
      channel: data.channel || 0,
    });
  },

  getHealthIndex: (deviceId) => {
    console.warn('getHealthIndex is deprecated, use getLatestAnalysis instead');
    return analysisApi.getLatestAnalysis(deviceId);
  },

  getFaultDiagnosis: (deviceId) => {
    console.warn('getFaultDiagnosis is deprecated, use getLatestAnalysis instead');
    return analysisApi.getLatestAnalysis(deviceId);
  },

  compareDevices: (deviceIds) => {
    console.warn('compareDevices is deprecated, use compareFeatures instead');
    return analysisApi.compareFeatures(deviceIds);
  },
};

export const reportsApi = {
  generateReport: (reportData) =>
    request('/reports', {
      method: 'POST',
      body: JSON.stringify(reportData),
    }),

  getReportList: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/reports${query ? `?${query}` : ''}`);
  },

  getReport: (reportId) => request(`/reports/${reportId}`),

  downloadReport: (reportId) => `${BASE_URL}/reports/${reportId}/download`,

  previewReport: (reportData) =>
    request('/reports/preview', {
      method: 'POST',
      body: JSON.stringify(reportData),
    }),

  deleteReport: (reportId) =>
    request(`/reports/${reportId}`, {
      method: 'DELETE',
    }),

  getReportTemplates: () => request('/reports/templates/list'),
};

export function createWebSocket(deviceId, onMessage, onError, onClose) {
  const wsUrl = `ws://localhost:8000/ws/${deviceId}`;
  const ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    console.log(`WebSocket connected to device ${deviceId}`);
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (onMessage) onMessage(data);
    } catch (e) {
      console.error('Failed to parse WebSocket message:', e);
    }
  };

  ws.onerror = (error) => {
    console.error(`WebSocket error for device ${deviceId}:`, error);
    if (onError) onError(error);
  };

  ws.onclose = (event) => {
    console.log(`WebSocket closed for device ${deviceId}:`, event.code, event.reason);
    if (onClose) onClose(event);
  };

  return ws;
}

/**
 * 带指数退避自动重连的 WebSocket 管理器。
 * 初始重连间隔 1 秒,每次失败翻倍,最大 30 秒。
 * status 状态值: 'connecting' | 'connected' | 'reconnecting' | 'disconnected'
 */
export function createReconnectingWebSocket(deviceId, { onMessage, onStatusChange } = {}) {
  const WS_URL = `ws://localhost:8000/ws/${deviceId}`;
  const BASE_DELAY = 1000;
  const MAX_DELAY = 30000;

  let ws = null;
  let retryCount = 0;
  let closedByUser = false;
  let reconnectTimer = null;
  let messageHandler = null;
  let statusHandler = null;

  function setStatus(status) {
    if (statusHandler) statusHandler(status);
  }

  function computeDelay() {
    const delay = Math.min(MAX_DELAY, BASE_DELAY * Math.pow(2, retryCount));
    return delay;
  }

  function scheduleReconnect() {
    if (closedByUser) return;
    const delay = computeDelay();
    setStatus('reconnecting');
    reconnectTimer = setTimeout(connect, delay);
  }

  function connect() {
    if (closedByUser) return;
    setStatus('connecting');
    try {
      ws = new WebSocket(WS_URL);
    } catch (e) {
      console.error(`WebSocket 创建失败 device ${deviceId}:`, e);
      retryCount += 1;
      scheduleReconnect();
      return;
    }

    ws.onopen = () => {
      retryCount = 0;
      setStatus('connected');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (messageHandler) messageHandler(data);
      } catch (e) {
        console.error(`WebSocket 消息解析失败 device ${deviceId}:`, e);
      }
    };

    ws.onerror = (error) => {
      console.error(`WebSocket 错误 device ${deviceId}:`, error);
    };

    ws.onclose = () => {
      if (ws) {
        ws.onopen = null;
        ws.onmessage = null;
        ws.onerror = null;
        ws.onclose = null;
      }
      ws = null;
      if (closedByUser) {
        setStatus('disconnected');
        return;
      }
      retryCount += 1;
      scheduleReconnect();
    };
  }

  function disconnect() {
    closedByUser = true;
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    if (ws) {
      try {
        ws.onopen = null;
        ws.onmessage = null;
        ws.onerror = null;
        ws.onclose = null;
        ws.close();
      } catch (e) {
        // ignore close errors
      }
      ws = null;
    }
    messageHandler = null;
    statusHandler = null;
    setStatus('disconnected');
  }

  messageHandler = onMessage || null;
  statusHandler = onStatusChange || null;

  connect();

  return { disconnect };
}

export const monitorApi = {
  getRealtimeSummary: () => request('/monitor/realtime-summary'),

  getDeviceState: (deviceId) => request(`/monitor/${deviceId}/state`),

  exportReport: (deviceId, hours = 24) => request(`/monitor/export-report?device_id=${deviceId}&hours=${hours}`),
};

export const diagnosisApi = {
  createTask: (taskData) =>
    request('/diagnosis/tasks', {
      method: 'POST',
      body: JSON.stringify(taskData),
    }),

  getTasks: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/diagnosis/tasks${query ? `?${query}` : ''}`);
  },

  getTask: (taskId) => request(`/diagnosis/tasks/${taskId}`),

  runTask: (taskId) =>
    request(`/diagnosis/tasks/${taskId}/run`, {
      method: 'POST',
    }),

  getMatchResults: (taskId) => request(`/diagnosis/tasks/${taskId}/match-results`),

  getReport: (taskId) => request(`/diagnosis/tasks/${taskId}/report`),

  downloadReport: (taskId) => `${BASE_URL}/diagnosis/tasks/${taskId}/report/download`,

  getKnowledge: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/diagnosis/knowledge${query ? `?${query}` : ''}`);
  },

  createKnowledge: (knowledgeData) =>
    request('/diagnosis/knowledge', {
      method: 'POST',
      body: JSON.stringify(knowledgeData),
    }),

  deleteKnowledge: (knowledgeId) =>
    request(`/diagnosis/knowledge/${knowledgeId}`, {
      method: 'DELETE',
    }),

  checkKnowledgeReference: (knowledgeId) =>
    request(`/diagnosis/knowledge/${knowledgeId}/check-reference`),
};

export const systemApi = {
  healthCheck: () => fetch('http://localhost:8000/health').then((r) => r.json()),

  getRoot: () => fetch('http://localhost:8000/').then((r) => r.json()),
};

export default {
  devices: devicesApi,
  sampling: samplingApi,
  alarms: alarmsApi,
  data: dataApi,
  analysis: analysisApi,
  reports: reportsApi,
  monitor: monitorApi,
  diagnosis: diagnosisApi,
  system: systemApi,
  createWebSocket,
  createReconnectingWebSocket,
};
