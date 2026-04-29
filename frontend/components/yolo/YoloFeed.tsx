/**
 * YOLO Live Feed — multi-camera grid with detection stats.
 * Now using the real backend YOLO model (best.pt) on Supabase images.
 */
'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { Camera, Activity, RefreshCw, AlertCircle } from 'lucide-react';
import { Zone } from '../../lib/supabase';
import { SimZone } from '../../lib/simulation-api';

interface YoloFeedProps {
  zones: Zone[];
  simZones?: SimZone[];
}

interface YoloDetection {
  class_id: number;
  class_name: string;
  confidence: number;
  bbox: number[];
  bbox_norm: { x: number; y: number; w: number; h: number };
}

interface YoloResult {
  zone_id: string;
  source_url: string;
  image_name: string;
  timestamp: string;
  num_detections: number;
  detections: YoloDetection[];
  annotated_image: string; // base64
  disaster_types: string[];
  summary: Record<string, { count: number; avg_conf: number; max_conf: number }>;
  error?: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

export default function YoloFeed({ zones, simZones = [] }: YoloFeedProps) {
  const [results, setResults] = useState<Record<string, YoloResult>>({});
  const [loading, setLoading] = useState<Record<string, boolean>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  
  // Use simZones for rendering if available (they always have 7 consistent zones),
  // fall back to Supabase zones
  const displayZones = simZones.length > 0
    ? simZones.map(z => ({ id: z.id, name: z.name }))
    : zones.map(z => ({ id: z.id, name: z.name || `Zone ${z.id.slice(0, 8)}` }));

  const fetchZoneDetection = useCallback(async (zoneId: string) => {
    setLoading(prev => ({ ...prev, [zoneId]: true }));
    setErrors(prev => ({ ...prev, [zoneId]: '' }));
    try {
      const res = await fetch(`${API_BASE}/api/v1/yolo/detect-zone`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ zone_id: zoneId, max_images: 1 }),
      });
      
      if (!res.ok) {
        setErrors(prev => ({ ...prev, [zoneId]: `HTTP ${res.status}` }));
        return;
      }
      const data = await res.json();
      
      if (data.results && data.results.length > 0) {
        const result = data.results[0];
        // Only accept results that have a valid annotated image
        if (result.annotated_image && !result.error) {
          setResults(prev => ({ ...prev, [zoneId]: result }));
        } else if (result.error) {
          setErrors(prev => ({ ...prev, [zoneId]: result.error }));
        } else {
          setErrors(prev => ({ ...prev, [zoneId]: 'No annotated image returned' }));
        }
      } else {
        setErrors(prev => ({ ...prev, [zoneId]: 'No images found in bucket for this zone' }));
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Connection failed';
      setErrors(prev => ({ ...prev, [zoneId]: msg }));
      console.error(`Failed to fetch YOLO for zone ${zoneId}:`, err);
    } finally {
      setLoading(prev => ({ ...prev, [zoneId]: false }));
    }
  }, []);

  // Initial load and polling
  useEffect(() => {
    if (displayZones.length === 0) return;
    
    // Initial fetch for all zones (staggered)
    displayZones.forEach((zone, i) => {
      setTimeout(() => fetchZoneDetection(zone.id), i * 2000);
    });
    
    // Poll every 15 seconds, staggered
    const interval = setInterval(() => {
      displayZones.forEach((zone, i) => {
        setTimeout(() => fetchZoneDetection(zone.id), i * 2000);
      });
    }, 15000);
    
    return () => clearInterval(interval);
  }, [displayZones.length, fetchZoneDetection]);

  return (
    <div className="space-y-4 animate-fade-in" id="yolo-feed-page">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-danger-500/20 to-danger-700/20 border border-danger-500/30 flex items-center justify-center">
            <Camera className="w-5 h-5 text-danger-400" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-surface-50">Live YOLO Feed</h2>
            <p className="text-xs text-surface-500">Real-time object detection stream linked to backend AI (best.pt)</p>
          </div>
        </div>
        <div className="flex items-center gap-2 glass-panel px-3 py-2">
          <Activity className="w-4 h-4 text-safe-400 animate-pulse" />
          <span className="text-xs font-mono text-surface-300">
            Scanning <span className="text-safe-400 font-bold ml-1">Live Detections</span>
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        {displayZones.map((zone, idx) => {
          const result = results[zone.id];
          const isLoading = loading[zone.id];
          const zoneError = errors[zone.id];
          const hasValidImage = result?.annotated_image && !result?.error;
          const isStale = result?.timestamp 
            ? (new Date().getTime() - new Date(result.timestamp).getTime() > 30000) 
            : true;

          return (
            <div key={zone.id} className={`glass-panel p-3 flex flex-col gap-2 transition-all ${(hasValidImage && !isStale) ? 'border-danger-500/50 shadow-[0_0_15px_rgba(239,68,68,0.15)]' : 'border-surface-700'}`}>
              <div className="flex justify-between items-center px-1">
                <span className="font-semibold text-surface-200">Zone {idx + 1} - {zone.name}</span>
                <div className="flex items-center gap-3">
                  {result && hasValidImage && (
                    <div className="flex flex-wrap items-center gap-2 text-[10px] font-mono">
                      {Object.entries(result.summary || {}).map(([cls, stat]) => (
                         <span key={cls} className={cls.includes('struct') || cls.includes('fire') || cls.includes('flood') ? 'text-red-400' : 'text-blue-400'}>
                           {stat.count} {cls}
                         </span>
                      ))}
                    </div>
                  )}
                  <div className="flex items-center gap-1">
                    {isLoading ? (
                      <RefreshCw className="w-3 h-3 text-surface-400 animate-spin" />
                    ) : (
                      <span className="relative flex h-2 w-2">
                        {hasValidImage && !isStale && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-danger-400 opacity-75"></span>}
                        <span className={`relative inline-flex rounded-full h-2 w-2 ${hasValidImage && !isStale ? 'bg-danger-500' : zoneError ? 'bg-warning-500' : 'bg-surface-500'}`}></span>
                      </span>
                    )}
                    <span className="text-xs text-surface-400">{isLoading ? 'Scanning' : (hasValidImage && !isStale ? 'Active' : 'Idle')}</span>
                  </div>
                </div>
              </div>
              
              <div className="relative rounded-lg overflow-hidden border border-surface-700 bg-surface-900 flex items-center justify-center" style={{ aspectRatio: '16/10' }}>
                {hasValidImage ? (
                  <>
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img 
                      src={result.annotated_image} 
                      alt={`Detections for ${zone.name}`} 
                      className={`w-full h-full object-contain transition-opacity duration-300 ${!isStale ? 'opacity-100' : 'opacity-70 grayscale-[30%]'}`} 
                    />
                    <div className="absolute bottom-1 right-1 bg-black/60 px-2 py-0.5 rounded text-[9px] font-mono text-surface-300 flex flex-col items-end">
                      {result.timestamp ? new Date(result.timestamp).toLocaleTimeString() : '—'}
                      <span className="text-[8px] text-surface-500">{result.image_name || 'inference'}</span>
                    </div>
                    <div className="absolute top-1 left-1 bg-black/60 px-2 py-0.5 rounded text-[9px] font-bold text-safe-400">
                      {result.num_detections} detection{result.num_detections !== 1 ? 's' : ''}
                    </div>
                  </>
                ) : (
                  <div className="flex flex-col items-center justify-center text-surface-500 gap-2 p-4">
                    {isLoading ? (
                       <RefreshCw className="w-6 h-6 animate-spin text-surface-400" />
                    ) : zoneError ? (
                       <AlertCircle className="w-6 h-6 text-warning-400 opacity-60" />
                    ) : (
                       <Camera className="w-8 h-8 opacity-20" />
                    )}
                    <span className="text-xs font-mono text-center">
                      {isLoading ? 'Running YOLO Inference...' : zoneError ? zoneError : 'Waiting for Feed...'}
                    </span>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

