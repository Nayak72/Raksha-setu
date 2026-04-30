/**
 * Allocation Page — per-shelter resource allocation view.
 */
'use client';

import AppShell, { useRealtimeData } from '../AppShell';
import { useSimulation } from '../../hooks/useSimulation';
import dynamic from 'next/dynamic';
import LoadingPanel from '../../components/ui/LoadingPanel';
import { Package, Wifi, WifiOff } from 'lucide-react';
import { useState, useEffect } from 'react';
import { fetchSheltersNear, SimShelter } from '../../lib/simulation-api';

const ResourceAllocationTable = dynamic(
  () => import('../../components/simulation/ResourceAllocationTable'),
  { ssr: false, loading: () => <LoadingPanel /> }
);

function AllocationContent() {
  const sim = useSimulation();
  const { shelters } = useRealtimeData();

  const [simSheltersMap, setSimSheltersMap] = useState<Record<string, SimShelter[]>>({});
  
  useEffect(() => {
    if (!sim?.zones || sim.zones.length === 0) return;
    const fetchAllShelters = async () => {
      const map: Record<string, SimShelter[]> = {};
      for (const zone of sim.zones) {
        try {
          const res = await fetchSheltersNear(zone.id);
          map[zone.id] = res;
        } catch (e) {}
      }
      setSimSheltersMap(map);
    };
    fetchAllShelters();
  }, [sim?.zones]);

  const allSimShelters = Object.values(simSheltersMap).flat();
  const uniqueSimShelters = Array.from(new Map(allSimShelters.map(s => [s.shelter_id, s])).values());

  return (
    <div className="space-y-5 animate-fade-in">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-warning-500/20 flex items-center justify-center">
            <Package size={20} className="text-warning-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">Resource Allocation</h1>
            <p className="text-xs text-surface-500">Per-shelter food, beds, medical kits & rescue teams</p>
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

      <ResourceAllocationTable 
        allocations={sim.allocations} 
        shelters={shelters.shelters} 
        simShelters={uniqueSimShelters} 
      />
    </div>
  );
}

export default function AllocationPage() {
  return (
    <AppShell>
      <AllocationContent />
    </AppShell>
  );
}
