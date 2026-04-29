/**
 * ZoneCriticalityCards — color-coded severity cards for each zone.
 */
'use client';

import { memo } from 'react';
import { SimZone } from '../../lib/simulation-api';
import { AlertTriangle, Flame, Shield, ShieldAlert } from 'lucide-react';

const SEVERITY_CONFIG = {
  critical: {
    bg: 'bg-danger-500/15',
    border: 'border-danger-500/40',
    text: 'text-danger-400',
    glow: 'shadow-danger-500/20',
    icon: Flame,
    label: 'CRITICAL',
    dot: 'bg-danger-500',
  },
  high: {
    bg: 'bg-warning-500/15',
    border: 'border-warning-500/40',
    text: 'text-warning-400',
    glow: 'shadow-warning-500/20',
    icon: AlertTriangle,
    label: 'HIGH',
    dot: 'bg-warning-500',
  },
  medium: {
    bg: 'bg-raksha-500/15',
    border: 'border-raksha-500/40',
    text: 'text-raksha-400',
    glow: 'shadow-raksha-500/20',
    icon: ShieldAlert,
    label: 'MEDIUM',
    dot: 'bg-raksha-500',
  },
  low: {
    bg: 'bg-safe-500/15',
    border: 'border-safe-500/40',
    text: 'text-safe-400',
    glow: 'shadow-safe-500/20',
    icon: Shield,
    label: 'LOW',
    dot: 'bg-safe-500',
  },
} as const;

function ZoneCriticalityCards({ zones }: { zones: SimZone[] }) {
  const sorted = [...zones].sort((a, b) => {
    const order = { critical: 0, high: 1, medium: 2, low: 3 };
    return order[a.severity] - order[b.severity];
  });

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
      {sorted.map((zone) => {
        const cfg = SEVERITY_CONFIG[zone.severity];
        const Icon = cfg.icon;

        return (
          <div
            key={zone.id}
            className={`relative overflow-hidden rounded-2xl border ${cfg.border} ${cfg.bg} p-4 transition-all duration-300 hover:shadow-lg ${cfg.glow}`}
          >
            {/* Severity badge */}
            <div className="flex items-center justify-between mb-3">
              <span className={`flex items-center gap-1.5 text-xs font-bold ${cfg.text}`}>
                <span className={`w-2 h-2 rounded-full ${cfg.dot} animate-pulse`} />
                {cfg.label}
              </span>
              <Icon size={16} className={cfg.text} />
            </div>

            {/* Zone Name */}
            <p className="text-[11px] text-surface-200 font-medium mb-1 truncate" title={zone.name}>
              {zone.name}
            </p>
            <div className="flex items-center gap-1.5 mb-2 text-xs">
              <span className="text-[10px] uppercase font-bold text-surface-400 bg-surface-800 px-1.5 py-0.5 rounded">
                {zone.disaster_type}
              </span>
              <span className="text-[10px] text-surface-500 font-mono truncate">
                ID: {zone.id.slice(0, 6)}
              </span>
            </div>

            {/* Metrics grid */}
            <div className="grid grid-cols-2 gap-2">
              <div>
                <p className="text-[9px] text-surface-500 uppercase tracking-wider">Affected</p>
                <p className="text-sm font-bold text-white">{zone.affected_population.toLocaleString()}</p>
              </div>
              <div>
                <p className="text-[9px] text-surface-500 uppercase tracking-wider">Damage</p>
                <p className={`text-sm font-bold ${cfg.text}`}>
                  {(zone.damage_level * 100).toFixed(0)}%
                </p>
              </div>
              <div>
                <p className="text-[9px] text-surface-500 uppercase tracking-wider">Alerts</p>
                <p className="text-sm font-bold text-white">{zone.alert_count}</p>
              </div>
              <div>
                <p className="text-[9px] text-surface-500 uppercase tracking-wider">Coords</p>
                <p className="text-[10px] font-mono text-surface-400">
                  {zone.lat.toFixed(2)}, {zone.lng.toFixed(2)}
                </p>
              </div>
            </div>

            {/* Damage bar */}
            <div className="mt-3">
              <div className="h-1.5 bg-surface-800 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    zone.severity === 'critical'
                      ? 'bg-danger-500'
                      : zone.severity === 'high'
                      ? 'bg-warning-500'
                      : zone.severity === 'medium'
                      ? 'bg-raksha-500'
                      : 'bg-safe-500'
                  }`}
                  style={{ width: `${zone.damage_level * 100}%` }}
                />
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default memo(ZoneCriticalityCards);
