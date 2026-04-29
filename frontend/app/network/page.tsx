/**
 * Network Monitor Page — system connectivity and network health dashboard.
 */
'use client';

import AppShell from '../AppShell';
import LoadingPanel from '../../components/ui/LoadingPanel';
import dynamic from 'next/dynamic';

const NetworkMonitorPanel = dynamic(() => import('../../components/NetworkMonitorPanel'), {
  ssr: false,
  loading: () => <LoadingPanel />,
});

function NetworkContent() {
  return (
    <div className="h-[calc(100vh-4rem)] animate-fade-in">
      <div className="glass-panel p-5 h-full">
        <NetworkMonitorPanel />
      </div>
    </div>
  );
}

export default function NetworkPage() {
  return (
    <AppShell>
      <NetworkContent />
    </AppShell>
  );
}
