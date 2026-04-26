/**
 * Metric cards row for the dashboard overview.
 */
import { motion } from 'framer-motion';
import {
  MapPin,
  Users,
  Home,
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  Minus,
} from 'lucide-react';
import { Zone, Volunteer, Shelter, Alert } from '../lib/supabase';

interface MetricCardsProps {
  zones: Zone[];
  volunteers: Volunteer[];
  shelters: Shelter[];
  alerts: Alert[];
}

export default function MetricCards({ zones, volunteers, shelters, alerts }: MetricCardsProps) {
  const criticalZones = zones.filter((z) => z.risk_score >= 60).length;
  const avgRisk = zones.length > 0
    ? zones.reduce((sum, z) => sum + z.risk_score, 0) / zones.length
    : 0;
  const activeVolunteers = volunteers.filter((v) => v.status === 'available').length;
  const totalBeds = shelters.reduce((sum, s) => sum + s.available_beds, 0);
  const recentAlerts = alerts.filter(
    (a) => new Date(a.timestamp) > new Date(Date.now() - 3600000)
  ).length;

  const metrics = [
    {
      label: 'Active Zones',
      value: zones.length,
      subValue: `${criticalZones} critical`,
      icon: MapPin,
      color: 'text-raksha-400',
      bgColor: 'from-raksha-500/10 to-raksha-500/5',
      borderColor: 'border-raksha-500/20',
      trend: criticalZones > 0 ? 'up' : 'neutral',
    },
    {
      label: 'Volunteers',
      value: volunteers.length,
      subValue: `${activeVolunteers} available`,
      icon: Users,
      color: 'text-safe-400',
      bgColor: 'from-safe-500/10 to-safe-500/5',
      borderColor: 'border-safe-500/20',
      trend: activeVolunteers > volunteers.length * 0.5 ? 'up' : 'down',
    },
    {
      label: 'Shelter Beds',
      value: totalBeds,
      subValue: `${shelters.length} shelters`,
      icon: Home,
      color: 'text-warning-400',
      bgColor: 'from-warning-500/10 to-warning-500/5',
      borderColor: 'border-warning-500/20',
      trend: totalBeds > 50 ? 'up' : 'neutral',
    },
    {
      label: 'Active Alerts',
      value: recentAlerts,
      subValue: `Avg risk: ${avgRisk.toFixed(1)}`,
      icon: AlertTriangle,
      color: recentAlerts > 0 ? 'text-danger-400' : 'text-surface-400',
      bgColor: recentAlerts > 0 ? 'from-danger-500/10 to-danger-500/5' : 'from-surface-500/10 to-surface-500/5',
      borderColor: recentAlerts > 0 ? 'border-danger-500/20' : 'border-surface-500/20',
      trend: recentAlerts > 5 ? 'up' : recentAlerts > 0 ? 'neutral' : 'down',
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {metrics.map((metric, i) => {
        const Icon = metric.icon;
        const TrendIcon =
          metric.trend === 'up' ? TrendingUp : metric.trend === 'down' ? TrendingDown : Minus;

        return (
          <motion.div
            key={metric.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            className={`metric-card bg-gradient-to-br ${metric.bgColor} ${metric.borderColor}`}
          >
            <div className="flex items-start justify-between mb-3">
              <div className={`p-2 rounded-xl bg-surface-800/40 ${metric.color}`}>
                <Icon size={18} />
              </div>
              <div className="flex items-center gap-1">
                <TrendIcon
                  size={12}
                  className={
                    metric.trend === 'up'
                      ? metric.label === 'Active Alerts'
                        ? 'text-danger-400'
                        : 'text-safe-400'
                      : metric.trend === 'down'
                      ? 'text-danger-400'
                      : 'text-surface-500'
                  }
                />
              </div>
            </div>

            <div className="text-2xl font-black text-white mb-0.5">{metric.value}</div>
            <div className="text-xs text-surface-400 font-medium">{metric.label}</div>
            <div className="text-[10px] text-surface-500 mt-1">{metric.subValue}</div>
          </motion.div>
        );
      })}
    </div>
  );
}
