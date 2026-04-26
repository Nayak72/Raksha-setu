import { useState, useEffect, useMemo } from 'react';
import { Camera, Activity } from 'lucide-react';
import { Zone, Detection } from '../lib/supabase';

const SUPABASE_BUCKET = 'https://wcaggixrdosfkewalokc.supabase.co/storage/v1/object/public/Input%20Images';

// We map real zone index to our hardcoded images just for visual presentation.
const ZONE_IMAGES = [
  [
    `${SUPABASE_BUCKET}/Zone%201/free-photo-of-group-of-men-working-at-a-calamity.jpeg`,
    `${SUPABASE_BUCKET}/Zone%201/images-2.jpeg`,
    `${SUPABASE_BUCKET}/Zone%201/images-3.jpeg`,
    `${SUPABASE_BUCKET}/Zone%201/Syrians-in-rural-Idlib-and-Aleppo-search-for-people-still-trapped-under-the-rubble.-Photo-Local-source.jpeg`,
  ],
  [
    `${SUPABASE_BUCKET}/Zone%202/150425094552-04-nepal-quake-0425.jpg`,
    `${SUPABASE_BUCKET}/Zone%202/gettyimages-472616228-640x640.jpg`,
    `${SUPABASE_BUCKET}/Zone%202/images-4.jpeg`,
    `${SUPABASE_BUCKET}/Zone%202/Nepal-Earthquake.jpeg`,
  ],
  [
    `${SUPABASE_BUCKET}/Zone%203/Nepal-floods.jpg`,
    `${SUPABASE_BUCKET}/Zone%203/hq720.jpg`,
    `${SUPABASE_BUCKET}/Zone%203/ANI-20240806134943.jpg`,
    `${SUPABASE_BUCKET}/Zone%203/images-10.jpeg`,
  ],
  [
    `${SUPABASE_BUCKET}/Zone%204/delhi-flood_668221551ab8b.jpg`,
    `${SUPABASE_BUCKET}/Zone%204/_107746111_gettyimages-1153321998.jpg`,
    `${SUPABASE_BUCKET}/Zone%204/india-monsoon-street-sq.jpg`,
    `${SUPABASE_BUCKET}/Zone%204/images-15.jpeg`,
  ],
  [
    `${SUPABASE_BUCKET}/Zone%201/massive-earthquake-hit-myanmar-67e6a46c05b57-png__700.jpg`,
    `${SUPABASE_BUCKET}/Zone%202/Quake3.jpg`,
    `${SUPABASE_BUCKET}/Zone%203/maxresdefault.jpg`,
    `${SUPABASE_BUCKET}/Zone%204/5f48d4778b164.jpg`,
  ],
];

type BoundingBox = {
  id: number;
  x: number;
  y: number;
  w: number;
  h: number;
  conf: string;
  label: string;
};

// Deterministically generate pseudo-random boxes based on detection ID so they don't jitter on re-renders,
// but DO update when a new detection arrives.
function generateBoxesForDetection(detectionId: string, count: number): BoundingBox[] {
  // Use the ID hash to seed randomness loosely
  let seed = Array.from(detectionId || "mock").reduce((acc, char) => acc + char.charCodeAt(0), 0);
  const rnd = () => {
    seed = (seed * 1664525 + 1013904223) % 4294967296;
    return seed / 4294967296;
  };
  
  // Cap visual boxes at 15 to avoid clutter, but represent the exact data.
  const visualCount = Math.min(count || 0, 15);
  
  return Array.from({ length: visualCount }).map((_, i) => ({
    id: i,
    x: rnd() * 60 + 10,
    y: rnd() * 50 + 15,
    w: rnd() * 15 + 8,
    h: rnd() * 25 + 15,
    conf: (rnd() * 0.2 + 0.75).toFixed(2), // 0.75 - 0.95
    label: rnd() > 0.3 ? 'person' : 'vehicle',
  }));
}

interface YoloFeedProps {
  zones: Zone[];
  detections: Detection[];
}

export default function YoloFeed({ zones, detections }: YoloFeedProps) {
  const [imageIdx, setImageIdx] = useState<Record<string, number>>({});
  const [lastDetIds, setLastDetIds] = useState<Record<string, string>>({});

  // When a new detection arrives for a zone, rotate its image to simulate a new frame
  useEffect(() => {
    const newIndices = { ...imageIdx };
    const newDetIds = { ...lastDetIds };
    let changed = false;
    
    // Process only the latest detections (e.g. top 5)
    detections.slice(0, 5).forEach(d => {
      // Just cycle the image whenever we see a detection
      const current = newIndices[d.zone_id] || 0;
      if (!newDetIds[d.zone_id] || newDetIds[d.zone_id] !== d.id) {
        newIndices[d.zone_id] = current + 1;
        newDetIds[d.zone_id] = d.id;
        changed = true;
      }
    });

    if (changed) {
      setImageIdx(newIndices);
      setLastDetIds(newDetIds);
    }
  }, [detections]);

  // Aggregate latest detection per zone
  const latestDetectionsByZone = useMemo(() => {
    const map = new Map();
    // Detections are ordered newest first from the hook
    detections.forEach(d => {
      if (!map.has(d.zone_id)) {
        map.set(d.zone_id, d);
      }
    });
    return map;
  }, [detections]);

  return (
    <div className="space-y-4" id="yolo-feed-page">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-danger-500/20 to-danger-700/20 border border-danger-500/30 flex items-center justify-center">
            <Camera className="w-5 h-5 text-danger-400" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-surface-50">Live YOLO Feed</h2>
            <p className="text-xs text-surface-500">Real-time object detection stream linked to backend AI</p>
          </div>
        </div>

        {/* Sync Status */}
        <div className="flex items-center gap-2 glass-panel px-3 py-2">
          <Activity className="w-4 h-4 text-safe-400 animate-pulse" />
          <span className="text-xs font-mono text-surface-300">
            Listening to <span className="text-safe-400 font-bold ml-1">detections</span>
          </span>
        </div>
      </div>

      {/* Zone Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {zones.map((zone, idx) => {
          const det = latestDetectionsByZone.get(zone.id);
          const images = ZONE_IMAGES[idx % ZONE_IMAGES.length];
          const currentImage = images[(imageIdx[zone.id] || 0) % images.length];
          
          // Use real detection data to generate boxes
          const zoneBoxes = det ? generateBoxesForDetection(det.id, det.count) : [];
          const personCount = zoneBoxes.filter(b => b.label === 'person').length;
          const vehicleCount = zoneBoxes.filter(b => b.label === 'vehicle').length;

          // Compute age of detection for visual feedback
          const isStale = det ? (new Date().getTime() - new Date(det.timestamp).getTime() > 30000) : true;

          return (
            <div key={zone.id} className={`glass-panel p-3 flex flex-col gap-2 transition-all ${!isStale && det ? 'border-danger-500/50 shadow-[0_0_15px_rgba(239,68,68,0.15)]' : 'border-surface-700'}`}>
              {/* Zone header */}
              <div className="flex justify-between items-center px-1">
                <span className="font-semibold text-surface-200">Zone {idx + 1}</span>
                <div className="flex items-center gap-3">
                  {/* Detection counts */}
                  {det && (
                    <div className="flex items-center gap-2 text-[10px] font-mono">
                      <span className="text-blue-400">{personCount} person{personCount !== 1 ? 's' : ''}</span>
                      <span className="text-surface-600">|</span>
                      <span className="text-red-400">{vehicleCount} vehicle{vehicleCount !== 1 ? 's' : ''}</span>
                    </div>
                  )}
                  {/* Live indicator */}
                  <div className="flex items-center gap-1">
                    <span className="relative flex h-2 w-2">
                      {!isStale && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-danger-400 opacity-75"></span>}
                      <span className={`relative inline-flex rounded-full h-2 w-2 ${!isStale ? 'bg-danger-500' : 'bg-surface-500'}`}></span>
                    </span>
                    <span className="text-xs text-surface-400">{!isStale ? 'Active' : 'Idle'}</span>
                  </div>
                </div>
              </div>

              {/* Image with bounding boxes */}
              <div className="relative rounded-lg overflow-hidden border border-surface-700 bg-surface-900" style={{ aspectRatio: '16/10' }}>
                <img
                  src={currentImage}
                  alt={`Zone ${idx + 1}`}
                  className={`w-full h-full object-cover transition-opacity duration-300 ${!isStale ? 'opacity-90' : 'opacity-40 grayscale-[50%]'}`}
                  crossOrigin="anonymous"
                  loading="eager"
                />

                {/* Bounding Boxes */}
                {!isStale && zoneBoxes.map((box) => (
                  <div
                    key={box.id}
                    className={`absolute border-2 ${box.label === 'person' ? 'border-blue-500' : 'border-red-500'} bg-black/10`}
                    style={{
                      left: `${box.x}%`,
                      top: `${box.y}%`,
                      width: `${box.w}%`,
                      height: `${box.h}%`,
                      transition: 'all 0.2s ease-out',
                    }}
                  >
                    <span
                      className={`absolute -top-5 left-0 text-[10px] px-1 font-mono text-white ${box.label === 'person' ? 'bg-blue-600' : 'bg-red-600'}`}
                    >
                      {box.label} {box.conf}
                    </span>
                  </div>
                ))}

                {/* Timestamp overlay */}
                <div className="absolute bottom-1 right-1 bg-black/60 px-2 py-0.5 rounded text-[9px] font-mono text-surface-300 flex flex-col items-end">
                  {det ? new Date(det.timestamp).toLocaleTimeString() : 'No Detections'}
                  {det && <span className="text-[8px] text-surface-500">ID: {det.id.split('-')[0]}</span>}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
