/**
 * Dashboard Page — overview cards + criticality zones + map + agent logs + broadcast.
 * Uses simulation data as the single source of truth for zone/evacuation stats.
 * Supabase data is used only for alerts, acknowledgments, and legacy volunteer/shelter DB counts.
 */
'use client';

import { useState, useEffect, useCallback } from 'react';
import AppShell, { useRealtimeData } from '../AppShell';
import { useSimulation } from '../../hooks/useSimulation';
import { fetchSheltersNear, SimShelter } from '../../lib/simulation-api';
import LoadingPanel from '../../components/ui/LoadingPanel';
import dynamic from 'next/dynamic';
import { Wifi, WifiOff, MapPin, Users, Home, AlertTriangle, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { motion } from 'framer-motion';
import type { BroadcastRecord, BroadcastStats } from '../../components/BroadcastStatus';

const LiveMap = dynamic(() => import('../../components/map/LiveMap'), {
  ssr: false,
  loading: () => <LoadingPanel />,
});
const AgentLogsPanel = dynamic(() => import('../../components/logs/AgentLogsPanel'), {
  ssr: false,
  loading: () => <LoadingPanel />,
});
const BroadcastStatus = dynamic(() => import('../../components/BroadcastStatus'), {
  ssr: false,
  loading: () => <LoadingPanel />,
});
const ZoneCriticalityCards = dynamic(
  () => import('../../components/simulation/ZoneCriticalityCards'),
  { ssr: false, loading: () => <LoadingPanel /> }
);

function DashboardContent() {
  const { zones, alerts, volunteers, shelters, detections, acknowledgments, agentLogs, systemStatus } =
    useRealtimeData();
  const sim = useSimulation();

  // ── Broadcast data ───────────────────────
  const [broadcasts, setBroadcasts] = useState<BroadcastRecord[]>([]);
  const [broadcastStats, setBroadcastStats] = useState<BroadcastStats>({
    total_sent: 0,
    devices_reached: 0,
  });

  const base = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

  const fetchBroadcasts = useCallback(async () => {
    try {
      const res = await fetch(`${base}/api/v1/broadcasts`);
      if (res.ok) {
        const data = await res.json();
        if (data.broadcasts) setBroadcasts(data.broadcasts);
        if (data.stats) setBroadcastStats(data.stats);
      }
    } catch { /* backend offline */ }
  }, [base]);

  useEffect(() => {
    fetchBroadcasts();
    const interval = setInterval(fetchBroadcasts, 5000);
    return () => clearInterval(interval);
  }, [fetchBroadcasts]);

  // Compute sim summary stats
  const critCount = sim.zones.filter((z) => z.severity === 'critical').length;
  const highCount = sim.zones.filter((z) => z.severity === 'high').length;
  const totalEvac = sim.evacuations.reduce((s, e) => s + e.evacuated_count, 0);
  const totalPop = sim.zones.reduce((s, z) => s + z.population, 0);

  // Fetch sim shelters for mapping lines
  const [simSheltersMap, setSimSheltersMap] = useState<Record<string, SimShelter[]>>({});
  
  useEffect(() => {
    if (sim.zones.length === 0) return;
    const fetchAllShelters = async () => {
      const map: Record<string, SimShelter[]> = {};
      for (const zone of sim.zones) {
        try {
          const res = await fetchSheltersNear(zone.id);
          map[zone.id] = res;
        } catch (e) {
          // ignore
        }
      }
      setSimSheltersMap(map);
    };
    fetchAllShelters();
  }, [sim.zones]);

  const allSimShelters = Object.values(simSheltersMap).flat();
  const simConnections = Object.entries(simSheltersMap).map(([zone_id, shelters]) => ({ zone_id, shelters }));

  // Unified metric cards — prefer simulation data when available
  const activeZoneCount = sim.zones.length > 0 ? sim.zones.length : zones.zones.length;
  const uniqueSimShelters = new Set(allSimShelters.map(s => s.shelter_id)).size;
  const shelterCount = uniqueSimShelters > 0 ? uniqueSimShelters : shelters.shelters.length;
  const recentAlerts = alerts.alerts.filter(
    (a) => new Date(a.timestamp) > new Date(Date.now() - 3600000)
  ).length;

  const metrics = [
    {
      label: 'Active Zones',
      value: activeZoneCount,
      subValue: `${critCount} critical · ${highCount} high`,
      icon: MapPin,
      color: 'text-raksha-400',
      bgColor: 'from-raksha-500/10 to-raksha-500/5',
      borderColor: 'border-raksha-500/20',
      trend: critCount > 0 ? 'up' as const : 'neutral' as const,
    },
    {
      label: 'Evacuated',
      value: totalEvac.toLocaleString(),
      subValue: `of ${totalPop.toLocaleString()} total pop`,
      icon: Users,
      color: 'text-safe-400',
      bgColor: 'from-safe-500/10 to-safe-500/5',
      borderColor: 'border-safe-500/20',
      trend: totalEvac > 0 ? 'up' as const : 'neutral' as const,
    },
    {
      label: 'Shelters',
      value: shelterCount,
      subValue: `${allSimShelters.reduce((s, sh) => s + sh.available_capacity, 0).toLocaleString()} beds available`,
      icon: Home,
      color: 'text-warning-400',
      bgColor: 'from-warning-500/10 to-warning-500/5',
      borderColor: 'border-warning-500/20',
      trend: 'up' as const,
    },
    {
      label: 'Active Alerts',
      value: recentAlerts,
      subValue: `${alerts.alerts.length} total`,
      icon: AlertTriangle,
      color: recentAlerts > 0 ? 'text-danger-400' : 'text-surface-400',
      bgColor: recentAlerts > 0 ? 'from-danger-500/10 to-danger-500/5' : 'from-surface-500/10 to-surface-500/5',
      borderColor: recentAlerts > 0 ? 'border-danger-500/20' : 'border-surface-500/20',
      trend: recentAlerts > 5 ? 'up' as const : recentAlerts > 0 ? 'neutral' as const : 'down' as const,
    },
  ];

  return (
    <div className="space-y-5 animate-fade-in" id="dashboard-page">
      {/* Connection status */}
      <div className="flex items-center justify-end gap-1.5">
        {sim.connected ? (
          <Wifi size={14} className="text-safe-400" />
        ) : (
          <WifiOff size={14} className="text-danger-400" />
        )}
        <span className="text-[10px] text-surface-500">
          {sim.connected ? 'WebSocket Live' : 'Polling Mode'}
          {sim.lastUpdate && ` · Updated ${sim.lastUpdate.toLocaleTimeString()}`}
        </span>
      </div>

      {/* Unified Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {metrics.map((metric, i) => {
          const Icon = metric.icon;
          const TrendIcon =
            metric.trend === 'up' ? TrendingUp : metric.trend === 'down' ? TrendingDown : Minus;

          return (
            <motion.div
              key={metric.label}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
              className={`metric-card bg-gradient-to-br ${metric.bgColor} ${metric.borderColor}`}
            >
              <div className="flex items-start justify-between mb-3">
                <div className={`p-2 rounded-xl bg-surface-800/40 ${metric.color}`}>
                  <Icon size={18} />
                </div>
                <div className="flex items-center gap-1">
                  <TrendIcon
                    size={12}
                    className={
                      metric.trend === 'up'
                        ? metric.label === 'Active Alerts'
                          ? 'text-danger-400'
                          : 'text-safe-400'
                        : metric.trend === 'down'
                        ? 'text-danger-400'
                        : 'text-surface-500'
                    }
                  />
                </div>
              </div>

              <div className="text-2xl font-black text-white mb-0.5">{metric.value}</div>
              <div className="text-xs text-surface-400 font-medium">{metric.label}</div>
              <div className="text-[10px] text-surface-500 mt-1">{metric.subValue}</div>
            </motion.div>
          );
        })}
      </div>

      {/* Zone Criticality Cards */}
      {sim.zones.length > 0 && <ZoneCriticalityCards zones={sim.zones} />}

      {/* Full-width Map */}
      <div className="glass-panel p-1 h-[480px]">
        <LiveMap
          zones={zones.zones}
          shelters={shelters.shelters}
          volunteerCount={volunteers.volunteers.length}
          simZones={sim.zones}
          simShelters={allSimShelters}
          simConnections={simConnections}
        />
      </div>

      {/* Row 2: Agent Logs + Broadcast */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2 glass-panel p-4 h-[420px]">
          <AgentLogsPanel
            agentLogs={agentLogs.logs}
            alerts={alerts.alerts}
            detections={detections.detections}
          />
        </div>
        <div className="glass-panel p-4 h-[420px]">
          <BroadcastStatus
            broadcasts={broadcasts}
            stats={broadcastStats}
            zones={sim.zones.map(z => ({ id: z.id, name: z.name }))}
            isOnline={!!systemStatus.status && !systemStatus.error}
          />
        </div>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <AppShell>
      <DashboardContent />
    </AppShell>
  );
}
