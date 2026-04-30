/**
 * Live YOLO Feed Page — multi-camera grid with detection stats.
 */
'use client';

import AppShell, { useRealtimeData } from '../AppShell';
import { useSimulation } from '../../hooks/useSimulation';
import LoadingPanel from '../../components/ui/LoadingPanel';
import dynamic from 'next/dynamic';

const YoloFeed = dynamic(() => import('../../components/yolo/YoloFeed'), {
  ssr: false,
  loading: () => <LoadingPanel />,
});

function LiveYoloContent() {
  const { zones } = useRealtimeData();
  const sim = useSimulation();

  return (
    <div className="animate-fade-in">
      <YoloFeed zones={zones.zones} simZones={sim.zones} />
    </div>
  );
}

export default function LiveYoloPage() {
  return (
    <AppShell>
      <LiveYoloContent />
    </AppShell>
  );
}

