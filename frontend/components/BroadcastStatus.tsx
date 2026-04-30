/**
 * Enhanced Broadcast Status component with live UDP broadcast tracking.
 * Shows real-time broadcast feed, device acknowledgments, and manual trigger.
 */
'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Radio, CheckCircle2, Clock, XCircle, Wifi, Send,
  Volume2, AlertTriangle, Shield, Activity, Zap, Signal,
} from 'lucide-react';

/* ── Types ─────────────────────────────────── */
export type BroadcastRecord = {
  id: string;
  zone_id: string;
  zone_name: string;
  severity: string;
  message: string;
  success: boolean;
  timestamp: string;
  cycle?: number;
  manual?: boolean;
};

export type BroadcastStats = {
  total_sent: number;
  successful?: number;
  failed?: number;
  devices_reached: number;
  recent_count?: number;
  recent_acks?: number;
};

export interface BroadcastStatusProps {
  /** Live broadcast records from WebSocket or API */
  broadcasts: BroadcastRecord[];
  /** Broadcast stats */
  stats: BroadcastStats;
  /** Available zones for manual broadcast */
  zones?: { id: string; name: string; severity?: string }[];
  /** Whether the backend is online */
  isOnline?: boolean;
}

/* ── Severity Helpers ─────────────────────── */
function severityColor(severity: string) {
  switch (severity?.toLowerCase()) {
    case 'critical': return { text: 'text-danger-400', bg: 'bg-danger-500/15', border: 'border-danger-500/30', ring: 'ring-danger-500/20' };
    case 'high':     return { text: 'text-warning-400', bg: 'bg-warning-500/15', border: 'border-warning-500/30', ring: 'ring-warning-500/20' };
    case 'medium':   return { text: 'text-raksha-400', bg: 'bg-raksha-500/15', border: 'border-raksha-500/30', ring: 'ring-raksha-500/20' };
    default:         return { text: 'text-surface-400', bg: 'bg-surface-500/10', border: 'border-surface-600/30', ring: 'ring-surface-500/20' };
  }
}

function severityIcon(severity: string) {
  switch (severity?.toLowerCase()) {
    case 'critical': return <AlertTriangle size={14} />;
    case 'high':     return <Zap size={14} />;
    case 'medium':   return <Signal size={14} />;
    default:         return <Wifi size={14} />;
  }
}

/* ── Stat Card ────────────────────────────── */
function StatCard({ icon, label, count, color, bg }: {
  icon: React.ReactNode; label: string; count: number; color: string; bg: string;
}) {
  return (
    <div className={`${bg} rounded-xl p-4 text-center border border-surface-700/20`}>
      <div className={`flex justify-center mb-1.5 ${color}`}>{icon}</div>
      <motion.div
        key={count}
        initial={{ scale: 1.3, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        className="text-2xl font-black text-white"
      >
        {count}
      </motion.div>
      <div className="text-[10px] text-surface-400 font-semibold uppercase tracking-wider mt-1">{label}</div>
    </div>
  );
}

/* ── Pulse Animation ──────────────────────── */
function PulseRing({ active }: { active: boolean }) {
  if (!active) return null;
  return (
    <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
      <motion.div
        className="w-32 h-32 rounded-full border-2 border-raksha-400/30"
        animate={{ scale: [1, 1.5, 2], opacity: [0.5, 0.2, 0] }}
        transition={{ duration: 2, repeat: Infinity, ease: 'easeOut' }}
      />
      <motion.div
        className="absolute w-32 h-32 rounded-full border-2 border-raksha-400/20"
        animate={{ scale: [1, 1.3, 1.8], opacity: [0.4, 0.15, 0] }}
        transition={{ duration: 2, repeat: Infinity, ease: 'easeOut', delay: 0.5 }}
      />
    </div>
  );
}

/* ── Main Component ───────────────────────── */
export default function BroadcastStatus({
  broadcasts,
  stats,
  zones = [],
  isOnline = false,
}: BroadcastStatusProps) {
  const [showManualForm, setShowManualForm] = useState(false);
  const [manualZone, setManualZone] = useState('');
  const [manualMessage, setManualMessage] = useState('');
  const [manualSeverity, setManualSeverity] = useState('high');
  const [sending, setSending] = useState(false);
  const [sendResult, setSendResult] = useState<string | null>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to newest broadcast
  useEffect(() => {
    if (listRef.current && broadcasts.length > 0) {
      listRef.current.scrollTop = 0;
    }
  }, [broadcasts.length]);

  const totalSent = stats.total_sent || 0;
  const devicesReached = stats.devices_reached || 0;
  const successCount = stats.successful ?? broadcasts.filter(b => b.success).length;
  const failedCount = stats.failed ?? broadcasts.filter(b => !b.success).length;
  const isActive = broadcasts.length > 0 && broadcasts[0]?.success;

  // Circular progress
  const maxDevices = Math.max(devicesReached, 50);
  const reachPercent = maxDevices > 0 ? (devicesReached / maxDevices) * 100 : 0;

  const handleManualBroadcast = useCallback(async () => {
    if (!manualZone || !manualMessage) return;
    setSending(true);
    setSendResult(null);
    try {
      const base = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
      const res = await fetch(`${base}/api/v1/broadcast-manual`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          zone_id: manualZone,
          message: manualMessage,
          severity: manualSeverity,
        }),
      });
      const data = await res.json();
      setSendResult(data.status === 'sent' ? '✅ Broadcast sent!' : '❌ Broadcast failed');
      setManualMessage('');
    } catch {
      setSendResult('❌ Connection failed');
    }
    setSending(false);
    setTimeout(() => setSendResult(null), 3000);
  }, [manualZone, manualMessage, manualSeverity]);

  return (
    <div className="flex flex-col h-full" id="broadcast-status-panel">
      {/* ── Header ─────────────────────────── */}
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-raksha-500/10">
            <Radio className="text-raksha-400" size={20} />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">UDP Broadcast Control</h2>
            <p className="text-[11px] text-surface-500 font-medium">
              Port 5005 · {isOnline ? 'Active' : 'Standby'} · LAN Broadcast
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold ${
            isActive ? 'bg-safe-500/15 text-safe-400' : 'bg-surface-700/30 text-surface-500'
          }`}>
            <div className={`w-2 h-2 rounded-full ${isActive ? 'bg-safe-400 animate-pulse' : 'bg-surface-600'}`} />
            {isActive ? 'Broadcasting' : 'Idle'}
          </div>
          <button
            onClick={() => setShowManualForm(!showManualForm)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-raksha-500/10 
                       text-raksha-400 text-xs font-semibold hover:bg-raksha-500/20 transition-colors"
          >
            <Send size={12} />
            Manual
          </button>
        </div>
      </div>

      {/* ── Manual Broadcast Form ──────────── */}
      <AnimatePresence>
        {showManualForm && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden mb-4"
          >
            <div className="glass-panel p-4 space-y-3 border border-raksha-500/20">
              <div className="text-xs font-semibold text-surface-300 uppercase tracking-wider flex items-center gap-2">
                <Volume2 size={12} className="text-raksha-400" />
                Send Manual Alert
              </div>
              <div className="grid grid-cols-2 gap-2">
                <select
                  value={manualZone}
                  onChange={(e) => setManualZone(e.target.value)}
                  className="col-span-1 px-3 py-2 rounded-lg bg-surface-800 border border-surface-700 
                             text-xs text-white focus:border-raksha-500 focus:outline-none"
                >
                  <option value="">Select Zone</option>
                  {zones.map((z) => (
                    <option key={z.id} value={z.id}>{z.name}</option>
                  ))}
                </select>
                <select
                  value={manualSeverity}
                  onChange={(e) => setManualSeverity(e.target.value)}
                  className="col-span-1 px-3 py-2 rounded-lg bg-surface-800 border border-surface-700 
                             text-xs text-white focus:border-raksha-500 focus:outline-none"
                >
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </select>
              </div>
              <textarea
                value={manualMessage}
                onChange={(e) => setManualMessage(e.target.value)}
                placeholder="Emergency alert message..."
                rows={2}
                className="w-full px-3 py-2 rounded-lg bg-surface-800 border border-surface-700 
                           text-xs text-white placeholder-surface-600 resize-none
                           focus:border-raksha-500 focus:outline-none"
              />
              <div className="flex items-center gap-2">
                <button
                  onClick={handleManualBroadcast}
                  disabled={sending || !manualZone || !manualMessage}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-lg font-semibold text-xs
                             bg-gradient-to-r from-raksha-500 to-raksha-600 text-white
                             hover:from-raksha-400 hover:to-raksha-500 transition-all
                             disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  <Send size={12} />
                  {sending ? 'Sending...' : 'Broadcast Now'}
                </button>
                {sendResult && (
                  <motion.span
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="text-xs font-medium"
                  >
                    {sendResult}
                  </motion.span>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Circular Device Indicator ─────── */}
      <div className="glass-panel p-6 mb-4 text-center relative">
        <PulseRing active={isActive} />
        <div className="relative inline-flex items-center justify-center mb-4">
          <svg width="120" height="120" viewBox="0 0 120 120">
            <circle cx="60" cy="60" r="52" fill="none" stroke="#1B2433" strokeWidth="8" />
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
                <stop offset="0%" stopColor="#2563EB" />
                <stop offset="50%" stopColor="#22C55E" />
                <stop offset="100%" stopColor="#34D399" />
              </linearGradient>
            </defs>
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <motion.span
              key={devicesReached}
              initial={{ scale: 1.3 }}
              animate={{ scale: 1 }}
              className="text-3xl font-black text-white"
            >
              {devicesReached}
            </motion.span>
            <span className="text-xs text-surface-400">devices</span>
          </div>
        </div>
        <div className="text-sm text-surface-300 font-semibold">Devices Reached</div>
        <div className="text-xs text-surface-500 mt-1">
          {totalSent} total broadcasts · Port 5005
        </div>
      </div>

      {/* ── Stat Grid ────────────────────── */}
      <div className="grid grid-cols-3 gap-2 mb-4">
        <StatCard
          icon={<CheckCircle2 size={16} />}
          label="Successful"
          count={successCount}
          color="text-safe-400"
          bg="bg-safe-500/10"
        />
        <StatCard
          icon={<Activity size={16} />}
          label="Total Sent"
          count={totalSent}
          color="text-raksha-400"
          bg="bg-raksha-500/10"
        />
        <StatCard
          icon={<XCircle size={16} />}
          label="Failed"
          count={failedCount}
          color="text-danger-400"
          bg="bg-danger-500/10"
        />
      </div>

      {/* ── Live Broadcast Feed ──────────── */}
      <div className="flex-1 overflow-y-auto space-y-2" ref={listRef}>
        <div className="flex items-center justify-between mb-2">
          <div className="text-xs font-semibold text-surface-400 uppercase tracking-wider">
            Live Broadcast Feed
          </div>
          <div className="flex items-center gap-1.5 text-[10px] text-surface-500">
            <div className={`w-1.5 h-1.5 rounded-full ${isActive ? 'bg-safe-400 animate-pulse' : 'bg-surface-600'}`} />
            {broadcasts.length} recent
          </div>
        </div>

        <AnimatePresence mode="popLayout">
          {broadcasts.slice(0, 15).map((broadcast, idx) => {
            const sc = severityColor(broadcast.severity);
            return (
              <motion.div
                key={broadcast.id}
                layout
                initial={{ opacity: 0, x: -20, scale: 0.95 }}
                animate={{ opacity: 1, x: 0, scale: 1 }}
                exit={{ opacity: 0, x: 20 }}
                transition={{ delay: idx * 0.03 }}
                className={`flex items-start gap-3 p-3 rounded-xl bg-surface-800/30 border ${sc.border} hover:bg-surface-800/50 transition-colors`}
              >
                <div className={`mt-0.5 p-1.5 rounded-lg ${sc.bg}`}>
                  {broadcast.success ? severityIcon(broadcast.severity) : <XCircle size={14} className="text-danger-400" />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <p className="text-xs text-white font-semibold truncate">
                      {broadcast.zone_name || broadcast.zone_id}
                    </p>
                    {broadcast.manual && (
                      <span className="text-[9px] px-1.5 py-0.5 rounded bg-raksha-500/20 text-raksha-400 font-bold">
                        MANUAL
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-surface-400 leading-relaxed line-clamp-2">
                    {broadcast.message}
                  </p>
                  <div className="flex items-center gap-3 mt-1.5">
                    <span className="text-[10px] text-surface-500 font-mono">
                      {new Date(broadcast.timestamp).toLocaleTimeString()}
                    </span>
                    <span className={`text-[10px] font-bold ${broadcast.success ? 'text-safe-400' : 'text-danger-400'}`}>
                      {broadcast.success ? '✓ Delivered' : '✗ Failed'}
                    </span>
                  </div>
                </div>
                <span className={`text-[10px] font-black uppercase px-2 py-1 rounded-lg ${sc.bg} ${sc.text} whitespace-nowrap`}>
                  {broadcast.severity}
                </span>
              </motion.div>
            );
          })}
        </AnimatePresence>

        {broadcasts.length === 0 && (
          <div className="text-center py-12 text-surface-500">
            <div className="relative inline-block mb-3">
              <Radio size={32} className="opacity-20" />
              <motion.div
                className="absolute inset-0"
                animate={{ opacity: [0.2, 0.5, 0.2] }}
                transition={{ duration: 2, repeat: Infinity }}
              >
                <Radio size={32} className="text-raksha-500" />
              </motion.div>
            </div>
            <p className="text-xs font-medium">Waiting for broadcasts...</p>
            <p className="text-[10px] text-surface-600 mt-1">
              Alerts will appear here when zones reach medium+ severity
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
