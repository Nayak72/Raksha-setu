/**
 * Full-page broadcast status view.
 */
import { Alert, Acknowledgment } from '../lib/supabase';
import BroadcastStatus from '../components/BroadcastStatus';

interface BroadcastPageProps {
  alerts: Alert[];
  acknowledgments: Acknowledgment[];
}

export default function BroadcastPage({ alerts, acknowledgments }: BroadcastPageProps) {
  return (
    <div className="h-[calc(100vh-4rem)] animate-fade-in" id="broadcast-page">
      <div className="glass-panel p-5 h-full">
        <BroadcastStatus alerts={alerts} acknowledgments={acknowledgments} />
      </div>
    </div>
  );
}
