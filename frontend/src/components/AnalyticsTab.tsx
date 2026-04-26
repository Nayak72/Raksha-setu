import { useState, useEffect, useCallback } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip as RechartsTooltip,
  ResponsiveContainer, CartesianGrid, AreaChart, Area,
  Cell, LineChart, Line, Legend
} from 'recharts';
import { Activity, Users, Shield, TrendingUp, AlertTriangle, Eye, Zap, RefreshCw } from 'lucide-react';
import type { Zone, Alert, Volunteer, Shelter, Detection } from '../lib/supabase';

// ── Simulation helpers ──────────────────────────────────────────
const REFRESH_INTERVAL = 12_000; // 12 seconds

function randomInt(min: number, max: number) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function generateAlertTrend() {
  const now = new Date();
  return Array.from({ length: 24 }).map((_, i) => {
    const hour = new Date(now);
    hour.setHours(now.getHours() - (23 - i));
    return {
      time: `${hour.getHours().toString().padStart(2, '0')}:00`,
      critical: randomInt(0, 4),
      high: randomInt(1, 7),
      medium: randomInt(2, 10),
      low: randomInt(1, 5),
    };
  });
}

function generateZoneRisk(zoneCount: number) {
  const colors = ['#ff6464', '#ffbd20', '#3bce7f', '#ff9e9e', '#17b363'];
  return Array.from({ length: Math.max(zoneCount, 5) }).map((_, i) => {
    const risk = randomInt(15, 95);
    return {
      name: `Zone ${i + 1}`,
      risk,
      color: risk > 75 ? '#ff6464' : risk > 45 ? '#ffbd20' : '#3bce7f',
    };
  }).sort((a, b) => b.risk - a.risk);
}

function generateVolunteerData() {
  return ['Zone 1', 'Zone 2', 'Zone 3', 'Zone 4', 'Zone 5'].map(zone => ({
    zone,
    deployed: randomInt(8, 30),
    available: randomInt(3, 20),
    enroute: randomInt(1, 8),
  }));
}

function generateShelterData() {
  return ['Shelter A', 'Shelter B', 'Shelter C', 'Shelter D', 'Shelter E'].map(name => {
    const capacity = randomInt(100, 350);
    const occupied = randomInt(30, capacity);
    return { name, capacity, occupied, available: capacity - occupied };
  });
}

function generateDetectionTimeline() {
  const now = new Date();
  return Array.from({ length: 12 }).map((_, i) => {
    const t = new Date(now);
    t.setSeconds(now.getSeconds() - (11 - i) * 12);
    return {
      time: `${t.getHours().toString().padStart(2, '0')}:${t.getMinutes().toString().padStart(2, '0')}:${t.getSeconds().toString().padStart(2, '0')}`,
      persons: randomInt(10, 45),
      vehicles: randomInt(2, 15),
    };
  });
}

// ── Animated Counter ────────────────────────────────────────────
function AnimatedCounter({ value, duration = 1200 }: { value: number; duration?: number }) {
  const [display, setDisplay] = useState(0);

  useEffect(() => {
    let start = 0;
    const step = Math.ceil(value / (duration / 16)) || 1;
    const timer = setInterval(() => {
      start += step;
      if (start >= value) {
        setDisplay(value);
        clearInterval(timer);
      } else {
        setDisplay(start);
      }
    }, 16);
    return () => clearInterval(timer);
  }, [value, duration]);

  return <span>{display.toLocaleString()}</span>;
}

// ── Stat Card ───────────────────────────────────────────────────
function StatCard({ icon: Icon, label, value, color, subtext }: {
  icon: React.ElementType;
  label: string;
  value: number;
  color: string;
  subtext?: string;
}) {
  return (
    <div className="glass-panel p-5 flex items-start gap-4 group hover:border-raksha-500/30 transition-all duration-300">
      <div
        className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0"
        style={{ background: `${color}18`, border: `1px solid ${color}30` }}
      >
        <Icon size={22} style={{ color }} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs text-surface-400 font-medium uppercase tracking-wider">{label}</p>
        <p className="text-2xl font-bold text-surface-50 mt-0.5">
          <AnimatedCounter value={value} />
        </p>
        {subtext && <p className="text-[11px] text-surface-500 mt-0.5">{subtext}</p>}
      </div>
    </div>
  );
}

// ── Tooltip Style ───────────────────────────────────────────────
const darkTooltipStyle = {
  backgroundColor: '#0f172a',
  borderColor: '#334155',
  borderRadius: '10px',
  boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
  fontSize: '12px',
};

// ── Props ───────────────────────────────────────────────────────
interface AnalyticsTabProps {
  zones: Zone[];
  alerts: Alert[];
  volunteers: Volunteer[];
  shelters: Shelter[];
  detections: Detection[];
}

// ── Main Component ──────────────────────────────────────────────
export default function AnalyticsTab({ zones, alerts, volunteers, shelters, detections }: AnalyticsTabProps) {
  const [tick, setTick] = useState(0);
  const [countdown, setCountdown] = useState(REFRESH_INTERVAL / 1000);

  // Simulation data state – regenerated every 12 seconds
  const [alertTrend, setAlertTrend] = useState(generateAlertTrend);
  const [zoneRisk, setZoneRisk] = useState(() => generateZoneRisk(zones.length || 5));
  const [volunteerData, setVolunteerData] = useState(generateVolunteerData);
  const [shelterData, setShelterData] = useState(generateShelterData);
  const [detectionTimeline, setDetectionTimeline] = useState(generateDetectionTimeline);

  // Refresh all simulation data
  const refreshAll = useCallback(() => {
    setAlertTrend(generateAlertTrend());
    setZoneRisk(generateZoneRisk(zones.length || 5));
    setVolunteerData(generateVolunteerData());
    setShelterData(generateShelterData());
    setDetectionTimeline(generateDetectionTimeline());
    setTick(t => t + 1);
    setCountdown(REFRESH_INTERVAL / 1000);
  }, [zones.length]);

  // Main 12-second refresh cycle
  useEffect(() => {
    const interval = setInterval(refreshAll, REFRESH_INTERVAL);
    return () => clearInterval(interval);
  }, [refreshAll]);

  // Visual countdown timer
  useEffect(() => {
    const timer = setInterval(() => {
      setCountdown(c => (c <= 1 ? REFRESH_INTERVAL / 1000 : c - 1));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Merge real data when available
  const totalAlerts = alerts.length > 0 ? alerts.length : alertTrend.reduce((s, h) => s + h.critical + h.high + h.medium + h.low, 0);
  const totalDeployed = volunteers.length > 0
    ? volunteers.filter(v => v.status === 'deployed' || v.status === 'dispatched').length
    : volunteerData.reduce((s, v) => s + v.deployed, 0);
  const totalAvailableBeds = shelters.length > 0
    ? shelters.reduce((s, sh) => s + (sh.available_beds || 0), 0)
    : shelterData.reduce((s, sh) => s + sh.available, 0);
  const totalDetections = detections.length > 0
    ? detections.reduce((s, d) => s + (d.count || 0), 0)
    : detectionTimeline.reduce((s, d) => s + d.persons + d.vehicles, 0);

  return (
    <div className="space-y-6" id="analytics-page">
      {/* Header */}
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

        {/* Countdown + Refresh */}
        <div className="flex items-center gap-3">
          <button
            onClick={refreshAll}
            className="glass-panel px-3 py-1.5 flex items-center gap-2 hover:border-raksha-500/40 transition-all text-xs"
          >
            <RefreshCw className="w-3.5 h-3.5 text-raksha-400" />
            <span className="text-surface-300">Refresh</span>
          </button>
          <div className="glass-panel px-3 py-1.5 flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-safe-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-safe-500" />
            </span>
            <span className="text-xs font-mono text-surface-300">
              Next update: <span className="text-safe-400 font-bold">{countdown}s</span>
            </span>
          </div>
        </div>
      </div>

      {/* Stat Cards Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard icon={AlertTriangle} label="Total Alerts (24h)" value={totalAlerts} color="#ff6464" subtext="Across all zones" />
        <StatCard icon={Users} label="Deployed Volunteers" value={totalDeployed} color="#3d84ff" subtext="Active in field" />
        <StatCard icon={Shield} label="Available Beds" value={totalAvailableBeds} color="#3bce7f" subtext="Across all shelters" />
        <StatCard icon={Eye} label="Detections (1h)" value={totalDetections} color="#ffbd20" subtext="Persons & vehicles" />
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Alert Trend – 24h Stacked Area */}
        <div className="glass-panel p-5 lg:col-span-2">
          <h3 className="text-base font-semibold text-surface-200 mb-4 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-danger-400" />
            Alert Trend (24-Hour)
            <span className="ml-auto text-[10px] text-surface-500 font-mono">Auto-refresh {REFRESH_INTERVAL / 1000}s</span>
          </h3>
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={alertTrend} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="gradCritical" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ff2d2d" stopOpacity={0.35} />
                    <stop offset="95%" stopColor="#ff2d2d" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="gradHigh" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ff9e9e" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#ff9e9e" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="gradMedium" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ffbd20" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#ffbd20" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="gradLow" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3bce7f" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="#3bce7f" stopOpacity={0} />
                  </linearGradient>
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

        {/* Zone Risk Distribution */}
        <div className="glass-panel p-5">
          <h3 className="text-base font-semibold text-surface-200 mb-4 flex items-center gap-2">
            <Zap className="w-4 h-4 text-warning-400" />
            Zone Risk Levels
          </h3>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={zoneRisk} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                <XAxis dataKey="name" stroke="#64748b" fontSize={11} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} domain={[0, 100]} />
                <RechartsTooltip contentStyle={darkTooltipStyle} formatter={(val: any) => [`${val}%`, 'Risk Score']} />
                <Bar dataKey="risk" radius={[6, 6, 0, 0]} name="Risk Score">
                  {zoneRisk.map((entry, i) => (
                    <Cell key={i} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Volunteer Deployment */}
        <div className="glass-panel p-5">
          <h3 className="text-base font-semibold text-surface-200 mb-4 flex items-center gap-2">
            <Users className="w-4 h-4 text-raksha-400" />
            Volunteer Deployment by Zone
          </h3>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={volunteerData} layout="vertical" margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
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
          <h3 className="text-base font-semibold text-surface-200 mb-4 flex items-center gap-2">
            <Shield className="w-4 h-4 text-safe-400" />
            Shelter Capacity
          </h3>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={shelterData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
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
          <h3 className="text-base font-semibold text-surface-200 mb-4 flex items-center gap-2">
            <Eye className="w-4 h-4 text-raksha-300" />
            YOLO Detection Timeline
          </h3>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={detectionTimeline} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
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
