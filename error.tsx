"use client";
export default function ErrorPage({ reset }: { reset: () => void }) { return <main className="fallback"><h1>Signal surface unavailable</h1><p>The ClearGlass website remains usable. No unverified values will be substituted.</p><button onClick={reset}>Retry snapshot</button></main>; }
