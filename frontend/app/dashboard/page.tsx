/**
 * Dashboard Page — overview cards + world map + alert feed + agent logs + broadcast.
 * Mirrors the original Vite dashboard layout exactly.
 */
'use client';

import AppShell, { useRealtimeData } from '../AppShell';
import LoadingPanel from '../../components/ui/LoadingPanel';
import MetricCards from '../../components/ui/MetricCards';
import AlertFeed from '../../components/logs/AlertFeed';
import dynamic from 'next/dynamic';

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

function DashboardContent() {
  const { zones, alerts, volunteers, shelters, detections, acknowledgments, agentLogs } =
    useRealtimeData();

  return (
    <div className="space-y-5 animate-fade-in" id="dashboard-page">
      <MetricCards
        zones={zones.zones}
        volunteers={volunteers.volunteers}
        shelters={shelters.shelters}
        alerts={alerts.alerts}
      />

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
