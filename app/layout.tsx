import type { Metadata } from "next";
import type { ReactNode } from "react";

import "@/components/motion/motion-tokens.css";
import "@/components/motion/motion-components.css";

export const metadata: Metadata = {
  title: "ClearGlass Inc.",
  description:
    "ClearGlass Inc. designs high-performance websites and intelligent digital systems.",
};

/**
 * Root layout. The App Router requires one, and this project had none — so
 * `next build` failed outright with "doesn't have a root layout" before this
 * file existed. Server Component: no client JS is introduced here.
 */
export default function RootLayout({
  children,
}: {
  children: ReactNode;
}): React.JSX.Element {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
