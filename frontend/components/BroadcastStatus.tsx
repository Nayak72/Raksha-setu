/**
 * Broadcast Status component.
 */
'use client';

import { motion } from 'framer-motion';
import { Radio, CheckCircle2, Clock, XCircle, Wifi } from 'lucide-react';
import { Acknowledgment, Alert } from '../lib/supabase';

interface BroadcastStatusProps {
  alerts: Alert[];
  acknowledgments: Acknowledgment[];
  totalDevices?: number;
}

function StatusCard({ icon, label, count, color, bg }: { icon: React.ReactNode; label: string; count: number; color: string; bg: string }) {
  return (
    <div className={`${bg} rounded-xl p-3 text-center border border-surface-700/20`}>
      <div className={`flex justify-center mb-1 ${color}`}>{icon}</div>
      <div className="text-lg font-bold text-white">{count}</div>
      <div className="text-[10px] text-surface-400 font-medium">{label}</div>
    </div>
  );
}

export default function BroadcastStatus({ alerts, acknowledgments, totalDevices = 1000 }: BroadcastStatusProps) {
  const latestAlert = alerts[0];
  const alertAcks = latestAlert ? acknowledgments.filter((a) => a.alert_id === latestAlert.id) : [];
  const reached = alertAcks.length;
  const acknowledged = alertAcks.filter((a) => a.status === 'acknowledged').length;
  const pending = alertAcks.filter((a) => a.status === 'pending').length;
  const failed = alertAcks.filter((a) => a.status === 'failed').length;
  const reachPercent = totalDevices > 0 ? (reached / totalDevices) * 100 : 0;

  return (
    <div className="flex flex-col h-full" id="broadcast-status-panel">
      <div className="flex items-center gap-2 mb-4">
        <Radio className="text-raksha-400" size={20} />
        <h2 className="text-lg font-bold text-white">Broadcast Status</h2>
        {latestAlert && (
          <span className={`ml-auto ${latestAlert.severity === 'critical' ? 'status-critical' : latestAlert.severity === 'high' ? 'status-warning' : 'status-info'}`}>
            {latestAlert.severity.toUpperCase()}
          </span>
        )}
      </div>

      <div className="glass-panel p-6 mb-4 text-center">
        <div className="relative inline-flex items-center justify-center mb-4">
          <svg width="120" height="120" viewBox="0 0 120 120">
            <circle cx="60" cy="60" r="52" fill="none" stroke="#1e293b" strokeWidth="8" />
            <motion.circle
              cx="60" cy="60" r="52" fill="none" stroke="url(#broadcastGradient)" strokeWidth="8" strokeLinecap="round"
              strokeDasharray={`${2 * Math.PI * 52}`}
              strokeDashoffset={`${2 * Math.PI * 52 * (1 - reachPercent / 100)}`}
              transform="rotate(-90 60 60)"
              initial={{ strokeDashoffset: 2 * Math.PI * 52 }}
              animate={{ strokeDashoffset: 2 * Math.PI * 52 * (1 - reachPercent / 100) }}
              transition={{ duration: 1, ease: 'easeOut' }}
            />
            <defs>
              <linearGradient id="broadcastGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#1a65ff" />
                <stop offset="100%" stopColor="#3bce7f" />
              </linearGradient>
            </defs>
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-3xl font-black text-white">{reached}</span>
            <span className="text-xs text-surface-400">/ {totalDevices}</span>
          </div>
        </div>
        <div className="text-sm text-surface-300 font-medium">Devices Reached</div>
        <div className="text-xs text-surface-500 mt-1">{reachPercent.toFixed(1)}% coverage</div>
      </div>

      <div className="grid grid-cols-3 gap-2 mb-4">
        <StatusCard icon={<CheckCircle2 size={16} />} label="Acknowledged" count={acknowledged} color="text-safe-400" bg="bg-safe-500/10" />
        <StatusCard icon={<Clock size={16} />} label="Pending" count={pending} color="text-warning-400" bg="bg-warning-500/10" />
        <StatusCard icon={<XCircle size={16} />} label="Failed" count={failed} color="text-danger-400" bg="bg-danger-500/10" />
      </div>

      <div className="flex-1 overflow-y-auto space-y-2">
        <div className="text-xs font-semibold text-surface-400 uppercase tracking-wider mb-2">Recent Broadcasts</div>
        {alerts.slice(0, 5).map((alert) => {
          const thisAcks = acknowledgments.filter((a) => a.alert_id === alert.id);
          return (
            <motion.div key={alert.id} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} className="flex items-center gap-3 p-3 rounded-xl bg-surface-800/30 border border-surface-700/30">
              <Wifi size={14} className={alert.severity === 'critical' ? 'text-danger-400' : alert.severity === 'high' ? 'text-warning-400' : 'text-raksha-400'} />
              <div className="flex-1 min-w-0">
                <p className="text-xs text-white font-medium truncate">{alert.message.slice(0, 60)}...</p>
                <p className="text-[10px] text-surface-500 font-mono mt-0.5">{new Date(alert.timestamp).toLocaleTimeString()} · {thisAcks.length} devices</p>
              </div>
              <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded ${alert.severity === 'critical' ? 'bg-danger-500/20 text-danger-400' : alert.severity === 'high' ? 'bg-warning-500/20 text-warning-400' : 'bg-raksha-500/20 text-raksha-400'}`}>
                {alert.severity}
              </span>
            </motion.div>
          );
        })}
        {alerts.length === 0 && (
          <div className="text-center py-8 text-surface-500">
            <Radio size={24} className="mx-auto mb-2 opacity-30" />
            <p className="text-xs">No broadcasts yet</p>
          </div>
        )}
      </div>
    </div>
  );
}
