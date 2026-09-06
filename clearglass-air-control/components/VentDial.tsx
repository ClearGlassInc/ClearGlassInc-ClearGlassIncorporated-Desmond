'use client';

import { motion } from '@/lib/motion-shim';
import { Compass, RotateCcw } from 'lucide-react';

export function VentDial({ value, onChange }: { value: number; onChange: (val: number) => void }) {
  return (
    <div className="space-y-6">
      <div className="relative mx-auto flex h-52 w-52 items-center justify-center rounded-full border border-white/15 bg-white/5 shadow-[inset_0_0_32px_rgba(255,255,255,0.04)]">
        <Compass className="absolute h-44 w-44 text-white/10" />
        <motion.div className="absolute h-3 w-24 origin-left rounded-full bg-gradient-to-r from-cyan-300 to-emerald-300 shadow-[0_0_20px_rgba(34,211,238,0.45)]" style={{ left: '50%' }} animate={{ rotate: value - 90 }} transition={{ type: 'spring', stiffness: 140, damping: 16 }} />
        <div className="z-10 rounded-full border border-white/10 bg-[#0a0f1e]/90 p-5 text-center backdrop-blur-xl"><RotateCcw className="mx-auto h-5 w-5 text-cyan-300" /><div className="text-3xl font-semibold">{value}°</div></div>
      </div>
      <div className="flex justify-between text-xs uppercase tracking-[2px] text-white/45"><span>Laminar</span><span>Vector sweep</span></div>
      <input aria-label="Vent vector angle" type="range" min="0" max="90" value={value} onChange={(e) => onChange(Number(e.target.value))} className="w-full accent-cyan-400" />
    </div>
  );
}
