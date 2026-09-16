/* ClearGlass · Project Board — sprint-operations console.
   ────────────────────────────────────────────────────────────────────────────
   Renders the whole surface from one same-origin feed, /data/project-board/board.json,
   which is the single source of truth. Nothing is duplicated inline: if the feed
   cannot be reached the board says so and offers a retry rather than quietly
   falling back to a second, drifting copy of the data.

   What it drives:
     • kanban board — drag and drop (pointer + keyboard), collapsible columns
     • task CRUD through a native <dialog>, persisted to localStorage
     • time sheet with a live-ticking leader row
     • sprint velocity gauge drawn as an SVG arc from the series data
     • activity feed with a real in-flight upload and an age-based range filter
     • week calendar whose schedule is filtered by the selected day
     • search, priority filter, sort cycle, JSON export, light/dark theme

   Local edits are stored under cg.projectboard.v1 and keyed to the feed's schema,
   so a schema change discards stale state instead of merging two shapes.
   Pairs with project-board.css. No dependencies.
   Drop in with <script defer src="project-board.js"></script>. */
(function () {
  "use strict";
  if (window.__cgProjectBoard) return;
  window.__cgProjectBoard = true;

  var FEED = "/data/project-board/board.json";
  var STORE = "cg.projectboard.v1";
  var THEME = "cg.projectboard.theme";
  var SVGNS = "http://www.w3.org/2000/svg";
  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  var PRIORITY_LABEL = { high: "High Priority", medium: "Medium Priority", low: "Low Priority" };
  var PRIORITY_RANK = { high: 0, medium: 1, low: 2, none: 3 };
  var FILTER_CYCLE = ["all", "high", "medium", "low"];
  var SORT_CYCLE = ["manual", "due", "priority", "title"];
  var SORT_LABEL = { manual: "Manual order", due: "Due date", priority: "Priority", title: "Title A–Z" };
  var RANGE_HOURS = { today: 24, week: 168, all: Infinity };
  var BOARD_GLYPH = { book: "\u{1F4D5}", snow: "❄", asterisk: "✳", cycle: "↻" };
  var REDUCED = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  var data = null;                 // the feed, untouched
  var state = {
    tasks: [], collapsed: {}, board: "all", sprint: "all", project: "dev-ai",
    q: "", priority: "all", sort: "manual", day: "", series: "", range: "today",
    open: null, editing: null
  };
  var timers = { sheet: null, upload: null };
  var sheetSeconds = {};           // memberId -> live seconds
  var uploadPct = {};              // activityId -> live percent

  // ── tiny DOM helpers ──────────────────────────────────────────────────

  function $(id) { return document.getElementById(id); }

  function h(tag, props, kids) {
    var node = document.createElement(tag), key, val, i;
    if (props) {
      for (key in props) {
        if (!Object.prototype.hasOwnProperty.call(props, key)) continue;
        val = props[key];
        if (val === null || val === undefined || val === false) continue;
        if (key === "text") node.textContent = val;
        else if (key === "cls") node.className = val;
        else if (key.slice(0, 2) === "on") node.addEventListener(key.slice(2), val);
        else node.setAttribute(key, val === true ? "" : String(val));
      }
    }
    if (kids) {
      if (!(kids instanceof Array)) kids = [kids];
      for (i = 0; i < kids.length; i++) {
        if (kids[i] === null || kids[i] === undefined || kids[i] === false) continue;
        node.appendChild(typeof kids[i] === "string" ? document.createTextNode(kids[i]) : kids[i]);
      }
    }
    return node;
  }

  function icon(id, size) {
    var svg = document.createElementNS(SVGNS, "svg");
    svg.setAttribute("class", "pb-ico");
    svg.setAttribute("aria-hidden", "true");
    if (size) svg.setAttribute("style", "width:" + size + "px;height:" + size + "px");
    var use = document.createElementNS(SVGNS, "use");
    use.setAttribute("href", "#" + id);
    svg.appendChild(use);
    return svg;
  }

  function clear(node) { while (node && node.firstChild) node.removeChild(node.firstChild); }

  function pad(n) { return (n < 10 ? "0" : "") + n; }

  // ── formatting ────────────────────────────────────────────────────────

  /* Split the ISO string rather than going through Date: new Date("2026-12-19")
     parses as UTC and can render a day early west of Greenwich. */
  function fmtDay(iso) {
    if (!iso) return "";
    var p = String(iso).split("-");
    if (p.length !== 3) return "";
    var m = parseInt(p[1], 10);
    if (!(m >= 1 && m <= 12)) return "";
    return MONTHS[m - 1] + " " + p[2];
  }

  function fmtRange(start, end) {
    if (start && end) return fmtDay(start) + " - " + fmtDay(end);
    if (end) return "Due " + fmtDay(end);
    if (start) return fmtDay(start);
    return "-";
  }

  function fmtHMS(sec) {
    sec = Math.max(0, Math.floor(sec));
    return Math.floor(sec / 3600) + "h " + pad(Math.floor(sec % 3600 / 60)) + "m " + pad(sec % 60) + "s";
  }

  function member(id) {
    var list = (data && data.members) || [], i;
    for (i = 0; i < list.length; i++) if (list[i].id === id) return list[i];
    return { id: id, name: id, initials: "?", hue: 240 };
  }

  function column(id) {
    var list = (data && data.columns) || [], i;
    for (i = 0; i < list.length; i++) if (list[i].id === id) return list[i];
    return null;
  }

  function sprint(id) {
    var list = (data && data.sprints) || [], i;
    for (i = 0; i < list.length; i++) if (list[i].id === id) return list[i];
    return null;
  }

  function boardName(id) {
    var list = (data && data.boards) || [], i, j;
    for (i = 0; i < list.length; i++) {
      if (list[i].id === id) return list[i].name;
      for (j = 0; j < (list[i].children || []).length; j++) {
        if (list[i].children[j].id === id) return list[i].children[j].name;
      }
    }
    return "";
  }

  function boardIds(id) {
    /* A parent board stands for itself plus its children, so selecting
       "Dashboard design" keeps the Admin / Client / Publishers cards. */
    var list = (data && data.boards) || [], i, j, out;
    for (i = 0; i < list.length; i++) {
      if (list[i].id !== id) continue;
      out = [id];
      for (j = 0; j < (list[i].children || []).length; j++) out.push(list[i].children[j].id);
      return out;
    }
    return [id];
  }

  // ── persistence ───────────────────────────────────────────────────────

  function save() {
    try {
      localStorage.setItem(STORE, JSON.stringify({
        schema: data ? data.schema : "",
        tasks: state.tasks, collapsed: state.collapsed, board: state.board,
        sprint: state.sprint, project: state.project, sort: state.sort,
        priority: state.priority, day: state.day, series: state.series, range: state.range
      }));
    } catch (e) { /* private mode or quota — the session still works */ }
  }

  function restore() {
    var raw, saved;
    try { raw = localStorage.getItem(STORE); } catch (e) { return false; }
    if (!raw) return false;
    try { saved = JSON.parse(raw); } catch (e) { return false; }
    if (!saved || saved.schema !== data.schema || !(saved.tasks instanceof Array)) return false;
    state.tasks = saved.tasks;
    state.collapsed = saved.collapsed || state.collapsed;
    state.board = saved.board || state.board;
    state.sprint = saved.sprint || state.sprint;
    state.project = saved.project || state.project;
    state.sort = saved.sort || state.sort;
    state.priority = saved.priority || state.priority;
    state.day = saved.day || state.day;
    state.series = saved.series || state.series;
    state.range = saved.range || state.range;
    return true;
  }

  // ── selection ─────────────────────────────────────────────────────────

  function visibleTasks() {
    var q = state.q.toLowerCase(), boards = state.board === "all" ? null : boardIds(state.board);
    var out = state.tasks.filter(function (t) {
      if (boards && boards.indexOf(t.board) === -1) return false;
      if (state.sprint !== "all" && t.sprint !== state.sprint) return false;
      if (state.priority !== "all" && (t.priority || "none") !== state.priority) return false;
      if (q && t.title.toLowerCase().indexOf(q) === -1) return false;
      return true;
    });
    if (state.sort === "due") {
      out.sort(function (a, b) { return (a.end || "9999").localeCompare(b.end || "9999"); });
    } else if (state.sort === "priority") {
      out.sort(function (a, b) {
        return PRIORITY_RANK[a.priority || "none"] - PRIORITY_RANK[b.priority || "none"];
      });
    } else if (state.sort === "title") {
      out.sort(function (a, b) { return a.title.localeCompare(b.title); });
    }
    return out;
  }

  function tasksIn(colId, pool) {
    return pool.filter(function (t) { return t.column === colId; });
  }

  // ── faces ─────────────────────────────────────────────────────────────

  function face(m, cls) {
    return h("span", {
      cls: "pb-face" + (cls ? " " + cls : ""),
      style: "--hue:" + m.hue,
      title: m.name + (m.role ? " · " + m.role : ""),
      "aria-hidden": "true"
    }, m.initials);
  }

  function faces(ids, max) {
    var wrap = h("span", { cls: "pb-faces" }), shown = Math.min(ids.length, max || 3), i;
    for (i = 0; i < shown; i++) wrap.appendChild(face(member(ids[i])));
    if (ids.length > shown) {
      wrap.appendChild(h("span", { cls: "pb-face pb-face--more" }, "+" + (ids.length - shown)));
    }
    wrap.appendChild(h("span", { cls: "pb-sr" }, ids.map(function (id) { return member(id).name; }).join(", ")));
    return wrap;
  }

  // ── board ─────────────────────────────────────────────────────────────

  function card(task) {
    var col = column(task.column), sp = sprint(task.sprint);
    var crumb = "Sprints / " + (sp ? sp.name : "Backlog") + " / " + (col ? col.name : task.column);
    var subs = task.subtasks || [];
    var node = h("article", {
      cls: "pb-card", draggable: "true", tabindex: "0", role: "listitem",
      "data-id": task.id, "aria-label": task.title + " — " + crumb
    });

    node.appendChild(h("div", { cls: "pb-card__top" }, [
      h("h3", { cls: "pb-card__title", text: task.title }),
      h("button", {
        cls: "pb-card__dots", type: "button", "data-act": "menu",
        title: "Task actions", "aria-label": "Actions for " + task.title
      }, icon("i-dots", 14)),
      h("div", { cls: "pb-card__tools" }, [
        h("button", { type: "button", "data-act": "delete", title: "Delete task" }, icon("i-trash")),
        h("button", { type: "button", "data-act": "edit", title: "Edit task" }, icon("i-pencil")),
        h("button", { type: "button", "data-act": "close", title: "Hide actions" }, icon("i-x"))
      ])
    ]));

    node.appendChild(h("p", { cls: "pb-card__crumb", text: crumb }));
    node.appendChild(h("div", { cls: "pb-card__meta" }, [
      icon("i-cal"), h("span", { text: fmtRange(task.start, task.end) })
    ]));

    node.appendChild(h("div", { cls: "pb-card__row" }, faces(task.assignees || [])));

    if (task.attachment) {
      node.appendChild(h("div", { cls: "pb-card__row" }, h("span", { cls: "pb-attach" }, [
        h("span", { cls: "pb-attach__thumb", "aria-hidden": "true" }),
        icon("i-clip", 12),
        h("span", { cls: "pb-attach__name", text: task.attachment.name })
      ])));
    }

    if (task.priority && task.priority !== "none" || subs.length) {
      node.appendChild(h("div", { cls: "pb-card__row" }, [
        task.priority && task.priority !== "none"
          ? h("span", { cls: "pb-flag", "data-p": task.priority }, [
              icon("i-flag"), h("span", { text: PRIORITY_LABEL[task.priority] })
            ])
          : null,
        subs.length
          ? h("span", { cls: "pb-sub", style: "margin-left:auto" }, [
              icon("i-branch"),
              h("span", { text: subs.length + (subs.length === 1 ? " subtask" : " subtasks") })
            ])
          : null
      ]));
    }

    return node;
  }

  function collapsedColumn(col, count) {
    return h("button", {
      cls: "pb-col pb-col--collapsed", type: "button",
      style: "--col-color:" + col.color, "data-col": col.id,
      title: "Expand " + col.name,
      "aria-label": "Expand " + col.name + " — " + count + " tasks",
      onclick: function () { state.collapsed[col.id] = false; save(); renderBoard(); }
    }, [
      h("span", { cls: "pb-col__dot", "aria-hidden": "true" }),
      h("span", { cls: "pb-col__rail", text: col.name }),
      h("span", { cls: "pb-col__n", text: String(count) })
    ]);
  }

  function openColumn(col, list) {
    var node = h("section", {
      cls: "pb-col", style: "--col-color:" + col.color, "data-col": col.id,
      "aria-label": col.name
    });

    node.appendChild(h("div", { cls: "pb-col__head" }, [
      h("span", { cls: "pb-chip", text: col.name }),
      h("span", { cls: "pb-col__count", text: String(list.length) }),
      h("button", {
        cls: "pb-iconbtn", type: "button", title: "Collapse " + col.name,
        "aria-label": "Collapse " + col.name,
        onclick: function () { state.collapsed[col.id] = true; save(); renderBoard(); }
      }, icon("i-chev-l", 15))
    ]));

    var listEl = h("div", { cls: "pb-col__list", role: "list" });
    if (!list.length) {
      listEl.appendChild(h("p", { cls: "pb-col__empty", text: "Drop a task here" }));
    } else {
      list.forEach(function (t) { listEl.appendChild(card(t)); });
    }
    node.appendChild(listEl);
    return node;
  }

  function renderBoard() {
    var board = $("pb-board");
    if (!board) return;
    clear(board);

    var pool = visibleTasks(), rails = null;
    (data.columns || []).forEach(function (col) {
      var list = tasksIn(col.id, pool);
      if (state.collapsed[col.id]) {
        if (!rails) { rails = h("div", { cls: "pb-rails" }); board.appendChild(rails); }
        rails.appendChild(collapsedColumn(col, list.length));
      } else {
        rails = null;
        board.appendChild(openColumn(col, list));
      }
    });

    renderScope(pool.length);
  }

  function renderScope(count) {
    var el = $("pb-scope");
    if (!el) return;
    var proj = state.project, name = proj, list = (data.projects || []), i;
    for (i = 0; i < list.length; i++) if (list[i].id === proj) name = list[i].name;
    var scope = state.sprint === "all" ? (data.workspace.sprint || "All sprints")
                                       : (sprint(state.sprint) || {}).name;
    el.textContent = name + " · " + scope + " · " + count +
      (count === 1 ? " task" : " tasks") +
      (state.board === "all" ? "" : " · " + boardName(state.board));
  }

  // ── panel ─────────────────────────────────────────────────────────────

  function renderProjects() {
    var wrap = $("pb-projects");
    if (!wrap) return;
    clear(wrap);

    wrap.appendChild(h("button", {
      cls: "pb-project pb-project--add", type: "button", title: "Add Project",
      onclick: function () { toast("Project intake is governed — request it from the Overview."); }
    }, [
      h("span", { cls: "pb-project__chip" }, icon("i-plus", 16)),
      h("span", { cls: "pb-project__name", text: "Add Project" })
    ]));

    (data.projects || []).forEach(function (p) {
      var on = p.id === state.project;
      wrap.appendChild(h("button", {
        cls: "pb-project" + (on ? " pb-project--active" : ""), type: "button",
        title: p.name, "aria-pressed": on ? "true" : "false",
        onclick: function () {
          state.project = p.id; save(); renderProjects(); renderScope(visibleTasks().length);
          toast(p.name + " selected");
        }
      }, [
        h("span", { cls: "pb-project__chip", style: "--hue:" + p.hue }, icon("i-" + p.glyph, 17)),
        h("span", { cls: "pb-project__name", text: p.name })
      ]));
    });
  }

  function treeRow(b) {
    var on = state.board === b.id;
    var row = h("button", {
      cls: "pb-tree__row", type: "button", "aria-current": on ? "true" : "false",
      onclick: function () {
        state.board = on ? "all" : b.id; save(); renderTree(); renderBoard();
      }
    }, [
      h("span", { cls: "pb-tree__glyph", style: "--hue:" + b.hue, "aria-hidden": "true" },
        BOARD_GLYPH[b.icon] || "●"),
      h("span", { cls: "pb-tree__label", text: b.name }),
      b.count ? h("span", { cls: "pb-count", text: String(b.count) }) : null
    ]);
    return row;
  }

  function renderTree() {
    var tree = $("pb-tree");
    if (!tree) return;
    clear(tree);

    (data.boards || []).forEach(function (b) {
      tree.appendChild(treeRow(b));
      if (!b.children || !b.children.length || b.expanded === false) return;
      var kids = h("div", { cls: "pb-tree__kids" });
      b.children.forEach(function (kid) {
        var on = state.board === kid.id;
        kids.appendChild(h("button", {
          cls: "pb-tree__kid", type: "button", "aria-current": on ? "true" : "false",
          onclick: function () {
            state.board = on ? "all" : kid.id; save(); renderTree(); renderBoard();
          }
        }, [
          h("span", { cls: "pb-tree__dot", "aria-hidden": "true" }),
          h("span", { cls: "pb-tree__label", text: kid.name }),
          kid.count ? h("span", { cls: "pb-count", text: String(kid.count) }) : null
        ]));
      });
      tree.appendChild(kids);
    });
  }

  function renderSprints() {
    var wrap = $("pb-sprints");
    if (!wrap) return;
    clear(wrap);

    wrap.appendChild(h("button", {
      cls: "pb-tree__row", type: "button",
      "aria-current": state.sprint === "all" ? "true" : "false",
      onclick: function () { state.sprint = "all"; save(); renderSprints(); renderBoard(); }
    }, [
      h("span", { cls: "pb-tree__glyph", style: "--hue:258", "aria-hidden": "true" }, "∑"),
      h("span", { cls: "pb-tree__label", text: "All sprints" })
    ]));

    (data.sprints || []).forEach(function (sp) {
      var on = state.sprint === sp.id;
      var count = state.tasks.filter(function (t) { return t.sprint === sp.id; }).length;
      wrap.appendChild(h("button", {
        cls: "pb-tree__row", type: "button", "aria-current": on ? "true" : "false",
        title: fmtRange(sp.start, sp.end) + " · " + sp.state,
        onclick: function () {
          state.sprint = on ? "all" : sp.id; save(); renderSprints(); renderBoard();
        }
      }, [
        h("span", {
          cls: "pb-tree__glyph", "aria-hidden": "true",
          style: "--hue:" + (sp.state === "active" ? 258 : sp.state === "done" ? 142 : 38)
        }, sp.state === "done" ? "✓" : sp.state === "active" ? "▶" : "○"),
        h("span", { cls: "pb-tree__label", text: sp.name }),
        count ? h("span", { cls: "pb-count", text: String(count) }) : null
      ]));
    });
  }

  // ── time sheet ────────────────────────────────────────────────────────

  function renderSheet() {
    var wrap = $("pb-sheet");
    if (!wrap) return;
    clear(wrap);

    var rows = (data.timesheet.entries || []).map(function (e) {
      return { member: e.member, seconds: sheetSeconds[e.member], running: !!e.running };
    });
    rows.sort(function (a, b) { return b.seconds - a.seconds; });

    rows.forEach(function (row, i) {
      var m = member(row.member);
      wrap.appendChild(h("div", {
        cls: "pb-sheet__row" + (i === 0 ? " pb-sheet__row--lead" : "")
      }, [
        h("span", { cls: "pb-sheet__rank", "aria-hidden": "true", text: String(i + 1) }),
        face(m),
        h("div", { cls: "pb-sheet__body" }, [
          h("div", { cls: "pb-sheet__name", text: m.name }),
          h("div", {
            cls: "pb-sheet__time", "data-member": row.member,
            text: "Total " + fmtHMS(row.seconds)
          })
        ]),
        i === 0 ? h("span", { cls: "pb-sheet__medal", "aria-label": "Top logger" }, "\u{1F3C5}") : null
      ]));
    });
  }

  function tickSheet() {
    var moved = false;
    (data.timesheet.entries || []).forEach(function (e) {
      if (!e.running) return;
      sheetSeconds[e.member] += 1;
      moved = true;
      var cell = document.querySelector('.pb-sheet__time[data-member="' + e.member + '"]');
      if (cell) cell.textContent = "Total " + fmtHMS(sheetSeconds[e.member]);
    });
    /* Only re-sort when a tick actually changes the standing — re-rendering the
       list every second would fight the user's pointer. */
    if (moved) {
      var rows = (data.timesheet.entries || []).map(function (e) { return sheetSeconds[e.member]; });
      var top = Math.max.apply(null, rows);
      var lead = document.querySelector(".pb-sheet__row--lead .pb-sheet__time");
      if (lead && parseHMS(lead.textContent) < top) renderSheet();
    }
  }

  function parseHMS(text) {
    var m = /(\d+)h\s+(\d+)m\s+(\d+)s/.exec(text || "");
    return m ? (+m[1]) * 3600 + (+m[2]) * 60 + (+m[3]) : -1;
  }

  // ── velocity gauge ────────────────────────────────────────────────────

  function gaugePoint(pct, r) {
    var theta = Math.PI * (1 - Math.max(0, Math.min(100, pct)) / 100);
    return { x: 120 + r * Math.cos(theta), y: 120 - r * Math.sin(theta) };
  }

  function renderGauge() {
    var wrap = $("pb-gauge");
    if (!wrap) return;
    clear(wrap);

    var series = data.velocity.series || [];
    var active = series.filter(function (s) { return s.label === state.series; })[0] || series[0];
    if (!active) return;

    var LEN = Math.PI * 100;
    var svg = document.createElementNS(SVGNS, "svg");
    svg.setAttribute("viewBox", "0 0 240 150");
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", "Sprint velocity " + active.percent + " percent for " + active.label);

    var defs = document.createElementNS(SVGNS, "defs");
    var grad = document.createElementNS(SVGNS, "linearGradient");
    grad.setAttribute("id", "pb-gauge-grad");
    grad.setAttribute("x1", "0"); grad.setAttribute("y1", "0");
    grad.setAttribute("x2", "1"); grad.setAttribute("y2", "0");
    [["0%", "#2dd4bf"], ["34%", "#a3e635"], ["62%", "#facc15"], ["84%", "#fb923c"], ["100%", "#ef4444"]]
      .forEach(function (stop) {
        var s = document.createElementNS(SVGNS, "stop");
        s.setAttribute("offset", stop[0]);
        s.setAttribute("stop-color", stop[1]);
        grad.appendChild(s);
      });
    defs.appendChild(grad);
    svg.appendChild(defs);

    function arc(cls, stroke, dash, opacity) {
      var p = document.createElementNS(SVGNS, "path");
      p.setAttribute("d", "M 20 120 A 100 100 0 0 1 220 120");
      p.setAttribute("fill", "none");
      p.setAttribute("stroke-width", "13");
      p.setAttribute("stroke-linecap", "round");
      if (cls) p.setAttribute("class", cls);
      if (stroke) p.setAttribute("stroke", stroke);
      if (dash) p.setAttribute("stroke-dasharray", dash);
      if (opacity) p.setAttribute("opacity", opacity);
      return p;
    }

    svg.appendChild(arc("pb-gauge__track", null, null, null));
    svg.appendChild(arc(null, "url(#pb-gauge-grad)", null, ".22"));
    svg.appendChild(arc(null, "url(#pb-gauge-grad)",
      (LEN * active.percent / 100).toFixed(2) + " " + LEN.toFixed(2), null));

    // tick marks every 10%
    var t;
    for (t = 0; t <= 100; t += 10) {
      var a = gaugePoint(t, 84), b = gaugePoint(t, 78);
      var tick = document.createElementNS(SVGNS, "line");
      tick.setAttribute("x1", a.x.toFixed(2)); tick.setAttribute("y1", a.y.toFixed(2));
      tick.setAttribute("x2", b.x.toFixed(2)); tick.setAttribute("y2", b.y.toFixed(2));
      tick.setAttribute("stroke", "currentColor");
      tick.setAttribute("stroke-width", "1.6");
      tick.setAttribute("opacity", ".2");
      svg.appendChild(tick);
    }

    var knob = gaugePoint(active.percent, 100);
    var ring = document.createElementNS(SVGNS, "circle");
    ring.setAttribute("cx", knob.x.toFixed(2)); ring.setAttribute("cy", knob.y.toFixed(2));
    ring.setAttribute("r", "8.5");
    ring.setAttribute("fill", active.color || "#22d3ee");
    /* Set through style, not a presentation attribute: only the CSS property
       resolves var(), and the knob has to punch out of whichever theme's card
       colour is behind it. */
    ring.style.stroke = "var(--card)";
    ring.setAttribute("stroke-width", "3.5");
    svg.appendChild(ring);

    wrap.appendChild(svg);
    wrap.appendChild(h("div", { cls: "pb-gauge__val" }, [
      h("div", { cls: "pb-gauge__pct", text: active.percent + "%" }),
      h("div", { cls: "pb-gauge__lbl", text: active.label })
    ]));
  }

  function renderLegend() {
    var wrap = $("pb-legend");
    if (!wrap) return;
    clear(wrap);
    (data.velocity.series || []).forEach(function (s) {
      wrap.appendChild(h("button", {
        type: "button", style: "--dot:" + s.color,
        "aria-pressed": state.series === s.label ? "true" : "false",
        onclick: function () {
          state.series = s.label; save(); renderGauge(); renderLegend();
        }
      }, s.label));
    });
  }

  // ── activity ──────────────────────────────────────────────────────────

  function feedItem(a) {
    var m = member(a.member);
    var node = h("article", { cls: "pb-feed__item", "data-id": a.id });
    var badge = a.kind === "upload" ? "i-upload" : a.kind === "move" ? "i-branch" : "i-comment";

    var text;
    if (a.kind === "comment") {
      text = h("p", { cls: "pb-feed__text", style: "margin:0" }, [
        h("b", { text: m.name }), " commented on ", h("b", { text: a.target })
      ]);
    } else if (a.kind === "move") {
      text = h("p", { cls: "pb-feed__text", style: "margin:0" }, [
        h("b", { text: m.name }), " moved ", h("b", { text: a.target }), " forward"
      ]);
    } else {
      text = h("p", { cls: "pb-feed__text", style: "margin:0" }, [
        h("b", { text: m.name }), " ", a.text
      ]);
    }

    node.appendChild(h("div", { cls: "pb-feed__head" }, [
      h("span", { cls: "pb-feed__badge" }, icon(badge)),
      text,
      h("time", { cls: "pb-feed__time", text: a.time })
    ]));

    if (a.file) {
      var pct = uploadPct[a.id];
      var done = pct >= 100;
      node.appendChild(h("div", { cls: "pb-file" }, [
        h("span", { cls: "pb-file__icon", "aria-hidden": "true" },
          (a.file.name.split(".").pop() || "file").toUpperCase().slice(0, 4)),
        h("div", { cls: "pb-file__body" }, [
          h("div", { cls: "pb-file__name", text: a.file.name }),
          h("div", { cls: "pb-file__sub" }, [
            h("span", { text: a.file.size }),
            h("span", { "data-pct": a.id, text: done ? "Uploaded" : a.file.state + " " + pct + "%" })
          ]),
          h("div", {
            cls: "pb-file__bar", role: "progressbar", "aria-label": "Upload of " + a.file.name,
            "aria-valuenow": String(pct), "aria-valuemin": "0", "aria-valuemax": "100"
          }, h("span", { cls: "pb-file__fill", "data-fill": a.id, style: "width:" + pct + "%" }))
        ])
      ]));
    }

    if (a.body) node.appendChild(h("p", { cls: "pb-feed__quote", text: a.body }));

    if (a.reply) {
      node.appendChild(h("div", { cls: "pb-feed__reply" }, [
        face(member("mehmet")),
        h("span", {}, [h("b", { text: a.reply.mention }), " " + a.reply.text + " " + (a.reply.emoji || "")])
      ]));
    }

    return node;
  }

  function renderFeed() {
    var wrap = $("pb-feed");
    if (!wrap) return;
    clear(wrap);
    var cap = RANGE_HOURS[state.range] || Infinity;
    var items = (data.activity || []).filter(function (a) { return (a.hours || 0) <= cap; });
    if (!items.length) {
      wrap.appendChild(h("p", { cls: "pb-sched__empty", text: "No activity in this range." }));
      return;
    }
    items.forEach(function (a) { wrap.appendChild(feedItem(a)); });
  }

  function tickUpload() {
    (data.activity || []).forEach(function (a) {
      if (!a.file || uploadPct[a.id] >= 100) return;
      uploadPct[a.id] = Math.min(100, uploadPct[a.id] + 1);
      var fill = document.querySelector('[data-fill="' + a.id + '"]');
      var label = document.querySelector('[data-pct="' + a.id + '"]');
      var pct = uploadPct[a.id];
      if (fill) {
        fill.style.width = pct + "%";
        if (fill.parentNode) fill.parentNode.setAttribute("aria-valuenow", String(pct));
      }
      if (label) label.textContent = pct >= 100 ? "Uploaded" : a.file.state + " " + pct + "%";
    });
  }

  // ── calendar ──────────────────────────────────────────────────────────

  function renderWeek() {
    var wrap = $("pb-week");
    if (!wrap) return;
    clear(wrap);
    (data.calendar.days || []).forEach(function (d) {
      var on = state.day === d.date;
      wrap.appendChild(h("button", {
        cls: "pb-day", type: "button", "aria-pressed": on ? "true" : "false",
        "aria-label": d.weekday + " " + d.day + " " + (data.calendar.month || ""),
        onclick: function () { state.day = d.date; save(); renderWeek(); renderSchedule(); }
      }, [
        h("span", { cls: "pb-day__n", text: String(d.day) }),
        h("span", { cls: "pb-day__w", text: d.weekday })
      ]));
    });
  }

  function renderSchedule() {
    var wrap = $("pb-sched"), title = $("pb-sched-title");
    if (!wrap) return;
    clear(wrap);

    var picked = (data.calendar.days || []).filter(function (d) { return d.date === state.day; })[0];
    if (title) {
      title.textContent = state.day === data.calendar.selected
        ? "Schedule Today"
        : "Schedule " + (picked ? picked.weekday + " " + picked.day : "");
    }

    var slots = (data.calendar.schedule || []).filter(function (s) { return s.date === state.day; });
    if (!slots.length) {
      wrap.appendChild(h("p", { cls: "pb-sched__empty", text: "Nothing scheduled." }));
      return;
    }
    slots.forEach(function (s) {
      wrap.appendChild(h("div", { cls: "pb-slot" }, [
        h("span", { cls: "pb-slot__time", text: s.time }),
        h("div", { cls: "pb-slot__body" }, [
          h("span", { cls: "pb-slot__name", text: s.title }),
          faces(s.attendees || [], 2),
          h("button", {
            cls: "pb-slot__more", type: "button",
            "aria-label": "Options for " + s.title,
            onclick: function () { toast(s.time + " · " + s.title); }
          }, icon("i-dots"))
        ])
      ]));
    });
  }

  // ── pricing / promo ───────────────────────────────────────────────────

  function renderStatic() {
    var p = data.pricing || {}, promo = data.promo || {};
    if ($("pb-price-amt") && p.amount) $("pb-price-amt").textContent = p.amount;
    if ($("pb-price-badge") && p.badge) $("pb-price-badge").textContent = p.badge;
    if ($("pb-price-period") && p.period) $("pb-price-period").textContent = p.period;
    if ($("pb-promo-text") && promo.title) $("pb-promo-text").textContent = promo.title;
    if ($("pb-learn-more") && promo.secondary) $("pb-learn-more").textContent = promo.secondary;
  }

  // ── toast ─────────────────────────────────────────────────────────────

  var toastTimer = null;
  function toast(message) {
    var el = $("pb-toast"), text = $("pb-toast-text");
    if (!el || !text) return;
    text.textContent = message;
    el.classList.add("is-on");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { el.classList.remove("is-on"); }, 2600);
  }

  // ── drag and drop ─────────────────────────────────────────────────────

  function taskById(id) {
    for (var i = 0; i < state.tasks.length; i++) if (state.tasks[i].id === id) return state.tasks[i];
    return null;
  }

  function moveTask(id, colId, beforeId) {
    var task = taskById(id);
    if (!task) return;
    var from = state.tasks.indexOf(task);
    state.tasks.splice(from, 1);
    var at = state.tasks.length;
    if (beforeId) {
      var target = taskById(beforeId);
      if (target) at = state.tasks.indexOf(target);
    }
    task.column = colId;
    state.tasks.splice(at, 0, task);
    save();
    renderBoard();
  }

  function insertionTarget(listEl, y) {
    var cards = [].slice.call(listEl.querySelectorAll(".pb-card:not(.is-dragging)")), i, box;
    for (i = 0; i < cards.length; i++) {
      box = cards[i].getBoundingClientRect();
      if (y < box.top + box.height / 2) return cards[i].getAttribute("data-id");
    }
    return null;
  }

  function wireBoard() {
    var board = $("pb-board");
    if (!board) return;

    board.addEventListener("dragstart", function (ev) {
      var el = ev.target.closest && ev.target.closest(".pb-card");
      if (!el) return;
      el.classList.add("is-dragging");
      state.open = el.getAttribute("data-id");
      try {
        ev.dataTransfer.setData("text/plain", state.open);
        ev.dataTransfer.effectAllowed = "move";
      } catch (e) { /* older engines */ }
    });

    board.addEventListener("dragend", function (ev) {
      var el = ev.target.closest && ev.target.closest(".pb-card");
      if (el) el.classList.remove("is-dragging");
      [].forEach.call(board.querySelectorAll(".is-over"), function (c) { c.classList.remove("is-over"); });
    });

    board.addEventListener("dragover", function (ev) {
      var col = ev.target.closest && ev.target.closest(".pb-col:not(.pb-col--collapsed)");
      if (!col) return;
      ev.preventDefault();
      ev.dataTransfer.dropEffect = "move";
      [].forEach.call(board.querySelectorAll(".is-over"), function (c) {
        if (c !== col) c.classList.remove("is-over");
      });
      col.classList.add("is-over");
    });

    board.addEventListener("dragleave", function (ev) {
      var col = ev.target.closest && ev.target.closest(".pb-col");
      if (col && !col.contains(ev.relatedTarget)) col.classList.remove("is-over");
    });

    board.addEventListener("drop", function (ev) {
      var col = ev.target.closest && ev.target.closest(".pb-col:not(.pb-col--collapsed)");
      if (!col) return;
      ev.preventDefault();
      col.classList.remove("is-over");
      var id = "";
      try { id = ev.dataTransfer.getData("text/plain"); } catch (e) { id = state.open || ""; }
      if (!id) return;
      var listEl = col.querySelector(".pb-col__list");
      moveTask(id, col.getAttribute("data-col"), listEl ? insertionTarget(listEl, ev.clientY) : null);
      toast("Moved to " + (column(col.getAttribute("data-col")) || {}).name);
    });

    // card actions
    board.addEventListener("click", function (ev) {
      var btn = ev.target.closest && ev.target.closest("[data-act]");
      if (!btn) return;
      var el = btn.closest(".pb-card");
      if (!el) return;
      var id = el.getAttribute("data-id"), act = btn.getAttribute("data-act");
      if (act === "menu") {
        el.classList.add("is-open");
        /* The dots button is display:none the moment .is-open lands, so hand the
           caret to the first tool rather than letting it fall back to <body>. */
        var first = el.querySelector('.pb-card__tools button');
        if (first) first.focus();
      } else if (act === "close") {
        el.classList.remove("is-open");
        var dots = el.querySelector(".pb-card__dots");
        if (dots) dots.focus();
      } else if (act === "edit") { openDialog(taskById(id)); }
      else if (act === "delete") {
        var task = taskById(id);
        if (!task) return;
        if (!window.confirm("Delete “" + task.title + "”?")) return;
        state.tasks.splice(state.tasks.indexOf(task), 1);
        save(); renderBoard(); renderSprints();
        toast("Task deleted");
      }
    });

    /* Keyboard equivalent of the drag: Ctrl/Cmd + arrows move a focused card
       between open columns, so the board is usable without a pointer. */
    board.addEventListener("keydown", function (ev) {
      var el = ev.target.closest && ev.target.closest(".pb-card");
      if (!el) return;
      var id = el.getAttribute("data-id");
      if (ev.key === "Enter") { ev.preventDefault(); openDialog(taskById(id)); return; }
      if (ev.key === "Delete" || ev.key === "Backspace") {
        ev.preventDefault();
        var task = taskById(id);
        if (task && window.confirm("Delete “" + task.title + "”?")) {
          state.tasks.splice(state.tasks.indexOf(task), 1);
          save(); renderBoard(); renderSprints(); toast("Task deleted");
        }
        return;
      }
      if (!(ev.ctrlKey || ev.metaKey)) return;
      if (ev.key !== "ArrowLeft" && ev.key !== "ArrowRight") return;
      ev.preventDefault();
      var open = (data.columns || []).filter(function (c) { return !state.collapsed[c.id]; });
      var task = taskById(id);
      if (!task) return;
      var at = -1, i;
      for (i = 0; i < open.length; i++) if (open[i].id === task.column) at = i;
      var next = open[at + (ev.key === "ArrowRight" ? 1 : -1)];
      if (!next) return;
      moveTask(id, next.id, null);
      toast("Moved to " + next.name);
      var moved = board.querySelector('.pb-card[data-id="' + id + '"]');
      if (moved) moved.focus();
    });
  }

  // ── dialog ────────────────────────────────────────────────────────────

  function fillDialogOptions() {
    var cols = $("pb-f-column"), boards = $("pb-f-board"), chips = $("pb-f-assignees");
    clear(cols); clear(boards); clear(chips);

    (data.columns || []).forEach(function (c) {
      cols.appendChild(h("option", { value: c.id, text: c.name }));
    });
    (data.boards || []).forEach(function (b) {
      boards.appendChild(h("option", { value: b.id, text: b.name }));
      (b.children || []).forEach(function (kid) {
        boards.appendChild(h("option", { value: kid.id, text: "— " + kid.name }));
      });
    });
    (data.members || []).forEach(function (m) {
      chips.appendChild(h("label", {}, [
        h("input", { type: "checkbox", value: m.id }),
        face(m), h("span", { text: m.name })
      ]));
    });
  }

  function openDialog(task) {
    var dlg = $("pb-dialog");
    if (!dlg) return;
    state.editing = task ? task.id : null;
    $("pb-dialog-title").textContent = task ? "Edit Task" : "Add Task";
    $("pb-f-title").value = task ? task.title : "";
    $("pb-f-column").value = task ? task.column : (data.columns[0] || {}).id;
    $("pb-f-board").value = task ? task.board : (data.boards[0] || {}).id;
    $("pb-f-start").value = task && task.start ? task.start : "";
    $("pb-f-end").value = task && task.end ? task.end : "";
    $("pb-f-priority").value = task ? (task.priority || "none") : "none";
    $("pb-f-subtasks").value = task
      ? (task.subtasks || []).map(function (s) { return s.title; }).join("\n")
      : "";
    [].forEach.call($("pb-f-assignees").querySelectorAll("input"), function (box) {
      box.checked = !!(task && (task.assignees || []).indexOf(box.value) > -1);
    });
    if (typeof dlg.showModal === "function") dlg.showModal(); else dlg.setAttribute("open", "");
    $("pb-f-title").focus();
  }

  function closeDialog() {
    var dlg = $("pb-dialog");
    if (!dlg) return;
    if (typeof dlg.close === "function") dlg.close(); else dlg.removeAttribute("open");
    state.editing = null;
  }

  function submitDialog(ev) {
    ev.preventDefault();
    var title = $("pb-f-title").value.trim();
    if (!title) { $("pb-f-title").focus(); return; }

    var assignees = [].filter.call($("pb-f-assignees").querySelectorAll("input"), function (b) {
      return b.checked;
    }).map(function (b) { return b.value; });

    var subtasks = $("pb-f-subtasks").value.split("\n").map(function (line) {
      return line.trim();
    }).filter(Boolean).map(function (line) { return { title: line, done: false }; });

    var patch = {
      title: title,
      column: $("pb-f-column").value,
      board: $("pb-f-board").value,
      start: $("pb-f-start").value || null,
      end: $("pb-f-end").value || null,
      priority: $("pb-f-priority").value,
      assignees: assignees,
      subtasks: subtasks
    };

    if (state.editing) {
      var task = taskById(state.editing);
      if (task) for (var k in patch) if (Object.prototype.hasOwnProperty.call(patch, k)) task[k] = patch[k];
      toast("Task updated");
    } else {
      patch.id = "t-" + Date.now().toString(36);
      patch.sprint = state.sprint === "all" ? (data.sprints[1] || data.sprints[0] || {}).id : state.sprint;
      state.tasks.unshift(patch);
      toast("Task added to " + (column(patch.column) || {}).name);
    }

    save();
    closeDialog();
    renderBoard();
    renderSprints();
  }

  // ── top bar ───────────────────────────────────────────────────────────

  function download(name, text, type) {
    var blob = new Blob([text], { type: type || "application/json" });
    var url = URL.createObjectURL(blob);
    var a = h("a", { href: url, download: name });
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  }

  function wireTopbar() {
    var q = $("pb-q");
    if (q) {
      q.addEventListener("input", function () {
        state.q = q.value.trim();
        renderBoard();
      });
    }

    var filter = $("pb-filter");
    if (filter) {
      filter.addEventListener("click", function () {
        var at = FILTER_CYCLE.indexOf(state.priority);
        state.priority = FILTER_CYCLE[(at + 1) % FILTER_CYCLE.length];
        filter.setAttribute("aria-pressed", state.priority === "all" ? "false" : "true");
        filter.title = state.priority === "all" ? "Filter by priority"
          : "Showing " + PRIORITY_LABEL[state.priority];
        save(); renderBoard();
        toast(state.priority === "all" ? "Showing all priorities" : PRIORITY_LABEL[state.priority] + " only");
      });
    }

    var sort = $("pb-sort");
    if (sort) {
      sort.addEventListener("click", function () {
        var at = SORT_CYCLE.indexOf(state.sort);
        state.sort = SORT_CYCLE[(at + 1) % SORT_CYCLE.length];
        sort.title = "Sort: " + SORT_LABEL[state.sort];
        save(); renderBoard();
        toast("Sorted by " + SORT_LABEL[state.sort]);
      });
    }

    var exp = $("pb-export");
    if (exp) {
      exp.addEventListener("click", function () {
        download("clearglass-project-board.json", JSON.stringify({
          schema: data.schema, exported: new Date().toISOString(),
          project: state.project, sprint: state.sprint, tasks: state.tasks
        }, null, 2));
        toast("Board exported as JSON");
      });
    }

    var add = $("pb-add");
    if (add) add.addEventListener("click", function () { openDialog(null); });

    var menu = $("pb-menu"), shell = $("pb-shell"), scrim = $("pb-scrim");
    function closePanel() {
      shell.classList.remove("is-panel-open");
      if (menu) menu.setAttribute("aria-expanded", "false");
    }
    if (menu) {
      menu.addEventListener("click", function () {
        var on = shell.classList.toggle("is-panel-open");
        menu.setAttribute("aria-expanded", on ? "true" : "false");
      });
    }
    if (scrim) scrim.addEventListener("click", closePanel);

    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape") closePanel();
      if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === "k") {
        ev.preventDefault();
        if (q) q.focus();
      }
      if (ev.key === "n" && !ev.ctrlKey && !ev.metaKey && !ev.altKey) {
        var tag = (document.activeElement && document.activeElement.tagName) || "";
        if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
        var dlg = $("pb-dialog");
        if (dlg && dlg.open) return;
        ev.preventDefault();
        openDialog(null);
      }
    });
  }

  function wirePanel() {
    var boardsToggle = $("pb-boards-toggle"), tree = $("pb-tree");
    if (boardsToggle && tree) {
      boardsToggle.addEventListener("click", function () {
        var on = boardsToggle.getAttribute("aria-expanded") === "true";
        boardsToggle.setAttribute("aria-expanded", on ? "false" : "true");
        tree.hidden = on;
      });
    }

    var sprintsToggle = $("pb-sprints-toggle"), sprints = $("pb-sprints");
    if (sprintsToggle && sprints) {
      sprintsToggle.addEventListener("click", function () {
        var on = sprintsToggle.getAttribute("aria-expanded") === "true";
        sprintsToggle.setAttribute("aria-expanded", on ? "false" : "true");
        sprints.hidden = on;
      });
    }

    var newBoard = $("pb-new-board");
    if (newBoard) {
      newBoard.addEventListener("click", function () {
        var name = window.prompt("Name the new board");
        if (!name) return;
        var id = name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || ("board-" + Date.now());
        data.boards.push({ id: id, name: name, icon: "asterisk", hue: 258 });
        renderTree();
        fillDialogOptions();
        toast("Board “" + name + "” created");
      });
    }

    var backlog = $("pb-backlog");
    if (backlog) {
      backlog.addEventListener("click", function () {
        state.sprint = "all"; state.board = "all"; state.q = "";
        if ($("pb-q")) $("pb-q").value = "";
        save(); renderTree(); renderSprints(); renderBoard();
        toast("Backlog — every board, every sprint");
      });
    }

    var share = $("pb-share-now");
    if (share) {
      share.addEventListener("click", function () {
        var url = location.origin + "/project-board.html";
        if (navigator.share) {
          navigator.share({ title: "ClearGlass Project Board", url: url }).catch(function () {});
          return;
        }
        if (navigator.clipboard) {
          navigator.clipboard.writeText(url).then(function () { toast("Board link copied"); },
            function () { toast(url); });
          return;
        }
        toast(url);
      });
    }

    var learn = $("pb-learn-more");
    if (learn) {
      learn.addEventListener("click", function () { location.href = "/advanced-features-tools-systems.html"; });
    }
  }

  function wireWidgets() {
    var range = $("pb-act-range");
    if (range) {
      range.value = state.range;
      range.addEventListener("change", function () {
        state.range = range.value; save(); renderFeed();
      });
    }

    var expand = $("pb-act-expand");
    if (expand) {
      expand.addEventListener("click", function () {
        var feed = $("pb-feed");
        var big = feed.style.maxHeight === "none";
        feed.style.maxHeight = big ? "" : "none";
        expand.setAttribute("aria-pressed", big ? "false" : "true");
      });
    }

    var sheetExport = $("pb-sheet-export");
    if (sheetExport) {
      sheetExport.addEventListener("click", function () {
        var rows = ["member,seconds,formatted"];
        (data.timesheet.entries || []).forEach(function (e) {
          rows.push([member(e.member).name, sheetSeconds[e.member], fmtHMS(sheetSeconds[e.member])].join(","));
        });
        download("clearglass-timesheet.csv", rows.join("\n"), "text/csv");
        toast("Time sheet exported as CSV");
      });
    }

    var sheetRange = $("pb-sheet-range");
    if (sheetRange) {
      sheetRange.addEventListener("click", function () {
        toast("Time sheet range: " + (data.workspace.sprint || "current sprint"));
      });
    }

    var velExport = $("pb-vel-export");
    if (velExport) {
      velExport.addEventListener("click", function () {
        download("clearglass-velocity.json", JSON.stringify(data.velocity, null, 2));
        toast("Velocity data downloaded");
      });
    }

    var velRange = $("pb-vel-range");
    if (velRange) {
      velRange.addEventListener("click", function () {
        var series = data.velocity.series || [];
        var at = -1, i;
        for (i = 0; i < series.length; i++) if (series[i].label === state.series) at = i;
        state.series = (series[(at + 1) % series.length] || {}).label;
        save(); renderGauge(); renderLegend();
        toast("Velocity window: " + state.series);
      });
    }

    var calToday = $("pb-cal-today");
    if (calToday) {
      calToday.addEventListener("click", function () {
        state.day = data.calendar.selected; save(); renderWeek(); renderSchedule();
        toast("Back to " + fmtDay(state.day));
      });
    }

    var calExport = $("pb-cal-export");
    if (calExport) {
      calExport.addEventListener("click", function () {
        var rows = ["date,time,title,attendees"];
        (data.calendar.schedule || []).forEach(function (s) {
          rows.push([s.date, s.time, '"' + s.title.replace(/"/g, '""') + '"',
            '"' + (s.attendees || []).map(function (id) { return member(id).name; }).join("; ") + '"'].join(","));
        });
        download("clearglass-schedule.csv", rows.join("\n"), "text/csv");
        toast("Schedule exported as CSV");
      });
    }

    var cta = $("pb-price-cta");
    if (cta) cta.addEventListener("click", function () { location.href = "/pricing.html"; });

    var dlg = $("pb-dialog"), form = $("pb-form");
    if (form) form.addEventListener("submit", submitDialog);
    if ($("pb-dialog-close")) $("pb-dialog-close").addEventListener("click", closeDialog);
    if ($("pb-dialog-cancel")) $("pb-dialog-cancel").addEventListener("click", closeDialog);
    if (dlg) {
      dlg.addEventListener("click", function (ev) {
        if (ev.target === dlg) closeDialog();   // click on the backdrop
      });
    }
  }

  // ── theme ─────────────────────────────────────────────────────────────

  function applyTheme(mode) {
    var root = document.documentElement;
    if (mode === "light") root.setAttribute("data-theme", "light");
    else root.removeAttribute("data-theme");
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", mode === "light" ? "#f4f5f8" : "#08080b");
    if ($("pb-theme-light")) $("pb-theme-light").setAttribute("aria-pressed", mode === "light" ? "true" : "false");
    if ($("pb-theme-dark")) $("pb-theme-dark").setAttribute("aria-pressed", mode === "light" ? "false" : "true");
    try { localStorage.setItem(THEME, mode); } catch (e) { /* no storage */ }
  }

  function wireTheme() {
    var saved = "dark";
    try { saved = localStorage.getItem(THEME) || "dark"; } catch (e) { /* no storage */ }
    applyTheme(saved);
    if ($("pb-theme-light")) $("pb-theme-light").addEventListener("click", function () { applyTheme("light"); });
    if ($("pb-theme-dark")) $("pb-theme-dark").addEventListener("click", function () { applyTheme("dark"); });
  }

  // ── rail ──────────────────────────────────────────────────────────────

  function wireRail() {
    [].forEach.call(document.querySelectorAll(".pb-rail__btn"), function (btn) {
      btn.addEventListener("click", function () {
        [].forEach.call(document.querySelectorAll(".pb-rail__btn"), function (b) {
          b.removeAttribute("aria-current");
        });
        btn.setAttribute("aria-current", "page");
        var view = btn.getAttribute("data-view");
        if (view === "reports") { location.href = "/control-surface.html"; return; }
        if (view === "settings") { location.href = "/advanced-features-tools-systems.html"; return; }
        if (view === "board") { $("pb-board").scrollIntoView({ behavior: REDUCED ? "auto" : "smooth" }); return; }
        if (view === "overview") {
          state.board = "all"; state.sprint = "all"; save();
          renderTree(); renderSprints(); renderBoard();
        }
        toast(btn.getAttribute("title") + " · " + (data.workspace.name || "workspace"));
      });
    });
  }

  // ── boot ──────────────────────────────────────────────────────────────

  function failure(err) {
    var board = $("pb-board");
    if (!board) return;
    clear(board);
    board.appendChild(h("div", {
      cls: "pb-col", style: "width:100%;max-height:none"
    }, [
      h("div", { cls: "pb-col__head" }, h("span", { cls: "pb-chip", style: "--col-color:#ef4444", text: "Feed offline" })),
      h("p", { cls: "pb-col__empty", style: "min-height:auto;padding:14px;text-align:center" },
        "Could not load " + FEED + (err ? " (" + err + ")" : "") + "."),
      h("div", { style: "display:flex;justify-content:center;padding-top:10px" },
        h("button", { cls: "pb-btn pb-btn--primary", type: "button", onclick: boot }, "Retry"))
    ]));
  }

  function seedRuntime() {
    /* Normalise the feed's optional collections once, up front, so no renderer
       has to defend against a missing key. */
    data.projects = data.projects || [];
    data.boards = data.boards || [];
    data.sprints = data.sprints || [];
    data.members = data.members || [];
    data.columns = data.columns || [];
    data.tasks = data.tasks || [];
    data.activity = data.activity || [];
    data.workspace = data.workspace || {};
    data.timesheet = data.timesheet || {};
    data.timesheet.entries = data.timesheet.entries || [];
    data.velocity = data.velocity || {};
    data.velocity.series = data.velocity.series || [];
    data.calendar = data.calendar || {};
    data.calendar.days = data.calendar.days || [];
    data.calendar.schedule = data.calendar.schedule || [];

    data.timesheet.entries.forEach(function (e) { sheetSeconds[e.member] = e.seconds || 0; });
    data.activity.forEach(function (a) { if (a.file) uploadPct[a.id] = a.file.percent || 0; });

    if (!state.tasks.length) state.tasks = JSON.parse(JSON.stringify(data.tasks));
    if (!state.day) state.day = data.calendar.selected || (data.calendar.days[0] || {}).date || "";
    if (!state.series) state.series = data.velocity.selected || (data.velocity.series[0] || {}).label || "";
    data.columns.forEach(function (c) {
      if (!(c.id in state.collapsed)) state.collapsed[c.id] = !!c.collapsed;
    });
    var active = data.projects.filter(function (p) { return p.active; })[0];
    if (active && state.project === "dev-ai") state.project = active.id;
  }

  function renderAll() {
    renderProjects();
    renderTree();
    renderSprints();
    renderBoard();
    renderSheet();
    renderGauge();
    renderLegend();
    renderFeed();
    renderWeek();
    renderSchedule();
    renderStatic();
  }

  var wired = false;

  function start() {
    seedRuntime();
    fillDialogOptions();
    renderAll();

    /* boot() runs again behind the Retry button, so bind the delegated
       listeners exactly once — a second pass would fire every handler twice. */
    if (!wired) {
      wired = true;
      wireBoard();
      wireTopbar();
      wirePanel();
      wireWidgets();
      wireRail();
      wireVisibility();
    }

    clearInterval(timers.sheet);
    clearInterval(timers.upload);
    timers.sheet = setInterval(tickSheet, 1000);
    if (!REDUCED) timers.upload = setInterval(tickUpload, 1400);
  }

  function wireVisibility() {
    document.addEventListener("visibilitychange", function () {
      /* Stop the clocks when the tab is hidden; catch the sheet up on return so
         the elapsed totals stay truthful rather than frozen. */
      if (document.hidden) {
        clearInterval(timers.sheet); clearInterval(timers.upload);
        timers.sheet = null; timers.upload = null;
        state.hiddenAt = Date.now();
      } else {
        if (state.hiddenAt) {
          var away = Math.floor((Date.now() - state.hiddenAt) / 1000);
          (data.timesheet.entries || []).forEach(function (e) {
            if (e.running) sheetSeconds[e.member] += away;
          });
          state.hiddenAt = 0;
          renderSheet();
        }
        if (!timers.sheet) timers.sheet = setInterval(tickSheet, 1000);
        if (!timers.upload && !REDUCED) timers.upload = setInterval(tickUpload, 1400);
      }
    });
  }

  function boot() {
    fetch(FEED, { credentials: "same-origin" }).then(function (res) {
      if (!res.ok) throw new Error("HTTP " + res.status);
      return res.json();
    }).then(function (json) {
      data = json;
      restore();
      start();
    })["catch"](function (err) {
      failure(err && err.message ? err.message : String(err));
    });
  }

  function init() {
    /* The theme lives on the static shell, so apply it before the feed lands —
       otherwise a light-theme visitor gets a dark flash on every load. */
    wireTheme();
    boot();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
