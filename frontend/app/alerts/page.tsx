/**
 * Alerts Page — full-height real-time alert feed with 100 items.
 */
'use client';

import AppShell, { useRealtimeData } from '../AppShell';
import AlertFeed from '../../components/logs/AlertFeed';

function AlertsContent() {
  const { alerts } = useRealtimeData();

  return (
    <div className="h-[calc(100vh-4rem)] animate-fade-in">
      <div className="glass-panel p-5 h-full">
        <AlertFeed alerts={alerts.alerts} maxItems={100} />
      </div>
    </div>
  );
}

export default function AlertsPage() {
  return (
    <AppShell>
      <AlertsContent />
    </AppShell>
  );
}
