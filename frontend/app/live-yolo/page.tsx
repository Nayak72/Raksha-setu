/**
 * Live YOLO Feed Page — multi-camera grid with detection stats.
 */
'use client';

import AppShell, { useRealtimeData } from '../AppShell';
import LoadingPanel from '../../components/ui/LoadingPanel';
import dynamic from 'next/dynamic';

const YoloFeed = dynamic(() => import('../../components/yolo/YoloFeed'), {
  ssr: false,
  loading: () => <LoadingPanel />,
});

function LiveYoloContent() {
  const { zones, detections } = useRealtimeData();

  return (
    <div className="animate-fade-in">
      <YoloFeed zones={zones.zones} detections={detections.detections} />
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
