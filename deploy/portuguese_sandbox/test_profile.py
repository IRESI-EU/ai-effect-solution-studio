import importlib.util
import json
from pathlib import Path
import pytest

spec=importlib.util.spec_from_file_location('pt_profile',Path(__file__).with_name('profile.py'))
profile=importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile)

def test_profile_isolated_private_and_bounded(tmp_path):
    directory=tmp_path/'fresh'
    profile.prepare(directory,'sha256:experimental')
    cfg=json.loads((directory/'compose.private.json').read_text())
    assert cfg['name']=='ai-effect-pt-parameters'
    assert cfg['networks']['private']['internal'] is True
    assert set(cfg['volumes'])=={'database','redis','models','adapter'}
    ports=[p for v in cfg['services'].values() for p in v.get('ports',[])]
    assert ports==['127.0.0.1:28188:8080','127.0.0.1:23124:3000']
    assert all(v['pull_policy']=='never' and v['restart']=='no' for v in cfg['services'].values())
    env=cfg['services']['api']['environment']
    assert env['DATABASE_URL'].endswith('/pt_parameter_sandbox')
    assert env['DESIGN_AI_ENABLED']=='false' and env['OPENAI_API_KEY']==''
    assert env['DESIGN_AI_DEMO_EXECUTION_GRANT_FILE']==''
    assert 'DESIGN_AI_ACCEPTANCE_BUDGET_FILE' not in env
    assert cfg['services']['ml']['mem_limit']=='3g'
    assert json.loads((directory/'preflight.json').read_text())['maximum_jobs']=={'TrainModel':1,'GenerateData':2}
    with pytest.raises(RuntimeError,match='existing profile'):
        profile.prepare(directory,'sha256:experimental')
