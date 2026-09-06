'use client';

import { motion } from '@/lib/motion-shim';
import { Activity, Wind } from 'lucide-react';
import { RingGauge } from './RingGauge';

interface AirflowGaugeProps {
  value: number;
  onChange: (val: number) => void;
}

export function AirflowGauge({ value, onChange }: AirflowGaugeProps) {
  const velocity = Math.round(240 + value * 8.6);

  return (
    <div className="space-y-5">
      <RingGauge value={value} label="Quantum-optimized supply velocity" unit="CFM%" gradientId="airflow" />
      <div className="grid grid-cols-2 gap-3 text-sm">
        <motion.div className="rounded-2xl border border-cyan-300/20 bg-cyan-300/10 p-3" whileHover={{ scale: 1.02 }}>
          <Wind className="mb-2 h-4 w-4 text-cyan-200" />
          <div className="text-white/50">Supply rate</div>
          <div className="text-lg font-semibold text-white">{velocity} CFM</div>
        </motion.div>
        <motion.div className="rounded-2xl border border-emerald-300/20 bg-emerald-300/10 p-3" whileHover={{ scale: 1.02 }}>
          <Activity className="mb-2 h-4 w-4 text-emerald-200" />
          <div className="text-white/50">Turbulence</div>
          <div className="text-lg font-semibold text-white">{Math.max(3, 18 - Math.round(value / 8))}%</div>
        </motion.div>
      </div>
      <label className="flex items-center justify-between text-sm text-white/60">
        <span className="flex items-center gap-2"><Wind className="h-4 w-4 text-cyan-300" /> Manual override</span>
        <span>{value}%</span>
      </label>
      <input aria-label="Airflow rate" type="range" min="0" max="100" value={value} onChange={(e) => onChange(Number(e.target.value))} className="w-full accent-cyan-400" />
    </div>
  );
}
