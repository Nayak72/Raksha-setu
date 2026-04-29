/**
 * App Shell — Client component that wraps all dashboard pages with
 * sidebar + header + emergency alert overlay + data providers.
 * This is the equivalent of the old App.tsx.
 */
'use client';

import { useState, useCallback, useEffect } from 'react';
import Sidebar from '../components/ui/Sidebar';
import Header from '../components/ui/Header';
import EmergencyAlert from '../components/ui/EmergencyAlert';
import {
  useZones, useAlerts, useVolunteers, useShelters,
  useDetections, useAcknowledgments, useSystemStatus, useAgentLogs,
} from '../hooks/useSupabaseRealtime';
import { Alert } from '../lib/supabase';

/**
 * React Context to share realtime data across all pages
 * without prop-drilling.
 */
import { createContext, useContext } from 'react';

export type RealtimeData = {
  zones: ReturnType<typeof useZones>;
  alerts: ReturnType<typeof useAlerts>;
  volunteers: ReturnType<typeof useVolunteers>;
  shelters: ReturnType<typeof useShelters>;
  detections: ReturnType<typeof useDetections>;
  acknowledgments: ReturnType<typeof useAcknowledgments>;
  agentLogs: ReturnType<typeof useAgentLogs>;
  systemStatus: ReturnType<typeof useSystemStatus>;
};

export const RealtimeContext = createContext<RealtimeData | null>(null);

export function useRealtimeData() {
  const ctx = useContext(RealtimeContext);
  if (!ctx) throw new Error('useRealtimeData must be used within AppShell');
  return ctx;
}

export default function AppShell({ children }: { children: React.ReactNode }) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [emergencyAlert, setEmergencyAlert] = useState<Alert | null>(null);

  const zonesData = useZones();
  const alertsData = useAlerts();
  const volunteersData = useVolunteers();
  const sheltersData = useShelters();
  const detectionsData = useDetections();
  const acksData = useAcknowledgments();
  const agentLogsData = useAgentLogs();
  const systemStatusData = useSystemStatus();

  useEffect(() => {
    if (alertsData.latestAlert && (alertsData.latestAlert.severity === 'critical' || alertsData.latestAlert.severity === 'high')) {
      setEmergencyAlert(alertsData.latestAlert);
    }
  }, [alertsData.latestAlert]);

  const handleRefresh = useCallback(() => {
    zonesData.refetch();
    alertsData.refetch();
    volunteersData.refetch();
    sheltersData.refetch();
    systemStatusData.refetch();
  }, [zonesData, alertsData, volunteersData, sheltersData, systemStatusData]);

  const handleDismissEmergency = useCallback(() => {
    setEmergencyAlert(null);
  }, []);

  const recentAlertCount = alertsData.alerts.filter(
    (a) => new Date(a.timestamp) > new Date(Date.now() - 3600000)
  ).length;

  const realtimeValue: RealtimeData = {
    zones: zonesData,
    alerts: alertsData,
    volunteers: volunteersData,
    shelters: sheltersData,
    detections: detectionsData,
    acknowledgments: acksData,
    agentLogs: agentLogsData,
    systemStatus: systemStatusData,
  };

  return (
    <RealtimeContext.Provider value={realtimeValue}>
      <div className="flex min-h-screen bg-surface-950">
        <Sidebar
          collapsed={sidebarCollapsed}
          onToggle={() => setSidebarCollapsed((p) => !p)}
          alertCount={recentAlertCount}
        />
        <div className="flex-1 flex flex-col min-h-screen overflow-hidden">
          <Header
            systemStatus={systemStatusData.status}
            statusLoading={systemStatusData.loading}
            statusError={systemStatusData.error}
            alertCount={recentAlertCount}
            onRefresh={handleRefresh}
          />
          <main className="flex-1 p-5 overflow-y-auto">{children}</main>
        </div>
        <EmergencyAlert alert={emergencyAlert} onDismiss={handleDismissEmergency} />
      </div>
    </RealtimeContext.Provider>
  );
}
