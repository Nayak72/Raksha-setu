/**
 * Full-page agent logs view.
 */
import { Alert, Detection, AgentLog } from '../lib/supabase';
import AgentLogsPanel from '../components/AgentLogsPanel';

interface AgentsPageProps {
  agentLogs: AgentLog[];
  alerts: Alert[];
  detections: Detection[];
}

export default function AgentsPage({ agentLogs, alerts, detections }: AgentsPageProps) {
  return (
    <div className="h-[calc(100vh-4rem)] animate-fade-in" id="agents-page">
      <div className="glass-panel p-5 h-full">
        <AgentLogsPanel agentLogs={agentLogs} alerts={alerts} detections={detections} />
      </div>
    </div>
  );
}
