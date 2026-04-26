/**
 * Sidebar navigation component.
 */
import { motion } from 'framer-motion';
import {
  LayoutDashboard,
  Map,
  Bell,
  Brain,
  Radio,
  Wifi,
  GitBranch,
  Shield,
  Activity,
  ChevronLeft,
  ChevronRight,
  Camera,
  PieChart
} from 'lucide-react';

export type NavPage =
  | 'dashboard'
  | 'map'
  | 'alerts'
  | 'agents'
  | 'broadcast'
  | 'mqtt'
  | 'graph'
  | 'analytics'
  | 'yolo';

interface SidebarProps {
  activePage: NavPage;
  onNavigate: (page: NavPage) => void;
  collapsed: boolean;
  onToggle: () => void;
  alertCount: number;
}

const navItems: { id: NavPage; label: string; icon: React.ElementType; group?: string }[] = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, group: 'Overview' },
  { id: 'analytics', label: 'Analytics', icon: PieChart, group: 'Overview' },
  { id: 'map', label: 'Live Map', icon: Map, group: 'Overview' },
  { id: 'yolo', label: 'Live YOLO', icon: Camera, group: 'Monitoring' },
  { id: 'alerts', label: 'Alerts', icon: Bell, group: 'Monitoring' },
  { id: 'agents', label: 'Agent Logs', icon: Brain, group: 'Monitoring' },
  { id: 'broadcast', label: 'Broadcast', icon: Radio, group: 'Monitoring' },
  { id: 'mqtt', label: 'MQTT Client', icon: Wifi, group: 'System' },
  { id: 'graph', label: 'Agent Graph', icon: GitBranch, group: 'System' },
];

export default function Sidebar({
  activePage,
  onNavigate,
  collapsed,
  onToggle,
  alertCount,
}: SidebarProps) {
  let lastGroup = '';

  return (
    <motion.aside
      initial={false}
      animate={{ width: collapsed ? 72 : 260 }}
      transition={{ duration: 0.25, ease: 'easeInOut' }}
      className="h-screen sticky top-0 flex flex-col bg-surface-900/80 backdrop-blur-xl border-r border-surface-700/50 z-40"
      id="sidebar"
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 h-16 border-b border-surface-700/50">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-raksha-500 to-raksha-700 flex items-center justify-center flex-shrink-0">
          <Shield size={18} className="text-white" />
        </div>
        {!collapsed && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="overflow-hidden"
          >
            <h1 className="text-sm font-black tracking-tight gradient-text whitespace-nowrap">
              RakshaSethu
            </h1>
            <p className="text-[9px] text-surface-500 font-medium tracking-wider uppercase">
              Disaster Command
            </p>
          </motion.div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 overflow-y-auto space-y-1">
        {navItems.map((item) => {
          const showGroupLabel = item.group && item.group !== lastGroup;
          if (item.group) lastGroup = item.group;
          const Icon = item.icon;
          const isActive = activePage === item.id;

          return (
            <div key={item.id}>
              {showGroupLabel && !collapsed && (
                <div className="text-[9px] font-bold uppercase tracking-[0.15em] text-surface-600 px-3 pt-4 pb-1.5">
                  {item.group}
                </div>
              )}
              <button
                onClick={() => onNavigate(item.id)}
                className={`w-full ${isActive ? 'nav-link-active' : 'nav-link'} ${
                  collapsed ? 'justify-center px-0' : ''
                }`}
                title={collapsed ? item.label : undefined}
                id={`nav-${item.id}`}
              >
                <div className="relative">
                  <Icon size={18} />
                  {item.id === 'alerts' && alertCount > 0 && (
                    <span className="absolute -top-1.5 -right-1.5 w-4 h-4 rounded-full bg-danger-500 text-[8px] font-bold text-white flex items-center justify-center animate-pulse">
                      {alertCount > 9 ? '9+' : alertCount}
                    </span>
                  )}
                </div>
                {!collapsed && (
                  <span className="text-sm font-medium whitespace-nowrap">{item.label}</span>
                )}
              </button>
            </div>
          );
        })}
      </nav>

      {/* System status */}
      <div className="px-3 pb-3 border-t border-surface-700/50 pt-3">
        <div
          className={`flex items-center ${
            collapsed ? 'justify-center' : 'gap-2 px-3'
          } py-2 rounded-lg bg-surface-800/40`}
        >
          <Activity size={14} className="text-safe-500 animate-pulse" />
          {!collapsed && (
            <span className="text-[10px] text-surface-400 font-medium">System Active</span>
          )}
        </div>
      </div>

      {/* Collapse toggle */}
      <button
        onClick={onToggle}
        className="flex items-center justify-center h-10 border-t border-surface-700/50 text-surface-500 hover:text-white hover:bg-surface-800/40 transition-colors"
        id="sidebar-toggle"
      >
        {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
      </button>
    </motion.aside>
  );
}
