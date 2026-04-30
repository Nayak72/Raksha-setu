/**
 * Evacuation Page — real-time evacuation tracking per zone.
 */
'use client';

import AppShell from '../AppShell';
import { useSimulation } from '../../hooks/useSimulation';
import dynamic from 'next/dynamic';
import LoadingPanel from '../../components/ui/LoadingPanel';
import { Users, Wifi, WifiOff } from 'lucide-react';

const EvacuationTracker = dynamic(
  () => import('../../components/simulation/EvacuationTracker'),
  { ssr: false, loading: () => <LoadingPanel /> }
);

function EvacuationContent() {
  const sim = useSimulation();

  return (
    <div className="space-y-5 animate-fade-in">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-safe-500/20 flex items-center justify-center">
            <Users size={20} className="text-safe-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">Evacuation Tracking</h1>
            <p className="text-xs text-surface-500">Live evacuation progress per zone</p>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          {sim.connected ? (
            <Wifi size={14} className="text-safe-400" />
          ) : (
            <WifiOff size={14} className="text-danger-400" />
          )}
          <span className="text-[10px] text-surface-500">
            {sim.connected ? 'Live' : 'Polling'}
          </span>
        </div>
      </div>

      <EvacuationTracker zones={sim.zones} evacuations={sim.evacuations} />
    </div>
  );
}

export default function EvacuationPage() {
  return (
    <AppShell>
      <EvacuationContent />
    </AppShell>
  );
}
