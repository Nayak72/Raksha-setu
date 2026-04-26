/**
 * Supabase client singleton with Realtime enabled.
 */
import { createClient } from '@supabase/supabase-js';

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL || 'https://wcaggixrdosfkewalokc.supabase.co';
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY || 'sb_publishable_8iOCeF-OD1WsT9ki-iS64Q_Moy91e4U';

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
  realtime: {
    params: {
      eventsPerSecond: 10,
    },
  },
});

export type Zone = {
  id: string;
  lat: number;
  lon: number;
  risk_score: number;
  created_at: string;
};

export type Volunteer = {
  id: string;
  location: string;
  status: string;
  skill_level: number;
  last_assigned_at: string | null;
  created_at: string;
};

export type Shelter = {
  id: string;
  location: string;
  capacity: number;
  available_beds: number;
  created_at: string;
};

export type Alert = {
  id: string;
  zone: string;
  message: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  timestamp: string;
};

export type Detection = {
  id: string;
  zone_id: string;
  count: number;
  timestamp: string;
};

export type Acknowledgment = {
  id: string;
  device_id: string;
  alert_id: string;
  status: string;
  timestamp: string;
};

export type AgentLog = {
  id: string;
  zone_id: string | null;
  timestamp: string;
  agent_name: string;
  decision: string;
  reasoning_steps: any;
  tools_used: any[];
  routing_decision: string;
  confidence: number;
};
