/**
 * AgentLogsAdvanced — structured, filterable agent decision logs.
 */
'use client';

import { useState, memo, useMemo } from 'react';
import { SimLog, SimZone } from '../../lib/simulation-api';
import { Brain, ChevronDown, ChevronUp, Filter, Search } from 'lucide-react';

function AgentLogsAdvanced({
  logs,
  zones,
}: {
  logs: SimLog[];
  zones: SimZone[];
}) {
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);
  const [zoneFilter, setZoneFilter] = useState<string>('');
  const [severityFilter, setSeverityFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');

  const filtered = useMemo(() => {
    return logs.filter((log) => {
      if (zoneFilter && log.zone_id !== zoneFilter) return false;
      if (severityFilter) {
        const zone = zones.find((z) => z.id === log.zone_id);
        if (zone && zone.severity !== severityFilter) return false;
      }
      if (searchQuery && !log.reasoning.toLowerCase().includes(searchQuery.toLowerCase())) return false;
      return true;
    });
  }, [logs, zoneFilter, severityFilter, searchQuery, zones]);

  const uniqueZoneIds = [...new Set(logs.map((l) => l.zone_id))];

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-surface-500" />
          <input
            type="text"
            placeholder="Search reasoning..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="input-field pl-9 text-sm"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter size={14} className="text-surface-500" />
          <select
            value={zoneFilter}
            onChange={(e) => setZoneFilter(e.target.value)}
            className="input-field text-sm w-40"
          >
            <option value="">All Zones</option>
            {uniqueZoneIds.map((id) => (
              <option key={id} value={id}>
                {id.slice(0, 8)}...
              </option>
            ))}
          </select>
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="input-field text-sm w-32"
          >
            <option value="">All Severity</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>
      </div>

      <p className="text-xs text-surface-500">{filtered.length} log entries</p>

      {/* Log entries */}
      <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
        {filtered.map((log, idx) => {
          const isExpanded = expandedIdx === idx;
          const urgencyColor =
            log.decision.evacuation_urgency === 'HIGH'
              ? 'text-danger-400'
              : log.decision.evacuation_urgency === 'MEDIUM'
              ? 'text-warning-400'
              : 'text-safe-400';

          return (
            <div
              key={`${log.zone_id}-${log.timestamp}-${idx}`}
              className="glass-panel overflow-hidden transition-all duration-300"
            >
              {/* Header row */}
              <button
                onClick={() => setExpandedIdx(isExpanded ? null : idx)}
                className="w-full flex items-center justify-between px-4 py-3 hover:bg-surface-800/40 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <Brain size={14} className="text-raksha-400" />
                  <span className="text-[10px] font-mono text-surface-500">
                    {new Date(log.timestamp).toLocaleTimeString()}
                  </span>
                  <span className="text-xs font-mono text-surface-400">
                    Zone: {log.zone_id.slice(0, 8)}
                  </span>
                  <span className={`text-[10px] font-bold uppercase ${urgencyColor}`}>
                    {log.decision.evacuation_urgency}
                  </span>
                </div>
                {isExpanded ? (
                  <ChevronUp size={14} className="text-surface-500" />
                ) : (
                  <ChevronDown size={14} className="text-surface-500" />
                )}
              </button>

              {/* Expanded detail */}
              {isExpanded && (
                <div className="px-4 pb-4 space-y-3 border-t border-surface-700/50 pt-3 animate-slide-down">
                  {/* Reasoning */}
                  <div>
                    <p className="text-[9px] uppercase tracking-wider text-surface-500 mb-1">Reasoning</p>
                    <p className="text-sm text-surface-200 leading-relaxed bg-surface-800/60 rounded-lg p-3">
                      {log.reasoning}
                    </p>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    {/* Inputs */}
                    <div>
                      <p className="text-[9px] uppercase tracking-wider text-surface-500 mb-1">Inputs</p>
                      <div className="bg-surface-800/60 rounded-lg p-3 space-y-1">
                        {Object.entries(log.inputs).map(([k, v]) => (
                          <div key={k} className="flex justify-between text-xs">
                            <span className="text-surface-400">{k}</span>
                            <span className="text-white font-mono">{typeof v === 'number' ? v.toFixed(2) : v}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Parameters */}
                    <div>
                      <p className="text-[9px] uppercase tracking-wider text-surface-500 mb-1">Parameters</p>
                      <div className="bg-surface-800/60 rounded-lg p-3 space-y-1">
                        {Object.entries(log.parameters).map(([k, v]) => (
                          <div key={k} className="flex justify-between text-xs">
                            <span className="text-surface-400">{k}</span>
                            <span className="text-white font-mono">{v}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Decision */}
                    <div>
                      <p className="text-[9px] uppercase tracking-wider text-surface-500 mb-1">Decision</p>
                      <div className="bg-surface-800/60 rounded-lg p-3 space-y-1">
                        {Object.entries(log.decision).map(([k, v]) => (
                          <div key={k} className="flex justify-between text-xs">
                            <span className="text-surface-400">{k.replace(/_/g, ' ')}</span>
                            <span className={`font-bold ${
                              v === 'HIGH' || v === 'critical' ? 'text-danger-400' :
                              v === 'MEDIUM' || v === 'high' ? 'text-warning-400' :
                              'text-safe-400'
                            }`}>
                              {v}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Thresholds */}
                  <div>
                    <p className="text-[9px] uppercase tracking-wider text-surface-500 mb-1">Thresholds</p>
                    <div className="flex gap-4">
                      {Object.entries(log.thresholds).map(([k, v]) => (
                        <span key={k} className="text-xs text-surface-400">
                          {k}: <span className="text-white font-mono">{v}</span>
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}

        {filtered.length === 0 && (
          <div className="text-center py-12 text-surface-500 text-sm">
            No agent logs match the current filters.
          </div>
        )}
      </div>
    </div>
  );
}

export default memo(AgentLogsAdvanced);
