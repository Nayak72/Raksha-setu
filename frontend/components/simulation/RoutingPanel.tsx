/**
 * RoutingPanel — displays rescue routes on a Leaflet map with route selection.
 * Uses plain Leaflet (same pattern as LiveMap) — no react-leaflet dependency.
 */
'use client';

import { useState, useEffect, useRef, memo } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { SimZone, SimRouteResult, fetchRoutes } from '../../lib/simulation-api';
import { Route, Clock, Ruler, Star } from 'lucide-react';

const ROUTE_COLORS = ['#1a65ff', '#ff6464', '#ffbd20', '#17b363', '#b74f06'];

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
      center: [12.9716, 77.5946],
      zoom: 13,
      zoomControl: true,
      attributionControl: false,
    });
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19 }).addTo(map);
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

    // Center on zone
    mapRef.current.setView([zone.lat, zone.lng], 13);

    // Zone marker (red dot)
    L.marker([zone.lat, zone.lng], {
      icon: L.divIcon({
        className: '',
        html: `<div style="width:16px;height:16px;border-radius:50%;background:#ff2d2d;border:3px solid white;box-shadow:0 0 12px rgba(255,45,45,0.6)"></div>`,
        iconSize: [16, 16],
        iconAnchor: [8, 8],
      }),
    })
      .bindPopup(`<b>Zone ${zone.id.slice(0, 8)}</b><br/>Severity: ${zone.severity}`)
      .addTo(layer);

    // Base marker (green dot)
    if (routeData.routes.length > 0) {
      const base = routeData.routes[0].path[0];
      L.marker(base as [number, number], {
        icon: L.divIcon({
          className: '',
          html: `<div style="width:16px;height:16px;border-radius:50%;background:#17b363;border:3px solid white;box-shadow:0 0 12px rgba(23,179,99,0.6)"></div>`,
          iconSize: [16, 16],
          iconAnchor: [8, 8],
        }),
      })
        .bindPopup('<b>Rescue Base</b>')
        .addTo(layer);
    }

    // Draw all routes
    routeData.routes.forEach((route, idx) => {
      const isSelected = idx === selectedRouteIdx;
      const polyline = L.polyline(
        route.path.map(([lat, lng]) => [lat, lng] as [number, number]),
        {
          color: ROUTE_COLORS[idx % ROUTE_COLORS.length],
          weight: isSelected ? 5 : 2,
          opacity: isSelected ? 1 : 0.4,
          dashArray: isSelected ? undefined : '8 6',
        }
      );
      polyline.on('click', () => setSelectedRouteIdx(idx));
      polyline.bindTooltip(`Route ${idx + 1} — ${route.distance.toFixed(1)} km`, {
        sticky: true,
      });
      polyline.addTo(layer);
    });
  }, [routeData, selectedRouteIdx, selectedZone, zones]);

  return (
    <div className="space-y-5">
      {/* Zone selector */}
      <div className="flex items-center gap-3">
        <Route size={16} className="text-raksha-400" />
        <select
          value={selectedZone}
          onChange={(e) => setSelectedZone(e.target.value)}
          className="input-field text-sm flex-1"
        >
          <option value="">Select a zone...</option>
          {zones.map((z) => (
            <option key={z.id} value={z.id}>
              Zone {z.id.slice(0, 8)} — {z.severity.toUpperCase()}
            </option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Map */}
        <div className="lg:col-span-2 glass-panel p-1 h-[500px] overflow-hidden rounded-2xl">
          <div ref={mapContainerRef} className="w-full h-full rounded-xl" id="routing-map" />
        </div>

        {/* Route list */}
        <div className="space-y-3">
          <h3 className="text-sm font-bold text-surface-300 uppercase tracking-wider">
            Available Routes
          </h3>

          {loading && <p className="text-sm text-surface-500 animate-pulse">Loading routes...</p>}

          {routeData?.routes.map((route, idx) => {
            const isSelected = idx === selectedRouteIdx;
            const isShortest = idx === routeData.shortest_route_index;

            return (
              <button
                key={idx}
                onClick={() => setSelectedRouteIdx(idx)}
                className={`w-full glass-panel p-4 text-left transition-all duration-300 ${
                  isSelected
                    ? 'border-raksha-500/50 shadow-lg shadow-raksha-500/10'
                    : 'hover:border-surface-600'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ background: ROUTE_COLORS[idx % ROUTE_COLORS.length] }}
                    />
                    <span className="text-sm font-semibold text-white">Route {idx + 1}</span>
                  </div>
                  {isShortest && (
                    <span className="flex items-center gap-1 text-[9px] font-bold uppercase bg-safe-500/20 text-safe-400 px-2 py-0.5 rounded-full border border-safe-500/30">
                      <Star size={10} /> Shortest
                    </span>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div className="flex items-center gap-1.5">
                    <Ruler size={12} className="text-surface-500" />
                    <span className="text-xs text-surface-300">{route.distance.toFixed(1)} km</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Clock size={12} className="text-surface-500" />
                    <span className="text-xs text-surface-300">{route.time} min</span>
                  </div>
                </div>
              </button>
            );
          })}

          {!loading && routeData && routeData.routes.length === 0 && (
            <p className="text-sm text-surface-500">No routes available.</p>
          )}
        </div>
      </div>
    </div>
  );
}

export default memo(RoutingPanel);
