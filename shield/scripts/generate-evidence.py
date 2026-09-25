#!/usr/bin/env python3
import hashlib,json,os,subprocess
from datetime import datetime,timezone
from pathlib import Path

artifact=Path(os.environ.get("SHIELD_ARTIFACT_DIR","artifacts/shield-g01"))
artifact.mkdir(parents=True,exist_ok=True)
def sha256(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda:f.read(65536),b""): h.update(chunk)
    return h.hexdigest()

files=sorted(p for p in artifact.rglob("*") if p.is_file())
commit=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
data={
  "schema_version":"1.0",
  "product":"ClearGlass Shield",
  "gate":"G01",
  "environment":"isolated-disposable-test",
  "repository":os.environ.get("GITHUB_REPOSITORY","ClearGlassInc/ClearGlassInc-ClearGlassIncorporated-Desmond"),
  "branch":os.environ.get("GITHUB_REF_NAME",""),
  "before_commit":os.environ.get("G01_BASELINE_SHA","b2349d00cd543132522ac36ae70938268cf2a935"),
  "commit":commit,
  "created_at":datetime.now(timezone.utc).isoformat(),
  "test_run_id":os.environ.get("SHIELD_RUN_ID",""),
  "components":["shield/client","shield/gateway","shield/scripts","shield/tests"],
  "controls":["isolated topology","standard WireGuard","test-only DNS","test-scope network lock","secret scan","deterministic teardown"],
  "tests":[],
  "artifacts":[str(p) for p in files],
  "artifact_hashes":[{"path":str(p),"sha256":sha256(p)} for p in files],
  "limitations":["Linux/container test scope only","No production validation","No independent audit","No customer traffic","No billing testing"],
  "teardown":{"attempted":True,"completed":not Path("/tmp/clearglass-shield-test").exists(),"evidence":"verify-clean.sh"},
  "stripe_interactions":0,
  "production_interactions":0,
  "customer_traffic":False,
  "production_status":"NOT_PRODUCTION",
  "commercial_status":"BILLING_LOCKED",
  "gate_decision":"FAIL"
}
(artifact/"g01-runtime-evidence.json").write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")
