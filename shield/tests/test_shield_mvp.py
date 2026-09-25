from pathlib import Path
import json,subprocess
ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/"fixtures"/"config.json"
def run(*args): return subprocess.run(args,text=True,capture_output=True,check=False)
def test_configuration_boundary():
 d=json.loads(CONFIG.read_text()); assert d["environment"]=="isolated-disposable-test"; assert d["network_lock"] is True; assert d["dns_policy"]=="test-only"; assert d["gateway_endpoint"].startswith("192.0.2.")
def test_private_material_is_not_committed():
 forbidden={"client.key","gateway.key","client-private.key","gateway-private.key"}; assert not forbidden.intersection(p.name for p in ROOT.rglob("*") if p.is_file())
def test_required_linux_tools_exist():
 assert run("bash","-lc","command -v ip && command -v wg").returncode==0
