"""Stage the existing qualified profile; never connect a provider or execute.

Uses the preserved AIE-37 database, account, catalogue, volumes and API port.
The owner gets one native Windows web entry point, independent of this command.
"""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import time

repo = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--original-checkout',type=Path,required=True)
parser.add_argument('--api-only',action='store_true')
args = parser.parse_args()
original = args.original_checkout.resolve(strict=True)
profile = original/'local-backups/aie37-profile-20261028'
allowance = original/'local-backups/dutch-seed-runtime/acceptance'
out = original/'local-backups/demo-acceptance-20261031'
out.mkdir(exist_ok=True)
authorization = out/'authorization'
authorization.mkdir(exist_ok=True)
assert (profile/'api.env').is_file() and (profile/'postgres.env').is_file()
assert (allowance/'luna-dutch-manual-20261018-04.sqlite3').is_file()
assert (allowance/'instance-settings-provider-task-20261027.json').is_file()
assert not (authorization/'one-execution.json').exists(), 'Staging must not pick up a live execution grant'
assert (repo/'apps/web/.next/BUILD_ID').is_file(), 'Build the verified frontend first'
if not args.api_only:
    with socket.socket() as connection:
        assert connection.connect_ex(('127.0.0.1',23121)) != 0, 'Inspect an existing web listener before replacing it'
status = subprocess.check_output(['docker','inspect','ai-effect-aie37-postgres-1','--format','{{.State.Status}}'],text=True).strip()
assert status=='running','Existing qualification database must be available; never recreate it'
environment=os.environ.copy()
environment.update(AIE37_PROFILE_DIR=str(profile),DEMO_ALLOWANCE_DIR=str(allowance),DEMO_AUTHORIZATION_DIR=str(authorization))
subprocess.run(['docker','image','inspect','ai-effect-aie37-api:qualification-v3','--format','{{.Id}}'],check=True,stdout=subprocess.DEVNULL)
with (out/'api-build.log').open('wb') as log:
    subprocess.run(['docker','build','--pull=false','--network=none','-f','deploy/aie37/Demo.Api.Dockerfile',
        '-t','ai-effect-aie37-api:goal-results-v1','.'],cwd=repo,env=environment,stdout=log,stderr=subprocess.STDOUT,check=True)
subprocess.run(['docker','compose','-p','ai-effect-aie37','-f','deploy/aie37/compose.yaml','-f','deploy/aie37/demo.compose.yaml',
    'up','-d','--no-deps','--no-build','api'],cwd=repo,env=environment,check=True)
environment.update(INTERNAL_API_URL='http://127.0.0.1:28185',
    NEXT_PUBLIC_ENVIRONMENT_LABEL='Local qualified Dutch demonstration — live acceptance locked',NEXT_TELEMETRY_DISABLED='1',OPENAI_API_KEY='')
if args.api_only:
    web_pid=json.loads((out/'staged-processes.json').read_text())['web_pid']
else:
    process=subprocess.Popen(['C:/Program Files/nodejs/node.exe','node_modules/next/dist/bin/next','start','--hostname','127.0.0.1','--port','23121'],
        cwd=repo/'apps/web',env=environment,stdin=subprocess.DEVNULL,stdout=(out/'web.stdout.log').open('ab'),stderr=(out/'web.stderr.log').open('ab'),
        creationflags=subprocess.DETACHED_PROCESS|subprocess.CREATE_NEW_PROCESS_GROUP|subprocess.CREATE_BREAKAWAY_FROM_JOB)
    time.sleep(2)
    web_pid=process.pid
record={'web_pid':web_pid,'web_port':23121,'api_port':28185,'build_id':(repo/'apps/web/.next/BUILD_ID').read_text().strip(),
    'source':str(repo),'starting_url':'http://localhost:23121/design-ai','provider_connected':False,'execution_grant':None,
    'shared_allowance_mode':'read-only existing 12/12 ledger','runtime_services_started':False}
(out/'staged-processes.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps(record,indent=2))
