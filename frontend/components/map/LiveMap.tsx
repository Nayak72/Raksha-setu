/**
 * Live Map component using Leaflet — dynamically imported to avoid SSR.
 */
'use client';

import { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Zone, Shelter } from '../../lib/supabase';
import { SimZone, SimShelter } from '../../lib/simulation-api';

// Fix default marker icons
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

interface LiveMapProps {
  zones: Zone[];       // legacy supabase
  shelters: Shelter[]; // legacy supabase
  volunteerCount: number;
  simZones?: SimZone[];
  simShelters?: SimShelter[];
  simConnections?: { zone_id: string; shelters: SimShelter[] }[];
}

function getRiskColor(risk: number): string {
  if (risk >= 80) return '#ff2d2d';
  if (risk >= 60) return '#ff6464';
  if (risk >= 40) return '#ffbd20';
  if (risk >= 20) return '#ffd14a';
  return '#3bce7f';
}

function getRiskLabel(risk: number): string {
  if (risk >= 80) return 'CRITICAL';
  if (risk >= 60) return 'HIGH';
  if (risk >= 40) return 'MEDIUM';
  if (risk >= 20) return 'LOW';
  return 'SAFE';
}

function createZoneIcon(risk: number, type: string = 'unknown'): L.DivIcon {
  const color = getRiskColor(risk);
  const label = getRiskLabel(risk);
  const typeIcon = type === 'flood' ? '🌊' : type === 'cyclone' ? '🌀' : type === 'landslide' ? '⛰️' : type === 'storm' ? '⛈️' : '🚨';
  
  return L.divIcon({
    className: 'custom-zone-marker',
    html: `
      <div style="position:relative;width:48px;height:48px;display:flex;align-items:center;justify-content:center;">
        <div style="position:absolute;inset:0;background:${color}20;border:2px solid ${color};border-radius:50%;animation:${risk >= 60 ? 'pulse 2s infinite' : 'none'};"></div>
        <div style="position:relative;width:24px;height:24px;background:${color};border-radius:50%;box-shadow:0 0 12px ${color}80;display:flex;align-items:center;justify-content:center;">
          <span style="font-size:12px;">${typeIcon}</span>
        </div>
        <div style="position:absolute;bottom:-18px;left:50%;transform:translateX(-50%);background:${color};color:white;font-size:8px;font-weight:700;padding:1px 6px;border-radius:4px;white-space:nowrap;letter-spacing:0.5px;">${label}</div>
      </div>
    `,
    iconSize: [48, 48],
    iconAnchor: [24, 24],
  });
}

function createShelterIcon(): L.DivIcon {
  return L.divIcon({
    className: 'custom-shelter-marker',
    html: `
      <div style="width:32px;height:32px;background:linear-gradient(135deg, #16a34a, #22c55e);border:2px solid #86efac;border-radius:8px;display:flex;align-items:center;justify-content:center;box-shadow:0 0 10px rgba(34, 197, 94, 0.4);">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
          <polyline points="9 22 9 12 15 12 15 22"/>
        </svg>
      </div>
    `,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  });
}

function parseShelterLocation(location: string): [number, number] | null {
  const pointMatch = location.match(/POINT\(([^ ]+) ([^)]+)\)/i);
  if (pointMatch) return [parseFloat(pointMatch[2]), parseFloat(pointMatch[1])];
  const parts = location.split(',').map(Number);
  if (parts.length === 2 && !isNaN(parts[0]) && !isNaN(parts[1])) return [parts[0], parts[1]];
  return null;
}

export default function LiveMap({ zones, shelters, volunteerCount, simZones = [], simShelters = [], simConnections = [] }: LiveMapProps) {
  const mapRef = useRef<L.Map | null>(null);
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const zoneLayerRef = useRef<L.LayerGroup>(L.layerGroup());
  const shelterLayerRef = useRef<L.LayerGroup>(L.layerGroup());
  const lineLayerRef = useRef<L.LayerGroup>(L.layerGroup());
  const hasFitBounds = useRef(false);

  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;
    const map = L.map(mapContainerRef.current, {
      center: [13.9, 74.8], // Centered on coastal Karnataka
      zoom: 8,
      zoomControl: true,
      attributionControl: false,
    });
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', { maxZoom: 19 }).addTo(map);
    lineLayerRef.current.addTo(map);
    zoneLayerRef.current.addTo(map);
    shelterLayerRef.current.addTo(map);
    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
      hasFitBounds.current = false;
    };
  }, []);

  useEffect(() => {
    const layer = zoneLayerRef.current;
    layer.clearLayers();

    // Support rendering both legacy zones and simZones (prioritize simZones)
    const renderZones = simZones.length > 0 
      ? simZones.map(z => ({ id: z.id, lat: z.lat, lon: z.lng, risk_score: z.damage_level * 100, type: z.disaster_type, name: z.name, pop: z.affected_population, dmg: z.damage_level })) 
      : zones.map(z => ({ id: z.id, lat: z.lat, lon: z.lon, risk_score: z.risk_score, type: z.disaster_type || 'unknown', name: z.name || `Zone ${z.id.slice(0,8)}`, pop: 0, dmg: z.risk_score/100 }));

    renderZones.forEach((zone) => {
      const marker = L.marker([zone.lat, zone.lon], { icon: createZoneIcon(zone.risk_score, zone.type) });
      marker.bindPopup(`
        <div style="font-family:Inter,sans-serif;padding:4px;">
          <div style="font-size:14px;font-weight:700;margin-bottom:6px;color:${getRiskColor(zone.risk_score)}">${zone.name}</div>
          <div style="font-size:12px;color:#94a3b8;margin-bottom:2px;">Disaster Type: <span style="color:white;text-transform:capitalize;">${zone.type}</span></div>
          <div style="font-size:12px;color:#94a3b8;margin-bottom:2px;">Severity: <span style="color:${getRiskColor(zone.risk_score)};font-weight:600;">${getRiskLabel(zone.risk_score)}</span></div>
          <div style="font-size:12px;color:#94a3b8;margin-bottom:2px;">Damage Level: <span style="color:white;font-weight:600;">${Math.round(zone.dmg * 100)}%</span></div>
          ${zone.pop > 0 ? `<div style="font-size:12px;color:#94a3b8;margin-bottom:4px;">Affected Pop: <span style="color:white;font-weight:600;">${zone.pop.toLocaleString()}</span></div>` : ''}
          <div style="font-size:10px;color:#64748b;margin-top:4px;">ID: ${zone.id.slice(0, 8)} | ${zone.lat.toFixed(4)}, ${zone.lon.toFixed(4)}</div>
        </div>
      `);
      L.circle([zone.lat, zone.lon], {
        radius: Math.max(1000, zone.risk_score * 50),
        color: getRiskColor(zone.risk_score),
        fillColor: getRiskColor(zone.risk_score),
        fillOpacity: 0.08,
        weight: 1,
        opacity: 0.3,
      }).addTo(layer);
      marker.addTo(layer);
    });

    if (renderZones.length > 0 && mapRef.current && !hasFitBounds.current) {
      const bounds = L.latLngBounds(renderZones.map((z) => [z.lat, z.lon]));
      mapRef.current.fitBounds(bounds, { padding: [50, 50], maxZoom: 10 });
      hasFitBounds.current = true;
    }
  }, [zones, simZones]);

  useEffect(() => {
    const layer = shelterLayerRef.current;
    const lines = lineLayerRef.current;
    layer.clearLayers();
    lines.clearLayers();

    // If we have simShelters, render them instead of legacy
    if (simShelters.length > 0) {
      // De-duplicate shelters (since multiple zones might share them)
      const uniqueShelters = Array.from(new Map(simShelters.map(s => [s.shelter_id, s])).values());
      
      uniqueShelters.forEach((shelter) => {
        const marker = L.marker([shelter.lat, shelter.lng], { icon: createShelterIcon() });
        const occupancy = ((shelter.capacity - shelter.available_capacity) / shelter.capacity) * 100;
        const occColor = occupancy > 80 ? '#ff2d2d' : occupancy > 50 ? '#ffbd20' : '#22c55e';
        
        marker.bindPopup(`
          <div style="font-family:Inter,sans-serif;padding:4px;">
            <div style="font-size:14px;font-weight:700;margin-bottom:6px;color:#22c55e;">🏥 ${shelter.name}</div>
            <div style="font-size:12px;color:#94a3b8;margin-bottom:2px;">Capacity: <span style="font-weight:600;color:white;">${shelter.capacity}</span></div>
            <div style="font-size:12px;color:#94a3b8;margin-bottom:4px;">Available: <span style="font-weight:600;color:${occColor};">${shelter.available_capacity}</span></div>
            <div style="background:#0f172a;border-radius:4px;height:6px;overflow:hidden;margin-top:4px;">
              <div style="height:100%;width:${occupancy}%;background:${occColor};border-radius:4px;"></div>
            </div>
            <div style="font-size:10px;color:#64748b;margin-top:4px;">ID: ${shelter.shelter_id.slice(0, 8)}</div>
          </div>
        `);
        marker.addTo(layer);
      });

      // Draw lines
      simConnections.forEach(({ zone_id, shelters }) => {
        const zone = simZones.find(z => z.id === zone_id);
        if (!zone) return;
        
        shelters.forEach(s => {
          L.polyline([[zone.lat, zone.lng], [s.lat, s.lng]], {
            color: '#22c55e',
            weight: 1.5,
            opacity: 0.3,
            dashArray: '4, 4'
          }).addTo(lines);
        });
      });
      return;
    }

    // Legacy shelters
    shelters.forEach((shelter) => {
      const coords = parseShelterLocation(shelter.location);
      if (!coords) return;
      const marker = L.marker(coords, { icon: createShelterIcon() });
      const occupancy = ((shelter.capacity - shelter.available_beds) / shelter.capacity) * 100;
      const occColor = occupancy > 80 ? '#ff2d2d' : occupancy > 50 ? '#ffbd20' : '#22c55e';
      marker.bindPopup(`
        <div style="font-family:Inter,sans-serif;padding:4px;">
          <div style="font-size:14px;font-weight:700;margin-bottom:6px;color:#22c55e;">🏥 Shelter ${shelter.id.slice(0, 8)}</div>
          <div style="font-size:12px;color:#94a3b8;margin-bottom:2px;">Capacity: <span style="font-weight:600;color:white;">${shelter.capacity}</span></div>
          <div style="font-size:12px;color:#94a3b8;margin-bottom:4px;">Available: <span style="font-weight:600;color:${occColor};">${shelter.available_beds}</span></div>
          <div style="background:#0f172a;border-radius:4px;height:6px;overflow:hidden;margin-top:4px;">
            <div style="height:100%;width:${occupancy}%;background:${occColor};border-radius:4px;"></div>
          </div>
        </div>
      `);
      marker.addTo(layer);
    });
  }, [shelters, simShelters, simConnections, simZones]);

  return (
    <div className="relative w-full h-full rounded-2xl overflow-hidden">
      <div ref={mapContainerRef} className="w-full h-full" id="live-map" />
      <div className="absolute bottom-4 left-4 glass-panel p-3 z-[1000]">
        <div className="text-xs font-semibold text-surface-300 mb-2 uppercase tracking-wider">Risk Levels</div>
        <div className="flex flex-col gap-1.5">
          {[
            { label: 'Critical', color: '#ff2d2d', range: '80-100' },
            { label: 'High', color: '#ff6464', range: '60-79' },
            { label: 'Medium', color: '#ffbd20', range: '40-59' },
            { label: 'Low', color: '#ffd14a', range: '20-39' },
            { label: 'Safe', color: '#3bce7f', range: '0-19' },
          ].map((level) => (
            <div key={level.label} className="flex items-center gap-2 text-xs">
              <div className="w-3 h-3 rounded-full" style={{ backgroundColor: level.color, boxShadow: `0 0 6px ${level.color}60` }} />
              <span className="text-surface-300">{level.label}</span>
              <span className="text-surface-500 ml-auto">{level.range}</span>
            </div>
          ))}
        </div>
        <div className="border-t border-surface-700/50 mt-2 pt-2 flex items-center gap-2 text-xs">
          <div className="w-3 h-3 rounded bg-raksha-500" />
          <span className="text-surface-300">Shelters</span>
        </div>
      </div>
      <div className="absolute top-4 right-4 glass-panel p-3 z-[1000]">
        <div className="flex items-center gap-4 text-xs">
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full bg-danger-500 animate-pulse" />
            <span className="text-surface-300">
              {simZones.length > 0
                ? `${simZones.filter((z) => z.severity === 'critical' || z.severity === 'high').length} High Risk`
                : `${zones.filter((z) => z.risk_score >= 60).length} High Risk`}
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full bg-raksha-500" />
            <span className="text-surface-300">
              {simZones.length > 0 ? `${simZones.length} Zones` : `${shelters.length} Shelters`}
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full bg-safe-500" />
            <span className="text-surface-300">{volunteerCount} Volunteers</span>
          </div>
        </div>
      </div>
    </div>
  );
}
