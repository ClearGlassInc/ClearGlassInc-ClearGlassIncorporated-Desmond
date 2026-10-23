// Agent OS console. Same-origin only; every value from the server is set with
// textContent, never parsed as HTML. Each request reports one of five states:
// loading, success, error, timeout, unavailable.
(function () {
  "use strict";
  var TIMEOUT_MS = 10000;
  var ACTIVE = { queued: 1, running: 1 };
  var current = null;
  var pollTimer = null;

  function $(id) { return document.getElementById(id); }
  function el(tag, text, state) {
    var node = document.createElement(tag);
    if (text !== undefined && text !== null) node.textContent = String(text);
    if (state) node.setAttribute("data-state", state);
    return node;
  }
  function store(key, value) {
    try {
      if (value === undefined) return sessionStorage.getItem(key) || "";
      sessionStorage.setItem(key, value);
    } catch (e) { /* storage blocked: tokens live only in the field */ }
    return value || "";
  }
  function setStatus(node, state, text) {
    node.setAttribute("data-state", state);
    node.textContent = text;
  }

  // One request, one honest outcome. Never throws.
  function call(method, path, body, approver) {
    var token = approver ? $("approver-token").value.trim() : $("token").value.trim();
    var ctrl = new AbortController();
    var timer = setTimeout(function () { ctrl.abort(); }, TIMEOUT_MS);
    var init = { method: method, headers: { Accept: "application/json" }, signal: ctrl.signal };
    if (token) init.headers.Authorization = "Bearer " + token;
    if (body) { init.headers["Content-Type"] = "application/json"; init.body = JSON.stringify(body); }
    return fetch(path, init).then(function (res) {
      clearTimeout(timer);
      return res.json().catch(function () { return {}; }).then(function (data) {
        if (res.ok) return { state: "success", status: res.status, data: data };
        var state = res.status === 503 ? "unavailable" : "error";
        return { state: state, status: res.status, data: data, message: data.error || ("HTTP " + res.status) };
      });
    }).catch(function (err) {
      clearTimeout(timer);
      if (err && err.name === "AbortError") return { state: "timeout", message: "no answer within " + TIMEOUT_MS / 1000 + "s" };
      return { state: "unavailable", message: "server unreachable" };
    });
  }

  function checkReady() {
    call("GET", "/readyz").then(function (r) {
      var node = $("ready");
      if (r.state === "success") return setStatus(node, "ok", "Ready · workers " + r.data.checks.workers_alive + "/" + r.data.checks.workers_expected + (r.data.checks.approvals_configured ? " · approvals on" : " · approvals off"));
      if (r.data && r.data.checks) return setStatus(node, "unavailable", "Not ready · store " + (r.data.checks.store ? "ok" : "down") + " · workers " + r.data.checks.workers_alive);
      setStatus(node, r.state, r.state === "timeout" ? "Server timed out" : "Server unavailable");
    });
  }

  function renderMission(m) {
    $("mission").hidden = false;
    $("mission-objective").textContent = m.objective;
    setStatus($("mission-state"), m.status, m.status.replace(/_/g, " "));
    $("mission-id").textContent = m.correlation_id;
    $("mission-note").textContent = (m.plan && m.plan.note) || "";
    $("cancel-btn").disabled = !(m.status in ACTIVE || m.status === "waiting_for_approval");
    var body = $("tasks");
    body.textContent = "";
    m.tasks.forEach(function (t) {
      var row = el("tr");
      row.appendChild(el("td", t.capability));
      row.appendChild(el("td", t.assigned_agent));
      row.appendChild(el("td", t.status.replace(/_/g, " "), t.status));
      row.appendChild(el("td", t.attempt + "/" + t.max_attempts));
      var cell = el("td");
      if (t.error) cell.appendChild(el("p", t.error, "error"));
      if (t.status === "waiting_for_approval") cell.appendChild(decisionControls(t));
      if (t.output || (t.evidence && t.evidence.length)) {
        var details = el("details");
        details.appendChild(el("summary", "Output and evidence"));
        if (t.evidence && t.evidence.length) {
          var list = el("ul");
          t.evidence.forEach(function (e) { list.appendChild(el("li", e)); });
          details.appendChild(list);
        }
        if (t.output) {
          var shown = t.output.json !== undefined ? JSON.stringify(t.output.json, null, 2) : (t.output.stdout || "(no output)");
          details.appendChild(el("pre", shown));
          if (t.output.stderr) details.appendChild(el("pre", t.output.stderr));
        }
        cell.appendChild(details);
      }
      row.appendChild(cell);
      body.appendChild(row);
    });
  }

  function decisionControls(task) {
    var wrap = el("div");
    var reason = el("input");
    reason.placeholder = "Reason (required)";
    reason.maxLength = 500;
    wrap.appendChild(reason);
    var note = el("p", "", "");
    note.className = "status";
    ["approve", "reject"].forEach(function (decision) {
      var btn = el("button", decision === "approve" ? "Approve" : "Reject");
      btn.type = "button";
      btn.disabled = !$("approver-token").value.trim();
      btn.title = btn.disabled ? "Enter the approver token to decide" : "";
      btn.addEventListener("click", function () {
        setStatus(note, "loading", "Sending decision…");
        call("POST", "/api/tasks/" + task.task_id + "/decision", { decision: decision, reason: reason.value }, true)
          .then(function (r) {
            if (r.state === "success") { setStatus(note, "ok", "Recorded."); return loadMission(current); }
            setStatus(note, r.state, "Not recorded: " + r.message);
          });
      });
      wrap.appendChild(btn);
    });
    wrap.appendChild(note);
    return wrap;
  }

  function loadMission(id) {
    if (!id) return;
    current = id;
    clearTimeout(pollTimer);
    var status = $("mission-status");
    if (!$("mission").hidden) status.textContent = ""; else setStatus(status, "loading", "Loading mission…");
    call("GET", "/api/missions/" + id).then(function (r) {
      if (r.state !== "success") {
        setStatus(status, r.state, "Mission could not be loaded: " + r.message);
        pollTimer = setTimeout(function () { loadMission(id); }, 5000);
        return;
      }
      status.textContent = "";
      renderMission(r.data);
      call("GET", "/api/missions/" + id + "/events").then(function (ev) {
        if (ev.state !== "success") return setStatus($("chain"), ev.state, "unknown");
        setStatus($("chain"), ev.data.chain_verified ? "verified" : "broken", ev.data.chain_verified ? "verified" : "BROKEN at " + ev.data.first_bad_index);
      });
      if (r.data.status in ACTIVE) pollTimer = setTimeout(function () { loadMission(id); }, 2000);
    });
  }

  function loadList() {
    var status = $("list-status");
    call("GET", "/api/missions?limit=15").then(function (r) {
      var list = $("missions");
      if (r.state !== "success") return setStatus(status, r.state, "Missions unavailable: " + r.message);
      status.textContent = "";
      list.textContent = "";
      if (!r.data.missions.length) setStatus(status, "ok", "No missions yet.");
      r.data.missions.forEach(function (m) {
        var item = el("li");
        var link = el("button", m.objective);
        link.type = "button";
        link.addEventListener("click", function () { loadMission(m.correlation_id); });
        item.appendChild(link);
        item.appendChild(el("span", " " + m.status.replace(/_/g, " "), m.status));
        list.appendChild(item);
      });
    });
  }

  function loadMetrics() {
    var status = $("metrics-status");
    call("GET", "/api/metrics").then(function (r) {
      if (r.state !== "success") return setStatus(status, r.state, "Metrics unavailable: " + r.message);
      status.textContent = "";
      var dl = $("metrics");
      dl.textContent = "";
      [["Missions", r.data.missions], ["Queue depth", r.data.queue_depth],
       ["Awaiting approval", r.data.awaiting_approval], ["Retries", r.data.retries],
       ["Oldest queued (s)", r.data.oldest_queued_seconds === null ? "—" : r.data.oldest_queued_seconds],
       ["Tasks by status", JSON.stringify(r.data.tasks_by_status)]].forEach(function (pair) {
        dl.appendChild(el("dt", pair[0]));
        dl.appendChild(el("dd", pair[1]));
      });
      var body = $("sources");
      body.textContent = "";
      r.data.data_sources.forEach(function (s) {
        var row = el("tr");
        row.appendChild(el("td", s.id));
        row.appendChild(el("td", s.feed));
        row.appendChild(el("td", (s.state || "unknown").replace(/_/g, " "), s.state));
        row.appendChild(el("td", s.age_hours === null || s.age_hours === undefined ? "—" : s.age_hours));
        row.appendChild(el("td", s.last_success_utc || "never"));
        body.appendChild(row);
      });
    });
  }

  function refreshAll() { loadList(); loadMetrics(); }

  document.addEventListener("DOMContentLoaded", function () {
    $("token").value = store("agentos.token");
    $("approver-token").value = store("agentos.approver");
    $("token").addEventListener("change", function () { store("agentos.token", this.value.trim()); refreshAll(); });
    $("approver-token").addEventListener("change", function () {
      store("agentos.approver", this.value.trim());
      if (current) loadMission(current);
    });
    $("submit-form").addEventListener("submit", function (e) {
      e.preventDefault();
      var status = $("submit-status");
      var objective = $("objective").value.trim();
      // One key per objective attempt: a retry after a timeout returns the same mission.
      var key = "console-" + (window.crypto && crypto.randomUUID ? crypto.randomUUID() : String(Date.now()));
      setStatus(status, "loading", "Planning…");
      call("POST", "/api/missions", { objective: objective, idempotency_key: key }).then(function (r) {
        if (r.state === "success") {
          var m = r.data;
          var note = m.status === "unmatched" ? "No registered capability matches — nothing was run." :
            m.tasks.length + " task(s) planned" + (m.plan.gated.length ? ", " + m.plan.gated.length + " waiting for approval" : "") + ".";
          setStatus(status, m.status === "unmatched" ? "warn" : "ok", note);
          loadMission(m.correlation_id);
          loadList();
          return;
        }
        var text = r.state === "timeout" ? "Timed out. The request may still have been accepted; check Recent missions before resubmitting." : "Not submitted: " + r.message;
        setStatus(status, r.state, text);
      });
    });
    $("cancel-btn").addEventListener("click", function () {
      if (!current) return;
      setStatus($("mission-status"), "loading", "Cancelling…");
      call("POST", "/api/missions/" + current + "/cancel").then(function (r) {
        if (r.state !== "success") return setStatus($("mission-status"), r.state, "Cancel failed: " + r.message);
        setStatus($("mission-status"), "ok", "Cancelled " + r.data.cancelled + " task(s); asked " + r.data.stop_requested + " running task(s) to stop.");
        loadMission(current);
      });
    });
    checkReady();
    setInterval(checkReady, 10000);
    if ($("token").value) refreshAll();
    setInterval(function () { if ($("token").value) refreshAll(); }, 15000);
  });
})();
