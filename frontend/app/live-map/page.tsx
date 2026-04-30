/**
 * Live Map Page — full-screen interactive Leaflet map with risk overlays.
 * Uses simulation data for consistent zone display across all pages.
 */
'use client';

import { useState, useEffect } from 'react';
import AppShell, { useRealtimeData } from '../AppShell';
import { useSimulation } from '../../hooks/useSimulation';
import { fetchSheltersNear, SimShelter } from '../../lib/simulation-api';
import LoadingPanel from '../../components/ui/LoadingPanel';
import dynamic from 'next/dynamic';

const LiveMap = dynamic(() => import('../../components/map/LiveMap'), {
  ssr: false,
  loading: () => <LoadingPanel />,
});

function LiveMapContent() {
  const { zones, shelters, volunteers } = useRealtimeData();
  const sim = useSimulation();

  // Fetch sim shelters for map connections
  const [simSheltersMap, setSimSheltersMap] = useState<Record<string, SimShelter[]>>({});

  useEffect(() => {
    if (sim.zones.length === 0) return;
    const fetchAllShelters = async () => {
      const map: Record<string, SimShelter[]> = {};
      for (const zone of sim.zones) {
        try {
          const res = await fetchSheltersNear(zone.id);
          map[zone.id] = res;
        } catch (e) {
          // ignore
        }
      }
      setSimSheltersMap(map);
    };
    fetchAllShelters();
  }, [sim.zones]);

  const allSimShelters = Object.values(simSheltersMap).flat();
  const simConnections = Object.entries(simSheltersMap).map(([zone_id, shelters]) => ({ zone_id, shelters }));

  const simTotalVolunteers = sim.zones.reduce((s, z, i) => {
    const activeMod = Math.round(Math.sin(i) * 2);
    return s + Math.max(0, activeMod) + Math.max(0, -activeMod);
  }, 0);
  const volunteerCount = volunteers.volunteers.length > 0 
    ? volunteers.volunteers.filter(v => v.status === 'deployed' || v.status === 'dispatched').length 
    : sim.zones.length > 0 ? simTotalVolunteers : 0;

  return (
    <div className="h-[calc(100vh-4rem)] animate-fade-in">
      <div className="glass-panel p-1 h-full">
        <LiveMap
          zones={zones.zones}
          shelters={shelters.shelters}
          volunteerCount={volunteerCount}
          simZones={sim.zones}
          simShelters={allSimShelters}
          simConnections={simConnections}
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
