/**
 * Full-page agent graph visualization.
 */
import { Alert, Detection } from '../lib/supabase';
import AgentGraph from '../components/AgentGraph';

interface GraphPageProps {
  alerts: Alert[];
  detections: Detection[];
}

export default function GraphPage({ alerts, detections }: GraphPageProps) {
  return (
    <div className="h-[calc(100vh-4rem)] animate-fade-in" id="graph-page">
      <div className="glass-panel p-1 h-full">
        <AgentGraph alerts={alerts} detections={detections} />
      </div>
    </div>
  );
}
