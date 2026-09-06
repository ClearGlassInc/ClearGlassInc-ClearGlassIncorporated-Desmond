(function () {
  "use strict";

  var root = document.getElementById("growth-system");
  if (!root) return;

  var flags = {
    ENABLE_WEBGPU_VISUALS: false,
    ENABLE_AI_DEMO: false,
    ENABLE_EXPERIMENT_LAB: false,
    ENABLE_ANALYTICS: false,
    ENABLE_LEAD_CAPTURE: false
  };

  function detectVisualMode() {
    var label = document.getElementById("visual-mode");
    if (!label) return;
    var canvas = document.createElement("canvas");
    var available = navigator.gpu ? "WebGPU available · disabled" :
      (canvas.getContext("webgl2") ? "WebGL available · disabled" :
        (canvas.getContext("2d") ? "Canvas available · SVG active" : "Static content mode"));
    label.textContent = available;
  }

  function recommendation(data) {
    var score = 0;
    if (data.status === "none" || data.status === "legacy") score += 2;
    if (data.constraint === "technology" || data.constraint === "governance") score += 2;
    if (data.stage === "build") score += 2;
    if (data.automation === "advanced") score += 1;
    var complexity = score >= 5 ? "High" : score >= 3 ? "Medium" : "Low";
    var starts = {
      clarity: ["Offer and information architecture", "Strategy → Experience engineering"],
      demand: ["Discoverability and measurement plan", "Strategy → Discoverability"],
      conversion: ["Conversion-path baseline", "Strategy → Conversion infrastructure"],
      operations: ["Workflow and integration map", "Strategy → Automation and AI"]
    };
    var start = starts[data.goal] || starts.clarity;
    var areas = [];
    if (data.status !== "modern") areas.push("technical foundation");
    if (data.constraint === "measurement") areas.push("consent-aware measurement");
    if (data.constraint === "governance") areas.push("security and approval controls");
    if (data.automation !== "low") areas.push("human-supervised workflow automation");
    if (!areas.length) areas.push("structured experimentation");
    var confidence = data.status && data.goal && data.constraint ? "Moderate" : "Low";
    return { start: start[0], pathway: start[1], complexity: complexity, areas: areas, confidence: confidence };
  }

  var scan = document.getElementById("readiness-form");
  if (scan) scan.addEventListener("submit", function (event) {
    event.preventDefault();
    if (!scan.reportValidity()) return;
    var data = Object.fromEntries(new FormData(scan).entries());
    var result = recommendation(data);
    document.getElementById("scan-result").innerHTML =
      '<p class="result-label">Educational recommendation</p><h3>' + result.start + '</h3>' +
      '<dl><div><dt>Potential improvement areas</dt><dd>' + result.areas.join(", ") + '</dd></div>' +
      '<div><dt>Suggested pathway</dt><dd>' + result.pathway + '</dd></div>' +
      '<div><dt>Estimated complexity</dt><dd><span class="complexity">' + result.complexity + '</span></dd></div>' +
      '<div><dt>Recommended next step</dt><dd>Validate assumptions in a human-led discovery session before selecting scope.</dd></div>' +
      '<div><dt>Confidence</dt><dd>' + result.confidence + ' — based only on the six answers supplied.</dd></div>' +
      '<div><dt>How this was generated</dt><dd>A deterministic rule set weighs website maturity, constraint, stage, and automation preference. No AI model or personal data was used.</dd></div></dl>';
  });

  var nodes = ["Website", "Landing pages", "Content", "Search visibility", "Analytics", "CRM", "Email automation", "Lead capture", "Customer support", "Deployment pipeline", "Security controls", "Conversion events", "Experimentation"];
  var states = ["Needs attention", "Not assessed", "Ready for review", "In progress", "Verified", "Not applicable"];
  var host = document.getElementById("twin-nodes");
  var detail = document.getElementById("twin-detail");
  function showNode(name, index, button) {
    host.querySelectorAll("button").forEach(function (item) { item.setAttribute("aria-pressed", String(item === button)); });
    detail.innerHTML = '<p class="result-label">Demo node record</p><h3>' + name + '</h3><dl>' +
      '<div><dt>Purpose</dt><dd>Support the ' + name.toLowerCase() + ' layer within the growth system.</dd></div>' +
      '<div><dt>Current state</dt><dd>' + states[index % states.length] + ' (illustrative)</dd></div>' +
      '<div><dt>Dependencies</dt><dd>Validated strategy, content, ownership, and measurement contract.</dd></div>' +
      '<div><dt>Possible improvement</dt><dd>Define evidence-backed acceptance criteria and a reversible delivery increment.</dd></div>' +
      '<div><dt>Estimated effort</dt><dd>' + (["Low", "Medium", "High"][index % 3]) + ' — requires discovery.</dd></div>' +
      '<div><dt>Business relevance</dt><dd>Clarify how this layer supports attention, trust, conversion, or learning.</dd></div>' +
      '<div><dt>Evidence required</dt><dd>Owner interview, approved analytics, technical inspection, and user evidence.</dd></div>' +
      '<div><dt>Owner</dt><dd>Unassigned demo role</dd></div><div><dt>Approval status</dt><dd>Human review required</dd></div></dl>';
  }
  if (host && detail) nodes.forEach(function (name, index) {
    var button = document.createElement("button");
    button.type = "button";
    button.className = "twin-node";
    button.setAttribute("role", "listitem");
    button.setAttribute("aria-pressed", "false");
    button.innerHTML = name + "<small>" + states[index % states.length] + " · demo</small>";
    button.addEventListener("click", function () { showNode(name, index, button); });
    host.appendChild(button);
  });

  var disableAI = document.getElementById("disable-ai");
  if (disableAI) disableAI.addEventListener("click", function () {
    flags.ENABLE_AI_DEMO = false;
    disableAI.setAttribute("aria-pressed", "true");
    disableAI.textContent = "AI processing disabled for this workspace";
  });

  detectVisualMode();
})();
