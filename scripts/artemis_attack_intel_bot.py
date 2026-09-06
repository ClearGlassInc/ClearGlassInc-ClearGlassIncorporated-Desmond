# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
#!/usr/bin/env python3
"""ClearGlassInc Artemis ATT&CK Intelligence Bot.

Python-first engine that generates a structured threat-intel and detection-engineering
report aligned to MITRE ATT&CK Enterprise (v18.1 at time of writing).
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ATTACK_VERSION = "Enterprise v18.1"

TACTIC_SEQUENCE: list[tuple[str, str]] = [
    ("TA0043", "Reconnaissance"),
    ("TA0042", "Resource Development"),
    ("TA0001", "Initial Access"),
    ("TA0002", "Execution"),
    ("TA0003", "Persistence"),
    ("TA0004", "Privilege Escalation"),
    ("TA0005", "Defense Evasion"),
    ("TA0006", "Credential Access"),
    ("TA0007", "Discovery"),
    ("TA0008", "Lateral Movement"),
    ("TA0009", "Collection"),
    ("TA0011", "Command and Control"),
    ("TA0010", "Exfiltration"),
    ("TA0040", "Impact"),
]

# Heuristic IOC to ATT&CK mappings used for pre-enrichment.
IOC_HEURISTICS: dict[str, dict[str, Any]] = {
    "ipv4": {
        "techniques": ["T1071.001", "T1090", "T1105"],
        "pattern": "C2, proxying, or payload transfer over application protocols",
        "confidence": "med",
    },
    "domain": {
        "techniques": ["T1568.001", "T1583.001", "T1071.004"],
        "pattern": "dynamic C2 domains, attacker infrastructure acquisition, DNS C2",
        "confidence": "med",
    },
    "url": {
        "techniques": ["T1566.002", "T1189", "T1105"],
        "pattern": "phishing link delivery, drive-by compromise, download staging",
        "confidence": "med",
    },
    "sha256": {
        "techniques": ["T1204.002", "T1059", "T1027"],
        "pattern": "malware execution, script-driven payloads, obfuscated binaries",
        "confidence": "high",
    },
}

TECHNIQUE_LIBRARY: dict[str, list[dict[str, Any]]] = {
    "TA0001": [
        {
            "id": "T1566",
            "name": "Phishing",
            "subtechniques": ["T1566.001 Spearphishing Attachment", "T1566.002 Spearphishing Link"],
            "example": "FIN7 and APT29 campaigns repeatedly leverage spearphishing for footholds.",
            "detection": "Detect inbound messages with external links + subsequent browser/network egress to newly-seen domains.",
            "mitigation": "M1017 User Training, M1049 Antivirus/Antimalware, M1021 Restrict Web-Based Content.",
            "data": "Email gateway, secure web proxy, DNS, EDR telemetry.",
        },
        {
            "id": "T1190",
            "name": "Exploit Public-Facing Application",
            "subtechniques": [],
            "example": "Multiple ransomware affiliates exploit edge appliances and VPN gateways.",
            "detection": "Correlate WAF exploit signatures with suspicious process spawn from web services.",
            "mitigation": "M1051 Update Software, M1030 Network Segmentation.",
            "data": "WAF, reverse proxy logs, process telemetry, IDS/IPS.",
        },
    ],
    "TA0002": [
        {
            "id": "T1059",
            "name": "Command and Scripting Interpreter",
            "subtechniques": ["T1059.001 PowerShell", "T1059.003 Windows Command Shell", "T1059.006 Python"],
            "example": "APT41 and Wizard Spider have used shell/script interpreters for post-exploitation.",
            "detection": "Flag encoded commands, suspicious parent-child lineage, and script engines launched by office/browser processes.",
            "mitigation": "M1026 Privileged Account Management, M1038 Execution Prevention.",
            "data": "Sysmon EID 1, EDR process trees, script block logs.",
        }
    ],
    "TA0003": [
        {
            "id": "T1547",
            "name": "Boot or Logon Autostart Execution",
            "subtechniques": ["T1547.001 Registry Run Keys/Startup Folder"],
            "example": "APT28 malware families maintain access through Run key modifications.",
            "detection": "Monitor startup registry persistence with unsigned binaries in user-writable paths.",
            "mitigation": "M1047 Audit, M1042 Disable or Remove Feature/Program.",
            "data": "Sysmon EID 13, registry audit logs, EDR.",
        }
    ],
    "TA0006": [
        {
            "id": "T1003",
            "name": "OS Credential Dumping",
            "subtechniques": ["T1003.001 LSASS Memory", "T1003.002 Security Account Manager"],
            "example": "Sandworm and many ransomware operators dump LSASS for credential theft.",
            "detection": "Alert on LSASS memory access by non-system binaries and suspicious handle requests.",
            "mitigation": "M1040 Behavior Prevention on Endpoint, M1025 Privileged Process Integrity.",
            "data": "EDR memory access events, Sysmon EID 10, ETW.",
        }
    ],
    "TA0011": [
        {
            "id": "T1071",
            "name": "Application Layer Protocol",
            "subtechniques": ["T1071.001 Web Protocols", "T1071.004 DNS"],
            "example": "APT29 and several crimeware crews use HTTPS/DNS for resilient C2.",
            "detection": "Detect periodic low-volume beacons with entropy anomalies and domain age risk signals.",
            "mitigation": "M1031 Network Intrusion Prevention, M1037 Filter Network Traffic.",
            "data": "Proxy logs, DNS logs, NetFlow, TLS metadata.",
        }
    ],
    "TA0010": [
        {
            "id": "T1041",
            "name": "Exfiltration Over C2 Channel",
            "subtechniques": [],
            "example": "State-sponsored operators often blend exfiltration into existing C2 streams.",
            "detection": "Identify unusual outbound byte spikes from non-standard service accounts/endpoints.",
            "mitigation": "M1037 Filter Network Traffic, M1057 Data Loss Prevention.",
            "data": "NetFlow, DLP alerts, CASB, firewall telemetry.",
        }
    ],
    "TA0040": [
        {
            "id": "T1486",
            "name": "Data Encrypted for Impact",
            "subtechniques": [],
            "example": "Ransomware actors such as LockBit affiliates deploy mass encryption.",
            "detection": "Detect rapid file extension churn and high-volume write/delete patterns.",
            "mitigation": "M1053 Data Backup, M1040 Behavior Prevention on Endpoint.",
            "data": "EDR file telemetry, backup logs, file integrity monitoring.",
        }
    ],
}


@dataclass
class Scenario:
    organization: str = "ClearGlassInc Artemis"
    target_environment: str = "enterprise cloud + on-prem hybrid"
    industry: str = "finance"
    known_iocs: list[str] = field(default_factory=list)
    threat_actor: str = "unknown"
    objective: str = "detect"


class ArtemisAttackBot:
    def __init__(self, scenario: Scenario):
        self.scenario = scenario

    @staticmethod
    def _ioc_type(ioc: str) -> str:
        if re.fullmatch(r"(?:\d{1,3}\.){3}\d{1,3}", ioc):
            return "ipv4"
        if re.fullmatch(r"[a-fA-F0-9]{64}", ioc):
            return "sha256"
        if ioc.startswith(("http://", "https://")):
            return "url"
        if re.search(r"[a-zA-Z0-9-]+\.[a-zA-Z]{2,}", ioc):
            return "domain"
        return "unknown"

    def build_ioc_enrichment(self) -> list[dict[str, Any]]:
        mappings: list[dict[str, Any]] = []
        for ioc in self.scenario.known_iocs:
            ioc_kind = self._ioc_type(ioc)
            heuristic = IOC_HEURISTICS.get(ioc_kind)
            if heuristic is None:
                mappings.append(
                    {
                        "ioc": ioc,
                        "type": ioc_kind,
                        "techniques": ["T1592", "T1595"],
                        "confidence": "low",
                        "notes": "Unclassified IOC format; manual analyst triage required.",
                    }
                )
                continue
            mappings.append(
                {
                    "ioc": ioc,
                    "type": ioc_kind,
                    "techniques": heuristic["techniques"],
                    "confidence": heuristic["confidence"],
                    "notes": heuristic["pattern"],
                }
            )
        return mappings

    def build_navigator_layer(self) -> dict[str, Any]:
        techniques = []
        score_by_tactic = {
            "TA0001": 4,
            "TA0002": 3,
            "TA0003": 3,
            "TA0006": 2,
            "TA0011": 3,
            "TA0010": 2,
            "TA0040": 2,
        }
        for tactic, entries in TECHNIQUE_LIBRARY.items():
            for entry in entries:
                techniques.append(
                    {
                        "techniqueID": entry["id"],
                        "score": score_by_tactic.get(tactic, 1),
                        "comment": f"{entry['name']} detection and response coverage for {tactic}",
                        "tactic": tactic,
                    }
                )
        return {
            "name": f"{self.scenario.organization} ATT&CK Coverage",
            "domain": "enterprise-attack",
            "version": "4.5",
            "description": f"Generated {datetime.now(timezone.utc).isoformat()} against ATT&CK {ATTACK_VERSION}",
            "techniques": techniques,
            "gradient": {"colors": ["#ff6666", "#ffe766", "#8ec843"], "minValue": 0, "maxValue": 5},
            "legendItems": [
                {"label": "0-1 Gap", "color": "#ff6666"},
                {"label": "2-3 Partial", "color": "#ffe766"},
                {"label": "4-5 Strong", "color": "#8ec843"},
            ],
        }

    def generate_report(self) -> dict[str, Any]:
        return {
            "meta": {
                "organization": self.scenario.organization,
                "attack_version": ATTACK_VERSION,
                "generated_utc": datetime.now(timezone.utc).isoformat(),
            },
            "scenario": asdict(self.scenario),
            "tactic_progression": [
                {
                    "tactic_id": tid,
                    "name": name,
                    "intent": f"Adversary objective during {name.lower()} phase.",
                    "likely_attack_paths": [
                        f"{self.scenario.target_environment}: identity abuse + endpoint compromise path",
                        f"{self.scenario.target_environment}: cloud control-plane and workload pivot path",
                    ],
                }
                for tid, name in TACTIC_SEQUENCE
            ],
            "techniques": TECHNIQUE_LIBRARY,
            "ioc_enrichment": self.build_ioc_enrichment(),
            "detection_engineering": {
                "high_signal_rules": [
                    "Impossible travel + privileged login + token issuance spike",
                    "Script interpreter spawned from user-facing apps with outbound beaconing",
                    "Data egress anomaly after privilege escalation sequence",
                ],
                "siem_soar_correlations": [
                    "Email click -> endpoint execution -> C2 over DNS within 30 minutes",
                    "New admin account -> suspicious lateral auth -> archive + egress",
                ],
                "tuning_guidance": [
                    "Baseline by asset criticality and service account behavior.",
                    "Use allowlists for known automation hosts and signed admin tools.",
                ],
                "coverage_gaps": [
                    "Container/runtime telemetry blind spots",
                    "East-west traffic visibility in hybrid segments",
                ],
            },
            "red_team_paths": [
                {
                    "name": "Phish-to-Exfil Chain",
                    "steps": [
                        "Spearphishing link delivers credential-harvest page",
                        "Stolen credentials used for VPN/cloud access",
                        "PowerShell payload establishes persistence",
                        "Credential dumping + lateral movement",
                        "Archive + exfiltration via HTTPS C2",
                    ],
                    "likely_tools": ["GoPhish", "Cobalt Strike", "Rubeus", "Impacket", "7zip"],
                }
            ],
            "blue_team_playbook": {
                "initial_access": {
                    "trigger": "Phishing click correlated with suspicious login",
                    "immediate_actions": ["Disable session tokens", "Force password reset", "Isolate endpoint"],
                    "containment": "Block IOC infrastructure and enforce conditional access",
                    "forensics": ["Email headers", "Browser history", "EDR process timeline"],
                },
                "post_exploitation": {
                    "trigger": "Credential dump or privilege escalation signal",
                    "immediate_actions": ["Suspend account", "Memory capture", "Block lateral protocols"],
                    "containment": "Segment affected subnet and rotate secrets",
                    "forensics": ["LSASS dump artifacts", "Security logs", "Kerberos tickets"],
                },
            },
            "strategic_gaps": {
                "weakest_areas": ["Credential access detections", "Exfiltration analytics"],
                "missing_telemetry": ["Comprehensive DNS logging", "Cloud workload runtime events"],
                "control_failures": ["MFA fatigue resilience", "Service account governance"],
                "recommendations": {
                    "quick_wins": ["Enable script block logging", "Deploy high-risk geo login rules"],
                    "mid_term": ["Graph-based UEBA for identity chains", "Unified case ontology"],
                    "long_term": ["Policy-as-code everywhere", "Adaptive model-router with eval gates"],
                },
            },
            "attack_navigator_layer": self.build_navigator_layer(),
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate ATT&CK intelligence report for ClearGlassInc Artemis")
    parser.add_argument("--target-environment", default="enterprise cloud + on-prem hybrid")
    parser.add_argument("--industry", default="finance")
    parser.add_argument("--threat-actor", default="unknown")
    parser.add_argument("--objective", default="detect")
    parser.add_argument("--ioc", action="append", default=[], help="Add IOC (can be repeated)")
    parser.add_argument("--output", default="artemis_attack_report.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    scenario = Scenario(
        target_environment=args.target_environment,
        industry=args.industry,
        known_iocs=args.ioc,
        threat_actor=args.threat_actor,
        objective=args.objective,
    )
    bot = ArtemisAttackBot(scenario)
    report = bot.generate_report()
    output_path = Path(args.output)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"[+] Wrote {output_path}")


if __name__ == "__main__":
    main()
