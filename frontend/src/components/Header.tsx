/**
 * Top header bar with system stats and actions.
 */
import { SystemStatus } from '../hooks/useSupabaseRealtime';

interface HeaderProps {
  systemStatus: SystemStatus | null;
  statusLoading: boolean;
  statusError: string | null;
  alertCount: number;
  onRefresh: () => void;
}

export default function Header(props: HeaderProps) {
  const {
    systemStatus,
    statusLoading,
    statusError,
    alertCount,
    onRefresh,
  } = props;

  const counts = systemStatus?.counts || { zones: 0, volunteers: 0, shelters: 0, active_alerts: 0 };

  return (
    <header
      className="h-16 flex items-center justify-between px-6 border-b border-surface-700/50 bg-surface-900/40 backdrop-blur-xl sticky top-0 z-30"
      id="header"
    >
      {/* Left: Time + status */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-surface-500">
            <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
          </svg>
          <span className="text-sm font-mono text-surface-300">
            {new Date().toLocaleTimeString()} IST
          </span>
        </div>

        <div className="w-px h-6 bg-surface-700/50" />

        {statusError ? (
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full bg-danger-500" />
            <span className="text-xs text-danger-400 font-medium">Backend Offline</span>
          </div>
        ) : systemStatus ? (
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-medium bg-safe-500/10 text-safe-400 border border-safe-500/20">
              ● Supabase
            </div>
            <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-medium ${
              systemStatus.mqtt_connected
                ? 'bg-safe-500/10 text-safe-400 border border-safe-500/20'
                : 'bg-danger-500/10 text-danger-400 border border-danger-500/20'
            }`}>
              ● MQTT
            </div>
            <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-medium ${
              systemStatus.pg_listener_active
                ? 'bg-safe-500/10 text-safe-400 border border-safe-500/20'
                : 'bg-danger-500/10 text-danger-400 border border-danger-500/20'
            }`}>
              ● PG Listener
            </div>
          </div>
        ) : statusLoading ? (
          <span className="text-xs text-surface-500">Connecting...</span>
        ) : null}
      </div>

      {/* Right */}
      <div className="flex items-center gap-3">
        {systemStatus && (
          <div className="hidden md:flex items-center gap-3 mr-2">
            <div className="text-center">
              <div className="text-sm font-bold text-white">{counts.zones || 0}</div>
              <div className="text-[9px] text-surface-500 uppercase tracking-wider">Zones</div>
            </div>
            <div className="text-center">
              <div className="text-sm font-bold text-white">{counts.volunteers || 0}</div>
              <div className="text-[9px] text-surface-500 uppercase tracking-wider">Volunteers</div>
            </div>
            <div className="text-center">
              <div className="text-sm font-bold text-white">{counts.shelters || 0}</div>
              <div className="text-[9px] text-surface-500 uppercase tracking-wider">Shelters</div>
            </div>
            <div className="text-center">
              <div className={`text-sm font-bold ${(counts.active_alerts || 0) > 0 ? 'text-danger-400' : 'text-white'}`}>
                {counts.active_alerts || 0}
              </div>
              <div className="text-[9px] text-surface-500 uppercase tracking-wider">Alerts</div>
            </div>
          </div>
        )}

        <div className="w-px h-6 bg-surface-700/50" />

        <button className="relative p-2 rounded-lg hover:bg-surface-800/60 transition-colors" id="alert-bell">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-surface-400">
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>
          </svg>
          {(alertCount || 0) > 0 && (
            <span className="absolute -top-0.5 -right-0.5 w-5 h-5 rounded-full bg-danger-500 text-[9px] font-bold text-white flex items-center justify-center animate-pulse">
              {alertCount > 99 ? '99+' : alertCount}
            </span>
          )}
        </button>

        <button
          onClick={onRefresh}
          className="p-2 rounded-lg hover:bg-surface-800/60 transition-colors group"
          title="Refresh all data"
          id="refresh-btn"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-surface-400 group-hover:text-white transition-colors">
            <polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/>
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
          </svg>
        </button>
      </div>
    </header>
  );
}
