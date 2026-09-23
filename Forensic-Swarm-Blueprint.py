"""
12-Agent Forensic Swarm Blueprint
Blackboard Architecture + Adjudicator Consensus
DARPA/NSA Mapped | Dashboard-Ready

Deploy: python forensic_swarm_blueprint.py
Dashboard API: FastAPI on /swarm/run
"""

import asyncio
import uuid
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any
from enum import Enum
from collections import defaultdict

# --- Core Types ---

class Severity(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class Evidence:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    agent: str = ""
    type: str = ""
    title: str = ""
    confidence: float = 0.0  # 0-1
    severity: Severity = Severity.MEDIUM
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    darpa_technique: str = ""  # e.g., DARPA Transparent Computing, NSA TTP
    nsa_mapping: str = ""
    mitre_id: str = ""

@dataclass
class Finding:
    consensus: bool
    verdict: str
    confidence: float
    contributing_agents: List[str]
    evidences: List[Evidence]
    adjudicator_notes: str = ""

# --- Blackboard: Shared Evidence Store ---

class Blackboard:
    def __init__(self):
        self.evidences: Dict[str, List[Evidence]] = defaultdict(list)
        self._lock = asyncio.Lock()
        self._subscribers = []
        self.case_id = str(uuid.uuid4())

    async def publish(self, ev: Evidence):
        async with self._lock:
            self.evidences[ev.type].append(ev)
            # publish to dashboard listeners
            for cb in self._subscribers:
                try:
                    await cb(ev)
                except Exception:
                    pass
        print(f"[BLACKBOARD] {ev.agent} -> {ev.title} ({ev.confidence:.2f}) | {ev.darpa_technique}")

    async def get_all(self) -> List[Evidence]:
        async with self._lock:
            return [e for lst in self.evidences.values() for e in lst]

    async def get_by_type(self, t: str) -> List[Evidence]:
        async with self._lock:
            return list(self.evidences.get(t, []))

    def subscribe(self, callback):
        self._subscribers.append(callback)

# --- Base Agent ---

class BaseForensicAgent:
    name: str = "base"
    darpa_program: str = ""
    nsa_technique: str = ""
    mitre: str = ""
    weight: float = 1.0  # for adjudicator

    def __init__(self, blackboard: Blackboard):
        self.bb = blackboard

    async def analyze(self, context: Dict[str, Any]) -> List[Evidence]:
        raise NotImplementedError

    async def run(self, context: Dict[str, Any]):
        try:
            findings = await self.analyze(context)
            for ev in findings:
                ev.agent = self.name
                ev.darpa_technique = self.darpa_program
                ev.nsa_mapping = self.nsa_technique
                ev.mitre_id = self.mitre
                await self.bb.publish(ev)
        except Exception as e:
            await self.bb.publish(Evidence(
                agent=self.name, type="error", title=f"{self.name} failed: {e}",
                confidence=0.0, severity=Severity.LOW
            ))

# --- 12 Specialized Agents ---

class MemoryForensicsAgent(BaseForensicAgent):
    name = "memory_forensics"
    darpa_program = "DARPA Transparent Computing - Process Provenance"
    nsa_technique = "NSA/CSS #4 - Memory Analysis"
    mitre = "T1055 Process Injection"
    weight = 1.3
    async def analyze(self, ctx):
        # plug in volatility3 / memprocfs
        await asyncio.sleep(0.2)
        return [Evidence(type="memory", title="Anomalous RWX private memory in lsass", confidence=0.88, severity=Severity.CRITICAL, data={"pid": 720, "protection": "RWX"})]

class DiskForensicsAgent(BaseForensicAgent):
    name = "disk_forensics"
    darpa_program = "DARPA RADICS - Disk Image Integrity"
    nsa_technique = "NSA #2 - File System Timeline"
    mitre = "T1070.004 File Deletion"
    weight = 1.0
    async def analyze(self, ctx):
        await asyncio.sleep(0.15)
        return [Evidence(type="disk", title="Deleted staging archive in $MFT unallocated", confidence=0.76, severity=Severity.HIGH)]

class NetworkForensicsAgent(BaseForensicAgent):
    name = "network_forensics"
    darpa_program = "DARPA CHASE - Network Hunt"
    nsa_technique = "NSA #12 - C2 Beacon Analysis"
    mitre = "T1071 Application Layer Protocol"
    weight = 1.2
    async def analyze(self, ctx):
        await asyncio.sleep(0.18)
        return [Evidence(type="network", title="Periodic 60s beacon to 185.220.x.x:443", confidence=0.91, severity=Severity.CRITICAL, data={"jitter": 0.03})]

class MalwareTriageAgent(BaseForensicAgent):
    name = "malware_triage"
    darpa_program = "DARPA HACMS / CFAR - Binary Analysis"
    nsa_technique = "NSA #6 - Malware Triaging"
    mitre = "T1204 User Execution"
    weight = 1.2
    async def analyze(self, ctx):
        await asyncio.sleep(0.25)
        return [Evidence(type="malware", title="Packed loader with API hammering", confidence=0.84, severity=Severity.HIGH)]

class TimelineReconstructorAgent(BaseForensicAgent):
    name = "timeline_reconstructor"
    darpa_program = "DARPA Transparent Computing TA2 - Causality Engine"
    nsa_technique = "NSA #1 - Timeline Correlation"
    mitre = "T1070 Indicator Removal"
    weight = 1.4
    async def analyze(self, ctx):
        await asyncio.sleep(0.22)
        # correlates all evidence types
        return [Evidence(type="timeline", title="Execution chain: phish.doc -> powershell -> lsass dump", confidence=0.89, severity=Severity.CRITICAL)]

class RegistryAnalyzerAgent(BaseForensicAgent):
    name = "registry_analyzer"
    darpa_program = "DARPA - Configuration Provenance"
    nsa_technique = "NSA #3 - Persistence via Registry"
    mitre = "T1112 Modify Registry"
    weight = 0.9
    async def analyze(self, ctx):
        await asyncio.sleep(0.12)
        return [Evidence(type="registry", title="Run key created by non-admin SID", confidence=0.73, severity=Severity.HIGH)]

class LogAnomalyAgent(BaseForensicAgent):
    name = "log_anomaly"
    darpa_program = "DARPA SIEVE - Log Integrity"
    nsa_technique = "NSA #8 - Event Log Tampering Detection"
    mitre = "T1562.002 Impair Defenses"
    weight = 1.0
    async def analyze(self, ctx):
        await asyncio.sleep(0.14)
        return [Evidence(type="log", title="4624/4625 log gap 02:13-02:47 UTC", confidence=0.81, severity=Severity.MEDIUM)]

class CryptoDetectorAgent(BaseForensicAgent):
    name = "crypto_detector"
    darpa_program = "DARPA Cyber Hunting - Crypto Misuse"
    nsa_technique = "NSA #9 - Obfuscation & Encoding"
    mitre = "T1027 Obfuscated Files"
    weight = 0.9
    async def analyze(self, ctx):
        await asyncio.sleep(0.1)
        return [Evidence(type="crypto", title="High entropy blob + RC4 key schedule in .tmp", confidence=0.77, severity=Severity.MEDIUM)]

class ThreatIntelCorrelatorAgent(BaseForensicAgent):
    name = "threat_intel_correlator"
    darpa_program = "DARPA Enhanced Attribution"
    nsa_technique = "NSA #11 - TTP Correlation"
    mitre = "T1580 Cloud Infra"
    weight = 1.1
    async def analyze(self, ctx):
        await asyncio.sleep(0.2)
        return [Evidence(type="intel", title="YARA hit APT29 loader + Infra overlap", confidence=0.86, severity=Severity.HIGH)]

class ProcessTreeAnalystAgent(BaseForensicAgent):
    name = "process_tree"
    darpa_program = "DARPA Transparent Computing - Process Tree Provenance"
    nsa_technique = "NSA #5 - Process Ancestry"
    mitre = "T1036 Masquerading"
    weight = 1.2
    async def analyze(self, ctx):
        await asyncio.sleep(0.16)
        return [Evidence(type="process", title="Suspicious parent spoof: explorer.exe spawning rundll32", confidence=0.88, severity=Severity.HIGH)]

class PersistenceHunterAgent(BaseForensicAgent):
    name = "persistence_hunter"
    darpa_program = "DARPA Rapid Attack Detection - Persistence"
    nsa_technique = "NSA #3.2 - Scheduled Task / WMI"
    mitre = "T1053.005 Scheduled Task"
    weight = 1.0
    async def analyze(self, ctx):
        await asyncio.sleep(0.13)
        return [Evidence(type="persistence", title="WMI Event Consumer with encoded PowerShell", confidence=0.90, severity=Severity.CRITICAL)]

class AttributionAgent(BaseForensicAgent):
    name = "attribution_provenance"
    darpa_program = "DARPA Cyber Attribution - Provenance Graph"
    nsa_technique = "NSA #15 - Attribution & Intent"
    mitre = "TA0001 Initial Access"
    weight = 0.8
    async def analyze(self, ctx):
        await asyncio.sleep(0.19)
        return [Evidence(type="attribution", title="Provenance graph points to spearphish origin", confidence=0.71, severity=Severity.MEDIUM, data={"origin_file": ctx.get("entry_point", "invoice.docm")})]

# --- Adjudicator with Consensus ---

class Adjudicator:
    def __init__(self, threshold: float = 0.75, quorum: int = 3):
        self.threshold = threshold
        self.quorum = quorum

    async def adjudicate(self, blackboard: Blackboard) -> Finding:
        evidences = await blackboard.get_all()
        evidences = [e for e in evidences if e.type != "error"]
        if not evidences:
            return Finding(False, "No evidence", 0.0, [], [])

        # Weighted confidence score
        weighted_sum = 0.0
        weight_total = 0.0
        agent_votes = defaultdict(float)
        for ev in evidences:
            # find agent weight
            w = next((a.weight for a in ALL_AGENTS if a.name == ev.agent), 1.0)
            weighted_sum += ev.confidence * w * ev.severity.value
            weight_total += w * ev.severity.value
            agent_votes[ev.agent] = max(agent_votes[ev.agent], ev.confidence)

        overall_conf = weighted_sum / weight_total if weight_total else 0.0
        high_conf_agents = [a for a,c in agent_votes.items() if c >= 0.75]

        # Consensus logic: threshold + quorum + critical chain
        critical_ev = [e for e in evidences if e.severity == Severity.CRITICAL]
        has_chain = any(e.type == "timeline" for e in evidences) and len(critical_ev) >= 1

        consensus = overall_conf >= self.threshold and len(high_conf_agents) >= self.quorum and has_chain
        verdict = "CONFIRMED COMPROMISE - Provenance chain validated" if consensus else "SUSPICIOUS - Requires human review"
        notes = f"Weighted conf {overall_conf:.2f}, {len(high_conf_agents)} high-conf agents, {len(critical_ev)} critical evidences, chain={has_chain}"

        return Finding(
            consensus=consensus,
            verdict=verdict,
            confidence=overall_conf,
            contributing_agents=list(agent_votes.keys()),
            evidences=sorted(evidences, key=lambda x: x.confidence, reverse=True)[:12],
            adjudicator_notes=notes
        )

ALL_AGENTS = [
    MemoryForensicsAgent, DiskForensicsAgent, NetworkForensicsAgent,
    MalwareTriageAgent, TimelineReconstructorAgent, RegistryAnalyzerAgent,
    LogAnomalyAgent, CryptoDetectorAgent, ThreatIntelCorrelatorAgent,
    ProcessTreeAnalystAgent, PersistenceHunterAgent, AttributionAgent
]

# --- Swarm Orchestrator ---

class SwarmOrchestrator:
    def __init__(self):
        self.blackboard = Blackboard()
        self.adjudicator = Adjudicator(threshold=0.78, quorum=4)
        self.agents = [AgentCls(self.blackboard) for AgentCls in ALL_AGENTS]

    async def run_case(self, context: Dict[str, Any]) -> Finding:
        start = time.time()
        print(f"\n=== Starting swarm case {self.blackboard.case_id} with {len(self.agents)} agents ===")
        # Parallel execution - core swarm concept
        await asyncio.gather(*[agent.run(context) for agent in self.agents])
        finding = await self.adjudicator.adjudicate(self.blackboard)
        elapsed = time.time() - start
        print(f"\n=== Adjudicator: {finding.verdict} ({finding.confidence:.2f}) in {elapsed:.2f}s ===")
        print(f"Notes: {finding.adjudicator_notes}")
        return finding

    def attach_dashboard_stream(self, ws_send_callback):
        # dashboard integration: stream evidence live
        self.blackboard.subscribe(ws_send_callback)

# --- Dashboard API (FastAPI) ---

"""
Uncomment for dashboard deployment:

from fastapi import FastAPI
app = FastAPI()

orchestrator = SwarmOrchestrator()

@app.post("/swarm/run")
async def run_swarm(entry_point: str = "suspicious.docm", host_image: str = "case-001"):
    context = {"entry_point": entry_point, "host_image": host_image}
    finding = await orchestrator.run_case(context)
    return finding

@app.get("/swarm/blackboard")
async def get_blackboard():
    return await orchestrator.blackboard.get_all()
"""

# --- CLI Runner ---

async def main():
    orchestrator = SwarmOrchestrator()
    
    # Dashboard streaming example
    async def dashboard_sink(ev: Evidence):
        # replace with websocket push to your React dashboard
        pass
    
    orchestrator.attach_dashboard_stream(dashboard_sink)
    
    context = {
        "entry_point": "invoice_2025.docm",
        "memory_dump": "host01.mem",
        "disk_image": "host01.E01",
        "pcap": "host01.pcap",
        "case_id": "DASH-2409"
    }
    
    finding = await orchestrator.run_case(context)
    
    print("\nTop Evidence:")
    for ev in finding.evidences:
        print(f" - [{ev.severity.name}] {ev.agent}: {ev.title} | {ev.darpa_technique} -> {ev.mitre_id} ({ev.confidence:.2f})")

if __name__ == "__main__":
    asyncio.run(main())
