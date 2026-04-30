/**
 * App Shell — Client component that wraps all dashboard pages with
 * sidebar + header + data providers.
 * Emergency alert overlay removed per CHANGE 3 (alert system removal).
 */
'use client';

import { useState, useCallback } from 'react';
import Sidebar from '../components/ui/Sidebar';
import Header from '../components/ui/Header';
import {
  useZones, useAlerts, useVolunteers, useShelters,
  useDetections, useAcknowledgments, useSystemStatus, useAgentLogs,
} from '../hooks/useSupabaseRealtime';

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

  const zonesData = useZones();
  const alertsData = useAlerts();
  const volunteersData = useVolunteers();
  const sheltersData = useShelters();
  const detectionsData = useDetections();
  const acksData = useAcknowledgments();
  const agentLogsData = useAgentLogs();
  const systemStatusData = useSystemStatus();

  const handleRefresh = useCallback(() => {
    zonesData.refetch();
    alertsData.refetch();
    volunteersData.refetch();
    sheltersData.refetch();
    systemStatusData.refetch();
  }, [zonesData, alertsData, volunteersData, sheltersData, systemStatusData]);

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
          alertCount={0}
        />
        <div className="flex-1 flex flex-col min-h-screen overflow-hidden">
          <Header
            systemStatus={systemStatusData.status}
            statusLoading={systemStatusData.loading}
            statusError={systemStatusData.error}
            alertCount={0}
            onRefresh={handleRefresh}
          />
          <main className="flex-1 p-5 overflow-y-auto">{children}</main>
        </div>
      </div>
    </RealtimeContext.Provider>
  );
}
