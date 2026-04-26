/**
 * Full-page alerts view.
 */
import { Alert } from '../lib/supabase';
import AlertFeed from '../components/AlertFeed';

interface AlertsPageProps {
  alerts: Alert[];
  onAlertClick?: (alert: Alert) => void;
}

export default function AlertsPage({ alerts, onAlertClick }: AlertsPageProps) {
  return (
    <div className="h-[calc(100vh-4rem)] animate-fade-in" id="alerts-page">
      <div className="glass-panel p-5 h-full">
        <AlertFeed alerts={alerts} onAlertClick={onAlertClick} maxItems={100} />
      </div>
    </div>
  );
}
