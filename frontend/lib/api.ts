/**
 * Centralized API layer for all backend calls.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8001';

export async function fetchAgentLogs() {
  const res = await fetch(`${API_BASE}/api/v1/agent-logs`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}



export async function triggerDetection(payload: {
  zone_id: string;
  count: number;
  metadata?: Record<string, unknown>;
}) {
  const res = await fetch(`${API_BASE}/api/v1/detect`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function simulateWeather(payload: Record<string, unknown>) {
  const res = await fetch(`${API_BASE}/api/v1/simulate-weather`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function broadcastAlert(payload: {
  zone: string;
  message: string;
  severity?: string;
}) {
  const res = await fetch(`${API_BASE}/api/v1/broadcast-alert`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function acknowledgeAlert(payload: {
  device_id: string;
  alert_id: string;
  status?: string;
}) {
  const res = await fetch(`${API_BASE}/api/v1/acknowledge`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchRagStats() {
  const res = await fetch(`${API_BASE}/api/v1/rag-stats`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function queryRag(payload: {
  query: string;
  zone_id?: string;
  collection?: string;
  n_results?: number;
}) {
  const params = new URLSearchParams();
  params.set('query', payload.query);
  if (payload.zone_id) params.set('zone_id', payload.zone_id);
  if (payload.collection) params.set('collection', payload.collection);
  if (payload.n_results) params.set('n_results', String(payload.n_results));

  const res = await fetch(`${API_BASE}/api/v1/rag-query?${params.toString()}`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
