/**
 * Sidebar navigation component — "use client" for Next.js App Router.
 * Uses Link + usePathname for route-based navigation.
 */
'use client';

import { motion } from 'framer-motion';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Map,
  Brain,
  Radio,
  Wifi,
  GitBranch,
  Shield,
  Activity,
  ChevronLeft,
  ChevronRight,
  Camera,
  PieChart,
  Home,
  Users,
  Route,
  Package,
} from 'lucide-react';

export type NavPage =
  | 'dashboard'
  | 'analytics'
  | 'live-map'
  | 'live-yolo'
  | 'agent-logs'
  | 'broadcast'
  | 'network'
  | 'agent-graph'
  | 'shelters'
  | 'evacuation'
  | 'routing'
  | 'allocation';

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
  alertCount: number;
}

const navItems: { id: NavPage; href: string; label: string; icon: React.ElementType; group?: string }[] = [
  { id: 'dashboard', href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard, group: 'Overview' },
  { id: 'analytics', href: '/analytics', label: 'Analytics', icon: PieChart, group: 'Overview' },
  { id: 'live-map', href: '/live-map', label: 'Live Map', icon: Map, group: 'Overview' },
  { id: 'shelters', href: '/shelters', label: 'Shelters', icon: Home, group: 'Operations' },
  { id: 'evacuation', href: '/evacuation', label: 'Evacuation', icon: Users, group: 'Operations' },
  { id: 'allocation', href: '/allocation', label: 'Resources', icon: Package, group: 'Operations' },
  { id: 'routing', href: '/routing', label: 'Routing', icon: Route, group: 'Operations' },
  { id: 'live-yolo', href: '/live-yolo', label: 'Live YOLO', icon: Camera, group: 'Monitoring' },
  { id: 'agent-logs', href: '/agent-logs', label: 'Agent Logs', icon: Brain, group: 'Monitoring' },
  { id: 'broadcast', href: '/broadcast', label: 'Broadcast', icon: Radio, group: 'Monitoring' },
  { id: 'agent-graph', href: '/agent-graph', label: 'Agent Graph', icon: GitBranch, group: 'System' },
];

export default function Sidebar({ collapsed, onToggle, alertCount }: SidebarProps) {
  const pathname = usePathname();
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
      <div className={`flex ${collapsed ? 'items-center justify-center h-20' : 'flex-col items-center py-6 text-center'} gap-3 px-4 border-b border-surface-700/50`}>
        <img src="/logo.jpeg" alt="RakshaSetu Logo" className={`${collapsed ? 'h-10' : 'h-24'} w-auto object-contain rounded-lg flex-shrink-0`} />
        {!collapsed && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="overflow-hidden flex flex-col items-center"
          >
            <h1 className="text-3xl font-black tracking-tight gradient-text whitespace-nowrap">
              Raksha-Setu
            </h1>
            <p className="text-xs text-surface-400 font-medium tracking-wider uppercase mt-1">
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
          const isActive = pathname === item.href || pathname.startsWith(item.href + '/');

          return (
            <div key={item.id}>
              {showGroupLabel && !collapsed && (
                <div className="text-[9px] font-bold uppercase tracking-[0.15em] text-surface-600 px-3 pt-4 pb-1.5">
                  {item.group}
                </div>
              )}
              <Link
                href={item.href}
                className={`w-full ${isActive ? 'nav-link-active' : 'nav-link'} ${
                  collapsed ? 'justify-center px-0' : ''
                }`}
                title={collapsed ? item.label : undefined}
                id={`nav-${item.id}`}
              >
                <div className="relative">
                  <Icon size={18} />
                </div>
                {!collapsed && (
                  <span className="text-sm font-medium whitespace-nowrap">{item.label}</span>
                )}
              </Link>
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
