/**
 * Agent Graph Visualization using ReactFlow.
 * Dynamically imported to avoid SSR issues.
 */
'use client';

import { useMemo, useEffect } from 'react';
import ReactFlow, {
  Node, Edge, Background, Controls, MiniMap,
  useNodesState, useEdgesState, ConnectionMode, MarkerType, Handle, Position,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Alert, Detection } from '../lib/supabase';

function AgentNode({ data }: { data: { label: string; type: string; status: string; description: string } }) {
  const colors: Record<string, { bg: string; border: string; text: string; glow: string }> = {
    trigger: { bg: 'bg-gradient-to-br from-warning-900/80 to-warning-950/80', border: 'border-warning-500/40', text: 'text-warning-400', glow: 'shadow-warning-500/20' },
    agent: { bg: 'bg-gradient-to-br from-raksha-900/80 to-raksha-950/80', border: 'border-raksha-500/40', text: 'text-raksha-400', glow: 'shadow-raksha-500/20' },
    service: { bg: 'bg-gradient-to-br from-safe-900/80 to-safe-950/80', border: 'border-safe-500/40', text: 'text-safe-400', glow: 'shadow-safe-500/20' },
    output: { bg: 'bg-gradient-to-br from-danger-900/80 to-danger-950/80', border: 'border-danger-500/40', text: 'text-danger-400', glow: 'shadow-danger-500/20' },
    database: { bg: 'bg-gradient-to-br from-raksha-900/80 to-raksha-950/80', border: 'border-raksha-500/40', text: 'text-raksha-300', glow: 'shadow-raksha-500/20' },
  };
  const style = colors[data.type] || colors.agent;
  const icons: Record<string, string> = { trigger: '⚡', agent: '🤖', service: '⚙️', output: '📡', database: '🗄️' };

  return (
    <div className={`${style.bg} ${style.border} border rounded-2xl p-4 min-w-[180px] backdrop-blur-sm shadow-lg ${style.glow}`}>
      <Handle type="target" position={Position.Left} className="!w-2 !h-2 !bg-surface-400 !border-none" />
      <div className="flex items-center gap-2 mb-1.5">
        <span className="text-base">{icons[data.type]}</span>
        <span className={`text-sm font-bold ${style.text}`}>{data.label}</span>
      </div>
      <p className="text-[10px] text-surface-400 leading-relaxed">{data.description}</p>
      <div className="flex items-center gap-1.5 mt-2">
        <div className={`w-1.5 h-1.5 rounded-full ${data.status === 'active' ? 'bg-safe-500 animate-pulse' : 'bg-surface-600'}`} />
        <span className="text-[9px] text-surface-500 uppercase tracking-wider font-medium">{data.status}</span>
      </div>
      <Handle type="source" position={Position.Right} className="!w-2 !h-2 !bg-surface-400 !border-none" />
    </div>
  );
}

const nodeTypes = { agentNode: AgentNode };

interface AgentGraphProps { alerts: Alert[]; detections: Detection[] }

export default function AgentGraph({ alerts, detections }: AgentGraphProps) {
  const hasActivity = alerts.length > 0 || detections.length > 0;

  const initialNodes: Node[] = useMemo(() => [
    { id: 'detection-event', type: 'agentNode', position: { x: 50, y: 50 }, data: { label: 'Detection Event', type: 'trigger', status: detections.length > 0 ? 'active' : 'idle', description: 'Crowd detection from sensors/cameras' } },
    { id: 'weather-event', type: 'agentNode', position: { x: 50, y: 220 }, data: { label: 'Weather Event', type: 'trigger', status: hasActivity ? 'active' : 'idle', description: 'Simulated weather conditions' } },
    { id: 'postgres', type: 'agentNode', position: { x: 320, y: 130 }, data: { label: 'PostgreSQL + NOTIFY', type: 'database', status: 'active', description: 'Supabase DB with PostGIS & pgvector' } },
    { id: 'detection-agent', type: 'agentNode', position: { x: 600, y: 30 }, data: { label: 'Detection Agent', type: 'agent', status: detections.length > 0 ? 'active' : 'idle', description: 'Evaluates crowd thresholds, escalates risk' } },
    { id: 'weather-agent', type: 'agentNode', position: { x: 600, y: 190 }, data: { label: 'Weather Agent', type: 'agent', status: 'idle', description: 'Computes risk delta from weather events' } },
    { id: 'dispatch-agent', type: 'agentNode', position: { x: 600, y: 350 }, data: { label: 'Dispatch Agent', type: 'agent', status: alerts.some((a) => a.severity === 'critical') ? 'active' : 'idle', description: 'Assigns volunteers to affected zones' } },
    { id: 'alert-service', type: 'agentNode', position: { x: 900, y: 30 }, data: { label: 'Alert Service', type: 'service', status: alerts.length > 0 ? 'active' : 'idle', description: 'Creates & persists alert records' } },
    { id: 'geo-service', type: 'agentNode', position: { x: 900, y: 190 }, data: { label: 'Geo Service', type: 'service', status: hasActivity ? 'active' : 'idle', description: 'PostGIS spatial queries for proximity' } },
    { id: 'rag-service', type: 'agentNode', position: { x: 900, y: 350 }, data: { label: 'RAG Service', type: 'service', status: 'idle', description: 'pgvector similarity search for context' } },
    { id: 'network-broadcast', type: 'agentNode', position: { x: 1200, y: 100 }, data: { label: 'Network Broadcast', type: 'output', status: 'active', description: 'UDP / FCM — broadcasts to all devices' } },
    { id: 'dashboard', type: 'agentNode', position: { x: 1200, y: 280 }, data: { label: 'Dashboard', type: 'output', status: 'active', description: 'This Next.js dashboard (you are here)' } },
  ], [alerts, detections, hasActivity]);

  const initialEdges: Edge[] = useMemo(() => [
    { id: 'e-det-pg', source: 'detection-event', target: 'postgres', animated: detections.length > 0, style: { stroke: '#F59E0B', strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: '#F59E0B' }, label: 'INSERT', labelStyle: { fill: '#9CA3AF', fontSize: 10 } },
    { id: 'e-wx-pg', source: 'weather-event', target: 'postgres', animated: false, style: { stroke: '#F59E0B', strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: '#F59E0B' }, label: 'INSERT', labelStyle: { fill: '#9CA3AF', fontSize: 10 } },
    { id: 'e-pg-det', source: 'postgres', target: 'detection-agent', animated: detections.length > 0, style: { stroke: '#2563EB', strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: '#2563EB' }, label: 'NOTIFY', labelStyle: { fill: '#94a3b8', fontSize: 10 } },
    { id: 'e-pg-wx', source: 'postgres', target: 'weather-agent', animated: false, style: { stroke: '#2563EB', strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: '#2563EB' }, label: 'NOTIFY', labelStyle: { fill: '#94a3b8', fontSize: 10 } },
    { id: 'e-det-alert', source: 'detection-agent', target: 'alert-service', animated: alerts.length > 0, style: { stroke: '#2563EB', strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: '#2563EB' } },
    { id: 'e-det-disp', source: 'detection-agent', target: 'dispatch-agent', animated: alerts.some((a) => a.severity === 'critical'), style: { stroke: '#2563EB', strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: '#2563EB' }, label: 'critical', labelStyle: { fill: '#EF4444', fontSize: 9 } },
    { id: 'e-wx-alert', source: 'weather-agent', target: 'alert-service', animated: false, style: { stroke: '#2563EB', strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: '#2563EB' } },
    { id: 'e-wx-disp', source: 'weather-agent', target: 'dispatch-agent', animated: false, style: { stroke: '#2563EB', strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: '#2563EB' } },
    { id: 'e-disp-geo', source: 'dispatch-agent', target: 'geo-service', animated: alerts.some((a) => a.severity === 'critical'), style: { stroke: '#22C55E', strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: '#22C55E' } },
    { id: 'e-alert-net', source: 'alert-service', target: 'network-broadcast', animated: alerts.length > 0, style: { stroke: '#EF4444', strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: '#EF4444' }, label: 'broadcast', labelStyle: { fill: '#F87171', fontSize: 9 } },
    { id: 'e-pg-dash', source: 'postgres', target: 'dashboard', animated: true, style: { stroke: '#2563EB', strokeWidth: 2, strokeDasharray: '5,5' }, markerEnd: { type: MarkerType.ArrowClosed, color: '#2563EB' }, label: 'Realtime', labelStyle: { fill: '#3B82F6', fontSize: 9 } },
    { id: 'e-net-dash', source: 'network-broadcast', target: 'dashboard', animated: true, style: { stroke: '#EF4444', strokeWidth: 2, strokeDasharray: '5,5' }, markerEnd: { type: MarkerType.ArrowClosed, color: '#EF4444' }, label: 'HTTP / WS', labelStyle: { fill: '#F87171', fontSize: 9 } },
  ], [alerts, detections]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  useEffect(() => { setNodes(initialNodes); setEdges(initialEdges); }, [initialNodes, initialEdges, setNodes, setEdges]);

  return (
    <div className="w-full h-full rounded-2xl overflow-hidden" id="agent-graph">
      <ReactFlow nodes={nodes} edges={edges} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} nodeTypes={nodeTypes} connectionMode={ConnectionMode.Loose} fitView fitViewOptions={{ padding: 0.2 }} minZoom={0.3} maxZoom={1.5} defaultEdgeOptions={{ type: 'smoothstep' }}>
        <Background color="#1B2433" gap={20} size={1} />
        <Controls showInteractive={false} style={{ background: '#1B2433', border: '1px solid #2A3441', borderRadius: '12px' }} />
        <MiniMap nodeColor={(node) => { const type = node.data?.type; if (type === 'trigger') return '#F59E0B'; if (type === 'agent') return '#2563EB'; if (type === 'service') return '#22C55E'; if (type === 'output') return '#EF4444'; if (type === 'database') return '#2563EB'; return '#6B7280'; }} maskColor="rgba(10, 15, 26, 0.8)" style={{ background: '#1B2433', border: '1px solid #2A3441', borderRadius: '12px' }} />
      </ReactFlow>
    </div>
  );
}
