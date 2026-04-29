/**
 * Agent Logs Panel — shows real-time agent decisions and reasoning.
 */
'use client';

import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Brain, Shield, CloudRain, Users, ChevronDown, ChevronUp, Search, Zap,
} from 'lucide-react';
import { Alert, Detection, AgentLog } from '../../lib/supabase';

type AgentLogEntry = {
  id: string;
  timestamp: Date;
  agent: 'detection' | 'weather' | 'dispatch' | 'system';
  action: string;
  reasoning: string;
  outcome: string;
  severity: 'info' | 'warning' | 'critical';
  data?: Record<string, unknown>;
};

const agentIcons = { detection: Shield, weather: CloudRain, dispatch: Users, system: Zap };
const agentColors = { detection: 'text-danger-400', weather: 'text-warning-400', dispatch: 'text-safe-400', system: 'text-raksha-400' };
const agentBgColors = { detection: 'bg-danger-500/10 border-danger-500/20', weather: 'bg-warning-500/10 border-warning-500/20', dispatch: 'bg-safe-500/10 border-safe-500/20', system: 'bg-raksha-500/10 border-raksha-500/20' };

interface AgentLogsPanelProps {
  agentLogs: AgentLog[];
  alerts: Alert[];
  detections: Detection[];
}

export default function AgentLogsPanel({ agentLogs }: AgentLogsPanelProps) {
  const [logs, setLogs] = useState<AgentLogEntry[]>([]);
  const [filter, setFilter] = useState<string>('all');
  const [search, setSearch] = useState('');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const formattedLogs: AgentLogEntry[] = agentLogs.map((log) => {
      let severity: 'info' | 'warning' | 'critical' = 'info';
      if (log.confidence < 70) severity = 'warning';
      if (log.confidence < 40 || (log.routing_decision && log.routing_decision.toLowerCase().includes('alert'))) severity = 'critical';

      let agentType: 'detection' | 'weather' | 'dispatch' | 'system' = 'system';
      const agentLower = (log.agent_name || '').toLowerCase();
      if (agentLower.includes('zone') || agentLower.includes('analyst') || agentLower.includes('triage')) agentType = 'detection';
      if (agentLower.includes('weather')) agentType = 'weather';
      if (agentLower.includes('dispatch') || agentLower.includes('allocator')) agentType = 'dispatch';

      let reasoningText = 'Reasoning processed.';
      if (Array.isArray(log.reasoning_steps)) {
        reasoningText = log.reasoning_steps.join('\\n');
      } else if (typeof log.reasoning_steps === 'string') {
        reasoningText = log.reasoning_steps;
      }

      return {
        id: log.id,
        timestamp: new Date(log.timestamp),
        agent: agentType,
        action: log.decision || `Agent invoked`,
        reasoning: reasoningText,
        outcome: log.routing_decision || 'Action complete.',
        severity,
        data: { tools: log.tools_used, confidence: log.confidence },
      };
    });
    setLogs(formattedLogs);
  }, [agentLogs]);

  const filteredLogs = logs.filter((log) => {
    if (filter !== 'all' && log.agent !== filter) return false;
    if (search && !log.action.toLowerCase().includes(search.toLowerCase()) &&
      !log.reasoning.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="flex flex-col h-full" id="agent-logs-panel">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Brain className="text-raksha-400" size={20} />
          <h2 className="text-lg font-bold text-white">Agent Decisions</h2>
          <span className="status-info">{logs.length} entries</span>
        </div>
      </div>

      <div className="flex gap-2 mb-3 flex-wrap">
        {['all', 'detection', 'weather', 'dispatch', 'system'].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 ${filter === f
              ? 'bg-raksha-500/20 text-raksha-400 border border-raksha-500/30'
              : 'bg-surface-800/40 text-surface-400 border border-surface-700/30 hover:text-white hover:border-surface-600'
            }`}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>

      <div className="relative mb-3">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-surface-500" />
        <input
          type="text"
          placeholder="Search logs..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="input-field pl-9 py-2 text-sm"
          id="agent-logs-search"
        />
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto space-y-2 pr-1">
        <AnimatePresence mode="popLayout">
          {filteredLogs.map((log) => {
            const Icon = agentIcons[log.agent];
            const isExpanded = expandedId === log.id;

            return (
              <motion.div
                key={log.id}
                layout
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className={`rounded-xl border p-3 cursor-pointer transition-all duration-200 ${agentBgColors[log.agent]}`}
                onClick={() => setExpandedId(isExpanded ? null : log.id)}
              >
                <div className="flex items-start gap-3">
                  <div className={`mt-0.5 p-1.5 rounded-lg ${agentBgColors[log.agent]}`}>
                    <Icon size={14} className={agentColors[log.agent]} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`text-xs font-bold uppercase tracking-wider ${agentColors[log.agent]}`}>
                        {log.agent}
                      </span>
                      <span className={`w-1.5 h-1.5 rounded-full ${log.severity === 'critical' ? 'bg-danger-500 animate-pulse' : log.severity === 'warning' ? 'bg-warning-500' : 'bg-surface-500'}`} />
                      <span className="text-[10px] text-surface-500 ml-auto font-mono">
                        {log.timestamp.toLocaleTimeString()}
                      </span>
                    </div>
                    <p className="text-sm text-white font-medium leading-snug">{log.action}</p>
                    <AnimatePresence>
                      {isExpanded && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          className="overflow-hidden"
                        >
                          <div className="mt-3 space-y-2">
                            <div className="bg-surface-900/40 rounded-lg p-2.5">
                              <div className="text-[10px] uppercase tracking-wider text-surface-500 mb-1 font-semibold">Reasoning</div>
                              <p className="text-xs text-surface-300 leading-relaxed font-mono">{log.reasoning}</p>
                            </div>
                            <div className="bg-surface-900/40 rounded-lg p-2.5">
                              <div className="text-[10px] uppercase tracking-wider text-surface-500 mb-1 font-semibold">Outcome</div>
                              <p className="text-xs text-surface-300 leading-relaxed">{log.outcome}</p>
                            </div>
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                  <button className="text-surface-500 hover:text-white transition-colors mt-1">
                    {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  </button>
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>

        {filteredLogs.length === 0 && (
          <div className="text-center py-12 text-surface-500">
            <Brain size={32} className="mx-auto mb-3 opacity-30" />
            <p className="text-sm">No agent logs yet</p>
            <p className="text-xs mt-1">Logs will appear as agents process events</p>
          </div>
        )}
      </div>
    </div>
  );
}
