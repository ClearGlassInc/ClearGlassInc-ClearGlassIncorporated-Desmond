"use strict";
// CLEARGLASS Decision OS. Client-only synthetic state machine. No network requests or external capabilities.
(() => {
  const $ = (selector) => document.querySelector(selector);
  const svgNS = "http://www.w3.org/2000/svg";
  const profiles = {
    revenue: { label: "Revenue sprint", brief: "Model a governed revenue sprint", taskNames: ["Discover", "Qualify", "Draft offers", "Review outreach", "Model delivery", "Review close"], gates: ["Approve sample outreach", "Approve simulated proposal"], desc: ["Review a fictional outbound campaign. This does not send messages.", "Assess a fictional commercial proposal. This cannot collect payment."] },
    launch: { label: "Product launch", brief: "Model a gated product launch", taskNames: ["Research", "Scope", "Prototype", "Review claims", "Test build", "Go / no-go"], gates: ["Review fictional launch copy", "Approve simulated release"], desc: ["Review fictional publication content without publishing.", "Review a simulated release. No files are deployed."] },
    security: { label: "Security response", brief: "Model a safe response workflow", taskNames: ["Triage", "Classify", "Investigate", "Review containment", "Prepare report", "Close incident"], gates: ["Approve mock containment", "Approve fictional incident report"], desc: ["Review a simulated containment action; no systems are modified.", "Review a synthetic report; nothing is exported or sent."] }
  };
  const tasks = [
    { id: "T-01", start: 1, end: 2, gate: false },
    { id: "T-02", start: 3, end: 4, gate: false },
    { id: "T-03", start: 5, end: 7, gate: false },
    { id: "T-04", start: 7, end: 9, gate: 0 },
    { id: "T-05", start: 9, end: 12, gate: false },
    { id: "T-06", start: 12, end: 14, gate: 1 }
  ];
  const nodes = [
    { id: "N-01", short: "SRC", label: "Scenario source", type: "evidence", x: 85, y: 130, detail: "The scenario input is a local deterministic fixture, not an external feed." },
    { id: "N-02", short: "SIG", label: "Signal intake", type: "task", x: 235, y: 85, detail: "Synthetic signal classification. No messages are received." },
    { id: "N-03", short: "CTX", label: "Context check", type: "evidence", x: 382, y: 155, detail: "Inspects modeled context and prerequisites." },
    { id: "N-04", short: "QLF", label: "Qualification", type: "task", x: 515, y: 85, detail: "Qualifies fictional opportunities or work items." },
    { id: "N-05", short: "DFT", label: "Draft step", type: "task", x: 660, y: 135, detail: "Prepares a candidate action inside the model only." },
    { id: "N-06", short: "G-1", label: "Human gate 1", type: "approval", x: 790, y: 84, detail: "Explicit simulated operator decision required for gated work." },
    { id: "N-07", short: "PLN", label: "Work plan", type: "task", x: 385, y: 275, detail: "Routes feasible tasks into the fourteen-day schedule." },
    { id: "N-08", short: "RISK", label: "Risk check", type: "evidence", x: 613, y: 275, detail: "Evaluates model conditions; not a real security assessment." },
    { id: "N-09", short: "G-2", label: "Human gate 2", type: "approval", x: 912, y: 215, detail: "Second operator approval before final modeled execution." },
    { id: "N-10", short: "OBS", label: "Evidence review", type: "evidence", x: 1030, y: 120, detail: "No actual sales, deployments, or operational outcomes can be verified from this demo." },
    { id: "N-11", short: "TML", label: "Timeline", type: "task", x: 170, y: 275, detail: "In-memory sprint timeline and bounded day advancement." },
    { id: "N-12", short: "AUD", label: "Audit trail", type: "evidence", x: 810, y: 305, detail: "Append-only browser-session event history of simulated decisions." }
  ];
  const edges = [[1,2],[2,3],[3,4],[4,5],[5,6],[6,9],[9,10],[1,11],[11,7],[7,8],[8,9],[3,7],[5,8],[8,12],[6,12],[9,12],[2,11]];
  const state = { scenario: "revenue", day: 1, running: false, halted: false, gateDecisions: [null, null], log: [], timer: null, selection: "N-04", sequence: 0 };
  function append(type, message) {
    const time = `D${String(state.day).padStart(2,"0")}:09`; // Model time, not a wall-clock claim.
    state.log.push({ seq: ++state.sequence, modelTime: time, kind: type, scenario: state.scenario, message });
    renderLog();
  }
  function gatePending(){ return state.gateDecisions.filter(x => x === null).length; }
  function taskState(t){
    if(t.gate !== false && state.gateDecisions[t.gate] !== "approved" && state.day >= t.start) return "blocked";
    if(t.gate === false && t.id === "T-05" && state.gateDecisions[0] !== "approved" && state.day >= t.start) return "blocked";
    if(state.day > t.end) return "done";
    if(state.day >= t.start) return "working";
    return "waiting";
  }
  function stopTick(){ if(state.timer !== null){clearInterval(state.timer);state.timer=null;}state.running=false; }
  function renderTop(){
    const name = state.halted ? "HALTED" : state.running ? "RUNNING" : state.day === 14 ? "FINAL DAY" : "READY";
    $("#run-status").innerHTML = "";
    $("#run-status").append(document.createTextNode(name + " "));
    const sub = document.createElement("span"); sub.textContent = state.halted ? "/ EMERGENCY LOCKOUT" : state.running ? "/ SIMULATED CLOCK" : "/ OPERATOR CONTROL"; $("#run-status").append(sub);
    $("#run-status").style.color = state.halted ? "var(--red)" : "var(--teal)";
    $("#run-clock").textContent = `DAY ${String(state.day).padStart(2,"0")} · 09:00 MODEL TIME · 14-DAY WINDOW`;
    $("#day-label").textContent = String(state.day).padStart(2,"0");
    $("#sprint-phase").textContent = `DAY ${String(state.day).padStart(2,"0")}`;
    $("#metric-gates").innerHTML = `${String(gatePending()).padStart(2,"0")}<span> pending</span>`;
    $("#metric-signals").innerHTML = `${String(6+Math.min(state.day-1,8)).padStart(2,"0")}<span> simulated</span>`;
    $("#metric-goal").innerHTML = `14<span> days</span>`;
    $("#brief-detail").textContent = profiles[state.scenario].brief;
    $("#step-btn").disabled = state.halted || state.day >= 14;
    $("#run-btn").disabled = state.halted || (state.day >= 14 && !state.running);
    $("#run-btn").textContent = state.running ? "Ⅱ Pause simulation" : "▶ Run simulation";
    $("#stop-btn").disabled = state.halted;
    $("#stop-btn").setAttribute("aria-pressed", String(state.halted));
  }
  function renderGraph(){
    const svg=$("#decision-graph");svg.replaceChildren();
    const defs=document.createElementNS(svgNS,"defs");const marker=document.createElementNS(svgNS,"marker");marker.setAttribute("id","end-arrow");marker.setAttribute("viewBox","0 0 10 10");marker.setAttribute("refX","9");marker.setAttribute("refY","5");marker.setAttribute("markerWidth","4");marker.setAttribute("markerHeight","4");marker.setAttribute("orient","auto-start-reverse");const shape=document.createElementNS(svgNS,"path");shape.setAttribute("d","M 0 0 L 10 5 L 0 10 z");shape.setAttribute("fill","#4a8d90");marker.append(shape);defs.append(marker);svg.append(defs);
    edges.forEach(([a,b],i)=>{const from=nodes[a-1],to=nodes[b-1];const path=document.createElementNS(svgNS,"path");path.setAttribute("d",`M${from.x} ${from.y} Q${(from.x+to.x)/2} ${((from.y+to.y)/2)+((i%4)-1.5)*27} ${to.x} ${to.y}`);path.setAttribute("class",`edge ${to.type === "approval" ? "approval" : ""} ${i%3===0 ? "flowing" : ""}`);path.setAttribute("marker-end","url(#end-arrow)");svg.append(path);});
    nodes.forEach(n=>{const g=document.createElementNS(svgNS,"g");g.setAttribute("class",`node ${n.type} ${state.selection===n.id ? "selected" : ""}`);g.setAttribute("transform",`translate(${n.x},${n.y})`);g.setAttribute("role","button");g.setAttribute("tabindex","0");g.setAttribute("aria-label",`${n.id} ${n.label}`);
      const circle=document.createElementNS(svgNS,"circle");circle.setAttribute("r",n.type==="approval"?19:16);const label=document.createElementNS(svgNS,"text");label.setAttribute("text-anchor","middle");label.setAttribute("y","4");label.setAttribute("class","node-short");label.textContent=n.short;const sub=document.createElementNS(svgNS,"text");sub.setAttribute("text-anchor","middle");sub.setAttribute("y","36");sub.textContent=n.id;g.append(circle,label,sub);const select=()=>{state.selection=n.id;renderInspector();renderGraph()};g.addEventListener("click",select);g.addEventListener("keydown",(e)=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();select();}});svg.append(g);
    });
  }
  function renderInspector(){const n=nodes.find(n=>n.id===state.selection)||nodes[0];$("#inspector-title").textContent=`${n.id} · ${n.label.toUpperCase()}`;$("#inspector-description").textContent=n.detail;$("#inspector-foot").textContent=`STATE: ${n.type==="approval"?"HUMAN GATED":"MODELED"}`;}
  function renderTasks(){const host=$("#task-list");host.replaceChildren();let done=0,blocked=0;tasks.forEach((t,index)=>{const status=taskState(t);if(status==="done")done++;if(status==="blocked")blocked++;const b=document.createElement("button");b.type="button";b.className="task-item";const icon=document.createElement("span");icon.className=`task-icon ${status}`;icon.textContent=status==="done"?"✓":status==="blocked"?"!":status==="working"?"↻":"·";const label=document.createElement("span");label.textContent=profiles[state.scenario].taskNames[index];const code=document.createElement("small");code.textContent=status.toUpperCase();b.append(icon,label,code);b.title=`${t.id} · Days ${t.start}–${t.end} · ${status}`;b.addEventListener("click",()=>{$("#sprint-callout").textContent=`${t.id}: ${profiles[state.scenario].taskNames[index]} · Days ${t.start}–${t.end} · ${status.toUpperCase()} in the fictional workflow.`;});host.append(b);});$("#task-count").textContent=String(tasks.length).padStart(2,"0");$("#task-complete").textContent=String(done).padStart(2,"0");$("#task-blocked").textContent=String(blocked).padStart(2,"0");}
  function renderSprint(){const dh=$("#day-header");dh.replaceChildren();dh.append(document.createElement("span"));for(let i=1;i<=14;i++){const el=document.createElement("span");el.textContent=String(i).padStart(2,"0");if(i===state.day)el.className="current";dh.append(el);}const host=$("#gantt");host.replaceChildren();tasks.slice(0,5).forEach((t,i)=>{const row=document.createElement("div");row.className="gantt-row";const name=document.createElement("span");name.className="gantt-name";name.textContent=profiles[state.scenario].taskNames[i];const cells=document.createElement("div");cells.className="gantt-days";for(let day=1;day<=14;day++){const cell=document.createElement("i");if(day>=t.start&&day<=t.end){cell.className=`on ${t.gate!==false?"gate":""} ${day<state.day&&taskState(t)!=="blocked"?"past":""}`;}cells.append(cell);}row.append(name,cells);host.append(row);});}
  function decideGate(index,decision){if(state.halted||state.gateDecisions[index]!==null)return;state.gateDecisions[index]=decision;append(decision==="approved"?"ok":"warn",`Gate G-${index+1} ${decision.toUpperCase()} by synthetic operator; no external execution.`);renderAll();}
  function renderGates(){const host=$("#approval-queue");host.replaceChildren();profiles[state.scenario].gates.forEach((name,index)=>{const card=document.createElement("div");card.className="gate-item";const top=document.createElement("div");top.className="gate-top";const id=document.createElement("span");id.className="gate-id";id.textContent=`GATE G-${index+1} / DAY ${index?12:7}`;const risk=document.createElement("span");risk.className="gate-risk";risk.textContent=index?"CRITICAL":"HIGH RISK";top.append(id,risk);const h3=document.createElement("h3");h3.textContent=name;const p=document.createElement("p");p.textContent=profiles[state.scenario].desc[index];card.append(top,h3,p);const decision=state.gateDecisions[index];if(decision){const label=document.createElement("div");label.className=`gate-decision ${decision==="rejected"?"rejected":""}`;label.textContent=`✓ DECISION RECORDED: ${decision.toUpperCase()} · MODEL ONLY`;card.append(label);}else if(state.halted){const locked=document.createElement("div");locked.className="gate-halted";locked.textContent="EMERGENCY LOCKOUT — RESET TO REOPEN SIMULATION";card.append(locked);}else{const actions=document.createElement("div");actions.className="gate-actions";const accept=document.createElement("button");accept.type="button";accept.textContent="✓ Simulate approve";accept.addEventListener("click",()=>decideGate(index,"approved"));const reject=document.createElement("button");reject.type="button";reject.className="reject";reject.textContent="× Simulate reject";reject.addEventListener("click",()=>decideGate(index,"rejected"));actions.append(accept,reject);card.append(actions);}host.append(card);});$("#gate-status").textContent=`${gatePending()} REQUIRE DECISION`;}
  function renderLog(){const host=$("#audit-log");host.replaceChildren();state.log.slice(-22).forEach(e=>{const div=document.createElement("div");div.className="log-line";const time=document.createElement("span");time.className="log-time";time.textContent=e.modelTime;const message=document.createElement("span");const kind=document.createElement("span");kind.className=`log-kind ${e.kind}`;kind.textContent=`[${e.kind.toUpperCase()}] `;message.append(kind,document.createTextNode(e.message));div.append(time,message);host.append(div);});$("#audit-count").textContent=`${state.log.length} ENTRIES`;host.scrollTop=host.scrollHeight;}
  function renderAll(){renderTop();renderTasks();renderSprint();renderGates();renderInspector();renderGraph();}
  function advance(){if(state.halted||state.day>=14)return false;state.day++;append("info",`Simulated clock advanced to day ${state.day}.`);renderAll();if(state.day===14){stopTick();append("ok","14-day model horizon reached. No external actions performed.");renderTop();}return true;}
  function toggleRun(){if(state.halted||state.day>=14)return;if(state.running){stopTick();append("info","Simulation paused by operator.");renderTop();return;}state.running=true;append("ok","Synthetic schedule started; local timer only.");renderTop();state.timer=setInterval(()=>{if(!advance())stopTick();},850);}
  function emergencyStop(){if(state.halted)return;stopTick();state.halted=true;append("warn","EMERGENCY STOP: simulated transitions and gate decisions frozen.");renderAll();}
  function resetScenario(nextScenario){stopTick();state.scenario=nextScenario;state.day=1;state.halted=false;state.gateDecisions=[null,null];state.selection="N-04";append("info",`Model reset to ${profiles[state.scenario].label}. Previous session ledger retained.`);renderAll();}
  function exportModel(){const payload={name:"ClearGlass Decision OS",version:"0.1.0",synthetic:true,notice:"Generated examples only; no live connections or real outcomes",scenario:state.scenario,day:state.day,halted:state.halted,approvals:state.gateDecisions.map((decision,i)=>({id:`G-${i+1}`,decision})),ledger:state.log.map(e=>({...e}))};const blob=new Blob([JSON.stringify(payload,null,2)],{type:"application/json"});const url=URL.createObjectURL(blob);const a=document.createElement("a");a.href=url;a.download=`clearglass-decision-os-${state.scenario}-day-${String(state.day).padStart(2,"0")}.json`;document.body.append(a);a.click();a.remove();URL.revokeObjectURL(url);append("info","Synthetic model exported to a local JSON download.");}
  $("#scenario").addEventListener("change",e=>resetScenario(e.target.value));$("#step-btn").addEventListener("click",advance);$("#run-btn").addEventListener("click",toggleRun);$("#stop-btn").addEventListener("click",emergencyStop);$("#reset-btn").addEventListener("click",()=>resetScenario(state.scenario));$("#export-btn").addEventListener("click",exportModel);
  const modal=$("#shortcuts-dialog");$("#help-btn").addEventListener("click",()=>modal.showModal());$("#close-help").addEventListener("click",()=>modal.close());document.addEventListener("keydown",e=>{if(modal.open||e.altKey||e.ctrlKey||e.metaKey||["INPUT","TEXTAREA","SELECT","BUTTON"].includes(document.activeElement?.tagName)||document.activeElement?.getAttribute("role")==="button")return;if(e.key===" "||e.key==="ArrowRight"){e.preventDefault();if(e.key===" ")toggleRun();else advance();}});
  append("ok","Synthetic execution environment initialized. Zero external connectors.");renderAll();
})();

