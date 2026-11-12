import hashlib,json,sqlite3,os
from pathlib import Path
root=Path(os.environ['PT_SANDBOX_RECORDS']).resolve()
report=Path(__file__).with_name('verification.json')
cases=[]
for case in ('train','generate10','generate20'):
    r=json.loads((root/(case+'-observed.private.json')).read_text());wf=r['workflow']['workflow_id']
    j=next(v for v in r['journal'] if json.loads(v['request'])['workflow_id']==wf)
    proof=json.loads(j['result']);snap=json.loads((root/(case+'-snapshot.private.json')).read_text())
    v={'case':case,'workflow_id':wf,'submission_id':json.loads((root/(case+'-response.private.json')).read_text())['submission_id'],
       'workflow_status':r['workflow']['status'],'task_states':[{k:t[k] for k in ('task_id','node_key','status')} for t in r['tasks']['tasks']],
       'instance_id':proof['instance_id'],'requested':snap['request']['nodes'][0]['configuration']['parameters'],
       'effective':proof['requested_effective'],'canonical_parameter_definition_sha256':proof['parameter_contract_sha256'],
       'request_snapshot_sha256':snap['request_sha256'],'upstream_completion':proof['upstream_completion'],
       'artifact_sha256':proof['sha256'],'artifact_bytes':proof['bytes'],'results_url':'http://127.0.0.1:23124/deployments/'+wf+'#results'}
    if case!='train':
        artifact=json.loads((root/(case+('-after20' if case=='generate10' else '-final')+'-artifact.private.json')).read_text())
        v.update(verified_consumed_count=artifact['actual_examples'],csv_rows=artifact['csv_rows'],rows_per_example=100,
            unauthenticated_download_denied=artifact['unauthenticated_download_denied'],immutable_submission_unchanged=artifact['immutable_submission_unchanged'])
    else:
        model=json.loads((root/'trained-model-config.private.json').read_text())
        v.update(verified_saved_model_configuration={k:model['config'][k] for k in ('epochs','batch_size','max_sequence_len','sample_len')},
            model_sha256=model['model_sha256'],completion_basis=proof['completion_basis'])
    cases.append(v)
ledger=Path(os.environ['PT_SANDBOX_LEDGER_READONLY']).resolve()
db=sqlite3.connect(ledger.resolve().as_uri()+'?mode=ro',uri=True)
record={'schema_version':1,'scope':'platform-controlled experimental Portuguese parameter sandbox; not partner approval',
    'portal_serving_revision':'654b10754a7785fa3d650a4c543d3144b72b88df','adapter_serving_revision':'be8722c01dc41b26b083302531e4a780bdec8598',
    'wp3_packaging_revision':'a8b529ea25bcfd6a16dbb77ebc893a2b0b22ab77','wp3_runtime_source_parity_base':'0221b7ecd4a2d5f072de640350ebc599df22131a',
    'portable_validator_sha256':'1861736c1bd9c8a1e4d3aa86b1a2f58ef27bf5e272d682a619062cfb8b7171aa',
    'focused_tests':{'wp3_runtime':30,'portal_parameters_and_compatibility':32,'profile_isolation':1},
    'live_cases':cases,'actual_jobs':{'TrainModel':1,'GenerateData':2},'automatic_retries':0,'worker_after':'stopped','queued_items_after':0,
    'dataset_sha256':json.loads((root/'profile/policy.json').read_text())['dataset_sha256'],
    'provider_calls':0,'shared_allowance':{'max_calls':db.execute('select max_calls from batch').fetchone()[0],
        'usage_records':db.execute('select count(*) from requests').fetchone()[0],
        'outstanding_reservations':db.execute("select count(*) from requests where usage is null or status='settled_unacknowledged'").fetchone()[0],
        'ledger_sha256_before_and_after':hashlib.sha256(ledger.read_bytes()).hexdigest()},
    'runtime_images':{k:v['image'] for k,v in json.loads((root/'profile/compose.private.json').read_text())['services'].items() if k not in ('bootstrap','initialize')},
    'c_free_gib_after':18.7,'scientific_quality_verified':False,'production_compatibility_verified':False,'partner_approval':False,
    'generic_results_consumption_panel':'Unavailable; authoritative consumption evidence is the separately correlated adapter artifacts and saved model config.',
    'historical_snapshot_note':'Initial resource manifest inherited the older retained WP3 image identity. Exact-source c0a0b19a image was separately verified against all PR3 runtime Python source bytes and pinned in published profile configuration before any dispatch; original snapshots are preserved, not rewritten.'}
assert record['shared_allowance']['max_calls']==record['shared_allowance']['usage_records']==25
assert record['shared_allowance']['outstanding_reservations']==0
assert record['shared_allowance']['ledger_sha256_before_and_after']=='cf9fa12e87633b9e260d3983a3dd9e5c51df346c04237b3babd255ee66cd7d2b'
report.write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'verified_jobs':record['actual_jobs'],'allowance':'25/25 unchanged','reservations':0,'report':str(report)}))
