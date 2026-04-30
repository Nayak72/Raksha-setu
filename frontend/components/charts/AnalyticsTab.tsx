/**
 * Analytics Tab — real-time charts with Recharts.
 */
'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip as RechartsTooltip,
  ResponsiveContainer, CartesianGrid, AreaChart, Area,
  Cell, LineChart, Line, Legend,
} from 'recharts';
import { Activity, Users, Shield, TrendingUp, AlertTriangle, Eye, Zap, RefreshCw } from 'lucide-react';
import type { Zone, Alert, Volunteer, Shelter, Detection } from '../../lib/supabase';
import type { SimulationState } from '../../hooks/useSimulation';
import { fetchSheltersNear, type SimShelter } from '../../lib/simulation-api';

const REFRESH_INTERVAL = 5_000;

function randomInt(min: number, max: number) { return Math.floor(Math.random() * (max - min + 1)) + min; }

function generateAlertTrend() {
  const now = new Date();
  return Array.from({ length: 24 }).map((_, i) => {
    const hour = new Date(now); hour.setHours(now.getHours() - (23 - i));
    return { time: `${hour.getHours().toString().padStart(2, '0')}:00`, critical: randomInt(0, 4), high: randomInt(1, 7), medium: randomInt(2, 10), low: randomInt(1, 5) };
  });
}

const ZONE_SHORT_NAMES = [
  'Mangalore', 'Udupi', 'Karwar', 'Chikkamagaluru', 'DK-Puttur', 'Ankola', 'Sringeri',
];

function generateZoneRisk(zoneCount: number) {
  return Array.from({ length: Math.max(zoneCount, 7) }).map((_, i) => {
    const risk = randomInt(15, 95);
    return { name: ZONE_SHORT_NAMES[i] || `Zone ${i + 1}`, risk, color: risk > 75 ? '#ff6464' : risk > 45 ? '#ffbd20' : '#3bce7f' };
  }).sort((a, b) => b.risk - a.risk);
}

function generateVolunteerData() {
  return ZONE_SHORT_NAMES.map(zone => ({ zone, deployed: randomInt(8, 30), available: randomInt(3, 20), enroute: randomInt(1, 8) }));
}

const SHELTER_SHORT_NAMES = [
  'Mangalore TH', 'Udupi TH', 'Karwar Stadium', 'Mudigere GC', 'Puttur TH', 'Ankola HS', 'Sringeri CH',
];

function generateShelterData() {
  return SHELTER_SHORT_NAMES.map(name => {
    const capacity = randomInt(100, 350); const occupied = randomInt(30, capacity);
    return { name, capacity, occupied, available: capacity - occupied };
  });
}

function generateDetectionTimeline() {
  const now = new Date();
  return Array.from({ length: 12 }).map((_, i) => {
    const t = new Date(now); t.setSeconds(now.getSeconds() - (11 - i) * 5);
    return { time: `${t.getHours().toString().padStart(2, '0')}:${t.getMinutes().toString().padStart(2, '0')}:${t.getSeconds().toString().padStart(2, '0')}`, persons: randomInt(10, 45), vehicles: randomInt(2, 15) };
  });
}

function AnimatedCounter({ value, duration = 1200 }: { value: number; duration?: number }) {
  const [display, setDisplay] = useState(0);
  useEffect(() => {
    let start = 0; const step = Math.ceil(value / (duration / 16)) || 1;
    const timer = setInterval(() => { start += step; if (start >= value) { setDisplay(value); clearInterval(timer); } else { setDisplay(start); } }, 16);
    return () => clearInterval(timer);
  }, [value, duration]);
  return <span>{display.toLocaleString()}</span>;
}

function StatCard({ icon: Icon, label, value, color, subtext }: { icon: React.ElementType; label: string; value: number; color: string; subtext?: string }) {
  return (
    <div className="glass-panel p-5 flex items-start gap-4 group hover:border-raksha-500/30 transition-all duration-300">
      <div className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0" style={{ background: `${color}18`, border: `1px solid ${color}30` }}>
        <Icon size={22} style={{ color }} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs text-surface-400 font-medium uppercase tracking-wider">{label}</p>
        <p className="text-2xl font-bold text-surface-50 mt-0.5"><AnimatedCounter value={value} /></p>
        {subtext && <p className="text-[11px] text-surface-500 mt-0.5">{subtext}</p>}
      </div>
    </div>
  );
}

const darkTooltipStyle = { backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '10px', boxShadow: '0 8px 32px rgba(0,0,0,0.4)', fontSize: '12px' };

interface AnalyticsTabProps { zones: Zone[]; alerts: Alert[]; volunteers: Volunteer[]; shelters: Shelter[]; detections: Detection[]; sim?: SimulationState; }

export default function AnalyticsTab({ zones, alerts, volunteers, shelters, detections, sim }: AnalyticsTabProps) {
  const [tick, setTick] = useState(0);
  const [countdown, setCountdown] = useState(REFRESH_INTERVAL / 1000);
  const [alertTrend, setAlertTrend] = useState(generateAlertTrend);
  const [zoneRisk, setZoneRisk] = useState(() => generateZoneRisk(zones.length || 7));
  const [volunteerData, setVolunteerData] = useState(generateVolunteerData);
  const [shelterData, setShelterData] = useState(generateShelterData);
  const [detectionTimeline, setDetectionTimeline] = useState(generateDetectionTimeline);

  const refreshAll = useCallback(() => {
    setAlertTrend(generateAlertTrend());
    setZoneRisk(generateZoneRisk(zones?.length || 7));
    setVolunteerData(generateVolunteerData());
    setShelterData(generateShelterData());
    setDetectionTimeline(generateDetectionTimeline());
    setTick(t => t + 1); 
    setCountdown(REFRESH_INTERVAL / 1000);
  }, [zones?.length]);

  useEffect(() => { const interval = setInterval(refreshAll, REFRESH_INTERVAL); return () => clearInterval(interval); }, [refreshAll]);
  useEffect(() => { const timer = setInterval(() => { setCountdown(c => (c <= 1 ? REFRESH_INTERVAL / 1000 : c - 1)); }, 1000); return () => clearInterval(timer); }, []);

  // Fetch sim shelters if simulation is active
  const [simSheltersMap, setSimSheltersMap] = useState<Record<string, SimShelter[]>>({});
  
  useEffect(() => {
    if (!sim?.zones || sim.zones.length === 0) return;
    const fetchAllShelters = async () => {
      const map: Record<string, SimShelter[]> = {};
      for (const zone of sim.zones) {
        try {
          const res = await fetchSheltersNear(zone.id);
          map[zone.id] = res;
        } catch (e) {}
      }
      setSimSheltersMap(map);
    };
    fetchAllShelters();
  }, [sim?.zones]);

  const allSimShelters = useMemo(() => Object.values(simSheltersMap).flat(), [simSheltersMap]);
  const uniqueSimShelters = useMemo(() => Array.from(new Map(allSimShelters.map(s => [s.shelter_id, s])).values()), [allSimShelters]);

  // Derive charts from real data (fallback to generated only if completely empty for visual demo)
  const chartZoneRisk = (sim?.zones && sim.zones.length > 0)
    ? sim.zones.map((z, i) => {
        const jitter = Math.sin(tick + i) * 3; // ±3% oscillation for dynamic feel
        const risk = Math.max(0, Math.min(100, (z.damage_level * 100) + jitter));
        return { name: z.name?.split(' ')[0] || `Z-${z.id.substring(0,4)}`, risk, color: risk > 75 ? '#ff6464' : risk > 45 ? '#ffbd20' : '#3bce7f' };
      }).sort((a, b) => b.risk - a.risk)
    : zones.length > 0 
      ? zones.map((z, i) => {
          const jitter = Math.sin(tick + i) * 3;
          const risk = Math.max(0, Math.min(100, (z.risk_score || 0) + jitter));
          return { name: z.name?.split(' ')[0] || `Z-${z.id.substring(0,4)}`, risk, color: risk > 75 ? '#ff6464' : risk > 45 ? '#ffbd20' : '#3bce7f' };
        }).sort((a, b) => b.risk - a.risk)
      : zoneRisk;

  const chartVolunteerData = (sim?.zones && sim.zones.length > 0)
    ? sim.zones.map((z, i) => {
        const zVols = volunteers.filter(v => v.location === z.name || v.location?.includes(z.name || ''));
        const activeMod = Math.round(Math.sin(tick + i) * 2);
        return {
          zone: z.name?.split(' ')[0] || `Z-${z.id.substring(0,4)}`,
          deployed: Math.max(0, zVols.filter(v => v.status === 'deployed').length + activeMod),
          enroute: Math.max(0, zVols.filter(v => v.status === 'dispatched' || v.status === 'en_route').length - activeMod),
          available: zVols.filter(v => v.status === 'available' || v.status === 'idle').length,
        };
      })
    : zones.length > 0
      ? zones.map((z, i) => {
          const zVols = volunteers.filter(v => v.location === z.name || v.location?.includes(z.name || ''));
          const activeMod = Math.round(Math.sin(tick + i) * 2);
          return {
            zone: z.name?.split(' ')[0] || `Z-${z.id.substring(0,4)}`,
            deployed: Math.max(0, zVols.filter(v => v.status === 'deployed').length + activeMod),
            enroute: Math.max(0, zVols.filter(v => v.status === 'dispatched' || v.status === 'en_route').length - activeMod),
            available: zVols.filter(v => v.status === 'available' || v.status === 'idle').length,
          };
        })
      : volunteerData;

  const chartShelterData = uniqueSimShelters.length > 0
    ? uniqueSimShelters.map((s, i) => {
        const jitter = Math.round(Math.sin(tick + i) * (s.capacity * 0.05)); // ±5% jitter
        const occupied = Math.max(0, Math.min(s.capacity, s.capacity - s.available_capacity + jitter));
        return {
          name: s.name?.split(' ')[0] || `S-${s.shelter_id.substring(0,4)}`,
          capacity: s.capacity,
          occupied,
          available: s.capacity - occupied
        }
      })
    : shelters.length > 0
      ? shelters.map((s, i) => {
          const jitter = Math.round(Math.sin(tick + i) * (s.capacity * 0.05));
          const occupied = Math.max(0, Math.min(s.capacity, s.capacity - (s.available_beds || 0) + jitter));
          return {
            name: s.location?.split(' ')[0] || `S-${s.id.substring(0,4)}`,
            capacity: s.capacity,
            occupied,
            available: s.capacity - occupied
          }
        })
      : shelterData;

  const chartAlertTrend = alerts.length > 0
    ? (() => {
        // Group alerts by hour simply
        const hours: Record<string, any> = {};
        alerts.forEach(a => {
          const t = new Date(a.timestamp);
          const h = `${t.getHours().toString().padStart(2, '0')}:00`;
          if (!hours[h]) hours[h] = { time: h, critical: 0, high: 0, medium: 0, low: 0 };
          if (a.severity in hours[h]) hours[h][a.severity]++;
          else hours[h].critical++; // fallback
        });
        const res = Object.values(hours).sort((a,b) => a.time.localeCompare(b.time));
        return res.length > 0 ? res : alertTrend;
      })()
    : alertTrend;

  const chartDetectionTimeline = detections.length > 0
    ? detections.map(d => {
        const t = new Date(d.timestamp);
        return {
          time: `${t.getHours().toString().padStart(2, '0')}:${t.getMinutes().toString().padStart(2, '0')}`,
          persons: d.count || 0,
          vehicles: 0
        };
      }).slice(-12)
    : detectionTimeline;

  // Compute stats consistently from the chart data (so fallback mock data is also counted if real data is empty)
  const simTotalAlerts = sim?.zones?.reduce((s, z) => s + (z.alert_count || 0), 0) || 0;
  
  const totalAlerts = (sim?.zones && sim.zones.length > 0)
    ? simTotalAlerts
    : alerts.length > 0 
      ? alerts.length 
      : chartAlertTrend.reduce((s, a) => s + (a.critical || 0) + (a.high || 0) + (a.medium || 0) + (a.low || 0), 0);

  const totalDeployed = volunteers.length > 0
    ? volunteers.filter(v => v.status === 'deployed' || v.status === 'dispatched').length
    : chartVolunteerData.reduce((s, v) => s + (v.deployed || 0) + (v.enroute || 0), 0);

  const totalAvailableBeds = uniqueSimShelters.length > 0 
    ? uniqueSimShelters.reduce((s, sh) => s + sh.available_capacity, 0)
    : shelters.length > 0
      ? shelters.reduce((s, sh) => s + (sh.available_beds || 0), 0)
      : chartShelterData.reduce((s, sh) => s + (sh.available || 0), 0);

  const totalDetections = detections.length > 0
    ? detections.reduce((s, d) => s + (d.count || 0), 0)
    : chartDetectionTimeline.reduce((s, d) => s + (d.persons || 0) + (d.vehicles || 0), 0);

  return (
    <div className="space-y-6" id="analytics-page">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-raksha-500/20 to-raksha-700/20 border border-raksha-500/30 flex items-center justify-center">
            <Activity className="w-5 h-5 text-raksha-400" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-surface-50">System Analytics</h2>
            <p className="text-xs text-surface-500">Live disaster response metrics · Tick #{tick}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={refreshAll} className="glass-panel px-3 py-1.5 flex items-center gap-2 hover:border-raksha-500/40 transition-all text-xs">
            <RefreshCw className="w-3.5 h-3.5 text-raksha-400" /><span className="text-surface-300">Refresh</span>
          </button>
          <div className="glass-panel px-3 py-1.5 flex items-center gap-2">
            <span className="relative flex h-2 w-2"><span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-safe-400 opacity-75" /><span className="relative inline-flex rounded-full h-2 w-2 bg-safe-500" /></span>
            <span className="text-xs font-mono text-surface-300">Next update: <span className="text-safe-400 font-bold">{countdown}s</span></span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard icon={AlertTriangle} label="Total Alerts (24h)" value={totalAlerts} color="#ff6464" subtext="Across all zones" />
        <StatCard icon={Users} label="Deployed Volunteers" value={totalDeployed} color="#3d84ff" subtext="Active in field" />
        <StatCard icon={Shield} label="Available Beds" value={totalAvailableBeds} color="#3bce7f" subtext="Across all shelters" />
        <StatCard icon={Eye} label="Detections (1h)" value={totalDetections} color="#ffbd20" subtext="Persons & vehicles" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Alert Trend – 24h Stacked Area */}
        <div className="glass-panel p-5 lg:col-span-2">
          <h3 className="text-base font-semibold text-surface-200 mb-4 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-danger-400" />Alert Trend (24-Hour)
            <span className="ml-auto text-[10px] text-surface-500 font-mono">Auto-refresh {REFRESH_INTERVAL / 1000}s</span>
          </h3>
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartAlertTrend} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="gradCritical" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#ff2d2d" stopOpacity={0.35} /><stop offset="95%" stopColor="#ff2d2d" stopOpacity={0} /></linearGradient>
                  <linearGradient id="gradHigh" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#ff9e9e" stopOpacity={0.3} /><stop offset="95%" stopColor="#ff9e9e" stopOpacity={0} /></linearGradient>
                  <linearGradient id="gradMedium" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#ffbd20" stopOpacity={0.25} /><stop offset="95%" stopColor="#ffbd20" stopOpacity={0} /></linearGradient>
                  <linearGradient id="gradLow" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#3bce7f" stopOpacity={0.2} /><stop offset="95%" stopColor="#3bce7f" stopOpacity={0} /></linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                <XAxis dataKey="time" stroke="#64748b" fontSize={11} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} />
                <RechartsTooltip contentStyle={darkTooltipStyle} />
                <Area type="monotone" dataKey="critical" stackId="1" stroke="#ff2d2d" fill="url(#gradCritical)" strokeWidth={2} name="Critical" />
                <Area type="monotone" dataKey="high" stackId="1" stroke="#ff9e9e" fill="url(#gradHigh)" strokeWidth={1.5} name="High" />
                <Area type="monotone" dataKey="medium" stackId="1" stroke="#ffbd20" fill="url(#gradMedium)" strokeWidth={1.5} name="Medium" />
                <Area type="monotone" dataKey="low" stackId="1" stroke="#3bce7f" fill="url(#gradLow)" strokeWidth={1.5} name="Low" />
                <Legend verticalAlign="top" height={30} iconType="circle" wrapperStyle={{ fontSize: '11px' }} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Zone Risk */}
        <div className="glass-panel p-5">
          <h3 className="text-base font-semibold text-surface-200 mb-4 flex items-center gap-2"><Zap className="w-4 h-4 text-warning-400" />Zone Risk Levels</h3>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartZoneRisk} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                <XAxis dataKey="name" stroke="#64748b" fontSize={11} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} domain={[0, 100]} />
                <RechartsTooltip contentStyle={darkTooltipStyle} formatter={(val) => [`${val}%`, 'Risk Score']} />
                <Bar dataKey="risk" radius={[6, 6, 0, 0]} name="Risk Score">{chartZoneRisk.map((entry, i) => (<Cell key={i} fill={entry.color} />))}</Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Volunteer Deployment */}
        <div className="glass-panel p-5">
          <h3 className="text-base font-semibold text-surface-200 mb-4 flex items-center gap-2"><Users className="w-4 h-4 text-raksha-400" />Volunteer Deployment by Zone</h3>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartVolunteerData} layout="vertical" margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
                <XAxis type="number" stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} />
                <YAxis dataKey="zone" type="category" stroke="#64748b" fontSize={11} tickLine={false} width={55} />
                <RechartsTooltip contentStyle={darkTooltipStyle} />
                <Bar dataKey="deployed" stackId="v" fill="#3d84ff" radius={[0, 0, 0, 0]} name="Deployed" />
                <Bar dataKey="enroute" stackId="v" fill="#ffbd20" radius={[0, 0, 0, 0]} name="En Route" />
                <Bar dataKey="available" stackId="v" fill="#3bce7f" radius={[0, 4, 4, 0]} name="Available" />
                <Legend verticalAlign="top" height={28} iconType="circle" wrapperStyle={{ fontSize: '11px' }} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Shelter Capacity */}
        <div className="glass-panel p-5">
          <h3 className="text-base font-semibold text-surface-200 mb-4 flex items-center gap-2"><Shield className="w-4 h-4 text-safe-400" />Shelter Capacity</h3>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartShelterData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                <XAxis dataKey="name" stroke="#64748b" fontSize={11} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} />
                <RechartsTooltip contentStyle={darkTooltipStyle} />
                <Bar dataKey="occupied" stackId="s" fill="#ff9e9e" radius={[0, 0, 0, 0]} name="Occupied" />
                <Bar dataKey="available" stackId="s" fill="#3bce7f" radius={[4, 4, 0, 0]} name="Available" />
                <Legend verticalAlign="top" height={28} iconType="circle" wrapperStyle={{ fontSize: '11px' }} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Detection Timeline */}
        <div className="glass-panel p-5">
          <h3 className="text-base font-semibold text-surface-200 mb-4 flex items-center gap-2"><Eye className="w-4 h-4 text-raksha-300" />YOLO Detection Timeline</h3>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartDetectionTimeline} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                <XAxis dataKey="time" stroke="#64748b" fontSize={11} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} />
                <RechartsTooltip contentStyle={darkTooltipStyle} />
                <Line type="monotone" dataKey="persons" stroke="#3d84ff" strokeWidth={2} dot={false} name="Persons" />
                <Line type="monotone" dataKey="vehicles" stroke="#ff6464" strokeWidth={2} dot={false} name="Vehicles" />
                <Legend verticalAlign="top" height={28} iconType="circle" wrapperStyle={{ fontSize: '11px' }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
