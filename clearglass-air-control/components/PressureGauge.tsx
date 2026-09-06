'use client';

import { motion } from '@/lib/motion-shim';
import { Gauge, Minus, Plus } from 'lucide-react';

export function PressureGauge({ value, onChange }: { value: number; onChange: (val: number) => void }) {
  const pct = ((value - 0.5) / 4) * 100;
  const status = value >= 2.2 && value <= 3.1 ? 'Positive pressure stable' : value < 2.2 ? 'Increase pressure delta' : 'Bleed-off recommended';

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between">
        <Gauge className="h-8 w-8 text-emerald-300" />
        <div className="text-right"><div className="text-6xl font-semibold tracking-[-3px]">{value.toFixed(1)}</div><div className="text-white/50">Pa differential</div></div>
      </div>
      <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
        <div className="mb-3 flex items-center justify-between text-xs uppercase tracking-[2px] text-white/45"><Minus className="h-4 w-4" /> Isolation corridor <Plus className="h-4 w-4" /></div>
        <div className="h-3 overflow-hidden rounded-full bg-white/10"><motion.div className="h-full rounded-full bg-gradient-to-r from-cyan-400 via-emerald-400 to-amber-300" animate={{ width: `${pct}%` }} transition={{ type: 'spring', stiffness: 120, damping: 18 }} /></div>
      </div>
      <div className="text-sm text-emerald-100/80">{status}</div>
      <input aria-label="Pressure differential" type="range" min="0.5" max="4.5" step="0.1" value={value} onChange={(e) => onChange(Number(e.target.value))} className="w-full accent-emerald-400" />
    </div>
  );
}
