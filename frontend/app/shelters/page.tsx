/**
 * Shelters Page — nearby shelters for each affected zone.
 */
'use client';

import AppShell from '../AppShell';
import { useSimulation } from '../../hooks/useSimulation';
import dynamic from 'next/dynamic';
import LoadingPanel from '../../components/ui/LoadingPanel';
import { Home, Wifi, WifiOff } from 'lucide-react';

const ShelterPanel = dynamic(
  () => import('../../components/simulation/ShelterPanel'),
  { ssr: false, loading: () => <LoadingPanel /> }
);

function SheltersContent() {
  const sim = useSimulation();

  return (
    <div className="space-y-5 animate-fade-in">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-raksha-500/20 flex items-center justify-center">
            <Home size={20} className="text-raksha-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">Nearby Shelters</h1>
            <p className="text-xs text-surface-500">Distance & capacity for affected zones</p>
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

      <ShelterPanel zones={sim.zones} />
    </div>
  );
}

export default function SheltersPage() {
  return (
    <AppShell>
      <SheltersContent />
    </AppShell>
  );
}
