/**
 * Alert Feed — scrollable list of recent alerts.
 */
import { motion, AnimatePresence } from 'framer-motion';
import { AlertTriangle, Clock, MapPin, ChevronRight } from 'lucide-react';
import { Alert } from '../lib/supabase';

interface AlertFeedProps {
  alerts: Alert[];
  onAlertClick?: (alert: Alert) => void;
  maxItems?: number;
}

const severityStyles: Record<string, { dot: string; badge: string; border: string }> = {
  critical: {
    dot: 'bg-danger-500 animate-pulse',
    badge: 'status-critical',
    border: 'border-l-danger-500',
  },
  high: {
    dot: 'bg-danger-400',
    badge: 'bg-danger-500/15 text-danger-400 border border-danger-500/25',
    border: 'border-l-danger-400',
  },
  medium: {
    dot: 'bg-warning-500',
    badge: 'status-warning',
    border: 'border-l-warning-500',
  },
  low: {
    dot: 'bg-safe-500',
    badge: 'status-safe',
    border: 'border-l-safe-500',
  },
};

export default function AlertFeed({ alerts, onAlertClick, maxItems = 20 }: AlertFeedProps) {
  const displayed = alerts.slice(0, maxItems);

  return (
    <div className="flex flex-col h-full" id="alert-feed">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <AlertTriangle className="text-warning-400" size={20} />
          <h2 className="text-lg font-bold text-white">Alert Feed</h2>
          <span className="status-warning">{alerts.length} total</span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto space-y-2 pr-1">
        <AnimatePresence mode="popLayout">
          {displayed.map((alert) => {
            const style = severityStyles[alert.severity] || severityStyles.low;

            return (
              <motion.div
                key={alert.id}
                layout
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                onClick={() => onAlertClick?.(alert)}
                className={`group p-3 rounded-xl bg-surface-800/30 border border-surface-700/30 border-l-2 ${style.border} cursor-pointer hover:bg-surface-800/50 hover:border-surface-600/40 transition-all duration-200`}
              >
                <div className="flex items-start gap-3">
                  <div className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${style.dot}`} />

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span
                        className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider ${style.badge}`}
                      >
                        {alert.severity}
                      </span>
                      <div className="flex items-center gap-1 text-[10px] text-surface-500 ml-auto">
                        <Clock size={10} />
                        {new Date(alert.timestamp).toLocaleTimeString()}
                      </div>
                    </div>

                    <p className="text-sm text-white font-medium leading-snug mb-1.5">
                      {alert.message}
                    </p>

                    <div className="flex items-center gap-1 text-[10px] text-surface-500">
                      <MapPin size={10} />
                      Zone {alert.zone.slice(0, 8)}...
                    </div>
                  </div>

                  <ChevronRight
                    size={14}
                    className="text-surface-600 group-hover:text-surface-400 transition-colors mt-1 flex-shrink-0"
                  />
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>

        {alerts.length === 0 && (
          <div className="text-center py-12 text-surface-500">
            <AlertTriangle size={32} className="mx-auto mb-3 opacity-30" />
            <p className="text-sm">No alerts yet</p>
            <p className="text-xs mt-1">Alerts will appear as agents detect threats</p>
          </div>
        )}
      </div>
    </div>
  );
}
