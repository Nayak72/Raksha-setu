/**
 * AgentLogsAdvanced — structured, filterable agent decision logs.
 * Grouped by agent_name with expandable rows showing all fields.
 */
'use client';

import { useState, memo, useMemo } from 'react';
import { SimLog, SimZone } from '../../lib/simulation-api';
import {
  Brain, ChevronDown, ChevronUp, Filter, Search,
  Shield, Cloud, BarChart3, Package, Eye, RefreshCw,
} from 'lucide-react';

const AGENT_CONFIG: Record<string, { icon: React.ElementType; color: string }> = {
  'Triage Agent':             { icon: Shield,     color: 'text-danger-400' },
  'Weather Agent':            { icon: Cloud,      color: 'text-raksha-400' },
  'Zone Analyst Agent':       { icon: BarChart3,  color: 'text-warning-400' },
  'Resource Allocator Agent': { icon: Package,    color: 'text-safe-400' },
  'Supervisor Agent':         { icon: Eye,        color: 'text-raksha-300' },
  'Feedback Agent':           { icon: RefreshCw,  color: 'text-warning-300' },
};

function AgentLogsAdvanced({
  logs,
  zones,
}: {
  logs: SimLog[];
  zones: SimZone[];
}) {
  const [expandedKey, setExpandedKey] = useState<string | null>(null);
  const [agentFilter, setAgentFilter] = useState<string>('');
  const [zoneFilter, setZoneFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');

  const filtered = useMemo(() => {
    return logs.filter((log) => {
      if (agentFilter && log.agent_name !== agentFilter) return false;
      if (zoneFilter && log.zone_id !== zoneFilter) return false;
      if (searchQuery && !log.reasoning.toLowerCase().includes(searchQuery.toLowerCase())) return false;
      return true;
    });
  }, [logs, agentFilter, zoneFilter, searchQuery]);

  const uniqueZoneIds = [...new Set(logs.map((l) => l.zone_id))];
  const uniqueAgents = [...new Set(logs.map((l) => l.agent_name))];

  // Group by agent
  const grouped = useMemo(() => {
    const map: Record<string, SimLog[]> = {};
    for (const log of filtered) {
      if (!map[log.agent_name]) map[log.agent_name] = [];
      map[log.agent_name].push(log);
    }
    return map;
  }, [filtered]);

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
            value={agentFilter}
            onChange={(e) => setAgentFilter(e.target.value)}
            className="input-field text-sm w-48"
          >
            <option value="">All Agents</option>
            {uniqueAgents.map((name) => (
              <option key={name} value={name}>{name}</option>
            ))}
          </select>
          <select
            value={zoneFilter}
            onChange={(e) => setZoneFilter(e.target.value)}
            className="input-field text-sm w-56"
          >
            <option value="">All Zones</option>
            {uniqueZoneIds.map((id) => {
              const zone = zones.find(z => z.id === id);
              return (
                <option key={id} value={id}>{zone ? zone.name : id.slice(0, 8)}</option>
              );
            })}
          </select>
        </div>
      </div>

      <p className="text-xs text-surface-500">{filtered.length} log entries</p>

      {/* Grouped log entries */}
      <div className="space-y-5 max-h-[600px] overflow-y-auto pr-1">
        {Object.entries(grouped).map(([agentName, agentLogs]) => {
          const cfg = AGENT_CONFIG[agentName] || { icon: Brain, color: 'text-surface-400' };
          const AgentIcon = cfg.icon;

          return (
            <div key={agentName}>
              {/* Agent group header */}
              <div className="flex items-center gap-2 mb-2">
                <AgentIcon size={16} className={cfg.color} />
                <span className={`text-sm font-bold ${cfg.color}`}>{agentName}</span>
                <span className="text-[10px] text-surface-600 bg-surface-800/60 px-2 py-0.5 rounded-full">
                  {agentLogs.length}
                </span>
              </div>

              <div className="space-y-2">
                {agentLogs.map((log, idx) => {
                  const key = `${agentName}-${log.zone_id}-${log.timestamp}-${idx}`;
                  const isExpanded = expandedKey === key;

                  return (
                    <div
                      key={key}
                      className="glass-panel overflow-hidden transition-all duration-300"
                    >
                      {/* Collapsed header */}
                      <button
                        onClick={() => setExpandedKey(isExpanded ? null : key)}
                        className="w-full flex items-center justify-between px-4 py-3 hover:bg-surface-800/40 transition-colors text-left"
                      >
                        <div className="flex items-center gap-3 min-w-0">
                          <span className="text-[10px] font-mono text-surface-500 flex-shrink-0">
                            {new Date(log.timestamp).toLocaleTimeString()}
                          </span>
                          <span className="text-xs text-surface-400 flex-shrink-0 truncate max-w-[180px]" title={zones.find(z => z.id === log.zone_id)?.name || log.zone_id}>
                            {zones.find(z => z.id === log.zone_id)?.name || `Zone ${log.zone_id.slice(0, 8)}`}
                          </span>
                          <span className="text-xs text-surface-300 truncate">
                            {log.decision}
                          </span>
                        </div>
                        {isExpanded ? (
                          <ChevronUp size={14} className="text-surface-500 flex-shrink-0" />
                        ) : (
                          <ChevronDown size={14} className="text-surface-500 flex-shrink-0" />
                        )}
                      </button>

                      {/* Expanded detail */}
                      {isExpanded && (
                        <div className="px-4 pb-4 space-y-3 border-t border-surface-700/50 pt-3 animate-slide-down">
                          {/* Decision + Outcome */}
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            <div>
                              <p className="text-[9px] uppercase tracking-wider text-surface-500 mb-1">Decision</p>
                              <p className="text-sm font-semibold text-white bg-surface-800/60 rounded-lg p-3">
                                {log.decision}
                              </p>
                            </div>
                            <div>
                              <p className="text-[9px] uppercase tracking-wider text-surface-500 mb-1">Outcome</p>
                              <p className="text-sm text-surface-200 bg-surface-800/60 rounded-lg p-3">
                                {log.outcome}
                              </p>
                            </div>
                          </div>

                          {/* Reasoning */}
                          <div>
                            <p className="text-[9px] uppercase tracking-wider text-surface-500 mb-1">Reasoning</p>
                            <p className="text-sm text-surface-200 leading-relaxed bg-surface-800/60 rounded-lg p-3">
                              {log.reasoning}
                            </p>
                          </div>

                          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            {/* Input Data */}
                            <div>
                              <p className="text-[9px] uppercase tracking-wider text-surface-500 mb-1">Input Data</p>
                              <div className="bg-surface-800/60 rounded-lg p-3 space-y-1">
                                {Object.entries(log.input_data).map(([k, v]) => (
                                  <div key={k} className="flex justify-between text-xs">
                                    <span className="text-surface-400">{k.replace(/_/g, ' ')}</span>
                                    <span className="text-white font-mono">
                                      {typeof v === 'number' ? (Number.isInteger(v) ? v : v.toFixed(3)) : String(v)}
                                    </span>
                                  </div>
                                ))}
                              </div>
                            </div>

                            {/* Parameters Used */}
                            <div>
                              <p className="text-[9px] uppercase tracking-wider text-surface-500 mb-1">Parameters</p>
                              <div className="bg-surface-800/60 rounded-lg p-3 space-y-1">
                                {Object.entries(log.parameters_used).map(([k, v]) => (
                                  <div key={k} className="flex justify-between text-xs">
                                    <span className="text-surface-400">{k.replace(/_/g, ' ')}</span>
                                    <span className="text-white font-mono">{String(v)}</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          </div>

                          {/* Thresholds Checked */}
                          {Array.isArray(log.thresholds_checked) && log.thresholds_checked.length > 0 && (
                            <div>
                              <p className="text-[9px] uppercase tracking-wider text-surface-500 mb-1">Thresholds Checked</p>
                              <div className="bg-surface-800/60 rounded-lg p-3">
                                <div className="grid grid-cols-4 gap-2 text-[10px] uppercase tracking-wider text-surface-500 pb-1 border-b border-surface-700/40 mb-1">
                                  <span>Parameter</span>
                                  <span className="text-right">Value</span>
                                  <span className="text-right">Threshold</span>
                                  <span className="text-right">Status</span>
                                </div>
                                {log.thresholds_checked.map((t, i) => (
                                  <div key={i} className="grid grid-cols-4 gap-2 text-xs py-1">
                                    <span className="text-surface-400">{t.parameter.replace(/_/g, ' ')}</span>
                                    <span className="text-right text-white font-mono">
                                      {typeof t.value === 'number' ? (Number.isInteger(t.value) ? t.value : t.value.toFixed(3)) : t.value}
                                    </span>
                                    <span className="text-right text-surface-300 font-mono">{t.threshold}</span>
                                    <span className={`text-right font-bold ${t.exceeded ? 'text-danger-400' : 'text-safe-400'}`}>
                                      {t.exceeded ? 'EXCEEDED' : 'OK'}
                                    </span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
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
