/**
 * ResourceAllocationTable — shows per-shelter resource allocation.
 */
'use client';

import { memo } from 'react';
import { SimAllocation, SimShelter } from '../../lib/simulation-api';
import { Package, Bed, Heart, Users } from 'lucide-react';
import { Shelter } from '../../lib/supabase';

function ResourceAllocationTable({ 
  allocations, 
  shelters = [], 
  simShelters = [] 
}: { 
  allocations: SimAllocation[], 
  shelters?: Shelter[],
  simShelters?: SimShelter[]
}) {
  const totals = allocations.reduce(
    (acc, a) => ({
      food: acc.food + a.food_units,
      beds: acc.beds + a.beds,
      medical: acc.medical + a.medical_kits,
      teams: acc.teams + a.rescue_teams,
    }),
    { food: 0, beds: 0, medical: 0, teams: 0 }
  );

  const getShelterName = (id: string) => {
    // Check local database first
    const shelter = shelters.find(s => s.id === id);
    if (shelter?.name) return shelter.name;
    // Check simulation API database
    const simShelter = simShelters.find(s => s.shelter_id === id);
    if (simShelter?.name) return simShelter.name;
    // Fallback to truncated ID
    return id.slice(0, 8);
  };

  return (
    <div className="space-y-5">
      {/* Summary cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="glass-panel p-4">
          <div className="flex items-center gap-2 mb-2">
            <Package size={16} className="text-warning-400" />
            <span className="text-[10px] uppercase tracking-wider text-surface-500">Food Units</span>
          </div>
          <p className="text-2xl font-black text-white">{totals.food.toLocaleString()}</p>
        </div>
        <div className="glass-panel p-4">
          <div className="flex items-center gap-2 mb-2">
            <Bed size={16} className="text-raksha-400" />
            <span className="text-[10px] uppercase tracking-wider text-surface-500">Beds</span>
          </div>
          <p className="text-2xl font-black text-white">{totals.beds.toLocaleString()}</p>
        </div>
        <div className="glass-panel p-4">
          <div className="flex items-center gap-2 mb-2">
            <Heart size={16} className="text-danger-400" />
            <span className="text-[10px] uppercase tracking-wider text-surface-500">Medical Kits</span>
          </div>
          <p className="text-2xl font-black text-white">{totals.medical.toLocaleString()}</p>
        </div>
        <div className="glass-panel p-4">
          <div className="flex items-center gap-2 mb-2">
            <Users size={16} className="text-safe-400" />
            <span className="text-[10px] uppercase tracking-wider text-surface-500">Rescue Teams</span>
          </div>
          <p className="text-2xl font-black text-white">{totals.teams}</p>
        </div>
      </div>

      {/* Table */}
      <div className="glass-panel overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-surface-700/50">
              <th className="text-left text-[10px] uppercase tracking-wider text-surface-500 px-5 py-3">Shelter Name</th>
              <th className="text-right text-[10px] uppercase tracking-wider text-surface-500 px-5 py-3">Food</th>
              <th className="text-right text-[10px] uppercase tracking-wider text-surface-500 px-5 py-3">Beds</th>
              <th className="text-right text-[10px] uppercase tracking-wider text-surface-500 px-5 py-3">Medical</th>
              <th className="text-right text-[10px] uppercase tracking-wider text-surface-500 px-5 py-3">Teams</th>
            </tr>
          </thead>
          <tbody>
            {allocations.map((a) => (
              <tr
                key={a.shelter_id}
                className="border-b border-surface-800/50 hover:bg-surface-800/30 transition-colors"
              >
                <td className="px-5 py-3 text-xs font-semibold text-surface-200">
                  {getShelterName(a.shelter_id)}
                </td>
                <td className="px-5 py-3 text-right text-sm font-semibold text-warning-400">
                  {a.food_units.toLocaleString()}
                </td>
                <td className="px-5 py-3 text-right text-sm font-semibold text-raksha-400">
                  {a.beds.toLocaleString()}
                </td>
                <td className="px-5 py-3 text-right text-sm font-semibold text-danger-400">
                  {a.medical_kits.toLocaleString()}
                </td>
                <td className="px-5 py-3 text-right text-sm font-semibold text-safe-400">
                  {a.rescue_teams}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default memo(ResourceAllocationTable);
