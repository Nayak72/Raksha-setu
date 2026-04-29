/**
 * Broadcast Page — broadcast status + metrics with device reach tracking.
 */
'use client';

import AppShell, { useRealtimeData } from '../AppShell';
import LoadingPanel from '../../components/ui/LoadingPanel';
import dynamic from 'next/dynamic';

const BroadcastStatus = dynamic(() => import('../../components/BroadcastStatus'), {
  ssr: false,
  loading: () => <LoadingPanel />,
});

function BroadcastContent() {
  const { alerts, acknowledgments } = useRealtimeData();

  return (
    <div className="h-[calc(100vh-4rem)] animate-fade-in">
      <div className="glass-panel p-5 h-full">
        <BroadcastStatus
          alerts={alerts.alerts}
          acknowledgments={acknowledgments.acks}
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
