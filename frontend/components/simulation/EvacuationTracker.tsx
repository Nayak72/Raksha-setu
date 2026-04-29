/**
 * EvacuationTracker — real-time evacuation progress per zone.
 */
'use client';

import { memo } from 'react';
import { SimZone, SimEvacuation } from '../../lib/simulation-api';
import { Users, TrendingUp } from 'lucide-react';

function EvacuationTracker({
  zones,
  evacuations,
}: {
  zones: SimZone[];
  evacuations: SimEvacuation[];
}) {
  const merged = zones.map((z) => {
    const evac = evacuations.find((e) => e.zone_id === z.id);
    const evacuated = evac?.evacuated_count || 0;
    const pct = z.population > 0 ? (evacuated / z.population) * 100 : 0;
    return { ...z, evacuated, pct };
  }).sort((a, b) => b.pct - a.pct);

  const totalPop = merged.reduce((s, z) => s + z.population, 0);
  const totalEvac = merged.reduce((s, z) => s + z.evacuated, 0);
  const overallPct = totalPop > 0 ? (totalEvac / totalPop) * 100 : 0;

  return (
    <div className="space-y-5">
      {/* Overall stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="glass-panel p-4 text-center">
          <p className="text-[10px] uppercase tracking-wider text-surface-500 mb-1">Total Population</p>
          <p className="text-2xl font-black text-white">{totalPop.toLocaleString()}</p>
        </div>
        <div className="glass-panel p-4 text-center">
          <p className="text-[10px] uppercase tracking-wider text-surface-500 mb-1">Total Evacuated</p>
          <p className="text-2xl font-black text-safe-400">{totalEvac.toLocaleString()}</p>
        </div>
        <div className="glass-panel p-4 text-center">
          <p className="text-[10px] uppercase tracking-wider text-surface-500 mb-1">Progress</p>
          <p className="text-2xl font-black text-raksha-400">{overallPct.toFixed(1)}%</p>
        </div>
      </div>

      {/* Per-zone breakdown */}
      <div className="space-y-3">
        {merged.map((zone) => {
          const severityColor =
            zone.severity === 'critical' ? 'text-danger-400' :
            zone.severity === 'high' ? 'text-warning-400' :
            zone.severity === 'medium' ? 'text-raksha-400' : 'text-safe-400';

          const barColor =
            zone.severity === 'critical' ? 'bg-danger-500' :
            zone.severity === 'high' ? 'bg-warning-500' :
            zone.severity === 'medium' ? 'bg-raksha-500' : 'bg-safe-500';

          return (
            <div
              key={zone.id}
              className="glass-panel p-4 transition-all duration-300 hover:border-surface-600"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Users size={14} className={severityColor} />
                  <span className="text-xs text-surface-200 font-medium truncate" title={zone.name}>
                    {zone.name}
                  </span>
                  <span className={`text-[10px] font-bold uppercase ${severityColor}`}>
                    {zone.severity}
                  </span>
                </div>
                <div className="flex items-center gap-1.5">
                  <TrendingUp size={12} className="text-safe-400" />
                  <span className="text-sm font-bold text-white">
                    {zone.evacuated.toLocaleString()} / {zone.population.toLocaleString()}
                  </span>
                </div>
              </div>

              {/* Progress bar */}
              <div className="h-2 bg-surface-800 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-700 ease-out ${barColor}`}
                  style={{ width: `${Math.min(100, zone.pct)}%` }}
                />
              </div>
              <p className="text-right text-[10px] text-surface-500 mt-1">
                {zone.pct.toFixed(1)}% evacuated
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default memo(EvacuationTracker);
