import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = { title: "ClearGlass Live Signal Fabric", description: "A fail-closed, verified real-time signal surface for ClearGlass Inc." };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="en"><body>{children}</body></html>; }
