'use client';

import { motion } from '@/lib/motion-shim';
import { ReactNode } from 'react';

interface GlassPanelProps {
  children: ReactNode;
  className?: string;
  title?: string;
}

export function GlassPanel({ children, className = '', title }: GlassPanelProps) {
  return (
    <motion.section
      whileHover={{ y: -2, scale: 1.005 }}
      transition={{ type: 'spring', stiffness: 300, damping: 20 }}
      className={`relative overflow-hidden rounded-3xl border border-white/20 bg-white/5 shadow-2xl backdrop-blur-2xl ${className}`}
      style={{
        background: 'linear-gradient(145deg, rgba(255,255,255,0.08) 0%, rgba(255,255,255,0.02) 100%)',
        boxShadow: '0 8px 32px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.2)',
      }}
    >
      <div className="pointer-events-none absolute inset-0 rounded-3xl border border-cyan-400/30" />
      <div className="absolute left-0 right-0 top-0 h-px bg-gradient-to-r from-transparent via-white/40 to-transparent" />
      {title && <div className="px-6 pb-2 pt-5 text-sm font-medium uppercase tracking-[2px] text-white/70">{title}</div>}
      <div className="p-6 pt-2">{children}</div>
    </motion.section>
  );
}
