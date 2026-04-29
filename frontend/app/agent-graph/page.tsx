/**
 * Agent Graph Page — node-based system visualization using ReactFlow.
 */
'use client';

import AppShell, { useRealtimeData } from '../AppShell';
import LoadingPanel from '../../components/ui/LoadingPanel';
import dynamic from 'next/dynamic';

const AgentGraph = dynamic(() => import('../../components/AgentGraph'), {
  ssr: false,
  loading: () => <LoadingPanel />,
});

function AgentGraphContent() {
  const { alerts, detections } = useRealtimeData();

  return (
    <div className="h-[calc(100vh-4rem)] animate-fade-in">
      <div className="glass-panel p-1 h-full">
        <AgentGraph alerts={alerts.alerts} detections={detections.detections} />
      </div>
    </div>
  );
}

export default function AgentGraphPage() {
  return (
    <AppShell>
      <AgentGraphContent />
    </AppShell>
  );
}
