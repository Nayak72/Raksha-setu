/**
 * Simulation API client — talks to the new FastAPI simulation engine.
 * All endpoints match the backend contracts exactly.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8001';

// ── Types ──────────────────────────────────────
export type SimZone = {
  id: string;
  name: string;
  lat: number;
  lng: number;
  population: number;
  affected_population: number;
  damage_level: number;
  alert_count: number;
  severity: 'critical' | 'high' | 'medium' | 'low';
  disaster_type: 'flood' | 'cyclone' | 'landslide' | 'storm';
};

export type SimShelter = {
  shelter_id: string;
  name: string;
  lat: number;
  lng: number;
  distance: number;
  capacity: number;
  available_capacity: number;
};

export type SimAllocation = {
  shelter_id: string;
  food_units: number;
  beds: number;
  medical_kits: number;
  rescue_teams: number;
};

export type SimEvacuation = {
  zone_id: string;
  evacuated_count: number;
};

export type SimRoute = {
  path: [number, number][];
  distance: number;
  time: number;
};

export type SimRouteResult = {
  routes: SimRoute[];
  shortest_route_index: number;
};

export type ThresholdCheck = {
  parameter: string;
  value: number;
  threshold: number;
  exceeded: boolean;
};

export type SimLog = {
  timestamp: string;
  agent_name: string;
  zone_id: string;
  input_data: Record<string, any>;
  parameters_used: Record<string, any>;
  thresholds_checked: ThresholdCheck[];
  decision: string;
  outcome: string;
  reasoning: string;
};

export type SimPayload = {
  zones: SimZone[];
  evacuations: SimEvacuation[];
  allocations: SimAllocation[];
  logs: SimLog[];
  routes: Record<string, SimRouteResult>;
  yolo_results?: any[];
  yolo_stats?: Record<string, any>;
};

// ── Fetchers ───────────────────────────────────

export async function fetchSimZones(): Promise<SimZone[]> {
  const res = await fetch(`${API_BASE}/api/v1/zones`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchSheltersNear(zone_id: string): Promise<SimShelter[]> {
  const res = await fetch(`${API_BASE}/api/v1/shelters/near?zone_id=${zone_id}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchAllocations(): Promise<SimAllocation[]> {
  const res = await fetch(`${API_BASE}/api/v1/allocation`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchEvacuations(): Promise<SimEvacuation[]> {
  const res = await fetch(`${API_BASE}/api/v1/evacuations`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchSimLogs(zone_id?: string): Promise<SimLog[]> {
  const url = zone_id
    ? `${API_BASE}/api/v1/logs?zone_id=${zone_id}`
    : `${API_BASE}/api/v1/logs`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchRoutes(zone_id: string): Promise<SimRouteResult> {
  const res = await fetch(`${API_BASE}/api/v1/routes?zone_id=${zone_id}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export function getWebSocketUrl(): string {
  const base = API_BASE.replace(/^http/, 'ws');
  return `${base}/api/v1/ws`;
}
