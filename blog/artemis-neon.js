(() => {
  "use strict";
  const consoleElement = document.querySelector("[data-power-console]");

  const buttons = consoleElement ? [...consoleElement.querySelectorAll("[data-power-select]")] : [];
  const output = consoleElement?.querySelector("[data-power-output]");
  const descriptions = {
    idle: "Telemetry watch",
    warming: "Core warming",
    active: "Stabilized core",
    critical: "Priority response",
    locked: "Human gate locked",
  };

  buttons.forEach((button) => {
    button.addEventListener("click", () => {
      const state = button.dataset.powerSelect;
      if (!Object.hasOwn(descriptions, state)) return;
      if (consoleElement) consoleElement.dataset.powerState = state;
      buttons.forEach((candidate) => candidate.setAttribute("aria-pressed", String(candidate === button)));
      if (output) output.textContent = descriptions[state];
    });
  });

  const architecture = document.querySelector("[data-architecture-console]");
  if (architecture) {
    const filters = [...architecture.querySelectorAll("[data-layer-select]")];
    const nodes = [...architecture.querySelectorAll("[data-layer]")];
    const status = architecture.querySelector("[data-layer-status]");
    const detail = architecture.querySelector("[data-layer-detail]");
    filters.forEach((filter) => filter.addEventListener("click", () => {
      const selected = filter.dataset.layerSelect;
      filters.forEach((item) => item.setAttribute("aria-pressed", String(item === filter)));
      nodes.forEach((node) => node.classList.toggle("is-muted", selected !== "all" && node.dataset.layer !== selected));
      if (status) status.textContent = selected === "all" ? "All trust domains visible" : `${selected} domain isolated`;
    }));
    nodes.forEach((node) => node.addEventListener("click", () => {
      nodes.forEach((item) => item.classList.toggle("is-selected", item === node));
      if (!detail) return;
      detail.querySelector("span").textContent = node.querySelector("strong").textContent;
      detail.querySelector("p").textContent = node.dataset.detail;
      detail.focus({ preventScroll: true });
    }));
  }

  const attackCycle = document.querySelector("[data-attack-cycle]");
  if (attackCycle) {
    const stages = [
      ["Stage 01 · Observe", "Reconnaissance and entry", "Fuse edge telemetry and source history, score confidence, and surface suspicious access without treating a model hypothesis as verified attribution.", "Defender control · phishing-resistant identity, least privilege, and zero-trust access"],
      ["Stage 02 · Constrain", "Privilege escalation", "Correlate identity, workload, and entitlement changes while deterministic policy—not model output—decides whether a privilege transition is allowed.", "Defender control · just-in-time access, separation of duties, and immutable authorization evidence"],
      ["Stage 03 · Contain", "Lateral movement", "Resolve related assets and sessions into the ontology, then propose bounded containment options with evidence, blast radius, and rollback steps.", "Defender control · microsegmentation, service identity, and east-west anomaly detection"],
      ["Stage 04 · Preserve", "Persistence and exfiltration", "Join endpoint, cloud, network, and data-lineage signals to identify persistence hypotheses and suspicious data movement across trust domains.", "Defender control · egress allowlists, tamper-evident telemetry, and scoped isolation approvals"],
      ["Stage 05 · Recover", "Execution and impact", "Draft an action package that ranks safe response choices, shows uncertainty, and halts at the human decision boundary before consequential execution.", "Defender control · tested restoration, continuity plans, and approval-gated response actions"],
      ["Stage 06 · Improve", "Governed learning and adaptation", "Convert operator corrections and mission outcomes into eval cases; promote prompt or workflow candidates only after review, canary evidence, and signed release approval.", "Defender control · drift alarms, versioned policy, Apollo rollback, and an append-only audit trail"],
    ];
    const stageButtons = [...attackCycle.querySelectorAll("[data-cycle-select]")];
    const setStage = (index) => {
      const stage = stages[index];
      if (!stage) return;
      stageButtons.forEach((button, buttonIndex) => button.setAttribute("aria-pressed", String(buttonIndex === index)));
      attackCycle.querySelector("[data-cycle-stage]").textContent = stage[0];
      attackCycle.querySelector("[data-cycle-title]").textContent = stage[1];
      attackCycle.querySelector("[data-cycle-detail]").textContent = stage[2];
      attackCycle.querySelector("[data-cycle-control]").textContent = stage[3];
      attackCycle.querySelector("[data-cycle-counter]").textContent = `${String(index + 1).padStart(2, "0")} / 06`;
    };
    stageButtons.forEach((button, index) => button.addEventListener("click", () => setStage(index)));
  }

  const progress = document.createElement("div");
  progress.className = "reading-progress";
  progress.setAttribute("aria-hidden", "true");
  document.body.prepend(progress);
  const updateProgress = () => {
    const distance = document.documentElement.scrollHeight - innerHeight;
    progress.style.transform = `scaleX(${distance > 0 ? Math.min(scrollY / distance, 1) : 0})`;
  };
  addEventListener("scroll", updateProgress, { passive: true });
  updateProgress();

  document.querySelectorAll("pre").forEach((pre) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "copy-code";
    button.textContent = "Copy code";
    button.setAttribute("aria-label", "Copy this code example");
    button.addEventListener("click", async () => {
      if (!navigator.clipboard) return;
      await navigator.clipboard.writeText(pre.querySelector("code")?.textContent || pre.textContent);
      button.textContent = "Copied";
      setTimeout(() => { button.textContent = "Copy code"; }, 1600);
    });
    pre.prepend(button);
  });
})();
