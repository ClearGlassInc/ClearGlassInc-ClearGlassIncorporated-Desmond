/* Progressive, container-measured action overflow for static ClearGlass pages. */
(function () {
  "use strict";

  var bars = document.querySelectorAll("[data-adaptive-action-bar]");
  if (!bars.length) return;

  var PRIORITY = { primary: 0, secondary: 1, overflow: 2 };

  bars.forEach(function (bar, barIndex) {
    var actions = Array.from(bar.querySelectorAll("[data-action-priority]"));
    if (!actions.length) return;

    var visible = document.createElement("div");
    visible.className = "adaptive-action-bar__visible";
    actions[0].parentNode.insertBefore(visible, actions[0]);
    actions.forEach(function (action, index) {
      action.dataset.actionOrder = String(index);
      visible.appendChild(action);
    });

    var menuId = "adaptive-action-menu-" + barIndex;
    var more = document.createElement("button");
    more.type = "button";
    more.className = "adaptive-action-bar__more";
    more.setAttribute("aria-haspopup", "menu");
    more.setAttribute("aria-expanded", "false");
    more.setAttribute("aria-controls", menuId);
    more.setAttribute("aria-label", "More actions");
    more.innerHTML = '<span aria-hidden="true">•••</span><span class="adaptive-action-bar__more-label">More</span>';
    bar.appendChild(more);

    var menu = document.createElement("div");
    menu.id = menuId;
    menu.className = "adaptive-action-menu";
    menu.setAttribute("role", "menu");
    menu.setAttribute("aria-label", "More actions");
    menu.dataset.open = "false";
    document.body.appendChild(menu); // Portal prevents clipping by overflow/transform ancestors.

    var widthCache = new Map();
    var raf = 0;
    var lastWidth = -1;

    function menuItems() { return Array.from(menu.querySelectorAll('[role="menuitem"]')); }
    function closeMenu(restoreFocus) {
      menu.dataset.open = "false";
      more.setAttribute("aria-expanded", "false");
      if (restoreFocus) more.focus();
    }
    function positionMenu() {
      var trigger = more.getBoundingClientRect();
      var gap = 8;
      var menuWidth = Math.min(340, window.innerWidth - 24);
      var left = Math.min(window.innerWidth - menuWidth - 12, Math.max(12, trigger.right - menuWidth));
      var below = window.innerHeight - trigger.bottom - gap;
      var estimatedHeight = Math.min(menu.scrollHeight || 240, window.innerHeight * .7);
      var top = below >= estimatedHeight || trigger.top < estimatedHeight
        ? trigger.bottom + gap
        : Math.max(12, trigger.top - estimatedHeight - gap);
      menu.style.left = left + "px";
      menu.style.top = top + "px";
    }
    function openMenu() {
      if (!menuItems().length) return;
      positionMenu();
      menu.dataset.open = "true";
      more.setAttribute("aria-expanded", "true");
      menuItems()[0].focus();
    }
    function cloneForMenu(action) {
      var item = action.cloneNode(true);
      item.className = "adaptive-action-menu__item";
      item.setAttribute("role", "menuitem");
      item.removeAttribute("data-action-priority");
      item.removeAttribute("data-action-order");
      item.addEventListener("click", function () { closeMenu(false); });
      return item;
    }
    function measure(action) {
      if (widthCache.has(action)) return widthCache.get(action);
      var rect = action.getBoundingClientRect();
      var style = getComputedStyle(action);
      var width = Math.ceil(rect.width + parseFloat(style.marginLeft || 0) + parseFloat(style.marginRight || 0));
      widthCache.set(action, width);
      return width;
    }
    function recalculate(force) {
      raf = 0;
      var available = Math.floor(bar.getBoundingClientRect().width);
      if (!force && available === lastWidth) return;
      lastWidth = available;
      closeMenu(false);

      actions.forEach(function (action) {
        if (action.parentNode !== visible) visible.appendChild(action);
        action.hidden = false;
      });
      menu.replaceChildren();
      more.dataset.visible = "false";
      bar.classList.remove("adaptive-action-bar--has-overflow");

      var widths = actions.map(measure);
      var total = widths.reduce(function (sum, width) { return sum + width - 1; }, 0);
      if (total <= available) return;

      more.dataset.visible = "true";
      bar.classList.add("adaptive-action-bar--has-overflow");
      var moreWidth = Math.ceil(more.getBoundingClientRect().width);
      var candidates = actions.map(function (action, index) {
        return { action: action, index: index, priority: PRIORITY[action.dataset.actionPriority] ?? PRIORITY.secondary };
      }).sort(function (a, b) { return b.priority - a.priority || b.index - a.index; });

      var used = total + moreWidth - 1;
      candidates.forEach(function (candidate) {
        if (used <= available || candidate.priority === PRIORITY.primary) return;
        candidate.action.hidden = true;
        used -= widths[candidate.index] - 1;
      });

      actions.filter(function (action) { return action.hidden; })
        .sort(function (a, b) { return Number(a.dataset.actionOrder) - Number(b.dataset.actionOrder); })
        .forEach(function (action) { menu.appendChild(cloneForMenu(action)); });
    }
    function schedule(force) {
      if (force) lastWidth = -1;
      if (!raf) raf = requestAnimationFrame(function () { recalculate(force); });
    }

    more.addEventListener("click", function () {
      menu.dataset.open === "true" ? closeMenu(false) : openMenu();
    });
    document.addEventListener("pointerdown", function (event) {
      if (menu.dataset.open === "true" && !menu.contains(event.target) && !more.contains(event.target)) closeMenu(false);
    });
    document.addEventListener("keydown", function (event) {
      if (menu.dataset.open !== "true") return;
      var items = menuItems();
      var index = items.indexOf(document.activeElement);
      if (event.key === "Escape") { event.preventDefault(); closeMenu(true); }
      if (event.key === "ArrowDown") { event.preventDefault(); items[(index + 1) % items.length].focus(); }
      if (event.key === "ArrowUp") { event.preventDefault(); items[(index - 1 + items.length) % items.length].focus(); }
      if (event.key === "Home") { event.preventDefault(); items[0].focus(); }
      if (event.key === "End") { event.preventDefault(); items[items.length - 1].focus(); }
    });
    window.addEventListener("resize", function () { schedule(false); }, { passive: true });
    window.addEventListener("scroll", function () {
      if (menu.dataset.open === "true") positionMenu();
    }, { passive: true });
    if ("ResizeObserver" in window) new ResizeObserver(function () { schedule(false); }).observe(bar);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () { widthCache.clear(); schedule(true); });
    recalculate(true);
  });
})();
