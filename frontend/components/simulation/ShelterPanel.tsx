/**
 * ShelterPanel — shows shelters near a selected zone with distance + capacity.
 */
'use client';

import { useState, useEffect, memo } from 'react';
import { SimZone, SimShelter, fetchSheltersNear } from '../../lib/simulation-api';
import { Home, MapPin, Users, ChevronRight } from 'lucide-react';

function ShelterPanel({ zones }: { zones: SimZone[] }) {
  const [selectedZone, setSelectedZone] = useState<string>('');
  const [shelters, setShelters] = useState<SimShelter[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!selectedZone) {
      setShelters([]);
      return;
    }
    setLoading(true);
    fetchSheltersNear(selectedZone)
      .then(setShelters)
      .catch(() => setShelters([]))
      .finally(() => setLoading(false));
  }, [selectedZone]);

  // Auto-select first zone
  useEffect(() => {
    if (zones.length > 0 && !selectedZone) {
      setSelectedZone(zones[0].id);
    }
  }, [zones, selectedZone]);

  return (
    <div className="space-y-5">
      {/* Zone selector */}
      <div className="flex items-center gap-3">
        <MapPin size={16} className="text-raksha-400" />
        <select
          value={selectedZone}
          onChange={(e) => setSelectedZone(e.target.value)}
          className="input-field text-sm flex-1"
        >
          <option value="">Select a zone...</option>
          {zones.map((z) => (
            <option key={z.id} value={z.id}>
              Zone {z.id.slice(0, 8)} — {z.severity.toUpperCase()} (Damage: {(z.damage_level * 100).toFixed(0)}%)
            </option>
          ))}
        </select>
      </div>

      {/* Shelter cards */}
      {loading && (
        <div className="text-center py-12 text-surface-500 text-sm animate-pulse">
          Loading shelters...
        </div>
      )}

      {!loading && shelters.length === 0 && selectedZone && (
        <div className="text-center py-12 text-surface-500 text-sm">
          No shelters found near this zone.
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {shelters.map((s, idx) => {
          const capacityPct = s.capacity > 0 ? (s.available_capacity / s.capacity) * 100 : 0;
          const capacityColor =
            capacityPct > 50 ? 'text-safe-400' : capacityPct > 20 ? 'text-warning-400' : 'text-danger-400';
          const barColor =
            capacityPct > 50 ? 'bg-safe-500' : capacityPct > 20 ? 'bg-warning-500' : 'bg-danger-500';

          return (
            <div
              key={s.shelter_id}
              className="glass-panel p-4 transition-all duration-300 hover:border-raksha-500/30 hover:shadow-lg hover:shadow-raksha-500/5"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-raksha-500/20 flex items-center justify-center">
                    <Home size={16} className="text-raksha-400" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-white">{s.name}</p>
                    <p className="text-[10px] text-surface-500 font-mono">{s.shelter_id.slice(0, 8)}</p>
                  </div>
                </div>
                {idx === 0 && (
                  <span className="text-[9px] font-bold uppercase bg-safe-500/20 text-safe-400 px-2 py-0.5 rounded-full border border-safe-500/30">
                    Nearest
                  </span>
                )}
              </div>

              <div className="grid grid-cols-2 gap-3 mb-3">
                <div>
                  <p className="text-[9px] uppercase tracking-wider text-surface-500">Distance</p>
                  <p className="text-sm font-bold text-white">{s.distance.toFixed(1)} km</p>
                </div>
                <div>
                  <p className="text-[9px] uppercase tracking-wider text-surface-500">Available</p>
                  <p className={`text-sm font-bold ${capacityColor}`}>
                    {s.available_capacity} / {s.capacity}
                  </p>
                </div>
              </div>

              {/* Capacity bar */}
              <div className="h-1.5 bg-surface-800 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${barColor}`}
                  style={{ width: `${capacityPct}%` }}
                />
              </div>
              <p className="text-right text-[10px] text-surface-500 mt-1">
                {capacityPct.toFixed(0)}% available
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default memo(ShelterPanel);
