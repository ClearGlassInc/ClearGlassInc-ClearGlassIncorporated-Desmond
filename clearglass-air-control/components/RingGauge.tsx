'use client';

import { motion } from '@/lib/motion-shim';

interface RingGaugeProps {
  value: number;
  max?: number;
  label: string;
  unit: string;
  gradientId: string;
}

export function RingGauge({ value, max = 100, label, unit, gradientId }: RingGaugeProps) {
  const radius = 78;
  const circumference = 2 * Math.PI * radius;
  const pct = Math.max(0, Math.min(1, value / max));
  return (
    <div className="flex flex-col items-center justify-center gap-4">
      <svg viewBox="0 0 200 200" className="h-56 w-56 drop-shadow-[0_0_22px_rgba(34,211,238,0.26)]">
        <defs><linearGradient id={gradientId} x1="0" x2="1"><stop stopColor="#22d3ee"/><stop offset="1" stopColor="#34d399"/></linearGradient></defs>
        <circle cx="100" cy="100" r={radius} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="14" />
        <motion.circle cx="100" cy="100" r={radius} fill="none" stroke={`url(#${gradientId})`} strokeLinecap="round" strokeWidth="14" strokeDasharray={circumference} animate={{ strokeDashoffset: circumference * (1 - pct) }} transform="rotate(-90 100 100)" />
        <text x="100" y="96" textAnchor="middle" className="fill-white text-4xl font-semibold">{Math.round(value)}</text>
        <text x="100" y="123" textAnchor="middle" className="fill-white/50 text-sm uppercase tracking-[3px]">{unit}</text>
      </svg>
      <div className="text-center text-xs uppercase tracking-[3px] text-cyan-200/70">{label}</div>
    </div>
  );
}
