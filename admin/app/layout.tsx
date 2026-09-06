import type { ReactNode } from "react";
import type { Metadata } from "next";

export const metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3001"),
  title: "ClearGlass Commerce — Admin Cockpit",
  description: "Orders, products, inventory, analytics, and the approval gate.",
  // Same holographic seal the marketing site uses as its tab icon, served from
  // this app's own public/ since it deploys on a separate origin.
  icons: {
    icon: "/clearglass-seal-192.png",
    shortcut: "/clearglass-seal-192.png",
    apple: "/clearglass-seal-192.png",
  },
  alternates: { canonical: "/" },
  openGraph: {
    title: "ClearGlass Commerce — Admin Cockpit",
    description: "Orders, products, inventory, analytics, and the approval gate.",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body
        style={{
          margin: 0,
          fontFamily: "Inter, system-ui, sans-serif",
          background: "#070a14",
          color: "#eef2ff",
        }}
      >
        {/* Keyboard/screen-reader skip link — first focusable element on the page. */}
        <a
          href="#main-content"
          style={{
            position: "absolute",
            left: -9999,
            top: 0,
            padding: "10px 14px",
            background: "#1a2340",
            color: "#eef2ff",
            borderRadius: 8,
            zIndex: 100,
          }}
          // Reveal on focus without any client JS or blocking behavior.
          className="cg-skip-link"
        >
          Skip to main content
        </a>
        <style>{`.cg-skip-link:focus{left:12px;top:12px;}`}</style>

        <nav
          aria-label="Primary"
          style={{
            display: "flex",
            gap: 18,
            alignItems: "center",
            padding: "14px 24px",
            borderBottom: "1px solid rgba(124,150,255,.16)",
          }}
        >
          <strong>Admin Cockpit</strong>
          <a href="/" style={{ color: "#9fc4ff" }}>
            Overview
          </a>
          <a href="/approvals" style={{ color: "#9fc4ff" }}>
            Approvals
          </a>
          <a href="/audit" style={{ color: "#9fc4ff" }}>
            Audit
          </a>
          <a href="/playbooks" style={{ color: "#9fc4ff" }}>
            Playbooks
          </a>
          {/* Logout is a real form POST — works without JavaScript. */}
          <form method="post" action="/api/auth/logout" style={{ marginLeft: "auto" }}>
            <button
              type="submit"
              style={{
                background: "transparent",
                border: "1px solid rgba(124,150,255,.3)",
                color: "#9fc4ff",
                borderRadius: 8,
                padding: "6px 12px",
                cursor: "pointer",
              }}
            >
              Sign out
            </button>
          </form>
        </nav>
        <main style={{ maxWidth: 1080, margin: "0 auto", padding: 24 }}>{children}</main>
        <footer aria-label="Copyright notice" style={{ maxWidth: 1080, margin: "0 auto", padding: "0 24px 24px", color: "#aab6d3" }}>
          <small>© {new Date().getFullYear()} ClearGlass Inc. All rights reserved.</small>
        </footer>
      </body>
    </html>
  );
}
