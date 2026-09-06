(() => {
  "use strict";

  const FEED_BASE = "/feeds/minerals";
  const REQUEST_TIMEOUT_MS = 9000;

  const byId = (id) => document.getElementById(id);

  function asText(value, fallback = "—") {
    if (value === null || value === undefined || value === "") return fallback;
    return String(value);
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function safeUrl(value) {
    try {
      const url = new URL(value, window.location.origin);
      if (url.protocol === "https:" || (url.protocol === "http:" && url.hostname === "localhost")) {
        return url.href;
      }
    } catch (_) {
      return null;
    }
    return null;
  }

  async function fetchJson(path) {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
    try {
      const response = await fetch(path, {
        method: "GET",
        headers: { Accept: "application/json" },
        cache: "no-store",
        signal: controller.signal,
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const contentType = response.headers.get("content-type") || "";
      if (!contentType.includes("json") && !path.endsWith(".json")) {
        throw new Error("Unexpected response type");
      }
      return await response.json();
    } finally {
      window.clearTimeout(timeout);
    }
  }

  function normalizeStatus(value) {
    const status = String(value || "UNKNOWN").trim().toUpperCase();
    const allowed = new Set([
      "LIVE", "NEAR LIVE", "DELAYED", "DAILY", "WEEKLY", "MONTHLY",
      "STATIC REFERENCE", "STALE", "DEGRADED", "OFFLINE", "UNAVAILABLE",
      "OPERATIONAL", "HEALTHY", "UNKNOWN"
    ]);
    return allowed.has(status) ? status : "UNKNOWN";
  }

  function statusClass(status) {
    const value = normalizeStatus(status).toLowerCase();
    if (["live", "near live", "operational", "healthy", "daily", "weekly", "monthly"].includes(value)) return "healthy";
    if (["degraded", "stale", "delayed"].includes(value)) return "degraded";
    if (["offline", "unavailable"].includes(value)) return "unavailable";
    if (value === "static reference") return "static";
    return "unknown";
  }

  function formatDate(value) {
    if (!value) return "—";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "INVALID DATE";
    return new Intl.DateTimeFormat(undefined, {
      year: "numeric", month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit", timeZoneName: "short"
    }).format(date);
  }

  function renderManifest(manifest) {
    const feeds = Array.isArray(manifest.feeds) ? manifest.feeds : [];
    const healthy = feeds.filter((feed) => ["LIVE", "NEAR LIVE", "DAILY", "WEEKLY", "MONTHLY", "STATIC REFERENCE", "HEALTHY"].includes(normalizeStatus(feed.status))).length;
    const degraded = feeds.filter((feed) => ["DEGRADED", "STALE", "DELAYED", "OFFLINE", "UNAVAILABLE"].includes(normalizeStatus(feed.status))).length;
    const overall = normalizeStatus(manifest.overall_status || "UNKNOWN");

    const statusNode = byId("system-status");
    const badgeNode = byId("system-status-badge");
    if (statusNode) statusNode.textContent = overall;
    if (badgeNode) {
      badgeNode.textContent = overall;
      badgeNode.className = `status ${statusClass(overall)}`;
    }
    if (byId("feeds-healthy")) byId("feeds-healthy").textContent = `${healthy} / ${feeds.length}`;
    if (byId("feeds-degraded")) byId("feeds-degraded").textContent = String(degraded);
    if (byId("last-sync")) byId("last-sync").textContent = formatDate(manifest.generated_at);
    if (byId("pipeline-status")) byId("pipeline-status").textContent = normalizeStatus(manifest.pipeline_status || overall);
    if (byId("manifest-version")) byId("manifest-version").textContent = asText(manifest.version);
    if (byId("manifest-message")) byId("manifest-message").textContent = "Feed status is source-derived. Missing or unavailable data remains explicitly degraded or unavailable.";

    const tbody = byId("feed-table-body");
    if (!tbody) return;
    tbody.textContent = "";
    if (!feeds.length) {
      const row = document.createElement("tr");
      row.innerHTML = '<td colspan="7">No feed definitions are available.</td>';
      tbody.appendChild(row);
      return;
    }

    feeds.forEach((feed) => {
      const row = document.createElement("tr");
      const sourceUrl = safeUrl(feed.source_url);
      const sourceName = escapeHtml(asText(feed.source, "Unknown provider"));
      const sourceCell = sourceUrl
        ? `<a href="${escapeHtml(sourceUrl)}" target="_blank" rel="noopener noreferrer">${sourceName}</a>`
        : sourceName;
      const status = normalizeStatus(feed.status);
      row.innerHTML = `
        <td><strong>${escapeHtml(asText(feed.name, feed.id))}</strong></td>
        <td>${sourceCell}</td>
        <td>${escapeHtml(asText(feed.expected_frequency, "UNKNOWN"))}</td>
        <td><span class="status ${statusClass(status)}">${escapeHtml(status)}</span></td>
        <td>${escapeHtml(formatDate(feed.source_updated_at))}</td>
        <td>${escapeHtml(formatDate(feed.retrieved_at))}</td>
        <td>${Number.isFinite(Number(feed.record_count)) ? Number(feed.record_count).toLocaleString() : "—"}</td>`;
      tbody.appendChild(row);
    });
  }

  function renderManifestError(error) {
    const text = navigator.onLine ? "Manifest unavailable. The page is operating in a degraded state." : "Offline. Cached page shell is available, but live feed health cannot be verified.";
    if (byId("system-status")) byId("system-status").textContent = "DEGRADED";
    if (byId("pipeline-status")) byId("pipeline-status").textContent = "NOT VERIFIED";
    if (byId("manifest-message")) byId("manifest-message").textContent = `${text} ${error?.message || ""}`.trim();
    const badge = byId("system-status-badge");
    if (badge) {
      badge.textContent = "DEGRADED";
      badge.className = "status degraded";
    }
  }

  function mineralCard(mineral) {
    const uses = Array.isArray(mineral.industrial_uses) && mineral.industrial_uses.length
      ? mineral.industrial_uses.slice(0, 4).join(", ")
      : "UNKNOWN";
    const importance = asText(mineral.strategic_importance, "Reference profile only");
    return `
      <article class="mineral-card" data-search="${escapeHtml([mineral.name, mineral.symbol, mineral.category, uses].join(" ").toLowerCase())}">
        <header><div><p class="eyebrow">${escapeHtml(asText(mineral.category, "UNKNOWN"))}</p><h3>${escapeHtml(asText(mineral.name, "Unnamed mineral"))}</h3></div><span class="mineral-symbol">${escapeHtml(asText(mineral.symbol, "N/A"))}</span></header>
        <p>${escapeHtml(importance)}</p>
        <ul class="meta-list">
          <li><span>Industrial uses</span><strong>${escapeHtml(uses)}</strong></li>
          <li><span>Canada exposure</span><strong>${escapeHtml(asText(mineral.canada_exposure, "UNKNOWN"))}</strong></li>
          <li><span>Risk level</span><strong>${escapeHtml(asText(mineral.risk_level, "UNKNOWN"))}</strong></li>
          <li><span>Data confidence</span><strong>${escapeHtml(asText(mineral.confidence, "UNKNOWN"))}</strong></li>
        </ul>
      </article>`;
  }

  function renderMinerals(payload) {
    const minerals = Array.isArray(payload.minerals) ? payload.minerals : [];
    const grid = byId("mineral-grid");
    const count = byId("mineral-count");
    if (!grid) return;
    grid.innerHTML = minerals.map(mineralCard).join("");
    if (count) count.textContent = `${minerals.length} mineral${minerals.length === 1 ? "" : "s"}`;
    wireSearch();
  }

  function renderMineralsError() {
    const grid = byId("mineral-grid");
    if (grid) grid.innerHTML = '<p class="state-message">Mineral reference metadata is unavailable. Risk values remain UNKNOWN.</p>';
  }

  function wireSearch() {
    const input = byId("mineral-query");
    const empty = byId("mineral-empty");
    const count = byId("mineral-count");
    if (!input) return;
    const cards = Array.from(document.querySelectorAll(".mineral-card"));
    const apply = () => {
      const query = input.value.trim().toLowerCase();
      let visible = 0;
      cards.forEach((card) => {
        const match = !query || (card.dataset.search || "").includes(query);
        card.hidden = !match;
        if (match) visible += 1;
      });
      if (empty) empty.hidden = visible !== 0;
      if (count) count.textContent = `${visible} of ${cards.length} shown`;
    };
    input.addEventListener("input", apply, { passive: true });
  }

  function renderPolicy(payload) {
    const list = byId("policy-list");
    const status = byId("policy-status");
    if (!list) return;
    const records = Array.isArray(payload.records) ? payload.records : [];
    const feedStatus = normalizeStatus(payload.status || (records.length ? "DAILY" : "UNAVAILABLE"));
    if (status) {
      status.textContent = feedStatus;
      status.className = `status ${statusClass(feedStatus)}`;
    }
    if (!records.length) {
      list.innerHTML = '<p class="state-message">No validated policy records are currently published. The source remains unavailable or has produced no matching critical-minerals items.</p>';
      return;
    }
    list.innerHTML = records.slice(0, 12).map((record) => {
      const url = safeUrl(record.url);
      const title = escapeHtml(asText(record.title, "Untitled policy signal"));
      const linkedTitle = url ? `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${title}</a>` : title;
      const minerals = Array.isArray(record.affected_minerals) && record.affected_minerals.length ? record.affected_minerals.join(", ") : "General critical minerals";
      return `<article class="policy-item"><p class="eyebrow">${escapeHtml(asText(record.impact_category, "POLICY / NEWS"))}</p><h3>${linkedTitle}</h3><p>${escapeHtml(formatDate(record.published_at))} · ${escapeHtml(minerals)} · Source: ${escapeHtml(asText(record.source, "UNKNOWN"))}</p></article>`;
    }).join("");
  }

  function renderPolicyError(error) {
    const list = byId("policy-list");
    const status = byId("policy-status");
    if (status) {
      status.textContent = "DEGRADED";
      status.className = "status degraded";
    }
    if (list) list.innerHTML = `<p class="state-message">Policy feed temporarily unavailable. Last-known-good data could not be verified in this browser session. ${escapeHtml(error?.message || "")}</p>`;
  }

  function calculateHhi() {
    const input = byId("share-input");
    const output = byId("hhi-result");
    if (!input || !output) return;
    const values = input.value.split(",").map((value) => Number(value.trim())).filter((value) => Number.isFinite(value));
    if (!values.length || values.some((value) => value < 0 || value > 100)) {
      output.textContent = "Enter valid percentage shares between 0 and 100.";
      return;
    }
    const total = values.reduce((sum, value) => sum + value, 0);
    if (Math.abs(total - 100) > 0.5) {
      output.textContent = `Shares total ${total.toFixed(2)}%. Normalize the input to approximately 100% before calculating HHI.`;
      return;
    }
    const sorted = [...values].sort((a, b) => b - a);
    const hhi = values.reduce((sum, share) => sum + (share * share), 0);
    const top = (n) => sorted.slice(0, n).reduce((sum, share) => sum + share, 0);
    output.innerHTML = `<strong>HHI ${hhi.toFixed(0)}</strong><br>Top 1: ${top(1).toFixed(1)}% · Top 3: ${top(3).toFixed(1)}% · Top 5: ${top(5).toFixed(1)}%<br><small>HHI = Σ(sᵢ²), with shares entered as percentages.</small>`;
  }

  function calculateScenario() {
    const shareNode = byId("producer-share");
    const shockNode = byId("output-shock");
    const output = byId("scenario-result");
    if (!shareNode || !shockNode || !output) return;
    const share = Number(shareNode.value);
    const shock = Number(shockNode.value);
    if (![share, shock].every(Number.isFinite) || share < 0 || share > 100 || shock < 0 || shock > 100) {
      output.textContent = "Values must be between 0% and 100%.";
      return;
    }
    const grossSupplyImpact = (share / 100) * (shock / 100) * 100;
    output.innerHTML = `<strong>SCENARIO ANALYSIS — NOT A FORECAST</strong><br>If a producer representing ${share.toFixed(1)}% of supply experiences a ${shock.toFixed(1)}% output reduction, the direct gross supply reduction is ${grossSupplyImpact.toFixed(2)}% before substitution, inventories, demand response, recycling, or alternate supply.`;
  }

  function wireAnalytics() {
    byId("calculate-hhi")?.addEventListener("click", calculateHhi);
    byId("calculate-scenario")?.addEventListener("click", calculateScenario);
  }

  async function initialize() {
    wireAnalytics();
    const tasks = [
      fetchJson(`${FEED_BASE}/manifest.json`).then(renderManifest).catch(renderManifestError),
      fetchJson(`${FEED_BASE}/metadata/minerals.json`).then(renderMinerals).catch(renderMineralsError),
      fetchJson(`${FEED_BASE}/latest/policy.json`).then(renderPolicy).catch(renderPolicyError),
    ];
    await Promise.allSettled(tasks);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialize, { once: true });
  } else {
    initialize();
  }
})();
