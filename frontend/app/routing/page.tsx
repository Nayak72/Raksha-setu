/**
 * Routing Page — rescue route visualization with map + route selection.
 */
'use client';

import AppShell from '../AppShell';
import { useSimulation } from '../../hooks/useSimulation';
import dynamic from 'next/dynamic';
import LoadingPanel from '../../components/ui/LoadingPanel';
import { Route, Wifi, WifiOff } from 'lucide-react';

const RoutingPanel = dynamic(
  () => import('../../components/simulation/RoutingPanel'),
  { ssr: false, loading: () => <LoadingPanel /> }
);

function RoutingContent() {
  const sim = useSimulation();

  return (
    <div className="space-y-5 animate-fade-in">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-raksha-500/20 flex items-center justify-center">
            <Route size={20} className="text-raksha-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">Rescue Routing</h1>
            <p className="text-xs text-surface-500">Multiple routes to affected zones with shortest path</p>
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

      <RoutingPanel zones={sim.zones} />
    </div>
  );
}

export default function RoutingPage() {
  return (
    <AppShell>
      <RoutingContent />
    </AppShell>
  );
}
