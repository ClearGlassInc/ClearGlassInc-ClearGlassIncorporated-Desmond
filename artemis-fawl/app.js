(() => {
"use strict";
const state={paused:false,filter:"all"};
const data={
kpis:[["Enterprise risk","24 / 100","↓ 4 · 91% conf."],["System integrity","99.2%","stable · 98% conf."],["Active agents","2 / 4","2 approval-gated"],["Workflow success","96.4%","↑ 1.8% · 30d"],["Availability","99.95%","simulated SLO"],["Hours saved","38.5","estimated · 30d"],["Revenue influence","CAD $18.4K","projected · not booked"]],
modules:["Mission Control","Agent Fleet","Security Operations","Infrastructure","Automation","AI Governance","OSINT","Compliance","Identity","DevSecOps","Data Pipelines","Knowledge Graph","Market Intelligence","Executive Operations"],
pipeline:[["Detected",28400,74],["Qualified",18400,86],["Approved",7200,94],["Won",3400,100]],
agents:[
["Opportunity Sentinel","Ranks authorized market and procurement signals","Running"],
["Evidence Steward","Validates provenance, freshness and conflicts","Running"],
["Proposal Architect","Drafts scoped offers; cannot send","Waiting approval"],
["Revenue Controller","Verifies value and records outcomes","Idle"]],
opportunities:[
[92,"Ontario SME cyber readiness review","Verified service offer matched to published buyer needs.","CAD $3,500–7,500","Review"],
[86,"AI governance evidence package","Existing ClearGlass capability aligned to compliance demand.","CAD $2,500–6,000","Review"],
[79,"Public procurement monitoring pilot","Delayed public source; revalidate before outreach.","CAD $1,500–4,000","Trace"]],
decisions:[
["Revenue signal strengthened","Two evidence sources support the SME readiness offer.","86% confidence · no execution"],
["Source freshness warning","Procurement feed is 18 hours old.","Revalidation required"],
["Workflow blocked correctly","Proposal dispatch lacks named human approval.","Policy FAWL-ACT-01"]],
events:[
["agent","Opportunity Sentinel completed scoring","No external action taken."],
["source","Demonstration registry validated","All visible values marked SIMULATED."],
["governance","Policy gate tested","High-impact execution remains locked."],
["agent","Evidence Steward checked conflicts","One stale source warning surfaced."],
["governance","Emergency pause ready","Read-only monitoring remains available."]]};
const $=s=>document.querySelector(s);
function render(){
$("#kpis").innerHTML=data.kpis.map(x=>`<article class="kpi"><span>${x[0]}</span><strong>${x[1]}</strong><small>${x[2]} · SIMULATED</small></article>`).join("");
$("#modules").innerHTML=data.modules.map((x,i)=>`<button class="module ${i===0?"active":""}" data-module="${x}"><span>${x}</span><i aria-hidden="true"></i></button>`).join("");
$("#pipelineChart").innerHTML=data.pipeline.map(x=>`<div class="bar-wrap"><div class="bar" style="height:${Math.round(x[1]/28400*125)}px" title="${x[0]}: CAD $${x[1].toLocaleString()}"></div>${x[0]}</div>`).join("");
$("#pipelineTable").innerHTML=data.pipeline.map(x=>`<tr><td>${x[0]}</td><td>CAD $${x[1].toLocaleString()}</td><td>${x[2]}%</td></tr>`).join("");
$("#agents").innerHTML=data.agents.map(x=>`<div class="agent"><span class="dot ${x[2]==="Running"?"ok":""}"></span><div><strong>${x[0]}</strong><small>${x[1]} · Trust tier T2</small></div><span class="status">${x[2]}</span></div>`).join("");
$("#opportunities").innerHTML=data.opportunities.map(x=>`<div class="opp"><span class="score">${x[0]}</span><div><strong>${x[1]}</strong><p>${x[2]} · SIMULATED</p></div><span class="value">${x[3]}</span><button data-detail="${x[1]}">${x[4]}</button></div>`).join("");
$("#decisions").innerHTML=data.decisions.map(x=>`<article class="decision"><span class="eyebrow">MATERIAL SIGNAL</span><strong>${x[0]}</strong><p>${x[1]}</p><span class="badge">${x[2]}</span></article>`).join("");
renderTimeline();
}
function renderTimeline(){const rows=state.filter==="all"?data.events:data.events.filter(x=>x[0]===state.filter);$("#timeline").innerHTML=rows.map((x,i)=>`<article class="event"><time>${String(12+i).padStart(2,"0")}:0${i} UTC</time><strong>${x[1]}</strong><span>${x[0].toUpperCase()} · ${x[2]}</span></article>`).join("")}
function openDetail(title,body){$("#dialogContent").innerHTML=`<span class="eyebrow">SOURCE-AWARE EXPLANATION</span><h2>${title}</h2><p>${body}</p><dl><dt>Source</dt><dd>ARTEMIS demonstration registry</dd><dt>Classification</dt><dd>SIMULATED / PUBLIC DEMO</dd><dt>Freshness</dt><dd>Generated at page load</dd><dt>Permission</dt><dd>Recommendation only; human approval required</dd></dl>`;$("#detailDialog").showModal()}
setInterval(()=>{$("#utcClock").textContent=new Date().toISOString().slice(11,19)+" UTC"},1000);
document.addEventListener("click",e=>{
const b=e.target.closest("button");if(!b)return;
if(b.id==="pause"){state.paused=!state.paused;b.setAttribute("aria-pressed",state.paused);b.textContent=state.paused?"Resume monitoring":"Emergency pause";document.documentElement.dataset.motion=state.paused?"off":"on";$("#announcer").textContent=state.paused?"Autonomous execution paused. Read-only monitoring remains active.":"Monitoring resumed. Execution remains permission gated."}
if(b.dataset.filter){state.filter=b.dataset.filter;document.querySelectorAll("[data-filter]").forEach(x=>x.classList.toggle("active",x===b));renderTimeline()}
if(b.dataset.module){document.querySelectorAll(".module").forEach(x=>x.classList.toggle("active",x===b));$("#announcer").textContent=b.dataset.module+" selected. Demonstration workspace retained."}
if(b.dataset.detail)openDetail(b.dataset.detail,"The score combines evidence quality (35%), expected value (25%), strategic fit (20%), effort (10%) and risk (10%). It is decision support, not guaranteed income.");
if(b.dataset.command)openDetail("ARTEMIS command result","Command interpreted locally against demonstration data. Production answers require an authenticated backend and authorized source connectors.");
if(b.id==="explainScore")openDetail("Opportunity scoring method","Weighted integer scoring: evidence 35%, value 25%, fit 20%, inverse effort 10%, inverse risk 10%. Missing evidence caps a result below approval level.");
if(b.id==="reviewApprovals")openDetail("Approval queue","Review mode cannot execute. Production approval must verify identity, permission scope, impact, rollback and a tamper-evident audit event.");
if(b.classList.contains("close"))$("#detailDialog").close();
});
$("#commandSearch").addEventListener("keydown",e=>{if(e.key==="Enter"){e.preventDefault();openDetail("Command search",`“${e.target.value||"No command entered"}” was not sent anywhere. This static demonstration performs no external data access.`)}});render();
})();