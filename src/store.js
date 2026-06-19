import { writable, derived } from 'svelte/store';

export const devices = writable([]);
export const currentDevice = writable(null);
export const samplingParams = writable({});
export const alarmRecords = writable([]);
export const alarmRules = writable([]);
export const alarmSummary = writable(null);

export const loading = writable({
  devices: false,
  currentDevice: false,
  samplingParams: false,
  alarms: false,
});

export const error = writable({
  devices: null,
  currentDevice: null,
  samplingParams: null,
  alarms: null,
});

export const unacknowledgedAlarmCount = derived(
  alarmRecords,
  ($alarmRecords) => $alarmRecords.filter((a) => !a.acknowledged).length
);

export const deviceStatusCounts = derived(devices, ($devices) => ({
  online: $devices.filter((d) => d.status === 'online').length,
  warning: $devices.filter((d) => d.status === 'warning').length,
  offline: $devices.filter((d) => d.status === 'offline').length,
  total: $devices.length,
}));

export function setLoading(key, value) {
  loading.update(($loading) => ({ ...$loading, [key]: value }));
}

export function setError(key, value) {
  error.update(($error) => ({ ...$error, [key]: value }));
}

export function clearError(key) {
  error.update(($error) => ({ ...$error, [key]: null }));
}

export function selectDevice(device) {
  currentDevice.set(device);
}

export function addDevice(device) {
  devices.update(($devices) => [...$devices, device]);
}

export function updateDevice(deviceId, updates) {
  devices.update(($devices) =>
    $devices.map((d) => (d.id === deviceId ? { ...d, ...updates } : d))
  );
}

export function removeDevice(deviceId) {
  devices.update(($devices) => $devices.filter((d) => d.id !== deviceId));
  if (currentDevice && currentDevice.id === deviceId) {
    currentDevice.set(null);
  }
}

export function acknowledgeAlarm(recordId) {
  alarmRecords.update(($records) =>
    $records.map((r) =>
      r.id === recordId
        ? { ...r, acknowledged: true, acknowledged_at: new Date().toISOString() }
        : r
    )
  );
}

export function batchAcknowledgeAlarms(recordIds) {
  const now = new Date().toISOString();
  alarmRecords.update(($records) =>
    $records.map((r) =>
      recordIds.includes(r.id) && !r.acknowledged
        ? { ...r, acknowledged: true, acknowledged_at: now }
        : r
    )
  );
}
