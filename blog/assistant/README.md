# ClearGlass Writing Help — blog assistant

A lightweight, modular writing assistant for the ClearGlass Insights blog on
GitHub Pages. One script tag, zero dependencies, no build step.

```html
<script defer src="assistant/writing-help.js"></script>
```

It injects a floating **“Writing help”** button (bottom-right) that opens a
side panel with the writing tools. If text is selected on the page when the
panel opens, it is preloaded into the **One-click polish** tool.

## Folder structure

```
blog/
├── index.html                 # Insights hub (search + category filters)
├── posts.json                 # machine-readable post index (drives internal-link tool)
├── feed.xml                   # RSS 2.0
├── <post>.html                # individual briefs
└── assistant/
    ├── writing-help.js        # the whole widget (UI + local engine + API adapter)
    └── README.md              # this file
```

## First-release feature set (shipped)

| Tool | Engine | Notes |
|------|--------|-------|
| Brainstorm topics | local | Viral-headline formulas × topic clusters |
| Generate outline | local | 4 post types: deep dive, tutorial, release notes, thought leadership |
| SEO titles + description | local | ≤ 60-char titles, meta description, detected keywords |
| Suggest internal links | local | Scores your draft against `posts.json`, returns ready-to-paste `<a>` snippets |
| Keywords + auto-tags | local | Frequency analysis minus stopwords |
| Reading level + stats | local | Flesch–Kincaid grade, reading ease, words/sentence, read time |
| Tone check | local | Flags hedging, buzzwords, exclamation abuse vs. house style |
| Rewrite for clarity | generative | Proxy if configured, else copy-ready expert prompt |
| One-click polish | generative | Preloads selected page text |
| Summarize / TL;DR | generative | Produces the “Core thesis” block format |
| Call-to-action | generative | Drafts the advisory CTA block |

Plus: tone selector, target word count, live word counter, request history
(last 20, `localStorage`, never leaves the browser), Cmd/Ctrl+Enter to run,
Esc to close, focus trap, `aria-*` labeling, reduced-motion support, hidden
in print.

## Two modes

### 1. No-backend (default)

Everything runs locally. Deterministic tools compute real results in the
browser. Generative tools build an expert prompt (house style baked in) with
a **Copy** button, for pasting into any AI chat. Nothing is fetched except
`posts.json` from your own origin.

### 2. API-powered via a backend proxy

Set the config **before** the script loads:

```html
<script>window.CG_WRITER_CONFIG = { endpoint: "https://writer-proxy.example.workers.dev" };</script>
<script defer src="assistant/writing-help.js"></script>
```

Generative tools then `POST {task, input, tone, targetWords}` to your proxy
and render `{output}` from the response. If the proxy errors, the widget
falls back to the copy-ready prompt automatically.

**Never ship an API key in the browser.** GitHub Pages is static — the key
must live server-side. Example Cloudflare Worker proxy:

```js
// wrangler secret put ANTHROPIC_API_KEY
const ALLOWED_ORIGIN = "https://www.clearglassinc.com";
const TASKS = new Set(["rewrite", "polish", "summarize", "cta"]);

export default {
  async fetch(req, env) {
    const headers = {
      "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
      "Access-Control-Allow-Headers": "Content-Type",
      "Content-Type": "application/json",
    };
    if (req.method === "OPTIONS") return new Response(null, { headers });
    if (req.method !== "POST") return new Response("{}", { status: 405, headers });

    const { task, input, tone, targetWords } = await req.json();
    if (!TASKS.has(task) || typeof input !== "string" || input.length > 20000)
      return new Response(JSON.stringify({ error: "bad request" }), { status: 400, headers });

    const r = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "x-api-key": env.ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
      },
      body: JSON.stringify({
        model: "claude-sonnet-5",
        max_tokens: 2000,
        system: "You are the editor of a founder-led technical field journal. Confident, precise, zero hype. Never invent facts.",
        messages: [{ role: "user", content:
          `Task: ${task}. Tone: ${tone}.` +
          (targetWords ? ` Target length: ~${targetWords} words.` : "") +
          `\n\n---\n${input}` }],
      }),
    });
    const j = await r.json();
    return new Response(JSON.stringify({ output: j.content?.[0]?.text ?? "" }), { headers });
  },
};
```

Hardening checklist for the proxy: pin the CORS origin, allowlist tasks, cap
input size, rate-limit by IP, set a monthly spend cap on the API key, and log
request counts (not content).

## Roadmap (advanced features)

1. **Content freshness check** — compare a post's `date` in `posts.json`
   against thresholds per category; surface "review by" nudges on the hub.
2. **Series-aware outlines** — read `series`/`seriesPart` from `posts.json`
   and scaffold "previously in this series" intros and next-part teasers.
3. **Front-matter generator** — emit the full `<head>` block (title, meta,
   OG/Twitter, `BlogPosting` JSON-LD) from a filled outline.
4. **Draft locker** — autosave drafts to `localStorage` with export to
   Markdown; no backend needed.
5. **Eval table helper** — paste raw numbers, get the styled comparison table
   markup used in briefs.
6. **Proxy streaming** — SSE support in API mode for long rewrites.
7. **Team presets** — load prompt presets from a `presets.json` so the desk
   can version its editorial prompts in git.

## Recommended UI copy

- Button: **“Writing help”** (calm, utility-grade; not “✨ AI Magic”).
- Panel subtitle: *“ClearGlass Insights desk assistant.”*
- Empty state: *“Paste a draft, a paragraph, or a topic seed…”*
- Proxy failure: *“Proxy error. Falling back to the copy-ready prompt.”*

## Best practices baked in

- **Performance:** one deferred script, styles injected once, no fonts or
  frameworks loaded, `posts.json` fetched once and cached in memory.
- **Privacy:** local mode sends nothing anywhere; history stays in
  `localStorage`; API mode sends only the text the author submits, to a
  proxy the site owner controls.
- **Maintainability:** every tool is an entry in the `TOOLS` map with a
  `label`, `hint`, and `run(input, opts)` — adding a tool is ~10 lines and
  cannot break the others. House style lives in one constant.
- **Accessibility:** dialog semantics, focus trap, Esc to close, visible
  focus rings, `aria-live` results region, reduced-motion respected.
