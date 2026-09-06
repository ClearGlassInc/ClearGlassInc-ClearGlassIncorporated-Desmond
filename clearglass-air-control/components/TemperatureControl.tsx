'use client';

import { motion } from '@/lib/motion-shim';
import { Snowflake, ThermometerSun } from 'lucide-react';

export function TemperatureControl({ value, onChange }: { value: number; onChange: (val: number) => void }) {
  const width = ((value - 16) / 12) * 100;
  const comfort = Math.max(0, 100 - Math.round(Math.abs(value - 22) * 12));

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <Snowflake className="mt-4 h-6 w-6 text-cyan-300" />
        <div className="text-right"><div className="text-[72px] font-semibold tabular-nums tracking-[-4px]">{value.toFixed(1)}</div><div className="text-2xl text-white/60">°C</div></div>
      </div>
      <input aria-label="Temperature setpoint" type="range" min="16" max="28" step="0.1" value={value} onChange={(e) => onChange(parseFloat(e.target.value))} className="w-full accent-cyan-400" />
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs uppercase tracking-[2px] text-white/45"><span>Cooling</span><ThermometerSun className="h-4 w-4 text-amber-200" /><span>Heating</span></div>
        <div className="h-2 overflow-hidden rounded-full bg-white/10"><motion.div className="h-full bg-gradient-to-r from-cyan-400 via-emerald-400 to-amber-400" animate={{ width: `${width}%` }} transition={{ type: 'spring', bounce: 0.2 }} /></div>
      </div>
      <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-3 text-sm text-white/60">Occupant comfort confidence <span className="font-semibold text-white">{comfort}%</span></div>
    </div>
  );
}
