/**
 * RoutingPanel — displays rescue routes on a Leaflet map with route selection.
 * Uses plain Leaflet (same pattern as LiveMap) — no react-leaflet dependency.
 *
 * Features:
 *  • Polyline rendering of multi-waypoint road paths
 *  • Different colors per route with animated flow indicators
 *  • Shortest route highlighted (bold + pulsing glow)
 *  • Click-to-select routes on map or sidebar
 *  • Route summary statistics
 */
'use client';

import { useState, useEffect, useRef, memo, useCallback } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { SimZone, SimRouteResult, fetchRoutes } from '../../lib/simulation-api';
import { Route, Clock, Ruler, Star, Navigation, MapPin, Zap } from 'lucide-react';

const ROUTE_COLORS = [
  '#3b82f6', // blue
  '#ef4444', // red
  '#f59e0b', // amber
  '#10b981', // emerald
  '#8b5cf6', // violet
];

const ROUTE_LABELS = ['Alpha', 'Bravo', 'Charlie', 'Delta', 'Echo'];

function RoutingPanel({ zones }: { zones: SimZone[] }) {
  const [selectedZone, setSelectedZone] = useState<string>('');
  const [routeData, setRouteData] = useState<SimRouteResult | null>(null);
  const [selectedRouteIdx, setSelectedRouteIdx] = useState<number>(0);
  const [loading, setLoading] = useState(false);

  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const routeLayerRef = useRef<L.LayerGroup>(L.layerGroup());

  // Init map
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;
    const map = L.map(mapContainerRef.current, {
      center: [13.9, 74.8], // Coastal Karnataka center
      zoom: 9,
      zoomControl: true,
      attributionControl: false,
    });
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
    }).addTo(map);
    routeLayerRef.current.addTo(map);
    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Fetch routes when zone changes
  useEffect(() => {
    if (!selectedZone) {
      setRouteData(null);
      return;
    }
    setLoading(true);
    fetchRoutes(selectedZone)
      .then((data) => {
        setRouteData(data);
        setSelectedRouteIdx(data.shortest_route_index);
      })
      .catch(() => setRouteData(null))
      .finally(() => setLoading(false));
  }, [selectedZone]);

  // Auto-select first zone
  useEffect(() => {
    if (zones.length > 0 && !selectedZone) {
      setSelectedZone(zones[0].id);
    }
  }, [zones, selectedZone]);

  // Draw routes on map
  useEffect(() => {
    const layer = routeLayerRef.current;
    layer.clearLayers();

    if (!routeData || !mapRef.current) return;

    const zone = zones.find((z) => z.id === selectedZone);
    if (!zone) return;

    // Fit map to show all route paths
    const allPoints: [number, number][] = [];
    routeData.routes.forEach((route) => {
      route.path.forEach(([lat, lng]) => allPoints.push([lat, lng]));
    });
    if (allPoints.length > 0) {
      const bounds = L.latLngBounds(allPoints);
      mapRef.current.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 });
    }

    // Draw non-selected routes first (so selected is on top)
    routeData.routes.forEach((route, idx) => {
      if (idx === selectedRouteIdx) return; // draw selected last

      const isShortest = idx === routeData.shortest_route_index;
      const color = ROUTE_COLORS[idx % ROUTE_COLORS.length];

      // Background glow for shortest
      if (isShortest) {
        L.polyline(
          route.path.map(([lat, lng]) => [lat, lng] as [number, number]),
          {
            color: color,
            weight: 8,
            opacity: 0.15,
            lineCap: 'round',
            lineJoin: 'round',
          }
        ).addTo(layer);
      }

      const polyline = L.polyline(
        route.path.map(([lat, lng]) => [lat, lng] as [number, number]),
        {
          color: color,
          weight: 3,
          opacity: 0.45,
          dashArray: '8 6',
          lineCap: 'round',
          lineJoin: 'round',
        }
      );
      polyline.on('click', () => setSelectedRouteIdx(idx));
      polyline.bindTooltip(
        `<b>Route ${ROUTE_LABELS[idx] || idx + 1}</b><br/>${route.distance.toFixed(1)} km · ${route.time} min${isShortest ? '<br/><span style="color:#10b981">★ Shortest</span>' : ''}`,
        { sticky: true, className: 'route-tooltip' }
      );
      polyline.addTo(layer);
    });

    // Draw selected route on top
    if (routeData.routes[selectedRouteIdx]) {
      const selectedRoute = routeData.routes[selectedRouteIdx];
      const color = ROUTE_COLORS[selectedRouteIdx % ROUTE_COLORS.length];
      const isShortest = selectedRouteIdx === routeData.shortest_route_index;

      // Outer glow
      L.polyline(
        selectedRoute.path.map(([lat, lng]) => [lat, lng] as [number, number]),
        {
          color: color,
          weight: 14,
          opacity: 0.12,
          lineCap: 'round',
          lineJoin: 'round',
        }
      ).addTo(layer);

      // Mid glow
      L.polyline(
        selectedRoute.path.map(([lat, lng]) => [lat, lng] as [number, number]),
        {
          color: color,
          weight: 8,
          opacity: 0.25,
          lineCap: 'round',
          lineJoin: 'round',
        }
      ).addTo(layer);

      // Main line
      const mainLine = L.polyline(
        selectedRoute.path.map(([lat, lng]) => [lat, lng] as [number, number]),
        {
          color: color,
          weight: 5,
          opacity: 1,
          lineCap: 'round',
          lineJoin: 'round',
        }
      );
      mainLine.on('click', () => setSelectedRouteIdx(selectedRouteIdx));
      mainLine.bindTooltip(
        `<b>Route ${ROUTE_LABELS[selectedRouteIdx] || selectedRouteIdx + 1}</b> (selected)<br/>${selectedRoute.distance.toFixed(1)} km · ${selectedRoute.time} min${isShortest ? '<br/><span style="color:#10b981">★ Shortest Route</span>' : ''}`,
        { sticky: true }
      );
      mainLine.addTo(layer);

      // Direction arrows along the selected route (waypoint markers)
      const pathLen = selectedRoute.path.length;
      const arrowInterval = Math.max(1, Math.floor(pathLen / 5));
      for (let i = arrowInterval; i < pathLen - 1; i += arrowInterval) {
        const [lat, lng] = selectedRoute.path[i];
        L.marker([lat, lng] as [number, number], {
          icon: L.divIcon({
            className: '',
            html: `<div style="width:8px;height:8px;border-radius:50%;background:${color};border:2px solid white;box-shadow:0 0 6px ${color}80"></div>`,
            iconSize: [8, 8],
            iconAnchor: [4, 4],
          }),
          interactive: false,
        }).addTo(layer);
      }
    }

    // Zone marker (red pulsing dot)
    L.marker([zone.lat, zone.lng], {
      icon: L.divIcon({
        className: '',
        html: `<div style="position:relative">
          <div style="width:20px;height:20px;border-radius:50%;background:#ef4444;border:3px solid white;box-shadow:0 0 16px rgba(239,68,68,0.6);position:relative;z-index:2"></div>
          <div style="position:absolute;top:-4px;left:-4px;width:28px;height:28px;border-radius:50%;border:2px solid rgba(239,68,68,0.4);animation:pulse 2s ease-in-out infinite"></div>
        </div>`,
        iconSize: [20, 20],
        iconAnchor: [10, 10],
      }),
    })
      .bindPopup(
        `<div style="text-align:center"><b style="color:#ef4444">⚠ ${zone.name}</b><br/><span style="font-size:12px">Severity: <b>${zone.severity.toUpperCase()}</b><br/>Type: ${zone.disaster_type}</span></div>`
      )
      .addTo(layer);

    // Origin marker (shelter/base — green dot)
    if (routeData.routes.length > 0) {
      const base = routeData.routes[0].path[0];
      L.marker(base as [number, number], {
        icon: L.divIcon({
          className: '',
          html: `<div style="position:relative">
            <div style="width:20px;height:20px;border-radius:50%;background:#10b981;border:3px solid white;box-shadow:0 0 16px rgba(16,185,129,0.6);position:relative;z-index:2"></div>
          </div>`,
          iconSize: [20, 20],
          iconAnchor: [10, 10],
        }),
      })
        .bindPopup('<div style="text-align:center"><b style="color:#10b981">🏥 Rescue Base / Shelter</b><br/><span style="font-size:12px">Nearest staging point</span></div>')
        .addTo(layer);
    }
  }, [routeData, selectedRouteIdx, selectedZone, zones]);

  // Compute summary stats
  const summary = routeData
    ? {
        totalRoutes: routeData.routes.length,
        shortestDist: routeData.routes[routeData.shortest_route_index]?.distance ?? 0,
        shortestTime: routeData.routes[routeData.shortest_route_index]?.time ?? 0,
        longestDist: Math.max(...routeData.routes.map((r) => r.distance)),
        avgTime: Math.round(
          routeData.routes.reduce((s, r) => s + r.time, 0) / routeData.routes.length
        ),
        totalWaypoints: routeData.routes[selectedRouteIdx]?.path.length ?? 0,
      }
    : null;

  return (
    <div className="space-y-5">
      {/* Zone selector */}
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-raksha-500/20 flex items-center justify-center">
          <Navigation size={14} className="text-raksha-400" />
        </div>
        <select
          value={selectedZone}
          onChange={(e) => setSelectedZone(e.target.value)}
          className="input-field text-sm flex-1"
          id="zone-route-selector"
        >
          <option value="">Select a zone...</option>
          {zones.map((z) => (
            <option key={z.id} value={z.id}>
              {z.name} — {z.severity.toUpperCase()}
            </option>
          ))}
        </select>
      </div>

      {/* Summary bar */}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="glass-panel p-3 text-center">
            <div className="text-[10px] uppercase tracking-wider text-surface-500 mb-1">Routes</div>
            <div className="text-lg font-bold text-white">{summary.totalRoutes}</div>
          </div>
          <div className="glass-panel p-3 text-center">
            <div className="text-[10px] uppercase tracking-wider text-surface-500 mb-1">Shortest</div>
            <div className="text-lg font-bold text-safe-400">{summary.shortestDist.toFixed(1)} km</div>
          </div>
          <div className="glass-panel p-3 text-center">
            <div className="text-[10px] uppercase tracking-wider text-surface-500 mb-1">Fastest</div>
            <div className="text-lg font-bold text-blue-400">{summary.shortestTime} min</div>
          </div>
          <div className="glass-panel p-3 text-center">
            <div className="text-[10px] uppercase tracking-wider text-surface-500 mb-1">Waypoints</div>
            <div className="text-lg font-bold text-amber-400">{summary.totalWaypoints}</div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Map */}
        <div className="lg:col-span-2 glass-panel p-1 h-[520px] overflow-hidden rounded-2xl relative">
          <div ref={mapContainerRef} className="w-full h-full rounded-xl" id="routing-map" />

          {/* Map legend */}
          <div className="absolute bottom-3 left-3 z-[1000] glass-panel p-3 space-y-1.5 text-[10px] rounded-xl">
            <div className="font-bold text-surface-300 uppercase tracking-wider mb-1">Legend</div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-[#10b981] border border-white/50" />
              <span className="text-surface-400">Rescue Base</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-[#ef4444] border border-white/50" />
              <span className="text-surface-400">Disaster Zone</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-6 h-[3px] rounded-full bg-white/60" />
              <span className="text-surface-400">Selected Route</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-6 h-[2px] rounded-full border-t-2 border-dashed border-white/30" />
              <span className="text-surface-400">Alt Routes</span>
            </div>
          </div>
        </div>

        {/* Route list */}
        <div className="space-y-3">
          <h3 className="text-sm font-bold text-surface-300 uppercase tracking-wider flex items-center gap-2">
            <Route size={14} className="text-raksha-400" />
            Available Routes
          </h3>

          {loading && (
            <div className="glass-panel p-6 text-center">
              <div className="animate-spin w-6 h-6 border-2 border-raksha-500 border-t-transparent rounded-full mx-auto mb-2" />
              <p className="text-sm text-surface-500">Calculating routes...</p>
            </div>
          )}

          {routeData?.routes.map((route, idx) => {
            const isSelected = idx === selectedRouteIdx;
            const isShortest = idx === routeData.shortest_route_index;
            const color = ROUTE_COLORS[idx % ROUTE_COLORS.length];
            const label = ROUTE_LABELS[idx] || `Route ${idx + 1}`;

            return (
              <button
                key={idx}
                onClick={() => setSelectedRouteIdx(idx)}
                id={`route-btn-${idx}`}
                className={`w-full glass-panel p-4 text-left transition-all duration-300 group ${
                  isSelected
                    ? 'border-raksha-500/50 shadow-lg shadow-raksha-500/10 scale-[1.02]'
                    : 'hover:border-surface-600 hover:scale-[1.01]'
                }`}
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2.5">
                    <div
                      className="w-4 h-4 rounded-full ring-2 ring-offset-1 ring-offset-surface-900 transition-all"
                      style={{
                        background: color,
                        '--tw-ring-color': color,
                        boxShadow: isSelected ? `0 0 12px ${color}60` : 'none',
                      } as React.CSSProperties}
                    />
                    <span className="text-sm font-semibold text-white">{label}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    {isShortest && (
                      <span className="flex items-center gap-1 text-[9px] font-bold uppercase bg-safe-500/20 text-safe-400 px-2 py-0.5 rounded-full border border-safe-500/30">
                        <Star size={10} /> Shortest
                      </span>
                    )}
                    {isSelected && (
                      <span className="flex items-center gap-1 text-[9px] font-bold uppercase bg-raksha-500/20 text-raksha-400 px-2 py-0.5 rounded-full border border-raksha-500/30">
                        <Zap size={10} /> Active
                      </span>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-2">
                  <div className="flex items-center gap-1.5">
                    <Ruler size={12} className="text-surface-500" />
                    <span className="text-xs text-surface-300">{route.distance.toFixed(1)} km</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Clock size={12} className="text-surface-500" />
                    <span className="text-xs text-surface-300">{route.time} min</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <MapPin size={12} className="text-surface-500" />
                    <span className="text-xs text-surface-300">{route.path.length} pts</span>
                  </div>
                </div>

                {/* Mini progress bar showing relative distance */}
                {routeData && (
                  <div className="mt-2.5">
                    <div className="h-1 bg-surface-800 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-500"
                        style={{
                          width: `${Math.min(100, (route.distance / Math.max(...routeData.routes.map((r) => r.distance))) * 100)}%`,
                          background: color,
                          opacity: isSelected ? 1 : 0.5,
                        }}
                      />
                    </div>
                  </div>
                )}
              </button>
            );
          })}

          {!loading && routeData && routeData.routes.length === 0 && (
            <div className="glass-panel p-6 text-center">
              <MapPin size={24} className="text-surface-600 mx-auto mb-2" />
              <p className="text-sm text-surface-500">No routes available for this zone.</p>
            </div>
          )}

          {!loading && !routeData && selectedZone && (
            <div className="glass-panel p-6 text-center">
              <Navigation size={24} className="text-surface-600 mx-auto mb-2" />
              <p className="text-sm text-surface-500">Select a zone to view routes.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default memo(RoutingPanel);
