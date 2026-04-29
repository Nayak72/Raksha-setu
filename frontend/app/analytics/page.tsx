/**
 * Analytics Page — multiple real-time charts: line, bar, stacked area.
 */
'use client';

import AppShell, { useRealtimeData } from '../AppShell';
import LoadingPanel from '../../components/ui/LoadingPanel';
import dynamic from 'next/dynamic';

const AnalyticsTab = dynamic(() => import('../../components/charts/AnalyticsTab'), {
  ssr: false,
  loading: () => <LoadingPanel />,
});

function AnalyticsContent() {
  const { zones, alerts, volunteers, shelters, detections } = useRealtimeData();

  return (
    <div className="animate-fade-in">
      <AnalyticsTab
        zones={zones.zones}
        alerts={alerts.alerts}
        volunteers={volunteers.volunteers}
        shelters={shelters.shelters}
        detections={detections.detections}
      />
    </div>
  );
}

export default function AnalyticsPage() {
  return (
    <AppShell>
      <AnalyticsContent />
    </AppShell>
  );
}
