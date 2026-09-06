/*!
 * ClearGlass Writing Help — a blog assistant for GitHub Pages.
 *
 * Zero-dependency, self-contained widget. Injects a floating button + side
 * panel with writing tools for the ClearGlass Insights desk.
 *
 * Modes:
 *   LOCAL (default) — everything runs in the browser. Deterministic tools
 *     (keywords, reading level, tone check, internal links, headline & outline
 *     generators) compute real results; generative tools (rewrite, polish,
 *     summarize, CTA) produce a copy-ready expert prompt tuned to the
 *     ClearGlass house style, for pasting into any AI chat.
 *   API — set window.CG_WRITER_CONFIG = { endpoint: "https://your-proxy/..." }
 *     BEFORE this script loads and generative tools will POST
 *     {task, input, tone, targetWords} to your backend proxy instead.
 *     Never put an API key in this file or anywhere in the browser.
 *     See blog/assistant/README.md for a secure proxy example.
 */
(function () {
  "use strict";
  if (window.__cgWriter) return; // idempotent

  var CFG = Object.assign({ endpoint: null, postsIndex: null }, window.CG_WRITER_CONFIG || {});
  // Resolve posts.json relative to the /blog/ directory regardless of page depth.
  if (!CFG.postsIndex) {
    CFG.postsIndex = /\/blog\//.test(location.pathname) ? location.pathname.replace(/\/blog\/.*$/, "/blog/posts.json") : "/blog/posts.json";
  }
  var HISTORY_KEY = "cg-writer-history-v1";
  var MAX_HISTORY = 20;

  /* ---------------------------------------------------------------- data */

  var CATEGORIES = ["Governed AI", "Autonomous Agents", "Cybersecurity Architecture", "OSINT Workflows", "AI Automation", "Financial Crime Detection", "High-Trust Software Engineering", "Policy-as-Code", "Intelligence Operations", "Founder Field Notes"];

  var HEADLINE_FORMULAS = [
    function (t) { return "The " + t + " Problem Is Not What You Think — It Is Accountability"; },
    function (t) { return "The " + cap(t) + " Pattern Serious Teams Ship Before They Scale"; },
    function (t) { return "12 Controls Every " + cap(t) + " Workflow Needs Before Production"; },
    function (t) { return "What We Would Never Let " + cap(t) + " Do Without Human Approval"; },
    function (t) { return cap(t) + ": The Architecture That Survives Contact With Reality"; },
    function (t) { return "Stop Measuring " + cap(t) + " by Volume. Measure It by Decisions."; },
    function (t) { return "A Field Guide to " + cap(t) + " for Teams Whose Mistakes Have Consequences"; },
    function (t) { return "The Boring " + cap(t) + " Discipline That Outperforms the Clever One"; }
  ];

  var OUTLINES = {
    "Technical deep dive": ["TL;DR / core thesis (3–4 bullets, each defensible)", "Lede: the operational problem, stated in consequences", "01 · Why the naive approach collapses", "02 · The architecture (diagram + typed contracts)", "03 · The governing rules (policy, risk bands, approvals)", "04 · Implementation: schemas + code the reader can lift", "05 · Failure modes and how the design bounds them", "06 · Scenario walkthrough, end to end", "Pull quote worth citing", "CTA: advisory / related briefs / series link"],
    "Tutorial": ["What you'll build and why it matters (one paragraph)", "Prerequisites and assumptions, stated honestly", "Step 1..N — each step: goal, code, verification", "The mistakes people make at each step (callouts)", "Full working result + how to verify it", "Where to extend it next", "Related briefs + series link"],
    "Release notes": ["Headline change in one sentence a busy reader keeps", "What shipped (grouped: features / fixes / governance)", "What changed for existing users — breaking first", "The one migration snippet people actually need", "What's next on the roadmap", "Where to send feedback"],
    "Thought leadership": ["Contrarian thesis, stated in the first two sentences", "The consensus view and the strongest case for it", "Why it fails in practice — named evidence", "The alternative model (give it a memorable name)", "What this predicts — falsifiable claims", "What to do Monday morning", "CTA: newsletter / briefing"]
  };

  var STOPWORDS = ("a,an,and,are,as,at,be,but,by,for,from,has,have,if,in,into,is,it,its,not,of,on,or,such,that,the,their,then,there,these,they,this,to,was,we,were,will,with,you,your,i,our,can,should,would,could,than,more,most,also,it's,about,over,after,before,when,what,which,who,how,why,do,does,did,so,no,yes,up,out,just,like,get,make,made,use,used,using,one,two,new").split(",");

  var HEDGES = ["maybe", "perhaps", "somewhat", "arguably", "sort of", "kind of", "i think", "we believe", "it seems", "possibly", "might be", "could be", "in my opinion", "basically", "actually", "very", "really", "quite", "pretty much"];
  var BUZZWORDS = ["synergy", "leverage", "cutting-edge", "revolutionary", "game-changing", "next-generation", "seamless", "robust", "world-class", "best-in-class", "innovative", "disruptive", "state-of-the-art", "paradigm", "holistic", "empower", "unlock", "supercharge"];

  var HOUSE_STYLE = "House style: founder-led field journal for engineers, analysts, and security leaders. Confident, precise, zero hype. Every claim defensible; every framework implementable; active voice; short sentences carrying one idea each; technical terms used exactly. Never fabricate metrics, customers, or urgency.";

  /* ---------------------------------------------------------------- utils */

  function cap(s) { s = String(s || "").trim(); return s ? s[0].toUpperCase() + s.slice(1) : s; }
  function esc(s) { var d = document.createElement("div"); d.textContent = s == null ? "" : String(s); return d.innerHTML; }
  function words(s) { return (String(s || "").toLowerCase().match(/[a-z0-9'-]+/g) || []); }
  function sentences(s) { return String(s || "").split(/[.!?]+[\s$]/).filter(function (x) { return x.trim().length > 1; }); }
  function syllables(w) { w = w.toLowerCase().replace(/[^a-z]/g, ""); if (!w) return 0; var m = w.replace(/e$/, "").match(/[aeiouy]{1,2}/g); return Math.max(1, m ? m.length : 1); }

  function keywordsOf(text, n) {
    var freq = {};
    words(text).forEach(function (w) { if (w.length > 2 && STOPWORDS.indexOf(w) === -1) freq[w] = (freq[w] || 0) + 1; });
    return Object.keys(freq).sort(function (a, b) { return freq[b] - freq[a]; }).slice(0, n || 12).map(function (k) { return { word: k, count: freq[k] }; });
  }

  function fleschKincaid(text) {
    var ws = words(text), ss = sentences(text);
    if (!ws.length || !ss.length) return null;
    var syl = ws.reduce(function (a, w) { return a + syllables(w); }, 0);
    var grade = 0.39 * (ws.length / ss.length) + 11.8 * (syl / ws.length) - 15.59;
    var ease = 206.835 - 1.015 * (ws.length / ss.length) - 84.6 * (syl / ws.length);
    return { grade: Math.max(0, Math.round(grade * 10) / 10, 0), ease: Math.round(ease), wordsPerSentence: Math.round((ws.length / ss.length) * 10) / 10 };
  }

  function loadHistory() { try { return JSON.parse(localStorage.getItem(HISTORY_KEY)) || []; } catch (e) { return []; } }
  function saveHistory(items) { try { localStorage.setItem(HISTORY_KEY, JSON.stringify(items.slice(0, MAX_HISTORY))); } catch (e) { /* private mode */ } }
  function pushHistory(entry) { var h = loadHistory(); h.unshift(entry); saveHistory(h); }

  var postsCache = null;
  function fetchPosts() {
    if (postsCache) return Promise.resolve(postsCache);
    return fetch(CFG.postsIndex).then(function (r) { return r.json(); }).then(function (j) { postsCache = j; return j; }).catch(function () { return { posts: [] }; });
  }

  /* ---------------------------------------------------------------- tools */
  /* Each tool returns { html } or a Promise of it. `input` = textarea text,
     `opts` = { tone, targetWords }. */

  function block(title, body, copyText) {
    return '<div class="cgw-block"><div class="cgw-block-head"><b>' + esc(title) + "</b>" +
      (copyText != null ? '<button class="cgw-copy" data-copy="' + esc(copyText) + '">Copy</button>' : "") +
      '</div><div class="cgw-block-body">' + body + "</div></div>";
  }

  function promptBlock(taskLabel, promptText) {
    var note = CFG.endpoint ? "" : '<p class="cgw-note">Local mode: paste this prompt into your AI chat of choice. Set <code>window.CG_WRITER_CONFIG.endpoint</code> to run it through your secure proxy instead.</p>';
    return note + block(taskLabel + " — expert prompt", "<pre>" + esc(promptText) + "</pre>", promptText);
  }

  function generative(task, taskLabel, buildPrompt) {
    return function (input, opts) {
      if (!input.trim()) return { html: '<p class="cgw-note">Paste or type some text first.</p>' };
      var prompt = buildPrompt(input, opts);
      if (!CFG.endpoint) return { html: promptBlock(taskLabel, prompt) };
      return fetch(CFG.endpoint, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task: task, input: input, tone: opts.tone, targetWords: opts.targetWords })
      }).then(function (r) { if (!r.ok) throw new Error("proxy " + r.status); return r.json(); })
        .then(function (j) { var out = j.output || j.text || JSON.stringify(j); return { html: block(taskLabel, "<pre>" + esc(out) + "</pre>", out) }; })
        .catch(function (e) { return { html: '<p class="cgw-note">Proxy error (' + esc(e.message) + "). Falling back to the copy-ready prompt.</p>" + promptBlock(taskLabel, prompt) }; });
    };
  }

  var TOOLS = {
    topics: {
      label: "Brainstorm topics", hint: "Seed with a subject, e.g. “agent audit logs”.",
      run: function (input) {
        var seed = input.trim() || "governed AI";
        var cats = CATEGORIES.slice(0, 5);
        var out = HEADLINE_FORMULAS.map(function (f) { return f(seed); });
        var angles = cats.map(function (c) { return c + " angle: “" + seed + "” for readers who own that risk."; });
        return { html: block("Headline candidates (viral headline system)", "<ol><li>" + out.map(esc).join("</li><li>") + "</li></ol>", out.join("\n")) + block("Cluster angles", "<ul><li>" + angles.map(esc).join("</li><li>") + "</li></ul>") };
      }
    },
    outline: {
      label: "Generate outline", hint: "Type the working title; pick post type below.",
      extra: '<select class="cgw-select" id="cgw-outline-type" aria-label="Post type">' + Object.keys(OUTLINES).map(function (k) { return "<option>" + esc(k) + "</option>"; }).join("") + "</select>",
      run: function (input) {
        var type = (document.getElementById("cgw-outline-type") || {}).value || "Technical deep dive";
        var items = OUTLINES[type];
        var text = (input.trim() ? input.trim() + "\n\n" : "") + items.map(function (x, i) { return (i + 1) + ". " + x; }).join("\n");
        return { html: block(type + " outline" + (input.trim() ? " — “" + esc(input.trim().slice(0, 60)) + "”" : ""), "<ol><li>" + items.map(esc).join("</li><li>") + "</li></ol>", text) };
      }
    },
    seo: {
      label: "SEO titles + description", hint: "Paste your draft or topic.",
      run: function (input) {
        var kws = keywordsOf(input, 5).map(function (k) { return k.word; });
        var seed = kws.slice(0, 2).join(" ") || input.trim().slice(0, 40) || "your topic";
        var titles = HEADLINE_FORMULAS.slice(0, 5).map(function (f) { var t = f(seed); return t.length > 62 ? t.slice(0, 59) + "…" : t; });
        var desc = "How to design " + seed + " that survives production: patterns, schemas, and governance rules from the ClearGlass Insights desk.";
        return { html: block("Title candidates (≤ 60 chars)", "<ol><li>" + titles.map(esc).join("</li><li>") + "</li></ol>", titles.join("\n")) + block("Meta description (" + desc.length + " chars)", "<p>" + esc(desc) + "</p>", desc) + (kws.length ? block("Detected keywords", "<p>" + kws.map(esc).join(", ") + "</p>") : "") };
      }
    },
    links: {
      label: "Suggest internal links", hint: "Paste a draft; matches against the live post index.",
      run: function (input) {
        if (!input.trim()) return { html: '<p class="cgw-note">Paste your draft first — suggestions are scored against blog/posts.json.</p>' };
        var draftKw = keywordsOf(input, 30).map(function (k) { return k.word; });
        return fetchPosts().then(function (idx) {
          var scored = (idx.posts || []).map(function (p) {
            var hay = (p.title + " " + p.description + " " + (p.tags || []).join(" ") + " " + (p.categories || []).join(" ")).toLowerCase();
            var score = draftKw.reduce(function (a, w) { return a + (hay.indexOf(w) !== -1 ? 1 : 0); }, 0);
            return { p: p, score: score };
          }).filter(function (x) { return x.score > 0; }).sort(function (a, b) { return b.score - a.score; }).slice(0, 4);
          if (!scored.length) return { html: '<p class="cgw-note">No strong matches in the index yet. Link to the pillar post and your series page as a baseline.</p>' };
          var html = scored.map(function (x) {
            var snippet = '<a class="link" href="' + esc(x.p.url) + '">' + esc(x.p.title) + "</a>";
            return '<li><b>' + esc(x.p.title) + "</b> — relevance " + x.score + '<br><code>' + esc(snippet) + "</code></li>";
          }).join("");
          return { html: block("Internal link candidates (per the SEO blueprint: pillar + series + 2 related)", "<ul>" + html + "</ul>") };
        });
      }
    },
    keywords: {
      label: "Keywords + auto-tags", hint: "Paste a draft to extract candidates.",
      run: function (input) {
        var ks = keywordsOf(input, 12);
        if (!ks.length) return { html: '<p class="cgw-note">Paste your draft first.</p>' };
        var tags = ks.slice(0, 6).map(function (k) { return k.word.replace(/[^a-z0-9]+/g, "-"); });
        return { html: block("Top keywords", "<p>" + ks.map(function (k) { return esc(k.word) + " ×" + k.count; }).join(" · ") + "</p>") + block("Suggested tags", "<p>" + tags.map(esc).join(", ") + "</p>", tags.join(", ")) };
      }
    },
    readability: {
      label: "Reading level + stats", hint: "Paste a draft for Flesch–Kincaid analysis.",
      run: function (input) {
        var fk = fleschKincaid(input);
        if (!fk) return { html: '<p class="cgw-note">Paste your draft first.</p>' };
        var ws = words(input).length;
        var verdict = fk.grade <= 10 ? "On target for a technical field journal." : fk.grade <= 13 ? "Acceptable for deep dives; tighten long sentences." : "Dense — split sentences and cut subordinate clauses.";
        return { html: block("Readability", "<p><b>" + ws + "</b> words · <b>~" + Math.max(1, Math.round(ws / 220)) + " min</b> read · grade level <b>" + fk.grade + "</b> · reading ease <b>" + fk.ease + "</b> · " + fk.wordsPerSentence + " words/sentence</p><p>" + esc(verdict) + "</p>") };
      }
    },
    tone: {
      label: "Tone check", hint: "Flags hedging, buzzwords, and drift from house style.",
      run: function (input) {
        if (!input.trim()) return { html: '<p class="cgw-note">Paste your draft first.</p>' };
        var low = input.toLowerCase();
        var hedges = HEDGES.filter(function (h) { return low.indexOf(h) !== -1; });
        var buzz = BUZZWORDS.filter(function (b) { return low.indexOf(b) !== -1; });
        var exclaims = (input.match(/!/g) || []).length;
        var issues = [];
        if (hedges.length) issues.push("<li><b>Hedging</b>: " + hedges.map(esc).join(", ") + " — state the claim or cut it.</li>");
        if (buzz.length) issues.push("<li><b>Buzzwords</b>: " + buzz.map(esc).join(", ") + " — replace with the specific mechanism.</li>");
        if (exclaims > 1) issues.push("<li><b>" + exclaims + " exclamation marks</b> — the desk speaks in periods.</li>");
        var body = issues.length ? "<ul>" + issues.join("") + "</ul>" : "<p>Clean. Confident, precise, zero hype — matches the house style.</p>";
        return { html: block("Tone report", body) };
      }
    },
    rewrite: {
      label: "Rewrite for clarity",
      hint: "Generative — uses your proxy if configured, else builds an expert prompt.",
      run: generative("rewrite", "Rewrite for clarity", function (input, o) {
        return HOUSE_STYLE + "\n\nRewrite the passage below for clarity in a " + o.tone + " tone" + (o.targetWords ? ", at roughly " + o.targetWords + " words" : "") + ". Preserve every technical claim exactly; do not add facts. Return only the rewrite.\n\n---\n" + input;
      })
    },
    polish: {
      label: "One-click polish",
      hint: "Select text on the page first, or paste it here.",
      run: generative("polish", "Polish", function (input, o) {
        return HOUSE_STYLE + "\n\nPolish the text below: fix grammar, tighten sentences, keep the author's voice and all technical content. Tone: " + o.tone + ". Return only the polished text.\n\n---\n" + input;
      })
    },
    summarize: {
      label: "Summarize / TL;DR",
      hint: "Generates the dark TL;DR block used at the top of every brief.",
      run: generative("summarize", "TL;DR", function (input, o) {
        return HOUSE_STYLE + "\n\nWrite a 'Core thesis' TL;DR for the post below: 3–4 bullets, each a defensible claim with the key term bolded, ≤ 25 words per bullet. Return only the bullets.\n\n---\n" + input;
      })
    },
    cta: {
      label: "Call-to-action",
      hint: "Drafts the advisory CTA block for the end of a post.",
      run: generative("cta", "CTA", function (input, o) {
        return HOUSE_STYLE + "\n\nWrite a closing CTA for the post below: one kicker line (≤ 6 words), one headline as a question the target reader is already asking (≤ 12 words), one supporting sentence naming what ClearGlass advisory does, and two button labels (primary: request a briefing; secondary: more insights). No hype, no fake urgency. Tone: " + o.tone + ".\n\n---\n" + input;
      })
    }
  };

  /* ------------------------------------------------------------------ UI */

  var css = "" +
    /* Docked mode (default): the pill lives inside #cg-dock, flush against the
       coin badge on its right. Negative right margin tucks the pill's rounded end
       under the circular coin so the two fuse into one continuous control; the
       extra right padding keeps the label clear of the overlap. Same dark glass +
       blue/violet ring as the coin so they read as one material and glow. */
    "#cgw-fab{position:relative;margin:0 -20px 0 0;display:inline-flex;align-items:center;gap:8px;padding:12px 34px 12px 18px;border-radius:999px;border:1px solid rgba(124,150,255,.5);border-right-color:rgba(124,150,255,.12);background:linear-gradient(180deg,rgba(18,20,42,.94),rgba(11,12,28,.94));color:#eaf3ff;font:700 13.5px/1 Inter,system-ui,sans-serif;cursor:pointer;box-shadow:0 6px 22px rgba(0,0,0,.4),0 0 18px rgba(96,165,250,.32);backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px);transition:box-shadow .2s ease,color .2s ease}" +
    "#cgw-fab:hover{color:#fff;box-shadow:0 8px 26px rgba(0,0,0,.5),0 0 30px rgba(96,165,250,.55),0 0 46px rgba(167,139,250,.35)}" +
    "#cgw-fab .dot{width:7px;height:7px;border-radius:50%;background:#55f2a6;box-shadow:0 0 8px #55f2a6;animation:cgwDot 2.4s ease-in-out infinite}" +
    "@keyframes cgwDot{0%,100%{opacity:1}50%{opacity:.45}}" +
    /* Fallback: if the shared dock isn't on the page, pin to the corner solo. */
    "#cgw-fab.cgw-fab-float{position:fixed;right:18px;bottom:18px;z-index:9000;margin:0;padding:12px 18px;border-right-color:rgba(124,150,255,.5)}" +
    "@media(max-width:640px){#cgw-fab{padding:11px 30px 11px 16px;font-size:12.5px}}" +
    "#cgw-panel{position:fixed;top:0;right:0;height:100dvh;width:min(430px,100vw);z-index:9001;background:#0a111e;color:#dbe7ff;border-left:1px solid rgba(180,214,255,.18);box-shadow:-24px 0 70px rgba(0,0,0,.5);display:flex;flex-direction:column;transform:translateX(102%);transition:transform .32s cubic-bezier(.16,1,.3,1);font-family:Inter,system-ui,sans-serif}" +
    "#cgw-panel.open{transform:none}" +
    "#cgw-panel *{box-sizing:border-box}" +
    ".cgw-head{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:16px 18px;border-bottom:1px solid rgba(180,214,255,.14)}" +
    ".cgw-head b{font-size:15px;color:#fff}.cgw-head small{display:block;color:#7f8db0;font-size:11px;margin-top:2px}" +
    ".cgw-x{background:none;border:1px solid rgba(180,214,255,.2);color:#aab8d8;border-radius:10px;width:32px;height:32px;cursor:pointer;font-size:15px}" +
    ".cgw-x:hover{color:#fff;border-color:#39d8ff}" +
    ".cgw-tools{display:flex;flex-wrap:wrap;gap:6px;padding:12px 16px;border-bottom:1px solid rgba(180,214,255,.1)}" +
    ".cgw-tool{border:1px solid rgba(180,214,255,.18);background:rgba(255,255,255,.05);color:#c6d4f2;border-radius:999px;padding:7px 11px;font:600 11px/1 'IBM Plex Mono',monospace;letter-spacing:.04em;cursor:pointer;text-transform:uppercase}" +
    ".cgw-tool[aria-pressed=true]{background:linear-gradient(135deg,#39d8ff,#55f2a6);color:#031016;border-color:transparent}" +
    ".cgw-body{flex:1;overflow-y:auto;padding:14px 16px;display:flex;flex-direction:column;gap:12px}" +
    ".cgw-hint{color:#8a97ba;font-size:12px}" +
    ".cgw-input{width:100%;min-height:110px;resize:vertical;border-radius:12px;border:1px solid rgba(180,214,255,.2);background:#060b15;color:#eef4ff;padding:12px;font:500 13px/1.5 Inter,system-ui,sans-serif}" +
    ".cgw-input:focus{outline:none;border-color:#39d8ff;box-shadow:0 0 0 3px rgba(57,216,255,.15)}" +
    ".cgw-row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}" +
    ".cgw-select,.cgw-num{border-radius:10px;border:1px solid rgba(180,214,255,.2);background:#060b15;color:#dbe7ff;padding:8px 10px;font:600 12px Inter,system-ui,sans-serif}" +
    ".cgw-num{width:110px}" +
    ".cgw-run{margin-left:auto;border:0;border-radius:999px;padding:10px 18px;font:800 13px Inter,system-ui,sans-serif;background:linear-gradient(135deg,#39d8ff,#55f2a6);color:#031016;cursor:pointer}" +
    ".cgw-run:hover{filter:brightness(1.08)}" +
    ".cgw-count{font:600 11px 'IBM Plex Mono',monospace;color:#7f8db0}" +
    ".cgw-out{display:flex;flex-direction:column;gap:10px}" +
    ".cgw-block{border:1px solid rgba(180,214,255,.16);border-radius:14px;background:rgba(255,255,255,.04);overflow:hidden}" +
    ".cgw-block-head{display:flex;justify-content:space-between;align-items:center;gap:8px;padding:10px 12px;border-bottom:1px solid rgba(180,214,255,.1);font-size:12px;color:#fff}" +
    ".cgw-block-body{padding:12px;font-size:13px;line-height:1.55;color:#c6d4f2}" +
    ".cgw-block-body pre{white-space:pre-wrap;word-break:break-word;font:500 12px/1.55 'IBM Plex Mono',monospace;color:#d9ffe9;margin:0}" +
    ".cgw-block-body ol,.cgw-block-body ul{margin:0;padding-left:18px}.cgw-block-body li{margin-bottom:7px}" +
    ".cgw-block-body code{font:500 11px 'IBM Plex Mono',monospace;background:rgba(0,0,0,.35);padding:2px 5px;border-radius:6px;color:#9fe8ff;word-break:break-all}" +
    ".cgw-copy{border:1px solid rgba(180,214,255,.25);background:none;color:#9fe8ff;border-radius:8px;padding:5px 10px;font:700 11px Inter,system-ui,sans-serif;cursor:pointer}" +
    ".cgw-copy:hover{border-color:#39d8ff;color:#fff}" +
    ".cgw-note{color:#ffd166;font-size:12px;line-height:1.5;margin:0}" +
    ".cgw-note code{font-family:'IBM Plex Mono',monospace;font-size:11px}" +
    ".cgw-hist{border-top:1px solid rgba(180,214,255,.12);padding:10px 16px 14px}" +
    ".cgw-hist summary{cursor:pointer;font:700 11px 'IBM Plex Mono',monospace;letter-spacing:.08em;color:#8a97ba;text-transform:uppercase}" +
    ".cgw-hist ul{list-style:none;margin:8px 0 0;padding:0;max-height:140px;overflow-y:auto}" +
    ".cgw-hist li{padding:7px 8px;border-radius:8px;font-size:12px;color:#aab8d8;cursor:pointer;display:flex;justify-content:space-between;gap:8px}" +
    ".cgw-hist li:hover{background:rgba(255,255,255,.06);color:#fff}" +
    ".cgw-hist .t{font-family:'IBM Plex Mono',monospace;font-size:10px;color:#66739a;flex-shrink:0}" +
    "@media(prefers-reduced-motion:reduce){#cgw-panel{transition:none}#cgw-fab{transition:none}#cgw-fab .dot{animation:none}}" +
    "@media print{#cgw-fab,#cgw-panel{display:none!important}}";

  var style = document.createElement("style");
  style.textContent = css;
  document.head.appendChild(style);

  var fab = document.createElement("button");
  fab.id = "cgw-fab";
  fab.setAttribute("aria-haspopup", "dialog");
  fab.setAttribute("aria-expanded", "false");
  fab.innerHTML = '<span class="dot" aria-hidden="true"></span>Writing help';
  // Dock the pill into the shared corner cluster (left of the coin badge) so the
  // two flow together as one control. Fall back to a solo fixed pill if the dock
  // isn't present (e.g. the badge script didn't load).
  var dock = document.getElementById("cg-dock");
  if (dock) { dock.insertBefore(fab, dock.firstChild); }
  else { fab.classList.add("cgw-fab-float"); document.body.appendChild(fab); }

  var panel = document.createElement("aside");
  panel.id = "cgw-panel";
  panel.setAttribute("role", "dialog");
  panel.setAttribute("aria-modal", "false");
  panel.setAttribute("aria-label", "ClearGlass writing assistant");
  panel.innerHTML =
    '<div class="cgw-head"><div><b>Writing help</b><small>ClearGlass Insights desk assistant · ' + (CFG.endpoint ? "proxy mode" : "local mode") + '</small></div><button class="cgw-x" aria-label="Close writing help">✕</button></div>' +
    '<div class="cgw-tools" role="tablist" aria-label="Writing tools">' +
    Object.keys(TOOLS).map(function (k, i) { return '<button class="cgw-tool" role="tab" data-tool="' + k + '" aria-pressed="' + (i === 0) + '">' + esc(TOOLS[k].label) + "</button>"; }).join("") +
    "</div>" +
    '<div class="cgw-body">' +
    '<p class="cgw-hint" id="cgw-hint"></p>' +
    '<div id="cgw-extra"></div>' +
    '<textarea class="cgw-input" id="cgw-input" aria-label="Your text" placeholder="Paste a draft, a paragraph, or a topic seed…"></textarea>' +
    '<div class="cgw-row">' +
    '<select class="cgw-select" id="cgw-tone" aria-label="Tone"><option>authoritative</option><option>conversational</option><option>executive-brief</option><option>tutorial-friendly</option><option>urgent-but-factual</option></select>' +
    '<input class="cgw-num" id="cgw-words" type="number" min="0" step="50" placeholder="target words" aria-label="Target word count"/>' +
    '<span class="cgw-count" id="cgw-count">0 words</span>' +
    '<button class="cgw-run" id="cgw-run">Run →</button>' +
    "</div>" +
    '<div class="cgw-out" id="cgw-out" aria-live="polite"></div>' +
    "</div>" +
    '<details class="cgw-hist"><summary>Recent requests</summary><ul id="cgw-histlist"></ul></details>';
  document.body.appendChild(panel);

  var input = panel.querySelector("#cgw-input"),
    out = panel.querySelector("#cgw-out"),
    hint = panel.querySelector("#cgw-hint"),
    extra = panel.querySelector("#cgw-extra"),
    count = panel.querySelector("#cgw-count"),
    histList = panel.querySelector("#cgw-histlist");
  var activeTool = Object.keys(TOOLS)[0];
  var lastFocus = null;

  function setTool(key) {
    activeTool = key;
    panel.querySelectorAll(".cgw-tool").forEach(function (b) { b.setAttribute("aria-pressed", String(b.dataset.tool === key)); });
    hint.textContent = TOOLS[key].hint || "";
    extra.innerHTML = TOOLS[key].extra || "";
  }

  function renderHistory() {
    var h = loadHistory();
    histList.innerHTML = h.length ? h.map(function (e, i) {
      return '<li data-i="' + i + '"><span>' + esc(TOOLS[e.tool] ? TOOLS[e.tool].label : e.tool) + " · " + esc((e.input || "").slice(0, 34)) + '…</span><span class="t">' + esc(e.at) + "</span></li>";
    }).join("") : '<li style="cursor:default">Nothing yet.</li>';
  }

  function openPanel() {
    lastFocus = document.activeElement;
    panel.classList.add("open");
    fab.setAttribute("aria-expanded", "true");
    // one-click polish: preload selected page text
    var sel = String(window.getSelection ? window.getSelection() : "").trim();
    if (sel && !input.value.trim()) { input.value = sel; setTool("polish"); updateCount(); }
    renderHistory();
    setTimeout(function () { input.focus(); }, 80);
  }
  function closePanel() {
    panel.classList.remove("open");
    fab.setAttribute("aria-expanded", "false");
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }

  function updateCount() { count.textContent = words(input.value).length + " words"; }

  function run() {
    var tool = TOOLS[activeTool];
    var opts = { tone: panel.querySelector("#cgw-tone").value, targetWords: parseInt(panel.querySelector("#cgw-words").value, 10) || 0 };
    out.innerHTML = '<p class="cgw-hint">Working…</p>';
    Promise.resolve(tool.run(input.value, opts)).then(function (res) {
      out.innerHTML = res.html;
      pushHistory({ tool: activeTool, input: input.value.slice(0, 240), at: new Date().toISOString().slice(11, 16), fullInput: input.value.slice(0, 4000) });
      renderHistory();
    }).catch(function (e) {
      out.innerHTML = '<p class="cgw-note">Something went wrong: ' + esc(e.message) + "</p>";
    });
  }

  /* events */
  fab.addEventListener("click", function () { panel.classList.contains("open") ? closePanel() : openPanel(); });
  panel.querySelector(".cgw-x").addEventListener("click", closePanel);
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && panel.classList.contains("open")) closePanel();
    // focus trap while open
    if (e.key === "Tab" && panel.classList.contains("open")) {
      var f = panel.querySelectorAll("button,select,input,textarea,summary,[tabindex]");
      if (!f.length) return;
      var first = f[0], last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) { last.focus(); e.preventDefault(); }
      else if (!e.shiftKey && document.activeElement === last) { first.focus(); e.preventDefault(); }
    }
  });
  panel.querySelector(".cgw-tools").addEventListener("click", function (e) {
    var b = e.target.closest("[data-tool]");
    if (b) setTool(b.dataset.tool);
  });
  panel.querySelector("#cgw-run").addEventListener("click", run);
  input.addEventListener("input", updateCount);
  input.addEventListener("keydown", function (e) { if ((e.metaKey || e.ctrlKey) && e.key === "Enter") run(); });
  out.addEventListener("click", function (e) {
    var b = e.target.closest(".cgw-copy");
    if (!b) return;
    var txt = b.getAttribute("data-copy");
    (navigator.clipboard ? navigator.clipboard.writeText(txt) : Promise.reject()).then(function () {
      b.textContent = "Copied ✓"; setTimeout(function () { b.textContent = "Copy"; }, 1500);
    }).catch(function () { /* clipboard unavailable */ });
  });
  histList.addEventListener("click", function (e) {
    var li = e.target.closest("[data-i]");
    if (!li) return;
    var entry = loadHistory()[+li.dataset.i];
    if (!entry) return;
    input.value = entry.fullInput || entry.input || "";
    setTool(TOOLS[entry.tool] ? entry.tool : activeTool);
    updateCount();
    input.focus();
  });

  setTool(activeTool);
  window.__cgWriter = { open: openPanel, close: closePanel, tools: Object.keys(TOOLS), config: CFG };
})();
