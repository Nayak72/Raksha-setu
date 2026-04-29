/**
 * Agent Logs Page — dual-tab view:
 *   Tab 1: Simulation agent decision logs (6 named agents, structured)
 *   Tab 2: Original Supabase LLM agent logs (preserved)
 */
'use client';

import { useState } from 'react';
import AppShell, { useRealtimeData } from '../AppShell';
import { useSimulation } from '../../hooks/useSimulation';
import LoadingPanel from '../../components/ui/LoadingPanel';
import dynamic from 'next/dynamic';
import { Brain, Cpu, Wifi, WifiOff } from 'lucide-react';

const AgentLogsPanel = dynamic(() => import('../../components/logs/AgentLogsPanel'), {
  ssr: false,
  loading: () => <LoadingPanel />,
});

const AgentLogsAdvanced = dynamic(
  () => import('../../components/simulation/AgentLogsAdvanced'),
  { ssr: false, loading: () => <LoadingPanel /> }
);

function AgentLogsContent() {
  const { agentLogs, detections } = useRealtimeData();
  const sim = useSimulation();
  const [activeTab, setActiveTab] = useState<'simulation' | 'supabase'>('simulation');

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-raksha-500/20 flex items-center justify-center">
            <Brain size={20} className="text-raksha-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">Agent Decision Logs</h1>
            <p className="text-xs text-surface-500">
              Structured reasoning, inputs, parameters & thresholds
            </p>
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

      {/* Tabs */}
      <div className="flex gap-2">
        <button
          onClick={() => setActiveTab('simulation')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200 ${
            activeTab === 'simulation'
              ? 'bg-raksha-500/20 text-raksha-400 border border-raksha-500/30'
              : 'text-surface-400 hover:bg-surface-800/60 hover:text-white'
          }`}
        >
          <Cpu size={14} />
          Simulation Agents
        </button>
        <button
          onClick={() => setActiveTab('supabase')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200 ${
            activeTab === 'supabase'
              ? 'bg-raksha-500/20 text-raksha-400 border border-raksha-500/30'
              : 'text-surface-400 hover:bg-surface-800/60 hover:text-white'
          }`}
        >
          <Brain size={14} />
          LLM Agent Logs
        </button>
      </div>

      {/* Content */}
      {activeTab === 'simulation' ? (
        <AgentLogsAdvanced logs={sim.logs} zones={sim.zones} />
      ) : (
        <div className="glass-panel p-5 h-[calc(100vh-14rem)]">
          <AgentLogsPanel
            agentLogs={agentLogs.logs}
            alerts={[]}
            detections={detections.detections}
          />
        </div>
      )}
    </div>
  );
}

export default function AgentLogsPage() {
  return (
    <AppShell>
      <AgentLogsContent />
    </AppShell>
  );
}
