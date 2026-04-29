/**
 * Network Monitor Panel — shows system connectivity status for UDP, Supabase, and PG Listener.
 * Replaces the old connectivity panel.
 */
'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Wifi, WifiOff, Radio, Circle, Activity, Server, Database, Zap, RefreshCw } from 'lucide-react';
import { fetchSystemStatus } from '../lib/api';

type NetworkLog = {
  type: 'udp' | 'supabase' | 'system' | 'alert';
  message: string;
  timestamp: Date;
  status: 'success' | 'error' | 'info';
};

export default function NetworkMonitorPanel() {
  const [systemStatus, setSystemStatus] = useState<Record<string, unknown> | null>(null);
  const [logs, setLogs] = useState<NetworkLog[]>([]);
  const [isPolling, setIsPolling] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  const addLog = useCallback((log: Omit<NetworkLog, 'timestamp'>) => {
    setLogs((prev) => [{ ...log, timestamp: new Date() }, ...prev].slice(0, 100));
  }, []);

  const refreshStatus = useCallback(async () => {
    try {
      const data = await fetchSystemStatus();
      setSystemStatus(data);
      setLastRefresh(new Date());
      addLog({ type: 'system', message: `Status OK — ${data.active_zones || 0} zones, ${data.pending_alerts || 0} pending alerts`, status: 'success' });
    } catch (err) {
      addLog({ type: 'system', message: `Backend unreachable: ${err instanceof Error ? err.message : 'unknown'}`, status: 'error' });
      setSystemStatus(null);
    }
  }, [addLog]);

  useEffect(() => {
    refreshStatus();
    if (!isPolling) return;
    const interval = setInterval(refreshStatus, 5000);
    return () => clearInterval(interval);
  }, [refreshStatus, isPolling]);

  const getLogColor = (log: NetworkLog): string => {
    if (log.status === 'error') return 'text-danger-400';
    if (log.status === 'success') return 'text-safe-400';
    return 'text-surface-300';
  };

  const getLogIcon = (log: NetworkLog) => {
    if (log.type === 'udp') return <Radio size={10} />;
    if (log.type === 'supabase') return <Database size={10} />;
    if (log.type === 'alert') return <Zap size={10} />;
    return <Server size={10} />;
  };

  const isOnline = systemStatus !== null;

  return (
    <div className="flex flex-col h-full" id="network-monitor-panel">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          {isOnline ? <Wifi className="text-safe-400" size={20} /> : <WifiOff className="text-surface-500" size={20} />}
          <h2 className="text-lg font-bold text-white">Network Monitor</h2>
          <span className={isOnline ? 'status-safe' : 'status-critical'}>
            <Circle size={6} fill="currentColor" />
            {isOnline ? 'Online' : 'Offline'}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsPolling((p) => !p)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${isPolling ? 'bg-safe-500/10 text-safe-400 border border-safe-500/20' : 'bg-surface-800/40 text-surface-400 border border-surface-700/30'}`}
          >
            {isPolling ? 'Auto-Refresh ON' : 'Auto-Refresh OFF'}
          </button>
          <button onClick={refreshStatus} className="p-1.5 rounded-lg hover:bg-surface-800/40 text-surface-400 hover:text-white transition-colors">
            <RefreshCw size={14} />
          </button>
        </div>
      </div>

      {/* Status Cards */}
      <div className="grid grid-cols-3 gap-2 mb-4">
        <div className={`rounded-xl p-3 text-center border ${isOnline ? 'bg-safe-500/10 border-safe-500/20' : 'bg-danger-500/10 border-danger-500/20'}`}>
          <Radio size={16} className={`mx-auto mb-1 ${isOnline ? 'text-safe-400' : 'text-danger-400'}`} />
          <div className="text-xs font-bold text-white">UDP</div>
          <div className="text-[10px] text-surface-400">{isOnline ? 'Broadcasting' : 'Down'}</div>
        </div>
        <div className={`rounded-xl p-3 text-center border ${isOnline ? 'bg-safe-500/10 border-safe-500/20' : 'bg-danger-500/10 border-danger-500/20'}`}>
          <Database size={16} className={`mx-auto mb-1 ${isOnline ? 'text-safe-400' : 'text-danger-400'}`} />
          <div className="text-xs font-bold text-white">Supabase</div>
          <div className="text-[10px] text-surface-400">{isOnline ? 'Connected' : 'Down'}</div>
        </div>
        <div className={`rounded-xl p-3 text-center border ${isOnline ? 'bg-safe-500/10 border-safe-500/20' : 'bg-danger-500/10 border-danger-500/20'}`}>
          <Activity size={16} className={`mx-auto mb-1 ${isOnline ? 'text-safe-400 animate-pulse' : 'text-danger-400'}`} />
          <div className="text-xs font-bold text-white">PG Listener</div>
          <div className="text-[10px] text-surface-400">{isOnline ? 'Active' : 'Down'}</div>
        </div>
      </div>

      {/* System Stats */}
      {systemStatus && (
        <div className="grid grid-cols-2 gap-2 mb-4">
          <div className="rounded-lg bg-surface-800/30 border border-surface-700/20 p-2.5">
            <div className="text-[10px] text-surface-500 uppercase tracking-wider">Active Zones</div>
            <div className="text-lg font-bold text-white">{(systemStatus as any).active_zones ?? 0}</div>
          </div>
          <div className="rounded-lg bg-surface-800/30 border border-surface-700/20 p-2.5">
            <div className="text-[10px] text-surface-500 uppercase tracking-wider">Pending Alerts</div>
            <div className="text-lg font-bold text-danger-400">{(systemStatus as any).pending_alerts ?? 0}</div>
          </div>
          <div className="rounded-lg bg-surface-800/30 border border-surface-700/20 p-2.5">
            <div className="text-[10px] text-surface-500 uppercase tracking-wider">Volunteers</div>
            <div className="text-lg font-bold text-white">{(systemStatus as any).available_volunteers ?? 0} / {(systemStatus as any).total_volunteers ?? 0}</div>
          </div>
          <div className="rounded-lg bg-surface-800/30 border border-surface-700/20 p-2.5">
            <div className="text-[10px] text-surface-500 uppercase tracking-wider">Uptime</div>
            <div className="text-lg font-bold text-white">{Math.floor(((systemStatus as any).uptime_seconds ?? 0) / 60)}m</div>
          </div>
        </div>
      )}

      {/* Activity Log */}
      <div className="text-xs font-semibold text-surface-400 uppercase tracking-wider mb-2">Activity Log</div>
      <div className="flex-1 overflow-y-auto space-y-1 pr-1">
        <AnimatePresence mode="popLayout">
          {logs.map((log, idx) => (
            <motion.div
              key={`${log.timestamp.getTime()}-${idx}`}
              layout
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="flex items-center gap-2 p-2 rounded-lg bg-surface-800/30 border border-surface-700/20"
            >
              <span className={getLogColor(log)}>{getLogIcon(log)}</span>
              <span className={`text-xs flex-1 ${getLogColor(log)}`}>{log.message}</span>
              <span className="text-[9px] text-surface-600 font-mono">{log.timestamp.toLocaleTimeString()}</span>
            </motion.div>
          ))}
        </AnimatePresence>
        {logs.length === 0 && (
          <div className="text-center py-8 text-surface-500">
            <Wifi size={24} className="mx-auto mb-2 opacity-30" />
            <p className="text-xs">Monitoring network activity...</p>
          </div>
        )}
      </div>

      {lastRefresh && (
        <div className="text-[9px] text-surface-600 text-center mt-2 font-mono">
          Last refresh: {lastRefresh.toLocaleTimeString()}
        </div>
      )}
    </div>
  );
}
