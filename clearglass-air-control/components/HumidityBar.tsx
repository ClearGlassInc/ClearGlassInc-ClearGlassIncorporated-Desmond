'use client';

import { motion } from '@/lib/motion-shim';
import { Droplets } from 'lucide-react';

export function HumidityBar({ value, onChange }: { value: number; onChange: (val: number) => void }) {
  const bars = Array.from({ length: 20 });

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between"><Droplets className="h-8 w-8 text-cyan-300" /><span className="text-5xl font-semibold">{value}%</span></div>
      <div className="grid grid-cols-20 gap-1" style={{ gridTemplateColumns: 'repeat(20, minmax(0, 1fr))' }}>
        {bars.map((_, i) => {
          const active = i < value / 5;
          return <motion.div key={i} initial={false} animate={{ opacity: active ? 1 : 0.34, scaleY: active ? 1 : 0.72 }} className={`h-16 origin-bottom rounded-full ${active ? 'bg-cyan-300/80 shadow-[0_0_12px_rgba(103,232,249,0.4)]' : 'bg-white/10'}`} />;
        })}
      </div>
      <div className="rounded-2xl border border-cyan-300/15 bg-cyan-300/10 p-3 text-sm text-cyan-50/75">Dewpoint guardrails active · target band 40–48%</div>
      <input aria-label="Humidity percentage" type="range" min="20" max="80" value={value} onChange={(e) => onChange(Number(e.target.value))} className="w-full accent-cyan-300" />
    </div>
  );
}
