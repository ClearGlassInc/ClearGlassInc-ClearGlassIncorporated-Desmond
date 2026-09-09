import Link from "next/link";

const modules = [
  { title: "Dual-Lens Evidence", text: "Compare independent capture channels, timestamps, hashes and sensor attestations before accepting a visual claim." },
  { title: "Live Integrity Monitor", text: "Flag discontinuities, metadata drift and provenance breaks without modifying the source evidence." },
  { title: "Correction Lab", text: "Run an isolated, reversible simulation showing how a manipulated narrative could diverge from the evidence ledger." },
  { title: "Influence Graph", text: "Map actors, evidence, decisions and dependencies with explicit confidence and provenance." },
  { title: "Human Gate", text: "Require analyst approval before a finding becomes an operational decision or external report." },
  { title: "Audit Ledger", text: "Persist append-oriented events so every finding can be reconstructed and independently reviewed." },
];

const demoEvents = [
  ["21:47:08", "CAM-A", "Frame sequence verified", "PASS"],
  ["21:47:08", "CAM-B", "Independent capture aligned", "PASS"],
  ["21:47:09", "PROV", "Source hash matched ledger", "PASS"],
  ["21:47:11", "ANALYST", "Narrative claim requires review", "HOLD"],
];

export default function RealityForensicsPage() {
  return (
    <main className="min-h-screen bg-black text-white px-6 py-10 md:px-12">
      <div className="mx-auto max-w-7xl">
        <nav className="mb-12 flex items-center justify-between border-b border-white/10 pb-5 text-sm">
          <Link href="/" className="font-semibold tracking-[0.2em]">CLEARGLASS</Link>
          <div className="flex gap-5 text-white/60"><Link href="/insights">Insights</Link><Link href="/dashboard">Command</Link></div>
        </nav>

        <section className="grid gap-10 lg:grid-cols-[1.2fr_.8fr] items-end">
          <div>
            <p className="mb-4 text-xs font-semibold uppercase tracking-[0.35em] text-red-400">Reality Integrity / Defensive Research</p>
            <h1 className="max-w-4xl text-5xl font-semibold tracking-tight md:text-7xl">TRUTH FABRIC<br/><span className="text-white/40">FORENSICS</span></h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-white/65">A ClearGlass research system for detecting provenance breaks, comparing independent evidence channels, modelling synthetic-media risk, and preserving a defensible chain of custody.</p>
            <div className="mt-8 flex flex-wrap gap-3"><span className="rounded-full border border-green-400/30 bg-green-400/10 px-4 py-2 text-xs text-green-300">EVIDENCE-FIRST</span><span className="rounded-full border border-white/15 px-4 py-2 text-xs text-white/60">HUMAN-GATED</span><span className="rounded-full border border-white/15 px-4 py-2 text-xs text-white/60">SIMULATION ONLY</span></div>
          </div>
          <div className="rounded-3xl border border-white/10 bg-white/[.045] p-6 shadow-2xl backdrop-blur-xl">
            <div className="flex justify-between text-xs uppercase tracking-widest text-white/40"><span>Integrity Score</span><span>LIVE DEMO</span></div>
            <div className="mt-6 text-7xl font-light">98.7<span className="text-2xl text-white/30">%</span></div>
            <div className="mt-5 h-2 overflow-hidden rounded-full bg-white/10"><div className="h-full w-[98.7%] bg-red-500" /></div>
            <p className="mt-4 text-sm text-white/50">Confidence is derived from independent evidence consistency—not from model confidence alone.</p>
          </div>
        </section>

        <section className="mt-20 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {modules.map((m, i) => <article key={m.title} className="group rounded-3xl border border-white/10 bg-white/[.035] p-7 transition hover:border-red-400/40 hover:bg-white/[.06]"><div className="text-xs text-red-400">0{i + 1}</div><h2 className="mt-8 text-xl font-medium">{m.title}</h2><p className="mt-3 leading-7 text-white/50">{m.text}</p></article>)}
        </section>

        <section className="mt-20 rounded-3xl border border-white/10 bg-white/[.035] p-6 md:p-8">
          <div className="flex flex-wrap items-end justify-between gap-4"><div><p className="text-xs uppercase tracking-[.3em] text-red-400">Evidence Stream</p><h2 className="mt-2 text-3xl font-semibold">Chain-of-custody monitor</h2></div><span className="rounded-full border border-green-400/30 px-3 py-1 text-xs text-green-300">4 / 4 CHECKS</span></div>
          <div className="mt-8 overflow-x-auto"><table className="w-full min-w-[620px] text-left text-sm"><thead className="border-b border-white/10 text-white/35"><tr><th className="py-3">TIME</th><th>SOURCE</th><th>EVENT</th><th>STATE</th></tr></thead><tbody>{demoEvents.map(([time, source, event, state]) => <tr key={time + source} className="border-b border-white/5"><td className="py-4 font-mono text-white/45">{time}</td><td className="font-mono text-white/55">{source}</td><td>{event}</td><td className={state === "PASS" ? "text-green-300" : "text-yellow-300"}>{state}</td></tr>)}</tbody></table></div>
        </section>

        <section className="mt-20 grid gap-6 lg:grid-cols-3">
          {[["01", "CAPTURE", "Preserve original media, metadata and cryptographic hashes."],["02", "CORRELATE", "Compare independent channels and identify temporal or provenance anomalies."],["03", "DECIDE", "Produce a confidence-bounded finding and stop at a human authorization gate."]].map(([n,t,d]) => <div key={n} className="border-t border-white/15 pt-5"><span className="text-xs text-red-400">{n}</span><h3 className="mt-5 text-2xl">{t}</h3><p className="mt-2 text-white/50 leading-7">{d}</p></div>)}
        </section>

        <footer className="mt-24 border-t border-white/10 py-8 text-xs leading-6 text-white/35">ClearGlass Truth Fabric Forensics is a defensive research and evidence-integrity architecture. It does not provide covert surveillance, biometric targeting, political manipulation, unauthorized access, or instructions for defeating security controls. Synthetic-media analysis is probabilistic and requires independent validation.</footer>
      </div>
    </main>
  );
}
