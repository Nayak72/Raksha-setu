/**
 * Live Map Page — full-screen interactive Leaflet map with risk overlays.
 */
'use client';

import AppShell, { useRealtimeData } from '../AppShell';
import LoadingPanel from '../../components/ui/LoadingPanel';
import dynamic from 'next/dynamic';

const LiveMap = dynamic(() => import('../../components/map/LiveMap'), {
  ssr: false,
  loading: () => <LoadingPanel />,
});

function LiveMapContent() {
  const { zones, shelters, volunteers } = useRealtimeData();

  return (
    <div className="h-[calc(100vh-4rem)] animate-fade-in">
      <div className="glass-panel p-1 h-full">
        <LiveMap
          zones={zones.zones}
          shelters={shelters.shelters}
          volunteerCount={volunteers.volunteers.length}
        />
      </div>
    </div>
  );
}

export default function LiveMapPage() {
  return (
    <AppShell>
      <LiveMapContent />
    </AppShell>
  );
}
