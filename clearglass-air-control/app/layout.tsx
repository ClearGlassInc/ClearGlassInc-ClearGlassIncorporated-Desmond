import type { Metadata } from 'next';
import type { ReactNode } from 'react';
import './globals.css';

export const metadata: Metadata = {
  // Same holographic seal the marketing site uses as its tab icon, served from
  // this app's own public/ since it deploys on a separate origin.
  icons: {
    icon: '/clearglass-seal-192.png',
    shortcut: '/clearglass-seal-192.png',
    apple: '/clearglass-seal-192.png',
  },
  title: 'ClearGlass Air Systems Control Surface',
  description: 'Quantum-neural smart glass air systems control surface prototype for ClearGlassInc Artemis.',
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
