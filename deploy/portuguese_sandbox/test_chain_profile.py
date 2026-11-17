import importlib.util
import json
from pathlib import Path

def test_chain_update_preserves_storage_old_worker_and_provider_guards(tmp_path):
    # Import by file to avoid the standard-library profile module.
    def module(name,file):
        spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(file));value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
    old=module("pt_initial_profile","profile.py");update=module("pt_chain_update","apply_chain_profile.py")
    directory=tmp_path/"profile";records=tmp_path/"records";records.mkdir()
    old.prepare(directory,"sha256:standalone-adapter")
    before=json.loads((directory/"compose.private.json").read_text())
    credentials=(directory/"credentials.json").read_bytes()
    update.prepare(directory,records)
    after=json.loads((directory/"compose.private.json").read_text())
    assert before["volumes"]==after["volumes"] and before["networks"]==after["networks"]
    assert before["services"]["worker"]==after["services"]["worker"]
    assert before["services"]["postgres"]==after["services"]["postgres"]
    assert before["services"]["redis"]==after["services"]["redis"]
    assert before["services"]["ml"]==after["services"]["ml"]
    assert credentials==(directory/"credentials.json").read_bytes()
    assert after["services"]["api"]["environment"]["OPENAI_API_KEY"]==""
    assert after["services"]["api"]["environment"]["DESIGN_AI_ENABLED"]=="false"
    assert all(v["read_only"] for v in after["services"]["api"]["volumes"])
    assert after["services"]["chain-worker"]["profiles"]==["operator"]
    assert "no daemon startup" in after["services"]["chain-worker"]["command"][-1]
    assert all(v["read_only"] for v in after["services"]["model-observer"]["volumes"])
