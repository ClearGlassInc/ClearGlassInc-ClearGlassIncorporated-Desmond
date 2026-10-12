import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DELOS OS — Synthetic World Operations",
  description: "Design reality. Test every outcome. A governed synthetic-world simulation command center by ClearGlass Inc.",
  robots: { index: false, follow: false }
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
