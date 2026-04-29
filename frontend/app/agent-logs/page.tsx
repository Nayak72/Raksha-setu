/**
 * Agent Logs Page — filterable decision logs from all agents.
 */
'use client';

import AppShell, { useRealtimeData } from '../AppShell';
import LoadingPanel from '../../components/ui/LoadingPanel';
import dynamic from 'next/dynamic';

const AgentLogsPanel = dynamic(() => import('../../components/logs/AgentLogsPanel'), {
  ssr: false,
  loading: () => <LoadingPanel />,
});

function AgentLogsContent() {
  const { agentLogs, alerts, detections } = useRealtimeData();

  return (
    <div className="h-[calc(100vh-4rem)] animate-fade-in">
      <div className="glass-panel p-5 h-full">
        <AgentLogsPanel
          agentLogs={agentLogs.logs}
          alerts={alerts.alerts}
          detections={detections.detections}
        />
      </div>
    </div>
  );
}

export default function AgentLogsPage() {
  return (
    <AppShell>
      <AgentLogsContent />
    </AppShell>
  );
}
