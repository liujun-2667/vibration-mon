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
      throw new Error(data.message || `HTTP error! status: ${response.status}`);
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

  batchAcknowledgeAlarms: (recordIds) =>
    request('/alarms/records/batch-acknowledge', {
      method: 'POST',
      body: JSON.stringify(recordIds),
    }),

  getAlarmSummary: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/alarms/records/summary${query ? `?${query}` : ''}`);
  },
};

export const dataApi = {
  getVibrationData: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/data/vibration${query ? `?${query}` : ''}`);
  },

  getLatestVibrationData: (deviceId) =>
    request(`/data/vibration/latest/${deviceId}`),

  getTimeDomainFeatures: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/data/features/time-domain${query ? `?${query}` : ''}`);
  },

  getFrequencyDomainFeatures: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/data/features/frequency-domain${query ? `?${query}` : ''}`);
  },

  getTrendData: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/data/trend${query ? `?${query}` : ''}`);
  },
};

export const analysisApi = {
  analyzeTimeDomain: (deviceId, data) =>
    request(`/analysis/time-domain/${deviceId}`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  analyzeFrequencyDomain: (deviceId, data) =>
    request(`/analysis/frequency-domain/${deviceId}`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getHealthIndex: (deviceId) =>
    request(`/analysis/health/${deviceId}`),

  getFaultDiagnosis: (deviceId) =>
    request(`/analysis/diagnosis/${deviceId}`),

  compareDevices: (deviceIds) =>
    request('/analysis/compare', {
      method: 'POST',
      body: JSON.stringify(deviceIds),
    }),
};

export const reportsApi = {
  generateReport: (reportData) =>
    request('/reports/generate', {
      method: 'POST',
      body: JSON.stringify(reportData),
    }),

  getReportList: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/reports${query ? `?${query}` : ''}`);
  },

  getReport: (reportId) => request(`/reports/${reportId}`),

  downloadReport: (reportId) => `${BASE_URL}/reports/${reportId}/download`,

  deleteReport: (reportId) =>
    request(`/reports/${reportId}`, {
      method: 'DELETE',
    }),
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
  system: systemApi,
  createWebSocket,
};
