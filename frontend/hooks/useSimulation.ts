/**
 * useSimulation — WebSocket + polling fallback hook for real-time simulation data.
 * Connects to the backend /ws endpoint. Falls back to 5s polling if WS fails.
 */
'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  SimZone, SimEvacuation, SimAllocation, SimLog, SimRouteResult, SimPayload,
  fetchSimZones, fetchEvacuations, fetchAllocations, fetchSimLogs,
  getWebSocketUrl,
} from '../lib/simulation-api';

export type SimulationState = {
  zones: SimZone[];
  evacuations: SimEvacuation[];
  allocations: SimAllocation[];
  logs: SimLog[];
  routes: Record<string, SimRouteResult>;
  connected: boolean;
  lastUpdate: Date | null;
};

export function useSimulation(): SimulationState & { refetch: () => void } {
  const [state, setState] = useState<SimulationState>({
    zones: [],
    evacuations: [],
    allocations: [],
    logs: [],
    routes: {},
    connected: false,
    lastUpdate: null,
  });

  const wsRef = useRef<WebSocket | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Polling fallback
  const pollData = useCallback(async () => {
    try {
      const [zones, evacuations, allocations, logs] = await Promise.all([
        fetchSimZones(),
        fetchEvacuations(),
        fetchAllocations(),
        fetchSimLogs(),
      ]);
      setState(prev => ({
        ...prev,
        zones,
        evacuations,
        allocations,
        logs,
        lastUpdate: new Date(),
      }));
    } catch {
      // Silently fail polling — will retry next interval
    }
  }, []);

  // WebSocket connection
  const connectWs = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      const ws = new WebSocket(getWebSocketUrl());
      wsRef.current = ws;

      ws.onopen = () => {
        setState(prev => ({ ...prev, connected: true }));
        // Stop polling if WS connected
        if (pollRef.current) {
          clearInterval(pollRef.current);
          pollRef.current = null;
        }
      };

      ws.onmessage = (event) => {
        try {
          const data: SimPayload = JSON.parse(event.data);
          setState(prev => ({
            ...prev,
            zones: data.zones || prev.zones,
            evacuations: data.evacuations || prev.evacuations,
            allocations: data.allocations || prev.allocations,
            logs: data.logs || prev.logs,
            routes: data.routes || prev.routes,
            lastUpdate: new Date(),
          }));
        } catch {
          // Malformed message, skip
        }
      };

      ws.onclose = () => {
        setState(prev => ({ ...prev, connected: false }));
        // Fallback to polling
        if (!pollRef.current) {
          pollRef.current = setInterval(pollData, 5000);
        }
        // Reconnect after 3s
        reconnectRef.current = setTimeout(connectWs, 3000);
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      // WS connection failed, use polling
      if (!pollRef.current) {
        pollRef.current = setInterval(pollData, 5000);
      }
    }
  }, [pollData]);

  useEffect(() => {
    // Initial data fetch
    pollData();
    // Try WebSocket
    connectWs();

    return () => {
      wsRef.current?.close();
      if (pollRef.current) clearInterval(pollRef.current);
      if (reconnectRef.current) clearTimeout(reconnectRef.current);
    };
  }, [connectWs, pollData]);

  return { ...state, refetch: pollData };
}
