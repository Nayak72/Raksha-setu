/**
 * Broadcast Page — Live UDP broadcast monitoring with device reach tracking.
 * Pulls data from both WebSocket (live) and REST API (history).
 */
'use client';

import { useState, useEffect, useCallback } from 'react';
import AppShell, { useRealtimeData } from '../AppShell';
import LoadingPanel from '../../components/ui/LoadingPanel';
import dynamic from 'next/dynamic';
import type { BroadcastRecord, BroadcastStats } from '../../components/BroadcastStatus';

const BroadcastStatus = dynamic(() => import('../../components/BroadcastStatus'), {
  ssr: false,
  loading: () => <LoadingPanel />,
});

function BroadcastContent() {
  const { zones, systemStatus } = useRealtimeData();
  const [broadcasts, setBroadcasts] = useState<BroadcastRecord[]>([]);
  const [stats, setStats] = useState<BroadcastStats>({
    total_sent: 0,
    devices_reached: 0,
  });

  const isOnline = !!systemStatus.status && !systemStatus.error;
  const base = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

  // Poll the broadcasts API for live data
  const fetchBroadcasts = useCallback(async () => {
    try {
      const res = await fetch(`${base}/api/v1/broadcasts`);
      if (res.ok) {
        const data = await res.json();
        if (data.broadcasts) setBroadcasts(data.broadcasts);
        if (data.stats) setStats(data.stats);
      }
    } catch {
      // Backend offline — broadcasts will appear when it comes online
    }
  }, [base]);

  useEffect(() => {
    fetchBroadcasts();
    const interval = setInterval(fetchBroadcasts, 3000); // Poll every 3s
    return () => clearInterval(interval);
  }, [fetchBroadcasts]);

  // Also listen for WebSocket updates if available
  useEffect(() => {
    let ws: WebSocket | null = null;
    try {
      const wsBase = base.replace('http', 'ws');
      ws = new WebSocket(`${wsBase}/api/v1/ws`);
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.broadcasts) {
            setBroadcasts(data.broadcasts);
          }
          if (data.broadcast_stats) {
            setStats(prev => ({
              ...prev,
              total_sent: data.broadcast_stats.total_sent ?? prev.total_sent,
              devices_reached: data.broadcast_stats.devices_reached ?? prev.devices_reached,
            }));
          }
        } catch { /* ignore parse errors */ }
      };
    } catch { /* WebSocket not available */ }

    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, [base]);

  // Build zone list for manual broadcast dropdown
  const zoneList = zones.zones.map((z) => ({
    id: z.id,
    name: z.name || z.id,
  }));

  return (
    <div className="h-[calc(100vh-4rem)] animate-fade-in">
      <div className="glass-panel p-5 h-full">
        <BroadcastStatus
          broadcasts={broadcasts}
          stats={stats}
          zones={zoneList}
          isOnline={isOnline}
        />
      </div>
    </div>
  );
}

export default function BroadcastPage() {
  return (
    <AppShell>
      <BroadcastContent />
    </AppShell>
  );
}
