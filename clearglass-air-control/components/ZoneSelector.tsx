'use client';

import { motion } from '@/lib/motion-shim';
import { Building2, Users } from 'lucide-react';
import { zones, ZoneId } from '@/lib/types';

export function ZoneSelector({ activeZone, onZoneChange }: { activeZone: ZoneId; onZoneChange: (zone: ZoneId) => void }) {
  return (
    <div className="grid gap-3">
      {zones.map((zone) => {
        const isActive = activeZone === zone.id;
        return (
          <motion.button key={zone.id} type="button" onClick={() => onZoneChange(zone.id)} whileHover={{ x: 3, scale: 1.01 }} whileTap={{ scale: 0.98 }} className={`rounded-2xl border px-4 py-3 text-left transition ${isActive ? 'border-cyan-300/60 bg-cyan-300/15 text-cyan-100 shadow-[0_0_24px_rgba(34,211,238,0.16)]' : 'border-white/10 bg-white/5 text-white/60 hover:border-white/25'}`}>
            <div className="flex items-center justify-between gap-3"><span className="font-medium">{zone.id}</span><span className="text-xs capitalize">{zone.pressureMode}</span></div>
            <div className="mt-2 flex items-center justify-between text-xs text-white/45"><span className="flex items-center gap-1"><Building2 className="h-3 w-3" />{zone.label}</span><span className="flex items-center gap-1"><Users className="h-3 w-3" />{zone.nodes} nodes</span></div>
          </motion.button>
        );
      })}
    </div>
  );
}
