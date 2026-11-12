"""Prepare the one isolated Portuguese profile. Does not start services or run jobs.
Private output must stay outside Git. Existing profiles/volumes are never mounted.
"""
import argparse, csv, hashlib, io, json, math, secrets, subprocess, uuid
from datetime import datetime,timedelta
from pathlib import Path

API='sha256:974628a92ee14719396f4e19e0cca7a274c64e60cc09b7e37b3beabe9290da28'
WEB='sha256:913b314cc09a974b7dddcc1a85bc889bda599694970aed80c7b7b758e68d8eeb'
ML='sha256:557246d79612eaa2106266d60cc6b36970634afebb659e371658cce6a1f1f61f'
WP3='sha256:edcac597f327dc817ff0c9b9c930dbf9b4cb62235d42f2ef1940845ca1820a21'
PG='sha256:5d143123fdf80462d1778cd4f24b9f7ca13c87174bca19141fb194c5a1ebca59'
REDIS='sha256:8b81dd37ff027bec4e516d41acfbe9fe2460070dc6d4a4570a2ac5b9d59df065'

def prepare(directory, adapter):
    directory=directory.resolve()
    if directory.exists(): raise RuntimeError('Refuse to replace an existing profile')
    directory.mkdir()
    owner=str(uuid.uuid4())
    credentials={'owner_id':owner,'email':'pt-sandbox-designer@example.test','password':secrets.token_urlsafe(30)}
    dbpassword=secrets.token_hex(24); control=secrets.token_urlsafe(36); orchestrator=secrets.token_urlsafe(36)
    (directory/'credentials.json').write_text(json.dumps(credentials,indent=2))
    (directory/'control.token').write_text(control)
    rows=io.StringIO(newline='');w=csv.writer(rows);w.writerow(['datetime','synthetic_load','synthetic_solar'])
    for i in range(400):
        w.writerow([(datetime(2026,1,1)+timedelta(hours=i)).isoformat(),round(10+math.sin(i/8)+i/1000,6),round(3+math.cos(i/5),6)])
    data=rows.getvalue().encode()
    (directory/'dataset.csv').write_bytes(data)
    policy={'owner_id':owner,'model_ref':'pt-approved-test-model','dataset_ref':'pt-approved-synthetic-data',
        'dataset_sha256':hashlib.sha256(data).hexdigest(),'sequence_len':100}
    (directory/'policy.json').write_text(json.dumps(policy,indent=2))
    private={'type':'bind','source':str(directory).replace('\\','/'),'target':'/private','read_only':True}
    review={'type':'bind','source':str(Path(__file__).resolve().parent).replace('\\','/'),'target':'/review','read_only':True}
    def svc(image,memory='512m',cpu=1):
        return {'image':image,'pull_policy':'never','restart':'no','networks':['private'],'mem_limit':memory,'cpus':cpu,
            'logging':{'driver':'json-file','options':{'max-size':'5m','max-file':'2'}}}
    services={}
    services['postgres']=svc(PG)
    services['postgres'].update(environment={'POSTGRES_USER':'pt_sandbox','POSTGRES_PASSWORD':dbpassword,'POSTGRES_DB':'pt_parameter_sandbox'},
        volumes=['database:/var/lib/postgresql/data'],healthcheck={'test':['CMD-SHELL','pg_isready -U pt_sandbox -d pt_parameter_sandbox'],'interval':'3s','timeout':'3s','retries':20})
    services['redis']=svc(REDIS,'128m',.5)
    services['redis'].update(command=['redis-server','--appendonly','yes'],volumes=['redis:/data'])
    for role,cmd in [('orchestrator',['python','main.py']),('worker',['python','worker_daemon.py'])]:
        services[role]=svc(WP3,'384m',1)
        services[role].update(command=cmd,environment={'REDIS_URL':'redis://redis:6379','ORCHESTRATOR_API_KEY':orchestrator},tmpfs=['/app/src/logs:rw,size=32m'])
    services['ml']=svc(ML,'3g',2)
    services['ml'].update(environment={'ML_GRETEL_PORT':'600','ML_GRETEL_RELOAD':'False','OMP_NUM_THREADS':'2','MKL_NUM_THREADS':'2','OPENBLAS_NUM_THREADS':'2'},
        entrypoint=['python','-m','uvicorn','main:app','--host','0.0.0.0','--port','600','--no-access-log'],
        volumes=['models:/app/models'],read_only=True,tmpfs=['/tmp:rw,size=512m'])
    services['pt-adapter']=svc(adapter,'384m',1)
    services['pt-adapter'].update(environment={'PT_SANDBOX_POLICY':'/private/policy.json','PT_SANDBOX_TOKEN_FILE':'/private/control.token',
        'PT_SANDBOX_STORAGE':'/state','PT_SANDBOX_UPSTREAM':'http://ml:600','PT_SANDBOX_SELF_URL':'http://pt-adapter:8080'},
        volumes=[private,'adapter:/state'],read_only=True,tmpfs=['/tmp:rw,size=32m'])
    apienv={'DATABASE_URL':'postgresql+psycopg://pt_sandbox:'+dbpassword+'@postgres:5432/pt_parameter_sandbox',
        'ORCHESTRATOR_BASE_URL':'http://orchestrator:8000','ORCHESTRATOR_API_KEY':orchestrator,
        'ORCHESTRATOR_SERVICES_API_KEY':control,'SESSION_COOKIE_NAME':'ai_effect_pt_sandbox_20261112',
        'SECURE_COOKIES':'false','DESIGN_AI_ENABLED':'false','OPENAI_API_KEY':'','DESIGN_AI_DEMO_EXECUTION_GRANT_FILE':''}
    services['api']=svc(API,'640m',1)
    services['api'].update(environment=apienv,ports=['127.0.0.1:28188:8080'],read_only=True,tmpfs=['/tmp:rw,size=64m'])
    services['web']=svc(WEB,'768m',1)
    services['web'].update(environment={'INTERNAL_API_URL':'http://api:8080','HOSTNAME':'0.0.0.0','PORT':'3000'},
        ports=['127.0.0.1:23124:3000'],networks=['private','browser'],read_only=True,tmpfs=['/tmp:rw,size=64m','/app/apps/web/.next/cache:rw,size=64m'])
    services['bootstrap']=svc(API)
    services['bootstrap'].update(profiles=['operator'],environment=apienv,entrypoint=['python','/review/bootstrap.py'],volumes=[private,review])
    services['initialize']=svc(API)
    services['initialize'].update(profiles=['operator'],user='0:0',entrypoint=['python','-c',
        "from pathlib import Path; import os; p=Path('/state'); assert not list(p.iterdir()), 'Adapter volume must be fresh'; (p/'dataset.csv').write_bytes(Path('/private/dataset.csv').read_bytes()); os.chown(p,10001,10001); os.chown(p/'dataset.csv',10001,10001)"],
        volumes=[private,'adapter:/state'])
    config={'name':'ai-effect-pt-parameters','services':services,'networks':{'private':{'internal':True},'browser':{}},
        'volumes':{v:{} for v in ['database','redis','models','adapter']}}
    (directory/'compose.private.json').write_text(json.dumps(config,indent=2))
    (directory/'preflight.json').write_text(json.dumps({'dataset_sha256':policy['dataset_sha256'],'rows':400,'training_sequences':4,
        'fixed_sequence_len':100,'maximum_jobs':{'TrainModel':1,'GenerateData':2},'images':{k:v['image'] for k,v in services.items()},
        'web_port':23124,'api_port':28188,'provider_disconnected':True,'ledger_attached':False},indent=2))
    print('Prepared private isolated profile; no services started, no jobs submitted.')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',type=Path,required=True);p.add_argument('--adapter',required=True)
    a=p.parse_args();prepare(a.directory,a.adapter)
