/* ClearGlass · governed editorial visuals
   Contextually places reviewed concept artwork on four approved pages.
   The module is additive, idempotent, dependency-free, and fail-quiet.
   Embedded artwork text is never promoted to machine-readable factual copy. */
(function () {
  "use strict";

  if (window.__cgEditorialVisuals) return;
  window.__cgEditorialVisuals = true;

  var page = (location.pathname.split("/").pop() || "").toLowerCase();
  var ITEMS = {
    "cyber-defense-console.html": {
      signal: "Incident simulation lens",
      title: "See the breach as an operating system problem.",
      copy: "A useful incident visual should move the reader from alarm to architecture: exposed identity, disrupted services, containment decisions, evidence preservation, recovery sequencing, and accountable human command.",
      src: "/assets/images/editorial/municipal-cyber-tabletop-concept.webp",
      width: 240,
      height: 360,
      alt: "Concept artwork showing a municipal cyber incident command interface over an aerial city map",
      disclosure: "Illustrative municipal ransomware tabletop scenario. It is not a report of an actual City of Burlington incident; dates, actors, records, and impacts shown in the artwork are fictional unless separately verified.",
      links: [
        ["Continuous threat-modeling framework", "/blog/autonomous-threat-modeling-2026.html"],
        ["Autonomous threat-modeling service", "/offers/autonomous-threat-modeling.html"]
      ],
      tone: "orange"
    },
    "advanced-features-tools-systems.html": {
      signal: "System decomposition",
      title: "Architecture becomes manageable when the layers are visible.",
      copy: "ClearGlass models systems as connected layers—interface, compute, storage, network, power, telemetry, policy, and recovery—so dependencies and failure boundaries can be reviewed before automation acts.",
      src: "/assets/images/editorial/laptop-system-decomposition-concept.webp",
      width: 240,
      height: 360,
      alt: "Conceptual exploded view of a laptop separated into display, chassis, thermal, compute, storage, wireless, battery, and expansion layers",
      disclosure: "Conceptual system-decomposition graphic. Component layout, numbering, and labels are illustrative and are not repair, safety, or service documentation.",
      links: [
        ["Map system relationships with AutoMap", "/automap.html"],
        ["Review governed autonomous operations", "/percival-os.html"]
      ],
      tone: "cyan"
    },
    "revenue-engine.html": {
      signal: "Growth operations concept",
      title: "Treat acquisition as an instrumented decision system.",
      copy: "The useful pattern is not visual spectacle. It is a controlled loop connecting audience hypotheses, creative tests, attribution, unit economics, approval gates, and post-campaign evidence.",
      src: "/assets/images/editorial/marketing-command-center-concept.webp",
      width: 400,
      height: 273,
      alt: "Concept artwork of a futuristic marketing command center with campaign, audience, funnel, and unit-economics panels",
      disclosure: "Concept artwork for a paid-growth operations interface. Names, seals, dashboards, metrics, people, and campaign claims in the artwork are not certifications, affiliations, customers, or measured results.",
      links: [
        ["Ethical sales-system playbook", "/blog/ethical-sales-system-100k-revenue-prompt.html"],
        ["Review ClearGlass engagements", "/offers/index.html"]
      ],
      tone: "gold"
    },
    "button-lab.html": {
      signal: "Trust-interface prototype",
      title: "Proof design must never outrun proof itself.",
      copy: "A premium testimonial treatment can establish hierarchy and confidence, but publication governance matters more than typography: attribution, permission, exact wording, role, organization, and evidence must be verified before an endorsement is presented as real.",
      src: "/assets/images/editorial/verified-trust-layout-concept.webp",
      width: 864,
      height: 1080,
      alt: "Sample dark testimonial layout with large quotation typography and a blue circuit-board motif",
      disclosure: "Sample testimonial-layout design. The displayed name, title, quotation, and endorsement are placeholder creative and are not presented as a verified customer testimonial.",
      links: [
        ["Explore web design and development", "/web-design.html"],
        ["Begin governed client onboarding", "/operations/client-onboarding.html"]
      ],
      tone: "violet"
    }
  };

  var item = ITEMS[page];
  if (!item) return;

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text) node.textContent = text;
    return node;
  }

  function addStyles() {
    if (document.getElementById("cg-editorial-visual-styles")) return;
    var style = document.createElement("style");
    style.id = "cg-editorial-visual-styles";
    style.textContent = [
      ".cgev{--cgev-a:#56e7ff;--cgev-b:#9b8cff;position:relative;z-index:1;width:min(1120px,92vw);margin:clamp(54px,8vw,100px) auto;padding:clamp(18px,3vw,32px);border:1px solid rgba(120,190,255,.25);border-radius:20px;background:linear-gradient(145deg,rgba(7,14,28,.94),rgba(11,18,38,.88));box-shadow:0 32px 86px -48px rgba(0,0,0,.95),0 0 34px rgba(70,190,255,.08);color:#edf7ff;font-family:Inter,system-ui,-apple-system,sans-serif;overflow:hidden}",
      ".cgev[data-tone='orange']{--cgev-a:#ff9a52;--cgev-b:#ff5e39}.cgev[data-tone='gold']{--cgev-a:#ffd66b;--cgev-b:#ff9a52}.cgev[data-tone='violet']{--cgev-a:#bba5ff;--cgev-b:#54d9ff}",
      ".cgev:before{content:'';position:absolute;inset:0 0 auto;height:2px;background:linear-gradient(90deg,transparent,var(--cgev-a),var(--cgev-b),transparent)}",
      ".cgev__grid{display:grid;grid-template-columns:minmax(220px,.78fr) minmax(0,1.22fr);gap:clamp(24px,5vw,64px);align-items:center}",
      ".cgev__media{margin:0;position:relative}.cgev__frame{padding:8px;border:1px solid rgba(140,205,255,.28);border-radius:16px;background:rgba(2,7,16,.72);box-shadow:inset 0 0 30px rgba(80,200,255,.06),0 24px 54px -34px rgba(0,0,0,.95)}",
      ".cgev__frame img{display:block;width:100%;height:auto;max-height:620px;object-fit:contain;border-radius:11px;background:#030711}",
      ".cgev__caption{margin-top:11px;color:#91a6c2;font:500 .72rem/1.55 ui-monospace,SFMono-Regular,Consolas,monospace}",
      ".cgev__signal{display:inline-flex;align-items:center;gap:9px;color:var(--cgev-a);font:700 .7rem/1.3 ui-monospace,SFMono-Regular,Consolas,monospace;letter-spacing:.16em;text-transform:uppercase}",
      ".cgev__signal:before{content:'';width:24px;height:1px;background:var(--cgev-a);box-shadow:0 0 10px var(--cgev-a)}",
      ".cgev h2{margin:15px 0 17px;color:#f5fbff;font-size:clamp(1.8rem,3.7vw,3.25rem);line-height:1.03;letter-spacing:-.035em;font-weight:760}",
      ".cgev__copy{margin:0;color:#aec0d6;font-size:clamp(.98rem,1.35vw,1.12rem);line-height:1.72;max-width:64ch}",
      ".cgev__notice{margin:20px 0 0;padding:13px 15px;border-left:3px solid var(--cgev-a);border-radius:0 9px 9px 0;background:rgba(116,155,205,.08);color:#c7d7e8;font-size:.84rem;line-height:1.55}",
      ".cgev__notice strong{color:var(--cgev-a);letter-spacing:.04em}",
      ".cgev__links{display:flex;flex-wrap:wrap;gap:10px;margin-top:22px}.cgev__links a{display:inline-flex;align-items:center;text-decoration:none;color:#eaf7ff;font-weight:700;font-size:.84rem;padding:10px 13px;border:1px solid rgba(130,200,255,.28);border-radius:999px;background:rgba(47,93,145,.13);transition:transform .18s,border-color .18s,box-shadow .18s}",
      ".cgev__links a:hover{transform:translateY(-1px);border-color:var(--cgev-a);box-shadow:0 0 22px rgba(80,205,255,.12)}.cgev__links a:focus-visible{outline:2px solid var(--cgev-a);outline-offset:3px}",
      "@media(max-width:760px){.cgev__grid{grid-template-columns:1fr}.cgev__media{max-width:520px;margin-inline:auto}.cgev{width:min(94vw,1120px)}}",
      "@media(prefers-reduced-motion:reduce){.cgev__links a{transition:none}}"
    ].join("");
    document.head.appendChild(style);
  }

  function build() {
    if (document.getElementById("cg-editorial-visual")) return;
    addStyles();

    var section = el("section", "cgev");
    section.id = "cg-editorial-visual";
    section.dataset.tone = item.tone;
    section.setAttribute("aria-labelledby", "cgev-title");

    var grid = el("div", "cgev__grid");
    var figure = el("figure", "cgev__media");
    var frame = el("div", "cgev__frame");
    var image = document.createElement("img");
    image.src = item.src;
    image.width = item.width;
    image.height = item.height;
    image.alt = item.alt;
    image.loading = "lazy";
    image.decoding = "async";
    image.fetchPriority = "low";
    frame.appendChild(image);
    figure.appendChild(frame);
    figure.appendChild(el("figcaption", "cgev__caption", "Concept visualization · editorial context only"));

    var body = el("div", "cgev__body");
    body.appendChild(el("span", "cgev__signal", item.signal));
    var heading = el("h2", "", item.title);
    heading.id = "cgev-title";
    body.appendChild(heading);
    body.appendChild(el("p", "cgev__copy", item.copy));

    var notice = el("p", "cgev__notice");
    var noticeLabel = el("strong", "", "Disclosure — ");
    notice.appendChild(noticeLabel);
    notice.appendChild(document.createTextNode(item.disclosure));
    body.appendChild(notice);

    var links = el("nav", "cgev__links");
    links.setAttribute("aria-label", "Related ClearGlass resources");
    item.links.forEach(function (entry) {
      var anchor = el("a", "", entry[0]);
      anchor.href = entry[1];
      links.appendChild(anchor);
    });
    body.appendChild(links);

    grid.appendChild(figure);
    grid.appendChild(body);
    section.appendChild(grid);

    var related = document.getElementById("cg-related");
    if (related && related.parentNode) {
      related.parentNode.insertBefore(section, related);
      return;
    }
    var footer = document.querySelector("footer");
    if (footer && footer.parentNode) {
      footer.parentNode.insertBefore(section, footer);
      return;
    }
    (document.querySelector("main") || document.body).appendChild(section);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", build, { once: true });
  } else {
    build();
  }
})();
