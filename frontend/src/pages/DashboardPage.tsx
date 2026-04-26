/**
 * Dashboard Page — main overview combining all panels.
 */
import { Zone, Alert, Volunteer, Shelter, Detection, Acknowledgment, AgentLog } from '../lib/supabase';
import MetricCards from '../components/MetricCards';
import LiveMap from '../components/LiveMap';
import AlertFeed from '../components/AlertFeed';
import AgentLogsPanel from '../components/AgentLogsPanel';
import BroadcastStatus from '../components/BroadcastStatus';

interface DashboardPageProps {
  zones: Zone[];
  alerts: Alert[];
  volunteers: Volunteer[];
  shelters: Shelter[];
  detections: Detection[];
  acknowledgments: Acknowledgment[];
  agentLogs: AgentLog[];
  onAlertClick?: (alert: Alert) => void;
}

export default function DashboardPage({
  zones,
  alerts,
  volunteers,
  shelters,
  detections,
  acknowledgments,
  agentLogs,
  onAlertClick,
}: DashboardPageProps) {
  return (
    <div className="space-y-5 animate-fade-in" id="dashboard-page">
      {/* Metric Cards */}
      <MetricCards zones={zones} volunteers={volunteers} shelters={shelters} alerts={alerts} />

      {/* Main Grid: Map + Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Map */}
        <div className="lg:col-span-2 glass-panel p-1 h-[480px]">
          <LiveMap zones={zones} shelters={shelters} volunteerCount={volunteers.length} />
        </div>

        {/* Alert Feed */}
        <div className="glass-panel p-4 h-[480px]">
          <AlertFeed alerts={alerts} onAlertClick={onAlertClick} />
        </div>
      </div>

      {/* Bottom Grid: Agent Logs + Broadcast */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Agent Logs */}
        <div className="lg:col-span-2 glass-panel p-4 h-[420px]">
          <AgentLogsPanel agentLogs={agentLogs} alerts={alerts} detections={detections} />
        </div>

        {/* Broadcast Status */}
        <div className="glass-panel p-4 h-[420px]">
          <BroadcastStatus alerts={alerts} acknowledgments={acknowledgments} />
        </div>
      </div>
    </div>
  );
}
