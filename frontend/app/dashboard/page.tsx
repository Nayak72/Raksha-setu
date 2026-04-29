/**
 * Dashboard Page — overview cards + criticality zones + map + alert feed + agent logs + broadcast.
 * Enhanced with simulation data (zone severity, evacuation stats).
 */
'use client';

import AppShell, { useRealtimeData } from '../AppShell';
import { useSimulation } from '../../hooks/useSimulation';
import LoadingPanel from '../../components/ui/LoadingPanel';
import MetricCards from '../../components/ui/MetricCards';
import AlertFeed from '../../components/logs/AlertFeed';
import dynamic from 'next/dynamic';
import { Wifi, WifiOff } from 'lucide-react';

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
  const { zones, alerts, volunteers, shelters, detections, acknowledgments, agentLogs } =
    useRealtimeData();
  const sim = useSimulation();

  // Compute sim summary stats
  const critCount = sim.zones.filter((z) => z.severity === 'critical').length;
  const highCount = sim.zones.filter((z) => z.severity === 'high').length;
  const totalEvac = sim.evacuations.reduce((s, e) => s + e.evacuated_count, 0);

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

      {/* Original metric cards */}
      <MetricCards
        zones={zones.zones}
        volunteers={volunteers.volunteers}
        shelters={shelters.shelters}
        alerts={alerts.alerts}
      />

      {/* Simulation quick stats */}
      {sim.zones.length > 0 && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="glass-panel p-4">
            <p className="text-[10px] uppercase tracking-wider text-surface-500 mb-1">Sim Zones</p>
            <p className="text-2xl font-black text-white">{sim.zones.length}</p>
          </div>
          <div className="glass-panel p-4">
            <p className="text-[10px] uppercase tracking-wider text-surface-500 mb-1">Critical</p>
            <p className="text-2xl font-black text-danger-400">{critCount}</p>
          </div>
          <div className="glass-panel p-4">
            <p className="text-[10px] uppercase tracking-wider text-surface-500 mb-1">High Risk</p>
            <p className="text-2xl font-black text-warning-400">{highCount}</p>
          </div>
          <div className="glass-panel p-4">
            <p className="text-[10px] uppercase tracking-wider text-surface-500 mb-1">Evacuated</p>
            <p className="text-2xl font-black text-safe-400">{totalEvac.toLocaleString()}</p>
          </div>
        </div>
      )}

      {/* Zone Criticality Cards */}
      {sim.zones.length > 0 && <ZoneCriticalityCards zones={sim.zones} />}

      {/* Row 1: Map + Alert Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2 glass-panel p-1 h-[480px]">
          <LiveMap
            zones={zones.zones}
            shelters={shelters.shelters}
            volunteerCount={volunteers.volunteers.length}
          />
        </div>
        <div className="glass-panel p-4 h-[480px]">
          <AlertFeed alerts={alerts.alerts} />
        </div>
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
            alerts={alerts.alerts}
            acknowledgments={acknowledgments.acks}
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
