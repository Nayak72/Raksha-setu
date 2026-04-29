/**
 * Full-screen emergency alert overlay with flashing + sound.
 */
'use client';

import { useEffect, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertTriangle, X, Volume2, VolumeX } from 'lucide-react';
import { Alert } from '../../lib/supabase';
import { soundManager } from '../../lib/sounds';

interface EmergencyAlertProps {
  alert: Alert | null;
  onDismiss: () => void;
}

export default function EmergencyAlert({ alert, onDismiss }: EmergencyAlertProps) {
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [flashPhase, setFlashPhase] = useState(false);

  useEffect(() => {
    if (!alert || alert.severity !== 'critical') return;
    const interval = setInterval(() => {
      setFlashPhase((prev) => !prev);
    }, 500);
    return () => clearInterval(interval);
  }, [alert]);

  useEffect(() => {
    if (!alert || !soundEnabled) return;
    if (alert.severity === 'critical') {
      soundManager.playEmergencyAlert();
      const interval = setInterval(() => {
        soundManager.playEmergencyAlert();
      }, 3000);
      return () => clearInterval(interval);
    } else {
      soundManager.playNotification();
    }
  }, [alert, soundEnabled]);

  useEffect(() => {
    if (!alert || alert.severity === 'critical') return;
    const timeout = setTimeout(onDismiss, 30000);
    return () => clearTimeout(timeout);
  }, [alert, onDismiss]);

  const toggleSound = useCallback(() => {
    setSoundEnabled((prev) => !prev);
  }, []);

  if (!alert) return null;

  const isCritical = alert.severity === 'critical';

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-[9999] flex items-center justify-center"
        style={{
          background: isCritical
            ? flashPhase
              ? 'rgba(255, 45, 45, 0.15)'
              : 'rgba(200, 8, 8, 0.2)'
            : 'rgba(0, 0, 0, 0.85)',
          backdropFilter: 'blur(8px)',
          transition: 'background 0.3s ease',
        }}
        id="emergency-alert-overlay"
      >
        {isCritical && (
          <>
            <motion.div
              className="absolute"
              animate={{ scale: [1, 2.5], opacity: [0.3, 0] }}
              transition={{ duration: 2, repeat: Infinity }}
              style={{ width: 200, height: 200, borderRadius: '50%', border: '2px solid rgba(255, 45, 45, 0.5)' }}
            />
            <motion.div
              className="absolute"
              animate={{ scale: [1, 3], opacity: [0.2, 0] }}
              transition={{ duration: 2.5, repeat: Infinity, delay: 0.5 }}
              style={{ width: 200, height: 200, borderRadius: '50%', border: '2px solid rgba(255, 45, 45, 0.3)' }}
            />
          </>
        )}

        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.8, opacity: 0 }}
          transition={{ type: 'spring', damping: 20 }}
          className={`relative max-w-lg w-full mx-4 rounded-3xl p-8 shadow-2xl ${
            isCritical
              ? 'bg-gradient-to-b from-danger-950/90 to-surface-900/95 border-2 border-danger-500/40'
              : 'bg-gradient-to-b from-warning-950/90 to-surface-900/95 border border-warning-500/30'
          }`}
          style={{
            boxShadow: isCritical
              ? '0 0 60px rgba(255, 45, 45, 0.3), 0 0 120px rgba(255, 45, 45, 0.1)'
              : '0 0 40px rgba(249, 155, 7, 0.2)',
          }}
        >
          <div className="absolute top-4 right-4 flex items-center gap-2">
            <button onClick={toggleSound} className="p-2 rounded-lg bg-surface-800/60 text-surface-400 hover:text-white transition-colors" id="emergency-sound-toggle">
              {soundEnabled ? <Volume2 size={16} /> : <VolumeX size={16} />}
            </button>
            <button onClick={onDismiss} className="p-2 rounded-lg bg-surface-800/60 text-surface-400 hover:text-white transition-colors" id="emergency-dismiss-btn">
              <X size={16} />
            </button>
          </div>

          <div className="flex justify-center mb-6">
            <motion.div
              animate={isCritical ? { scale: [1, 1.15, 1] } : {}}
              transition={{ duration: 1, repeat: Infinity }}
              className={`w-20 h-20 rounded-full flex items-center justify-center ${
                isCritical ? 'bg-danger-500/20' : 'bg-warning-500/20'
              }`}
            >
              <AlertTriangle size={40} className={isCritical ? 'text-danger-400' : 'text-warning-400'} />
            </motion.div>
          </div>

          <h1 className={`text-center text-2xl font-black mb-2 tracking-wide uppercase ${
            isCritical ? 'text-danger-400' : 'text-warning-400'
          }`}>
            {isCritical ? '🚨 CRITICAL EMERGENCY' : '⚠️ ALERT'}
          </h1>

          <div className="flex justify-center mb-6">
            <span className={`px-4 py-1 rounded-full text-xs font-bold uppercase tracking-widest ${
              isCritical
                ? 'bg-danger-500/20 text-danger-400 border border-danger-500/40'
                : 'bg-warning-500/20 text-warning-400 border border-warning-500/40'
            }`}>
              Severity: {alert.severity}
            </span>
          </div>

          <div className="text-center mb-6">
            <p className="text-lg text-white font-medium leading-relaxed">{alert.message}</p>
          </div>

          <div className="grid grid-cols-2 gap-3 mb-6">
            <div className="bg-surface-800/50 rounded-xl p-3 text-center">
              <div className="text-xs text-surface-400 mb-1">Zone</div>
              <div className="text-sm font-mono font-semibold text-white">{alert.zone.slice(0, 8)}...</div>
            </div>
            <div className="bg-surface-800/50 rounded-xl p-3 text-center">
              <div className="text-xs text-surface-400 mb-1">Time</div>
              <div className="text-sm font-mono font-semibold text-white">{new Date(alert.timestamp).toLocaleTimeString()}</div>
            </div>
          </div>

          <div className="flex gap-3">
            <button
              onClick={onDismiss}
              className={`flex-1 py-3 rounded-xl font-semibold transition-all duration-200 active:scale-95 ${
                isCritical
                  ? 'bg-danger-600 hover:bg-danger-500 text-white shadow-lg shadow-danger-500/25'
                  : 'bg-warning-600 hover:bg-warning-500 text-white shadow-lg shadow-warning-500/25'
              }`}
              id="emergency-acknowledge-btn"
            >
              Acknowledge
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
