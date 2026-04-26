/**
 * Full-screen map page.
 */
import { Zone, Shelter, Volunteer } from '../lib/supabase';
import LiveMap from '../components/LiveMap';

interface MapPageProps {
  zones: Zone[];
  shelters: Shelter[];
  volunteers: Volunteer[];
}

export default function MapPage({ zones, shelters, volunteers }: MapPageProps) {
  return (
    <div className="h-[calc(100vh-4rem)] animate-fade-in" id="map-page">
      <div className="glass-panel p-1 h-full">
        <LiveMap zones={zones} shelters={shelters} volunteerCount={volunteers.length} />
      </div>
    </div>
  );
}
