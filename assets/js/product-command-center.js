(function () {
  "use strict";

  const root = document.querySelector("[data-product-command-center]");
  if (!root) return;

  const catalogUrl = root.dataset.catalogUrl || "/data/products.json";
  const state = { products: [], query: "", category: "all", sort: "recommended", view: "grid", favoritesOnly: false, favorites: new Set(), compared: new Set() };
  const els = {
    grid: root.querySelector("[data-product-grid]"), search: root.querySelector("[data-product-search]"),
    category: root.querySelector("[data-product-category]"), sort: root.querySelector("[data-product-sort]"),
    count: root.querySelector("[data-product-count]"), chips: root.querySelector("[data-product-chips]"),
    collections: root.querySelector("[data-product-collections]"), tray: root.querySelector("[data-compare-tray]"),
    trayItems: root.querySelector("[data-compare-items]"), dialog: root.querySelector("[data-product-dialog]"),
    dialogContent: root.querySelector("[data-dialog-content]"), toast: root.querySelector("[data-product-toast]"),
    featured: root.querySelector("[data-featured-product]"), total: root.querySelector("[data-total-products]"),
    categoryTotal: root.querySelector("[data-total-categories]"), favoriteTotal: root.querySelector("[data-total-favorites]"),
    compareTotal: root.querySelector("[data-total-compared]")
  };

  function track(name, detail) {
    const payload = Object.assign({ event: name, catalog: "product-command-center" }, detail || {});
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push(payload);
    window.dispatchEvent(new CustomEvent("clearglass:analytics", { detail: payload }));
  }

  function safeStorage(key, fallback) {
    try { return JSON.parse(localStorage.getItem(key)) || fallback; } catch (_) { return fallback; }
  }

  function escapeHtml(value) {
    return String(value || "").replace(/[&<>"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[char]));
  }

  function readUrlState() {
    const params = new URLSearchParams(location.search);
    state.query = (params.get("q") || "").slice(0, 120);
    state.category = params.get("category") || "all";
    state.sort = params.get("sort") || "recommended";
    state.view = safeStorage("cg-products-view", "grid");
    state.favorites = new Set(safeStorage("cg-product-favorites", []));
  }

  function syncUrl() {
    const params = new URLSearchParams(location.search);
    [["q", state.query], ["category", state.category === "all" ? "" : state.category], ["sort", state.sort === "recommended" ? "" : state.sort]].forEach(([key, value]) => value ? params.set(key, value) : params.delete(key));
    const query = params.toString();
    history.replaceState(null, "", `${location.pathname}${query ? `?${query}` : ""}${location.hash}`);
  }

  function normalizedText(product) {
    return [product.name, product.category, product.sku, product.description, ...(product.tags || []), ...(product.features || []), ...(product.useCases || [])].filter(Boolean).join(" ").toLocaleLowerCase();
  }

  function visibleProducts() {
    const query = state.query.trim().toLocaleLowerCase();
    return state.products.filter((product) => (!query || normalizedText(product).includes(query)) && (state.category === "all" || product.category === state.category) && (!state.favoritesOnly || state.favorites.has(product.id))).sort(sorters[state.sort] || sorters.recommended);
  }

  const sorters = {
    recommended: (a, b) => Number(Boolean(b.recommended)) - Number(Boolean(a.recommended)) || a.name.localeCompare(b.name),
    featured: (a, b) => Number(Boolean(b.featured)) - Number(Boolean(a.featured)) || a.name.localeCompare(b.name),
    newest: (a, b) => Number(Boolean(b.new)) - Number(Boolean(a.new)) || a.name.localeCompare(b.name),
    popular: (a, b) => Number(Boolean(b.bestseller)) - Number(Boolean(a.bestseller)) || a.name.localeCompare(b.name),
    "price-low": (a, b) => (a.price == null) - (b.price == null) || (a.price || 0) - (b.price || 0) || a.name.localeCompare(b.name),
    "price-high": (a, b) => (a.price == null) - (b.price == null) || (b.price || 0) - (a.price || 0) || a.name.localeCompare(b.name),
    "name-az": (a, b) => a.name.localeCompare(b.name), "name-za": (a, b) => b.name.localeCompare(a.name)
  };

  function badgeMarkup(product) {
    const badges = [product.featured && "Featured", product.new && "New", product.bestseller && "Bestseller", product.recommended && "Recommended", product.status !== "available" && product.status].filter(Boolean).slice(0, 2);
    return badges.map((badge) => `<span class="pc-badge">${escapeHtml(String(badge).replace("-", " "))}</span>`).join("");
  }

  function cardMarkup(product) {
    const favorite = state.favorites.has(product.id), compared = state.compared.has(product.id);
    return `<article class="pc-card" data-product-id="${escapeHtml(product.id)}" data-compared="${compared}">
      <div class="pc-card-top"><span class="pc-icon" aria-hidden="true">${escapeHtml(product.icon || "◇")}</span><button class="pc-favorite" type="button" data-favorite="${escapeHtml(product.id)}" aria-pressed="${favorite}" aria-label="${favorite ? "Remove" : "Add"} ${escapeHtml(product.name)} ${favorite ? "from" : "to"} favorites">${favorite ? "♥" : "♡"}</button></div>
      <div><span class="pc-label">${escapeHtml(product.category)}</span><h2>${escapeHtml(product.name)}</h2></div>
      <p>${escapeHtml(product.shortDescription || product.description || "Details available on the product page.")}</p>
      <div class="pc-badges">${badgeMarkup(product)}<span class="pc-badge">${escapeHtml(product.status)}</span></div>
      <div class="pc-tags" aria-label="Product tags">${(product.tags || []).slice(0, 4).map((tag) => `<span>#${escapeHtml(tag)}</span>`).join("")}</div>
      <div class="pc-card-actions"><a class="pc-primary" href="${escapeHtml(product.productUrl)}" data-product-link="${escapeHtml(product.id)}">View product</a><button type="button" data-quick-view="${escapeHtml(product.id)}">Quick view</button><button type="button" data-compare="${escapeHtml(product.id)}" aria-pressed="${compared}">${compared ? "Remove compare" : "Add to compare"}</button><a href="/#contact">Contact</a></div>
    </article>`;
  }

  function render() {
    const products = visibleProducts();
    els.grid.dataset.view = state.view;
    els.grid.innerHTML = products.length ? products.map(cardMarkup).join("") : `<div class="pc-empty"><span class="pc-label">Recovery path</span><h2>No products match the current criteria.</h2><p>Reset the command center or browse a complete collection.</p><div class="pc-empty-actions"><button class="pc-control" type="button" data-clear-all>Clear filters</button><button class="pc-control" type="button" data-featured-reset>View all products</button></div></div>`;
    els.count.textContent = `${products.length} ${products.length === 1 ? "product" : "products"}`;
    els.count.setAttribute("aria-label", `${products.length} products shown`);
    els.favoriteTotal.textContent = state.favorites.size;
    els.compareTotal.textContent = state.compared.size;
    renderChips(); renderTray();
  }

  function renderChips() {
    const chips = [];
    if (state.query) chips.push(["query", `Search: ${state.query}`]);
    if (state.category !== "all") chips.push(["category", state.category]);
    if (state.favoritesOnly) chips.push(["favorites", "Favorites"]);
    els.chips.innerHTML = chips.map(([key, label]) => `<button class="pc-chip" type="button" data-remove-filter="${key}">${escapeHtml(label)} ×</button>`).join("") + (chips.length > 1 ? '<button class="pc-chip" type="button" data-clear-all>Clear all</button>' : "");
  }

  function renderTray() {
    const products = state.products.filter((product) => state.compared.has(product.id));
    els.tray.hidden = !products.length;
    els.trayItems.innerHTML = products.map((product) => `<span class="pc-tray-item">${escapeHtml(product.name)} ✓</span>`).join("");
  }

  function setFilter(key, value, eventName) {
    state[key] = value; syncUrl(); render();
    if (eventName) track(eventName, { filter: key, value });
  }

  function toggleFavorite(id) {
    state.favorites.has(id) ? state.favorites.delete(id) : state.favorites.add(id);
    localStorage.setItem("cg-product-favorites", JSON.stringify([...state.favorites])); render();
  }

  function toggleCompare(id) {
    if (state.compared.has(id)) { state.compared.delete(id); track("comparison_removed", { product_id: id }); }
    else if (state.compared.size < 4) { state.compared.add(id); track("comparison_added", { product_id: id }); }
    else { showToast("Compare up to four products at a time."); }
    render();
  }

  function showToast(message) {
    els.toast.textContent = message; els.toast.hidden = false;
    clearTimeout(showToast.timer); showToast.timer = setTimeout(() => { els.toast.hidden = true; }, 3200);
  }

  function openInspector(id) {
    const product = state.products.find((item) => item.id === id); if (!product) return;
    els.dialogContent.innerHTML = `<span class="pc-label">Product inspector · ${escapeHtml(product.category)}</span><h2 id="product-dialog-title">${escapeHtml(product.name)}</h2><p>${escapeHtml(product.description)}</p><div class="pc-badges"><span class="pc-badge">${escapeHtml(product.status)}</span>${badgeMarkup(product)}</div><h3>Product metadata</h3><p>${(product.tags || []).length ? product.tags.map((tag) => `#${escapeHtml(tag)}`).join(" · ") : "See the full product page for verified capabilities."}</p><div class="pc-inspector-actions"><a href="${escapeHtml(product.productUrl)}" data-product-link="${escapeHtml(product.id)}">Full product details</a><a href="/#contact">Contact ClearGlass</a></div>`;
    els.dialog.showModal(); track("quick_view_opened", { product_id: id });
  }

  function openComparison() {
    const products = state.products.filter((product) => state.compared.has(product.id));
    if (products.length < 2) { showToast("Select at least two products to compare."); return; }
    const row = (label, value) => `<tr><th scope="row">${label}</th>${products.map((product) => `<td>${escapeHtml(value(product))}</td>`).join("")}</tr>`;
    els.dialogContent.innerHTML = `<span class="pc-label">Comparison workspace</span><h2 id="product-dialog-title">Compare products</h2><div role="region" aria-label="Product comparison" tabindex="0"><table class="pc-comparison"><thead><tr><th scope="col">Attribute</th>${products.map((product) => `<th scope="col">${escapeHtml(product.name)}</th>`).join("")}</tr></thead><tbody>${row("Category", (p) => p.category)}${row("Availability", (p) => p.status)}${row("Pricing", (p) => p.price == null ? "Contact for pricing" : `${p.currency || "CAD"} ${p.price}`)}${row("Description", (p) => p.description)}${row("Tags", (p) => (p.tags || []).join(", ") || "Not specified")}</tbody></table></div>`;
    els.dialog.showModal();
  }

  function populateControls() {
    const categories = [...new Set(state.products.map((product) => product.category))].sort();
    els.category.innerHTML = '<option value="all">All categories</option>' + categories.map((category) => `<option value="${escapeHtml(category)}">${escapeHtml(category)}</option>`).join("");
    if (!categories.includes(state.category)) state.category = "all";
    els.category.value = state.category; els.search.value = state.query; els.sort.value = sorters[state.sort] ? state.sort : "recommended";
    root.querySelectorAll("[data-view]").forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.view === state.view)));
    els.total.textContent = state.products.length; els.categoryTotal.textContent = categories.length;
    els.collections.innerHTML = `<button class="pc-collection" type="button" data-collection="all" aria-pressed="${state.category === "all"}">All systems · ${state.products.length}</button>` + categories.map((category) => `<button class="pc-collection" type="button" data-collection="${escapeHtml(category)}" aria-pressed="${state.category === category}">${escapeHtml(category)} · ${state.products.filter((product) => product.category === category).length}</button>`).join("");
    const featured = state.products.find((product) => product.featured) || state.products[0];
    if (featured) els.featured.innerHTML = `<div><span class="pc-label">Catalog spotlight</span><h2>${escapeHtml(featured.name)}</h2><p>${escapeHtml(featured.description)}</p></div><a class="pc-control" href="${escapeHtml(featured.productUrl)}">Explore system</a>`;
  }

  root.addEventListener("click", (event) => {
    const target = event.target.closest("button,a"); if (!target) return;
    if (target.dataset.favorite) toggleFavorite(target.dataset.favorite);
    if (target.dataset.compare) toggleCompare(target.dataset.compare);
    if (target.dataset.quickView) openInspector(target.dataset.quickView);
    if (target.dataset.collection) { els.category.value = target.dataset.collection; setFilter("category", target.dataset.collection, "filter_applied"); populateControls(); render(); }
    if (target.dataset.view) { state.view = target.dataset.view; localStorage.setItem("cg-products-view", JSON.stringify(state.view)); root.querySelectorAll("[data-view]").forEach((button) => button.setAttribute("aria-pressed", String(button === target))); render(); }
    if (target.matches("[data-favorites-filter]")) setFilter("favoritesOnly", !state.favoritesOnly, state.favoritesOnly ? "filter_removed" : "filter_applied");
    if (target.matches("[data-clear-all],[data-featured-reset]")) { state.query = ""; state.category = "all"; state.favoritesOnly = false; els.search.value = ""; els.category.value = "all"; syncUrl(); populateControls(); render(); track("filter_removed", { filter: "all" }); }
    if (target.dataset.removeFilter) { const key = target.dataset.removeFilter; if (key === "query") { state.query = ""; els.search.value = ""; } else if (key === "category") { state.category = "all"; els.category.value = "all"; } else state.favoritesOnly = false; syncUrl(); render(); track("filter_removed", { filter: key }); }
    if (target.matches("[data-open-comparison]")) openComparison();
    if (target.matches("[data-close-dialog]")) els.dialog.close();
    if (target.dataset.productLink) track("product_click", { product_id: target.dataset.productLink });
  });
  els.search.addEventListener("input", () => { state.query = els.search.value.slice(0, 120); syncUrl(); render(); track("search", { query_length: state.query.length }); });
  els.category.addEventListener("change", () => { setFilter("category", els.category.value, "filter_applied"); populateControls(); render(); });
  els.sort.addEventListener("change", () => setFilter("sort", els.sort.value, "sort_changed"));
  els.dialog.addEventListener("click", (event) => { if (event.target === els.dialog) els.dialog.close(); });

  readUrlState();
  fetch(catalogUrl, { credentials: "same-origin" }).then((response) => { if (!response.ok) throw new Error(`Catalog request failed: ${response.status}`); return response.json(); }).then((catalog) => {
    if (!catalog || !Array.isArray(catalog.products)) throw new Error("Invalid catalog response");
    state.products = catalog.products.filter((product) => product && product.id && product.name && product.productUrl);
    populateControls(); render(); track("product_view", { product_count: state.products.length });
  }).catch(() => { els.grid.innerHTML = '<div class="pc-empty"><h2>The catalog could not be loaded.</h2><p>Please refresh the page or contact ClearGlass for assistance.</p><div class="pc-empty-actions"><a class="pc-control" href="/products.html">Reload catalog</a><a class="pc-control" href="/#contact">Contact ClearGlass</a></div></div>'; els.count.textContent = "Catalog unavailable"; });
})();
