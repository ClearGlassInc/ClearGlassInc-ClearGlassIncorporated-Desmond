'use client';

import { motion } from '@/lib/motion-shim';
import { ShieldCheck, Sparkles } from 'lucide-react';
import { RingGauge } from './RingGauge';

export function FiltrationStatus({ value, onChange }: { value: number; onChange: (val: number) => void }) {
  const stages = ['HEPA', 'Carbon', 'UV-C', 'Ion'];

  return (
    <div className="space-y-4">
      <RingGauge value={value} label="HEPA + PDLC particulate confidence" unit="PURE" gradientId="filter" />
      <div className="grid grid-cols-4 gap-2">
        {stages.map((stage, index) => <motion.div key={stage} className="rounded-xl border border-emerald-300/20 bg-emerald-300/10 p-2 text-center text-xs text-emerald-100" animate={{ y: [0, -2, 0] }} transition={{ duration: 2, delay: index * 0.15, repeat: Infinity }}>{stage}</motion.div>)}
      </div>
      <div className="flex items-center justify-between rounded-2xl border border-emerald-300/20 bg-emerald-300/10 p-4 text-emerald-200"><ShieldCheck className="h-5 w-5" /><span>Bio-safe circulation nominal</span><Sparkles className="h-4 w-4" /></div>
      <input aria-label="Filtration confidence" type="range" min="70" max="100" value={value} onChange={(e) => onChange(Number(e.target.value))} className="w-full accent-emerald-400" />
    </div>
  );
}
