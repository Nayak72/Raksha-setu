/**
 * RakshaSethu Dashboard — Main Application.
 * Minimal version to debug rendering.
 */
import { useState, useCallback, useEffect } from 'react';
import Sidebar, { NavPage } from './components/Sidebar';
import Header from './components/Header';
import EmergencyAlert from './components/EmergencyAlert';
import MetricCards from './components/MetricCards';
import AlertFeed from './components/AlertFeed';
import {
  useZones,
  useAlerts,
  useVolunteers,
  useShelters,
  useDetections,
  useAcknowledgments,
  useSystemStatus,
  useAgentLogs,
} from './hooks/useSupabaseRealtime';
import { Alert } from './lib/supabase';

// Lazy load heavy components
import { lazy, Suspense } from 'react';
const LiveMap = lazy(() => import('./components/LiveMap'));
const AgentLogsPanel = lazy(() => import('./components/AgentLogsPanel'));
const BroadcastStatus = lazy(() => import('./components/BroadcastStatus'));
const MqttClientPanel = lazy(() => import('./components/MqttClientPanel'));
const AgentGraph = lazy(() => import('./components/AgentGraph'));
const YoloFeed = lazy(() => import('./components/YoloFeed'));
const AnalyticsTab = lazy(() => import('./components/AnalyticsTab'));

function LoadingPanel() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="text-surface-500 text-sm">Loading...</div>
    </div>
  );
}

export default function App() {
  const [activePage, setActivePage] = useState<NavPage>('dashboard');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [emergencyAlert, setEmergencyAlert] = useState<Alert | null>(null);

  const { zones, refetch: refetchZones } = useZones();
  const { alerts, latestAlert, refetch: refetchAlerts } = useAlerts();
  const { volunteers, refetch: refetchVolunteers } = useVolunteers();
  const { shelters, refetch: refetchShelters } = useShelters();
  const { detections } = useDetections();
  const { acks: acknowledgments } = useAcknowledgments();
  const { logs: agentLogs } = useAgentLogs();
  const {
    status: systemStatus,
    loading: statusLoading,
    error: statusError,
    refetch: refetchStatus,
  } = useSystemStatus();

  useEffect(() => {
    if (latestAlert && (latestAlert.severity === 'critical' || latestAlert.severity === 'high')) {
      setEmergencyAlert(latestAlert);
    }
  }, [latestAlert]);

  const handleRefresh = useCallback(() => {
    refetchZones();
    refetchAlerts();
    refetchVolunteers();
    refetchShelters();
    refetchStatus();
  }, [refetchZones, refetchAlerts, refetchVolunteers, refetchShelters, refetchStatus]);

  const handleAlertClick = useCallback((alert: Alert) => {
    setEmergencyAlert(alert);
  }, []);

  const handleDismissEmergency = useCallback(() => {
    setEmergencyAlert(null);
  }, []);

  const recentAlertCount = alerts.filter(
    (a) => new Date(a.timestamp) > new Date(Date.now() - 3600000)
  ).length;

  const renderPage = () => {
    switch (activePage) {
      case 'dashboard':
        return (
          <div className="space-y-5 animate-fade-in" id="dashboard-page">
            <MetricCards zones={zones} volunteers={volunteers} shelters={shelters} alerts={alerts} />
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
              <div className="lg:col-span-2 glass-panel p-1 h-[480px]">
                <Suspense fallback={<LoadingPanel />}>
                  <LiveMap zones={zones} shelters={shelters} volunteerCount={volunteers.length} />
                </Suspense>
              </div>
              <div className="glass-panel p-4 h-[480px]">
                <AlertFeed alerts={alerts} onAlertClick={handleAlertClick} />
              </div>
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
              <div className="lg:col-span-2 glass-panel p-4 h-[420px]">
                <Suspense fallback={<LoadingPanel />}>
                  <AgentLogsPanel agentLogs={agentLogs} alerts={alerts} detections={detections} />
                </Suspense>
              </div>
              <div className="glass-panel p-4 h-[420px]">
                <Suspense fallback={<LoadingPanel />}>
                  <BroadcastStatus alerts={alerts} acknowledgments={acknowledgments} />
                </Suspense>
              </div>
            </div>
          </div>
        );
      case 'map':
        return (
          <div className="h-[calc(100vh-4rem)] animate-fade-in">
            <div className="glass-panel p-1 h-full">
              <Suspense fallback={<LoadingPanel />}>
                <LiveMap zones={zones} shelters={shelters} volunteerCount={volunteers.length} />
              </Suspense>
            </div>
          </div>
        );
      case 'alerts':
        return (
          <div className="h-[calc(100vh-4rem)] animate-fade-in">
            <div className="glass-panel p-5 h-full">
              <AlertFeed alerts={alerts} onAlertClick={handleAlertClick} maxItems={100} />
            </div>
          </div>
        );
      case 'agents':
        return (
          <div className="h-[calc(100vh-4rem)] animate-fade-in">
            <div className="glass-panel p-5 h-full">
              <Suspense fallback={<LoadingPanel />}>
                <AgentLogsPanel agentLogs={agentLogs} alerts={alerts} detections={detections} />
              </Suspense>
            </div>
          </div>
        );
      case 'broadcast':
        return (
          <div className="h-[calc(100vh-4rem)] animate-fade-in">
            <div className="glass-panel p-5 h-full">
              <Suspense fallback={<LoadingPanel />}>
                <BroadcastStatus alerts={alerts} acknowledgments={acknowledgments} />
              </Suspense>
            </div>
          </div>
        );
      case 'mqtt':
        return (
          <div className="h-[calc(100vh-4rem)] animate-fade-in">
            <div className="glass-panel p-5 h-full">
              <Suspense fallback={<LoadingPanel />}>
                <MqttClientPanel />
              </Suspense>
            </div>
          </div>
        );
      case 'graph':
        return (
          <div className="h-[calc(100vh-4rem)] animate-fade-in">
            <div className="glass-panel p-1 h-full">
              <Suspense fallback={<LoadingPanel />}>
                <AgentGraph alerts={alerts} detections={detections} />
              </Suspense>
            </div>
          </div>
        );
      case 'yolo':
        return (
          <div className="animate-fade-in">
            <Suspense fallback={<LoadingPanel />}>
              <YoloFeed zones={zones} detections={detections} />
            </Suspense>
          </div>
        );
      case 'analytics':
        return (
          <div className="animate-fade-in">
            <Suspense fallback={<LoadingPanel />}>
              <AnalyticsTab 
                zones={zones} 
                alerts={alerts} 
                volunteers={volunteers} 
                shelters={shelters} 
                detections={detections} 
              />
            </Suspense>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="flex min-h-screen bg-surface-950">
      <Sidebar
        activePage={activePage}
        onNavigate={setActivePage}
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed((p) => !p)}
        alertCount={recentAlertCount}
      />

      <div className="flex-1 flex flex-col min-h-screen overflow-hidden">
        <Header
          systemStatus={systemStatus}
          statusLoading={statusLoading}
          statusError={statusError}
          alertCount={recentAlertCount}
          onRefresh={handleRefresh}
        />

        <main className="flex-1 p-5 overflow-y-auto">{renderPage()}</main>
      </div>

      <EmergencyAlert alert={emergencyAlert} onDismiss={handleDismissEmergency} />
    </div>
  );
}
