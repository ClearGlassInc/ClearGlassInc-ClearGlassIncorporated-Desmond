import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";
import { getActor } from "@/lib/auth/server";
import { can } from "@/lib/auth/roles";
import { config } from "@/lib/config";
import { signOut } from "./actions";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "ClearGlass OSINT Fraud Detection - Prototype",
  description: "Evidence-first investigation workspace. Local prototype on synthetic data.",
  robots: { index: false, follow: false },
};

const NAV = [
  { href: "/", label: "Overview" },
  { href: "/investigations", label: "Investigations" },
  { href: "/alerts", label: "Alert queue" },
  { href: "/evidence", label: "Evidence library" },
  { href: "/incidents", label: "Incidents" },
  { href: "/rules", label: "Pattern registry" },
  { href: "/entities", label: "Entity explorer" },
  { href: "/import", label: "Import center" },
  { href: "/audit", label: "Audit view", permission: "audit:view" as const },
];

export default async function RootLayout({ children }: { children: ReactNode }) {
  const actor = await getActor();
  const demo = config().demoAuthEnabled;
  return (
    <html lang="en-CA">
      <body>
        <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 btn">
          Skip to content
        </a>
        {demo ? (
          <div role="note" className="border-b border-amber-300/30 bg-amber-300/10 px-4 py-1.5 text-center text-xs font-medium text-amber-100">
            DEMO AUTHENTICATION - local development only. Anyone who can reach this app can choose a demo user.
          </div>
        ) : null}
        <div className="border-b border-white/10 bg-black/20 px-4 py-1.5 text-center text-xs text-slate-300">
          Prototype workspace. Records labelled <strong className="text-amber-200">Synthetic</strong> are fixtures, not real cases. Rule matches are reasons to
          review, not findings of fraud.
        </div>
        <div className="mx-auto flex max-w-[92rem] gap-6 px-4 py-6 lg:px-6">
          {actor ? (
            <nav aria-label="Workspace" className="hidden w-56 shrink-0 lg:block">
              <div className="glass sticky top-6 p-4">
                <div className="mb-4">
                  <div className="text-base font-semibold tracking-tight text-white">
                    Clear<span className="text-cyan-300">Glass</span>
                  </div>
                  <div className="text-[11px] uppercase tracking-[0.18em] text-slate-400">OSINT fraud detection</div>
                </div>
                <ul className="space-y-1">
                  {NAV.filter((n) => !n.permission || can(actor.role, n.permission)).map((n) => (
                    <li key={n.href}>
                      <a href={n.href} className="block rounded-md px-2 py-1.5 text-sm text-slate-200 no-underline hover:bg-white/10 hover:no-underline">
                        {n.label}
                      </a>
                    </li>
                  ))}
                </ul>
                <div className="mt-6 border-t border-white/10 pt-4 text-xs">
                  <div className="text-slate-200">{actor.name}</div>
                  <div className="text-slate-400">Role: {actor.role.replace("_", "-").toLowerCase()}</div>
                  <form action={signOut} className="mt-2">
                    <button className="btn-quiet text-xs" type="submit">
                      Sign out
                    </button>
                  </form>
                </div>
              </div>
            </nav>
          ) : null}
          <div className="min-w-0 flex-1">
            {actor ? (
              <nav aria-label="Workspace (compact)" className="mb-4 flex gap-2 overflow-x-auto lg:hidden">
                {NAV.filter((n) => !n.permission || can(actor.role, n.permission)).map((n) => (
                  <a key={n.href} href={n.href} className="btn-quiet whitespace-nowrap text-xs">
                    {n.label}
                  </a>
                ))}
              </nav>
            ) : null}
            <main id="main">{children}</main>
          </div>
        </div>
      </body>
    </html>
  );
}
