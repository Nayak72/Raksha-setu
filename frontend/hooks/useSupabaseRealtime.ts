/**
 * React hooks for Supabase Realtime subscriptions.
 * Provides live data from zones, alerts, volunteers, shelters, etc.
 * Migrated: import.meta.env → process.env
 */
'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { supabase, Zone, Alert, Volunteer, Shelter, Detection, Acknowledgment, AgentLog } from '../lib/supabase';
import { RealtimeChannel } from '@supabase/supabase-js';

// ─── Agent Logs ─────────────────────────────
export function useAgentLogs() {
  const [logs, setLogs] = useState<AgentLog[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchLogs = useCallback(async () => {
    try {
      const base = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8001';
      const res = await fetch(`${base}/api/v1/agent-logs`);
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data)) {
          setLogs(data);
        }
      } else {
        // API unavailable, will fallback to Supabase
        throw new Error(`HTTP ${res.status}`);
      }
    } catch (err) {
      // Fallback to Supabase when API unavailable
      const { data, error } = await supabase
        .from('agent_logs')
        .select('*')
        .order('timestamp', { ascending: false })
        .limit(100);
      if (!error && data) setLogs(data);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchLogs();

    const channel: RealtimeChannel = supabase
      .channel('agent-logs-realtime')
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'agent_logs' }, (payload) => {
        setLogs((prev) => [payload.new as AgentLog, ...prev].slice(0, 100));
      })
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [fetchLogs]);

  return { logs, loading, refetch: fetchLogs };
}

// ─── Zones ─────────────────────────────────
export function useZones() {
  const [zones, setZones] = useState<Zone[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchZones = useCallback(async () => {
    const { data, error } = await supabase.from('zones').select('*');
    if (!error && data) setZones(data);
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchZones();

    const channel: RealtimeChannel = supabase
      .channel('zones-realtime')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'zones' }, (payload) => {
        if (payload.eventType === 'INSERT') {
          setZones((prev) => [...prev, payload.new as Zone]);
        } else if (payload.eventType === 'UPDATE') {
          setZones((prev) =>
            prev.map((z) => (z.id === (payload.new as Zone).id ? (payload.new as Zone) : z))
          );
        } else if (payload.eventType === 'DELETE') {
          setZones((prev) => prev.filter((z) => z.id !== (payload.old as Zone).id));
        }
      })
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [fetchZones]);

  return { zones, loading, refetch: fetchZones };
}

// ─── Alerts ─────────────────────────────────
export function useAlerts() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [latestAlert, setLatestAlert] = useState<Alert | null>(null);

  const fetchAlerts = useCallback(async () => {
    const { data, error } = await supabase
      .from('alerts')
      .select('*')
      .order('timestamp', { ascending: false })
      .limit(100);
    if (!error && data) setAlerts(data);
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchAlerts();

    const channel: RealtimeChannel = supabase
      .channel('alerts-realtime')
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'alerts' }, (payload) => {
        const newAlert = payload.new as Alert;
        setAlerts((prev) => [newAlert, ...prev].slice(0, 100));
        setLatestAlert(newAlert);
      })
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [fetchAlerts]);

  return { alerts, loading, latestAlert, refetch: fetchAlerts };
}

// ─── Volunteers ─────────────────────────────
export function useVolunteers() {
  const [volunteers, setVolunteers] = useState<Volunteer[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchVolunteers = useCallback(async () => {
    const { data, error } = await supabase.from('volunteers').select('*');
    if (!error && data) setVolunteers(data);
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchVolunteers();

    const channel: RealtimeChannel = supabase
      .channel('volunteers-realtime')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'volunteers' }, (payload) => {
        if (payload.eventType === 'INSERT') {
          setVolunteers((prev) => [...prev, payload.new as Volunteer]);
        } else if (payload.eventType === 'UPDATE') {
          setVolunteers((prev) =>
            prev.map((v) => (v.id === (payload.new as Volunteer).id ? (payload.new as Volunteer) : v))
          );
        } else if (payload.eventType === 'DELETE') {
          setVolunteers((prev) => prev.filter((v) => v.id !== (payload.old as Volunteer).id));
        }
      })
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [fetchVolunteers]);

  return { volunteers, loading, refetch: fetchVolunteers };
}

// ─── Shelters ─────────────────────────────────
export function useShelters() {
  const [shelters, setShelters] = useState<Shelter[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchShelters = useCallback(async () => {
    const { data, error } = await supabase.from('shelters').select('*');
    if (!error && data) setShelters(data);
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchShelters();

    const channel: RealtimeChannel = supabase
      .channel('shelters-realtime')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'shelters' }, (payload) => {
        if (payload.eventType === 'INSERT') {
          setShelters((prev) => [...prev, payload.new as Shelter]);
        } else if (payload.eventType === 'UPDATE') {
          setShelters((prev) =>
            prev.map((s) => (s.id === (payload.new as Shelter).id ? (payload.new as Shelter) : s))
          );
        }
      })
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [fetchShelters]);

  return { shelters, loading, refetch: fetchShelters };
}

// ─── Detections ─────────────────────────────
export function useDetections() {
  const [detections, setDetections] = useState<Detection[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchDetections = useCallback(async () => {
    const { data, error } = await supabase
      .from('detections')
      .select('*')
      .order('timestamp', { ascending: false })
      .limit(50);
    if (!error && data) setDetections(data);
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchDetections();

    const channel: RealtimeChannel = supabase
      .channel('detections-realtime')
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'detections' }, (payload) => {
        setDetections((prev) => [payload.new as Detection, ...prev].slice(0, 50));
      })
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [fetchDetections]);

  return { detections, loading, refetch: fetchDetections };
}

// ─── Acknowledgments (Broadcast Status) ─────
export function useAcknowledgments(alertId?: string) {
  const [acks, setAcks] = useState<Acknowledgment[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchAcks = useCallback(async () => {
    let query = supabase.from('acknowledgments').select('*');
    if (alertId) query = query.eq('alert_id', alertId);
    const { data, error } = await query.order('timestamp', { ascending: false });
    if (!error && data) setAcks(data);
    setLoading(false);
  }, [alertId]);

  useEffect(() => {
    fetchAcks();

    const channel: RealtimeChannel = supabase
      .channel('acks-realtime')
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'acknowledgments' }, (payload) => {
        setAcks((prev) => [payload.new as Acknowledgment, ...prev]);
      })
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [fetchAcks]);

  return { acks, loading, refetch: fetchAcks };
}

// ─── System Status ──────────────────────────
export type SystemStatus = {
  status: string;
  udp_active: boolean;
  pg_listener_active: boolean;
  counts: {
    zones: number;
    volunteers: number;
    shelters: number;
    active_alerts: number;
  };
};

export function useSystemStatus() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | undefined>(undefined);

  const fetchStatus = useCallback(async () => {
    const base = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8001';
    try {
      const res = await fetch(`${base}/api/v1/status`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setStatus(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Connection failed');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    intervalRef.current = setInterval(fetchStatus, 5000);
    return () => clearInterval(intervalRef.current);
  }, [fetchStatus]);

  return { status, loading, error, refetch: fetchStatus };
}
