"""Export only explicit non-secret diagnostic fields from completed browser Runs."""
import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import shutil


def publish(directory, output):
    fixture=(directory/'inputs/DEVELOPMENT-SOFTWARE-FIXTURE.csv').read_bytes()
    rows=list(csv.DictReader(io.StringIO(fixture.decode())))
    assert len(rows)==32 and list(rows[0])[0]=='datetime'
    assert all(math.isfinite(float(v)) for r in rows for k,v in r.items() if k!='datetime')
    models={m['model_sha256']:m for m in json.loads((directory/'saved-model-reinspection.private.json').read_text())['models']}
    runs=[]
    for label in ('first-run','second-run'):
        record=json.loads((directory/(label+'.private.json')).read_text())
        snapshot=record['snapshot']; tasks=[]
        for value in record['records']:
            receipt=value['receipt']; observation=receipt['runtime_observation']; config=receipt['configuration']
            model=observation['model']; verified=models[model['sha256']]
            assert verified['weights_sha256']==model['weights_sha256'] and verified['weight_elements']==model['weight_elements']
            if receipt['method']=='TrainModel':
                assert receipt['input_sha256']==hashlib.sha256(fixture).hexdigest()
                assert verified['saved_configuration']=={'epochs':observation['observed_parameters']['epochs'],
                    'batch_size':observation['observed_parameters']['batch_size'],'max_sequence_len':observation['observed_parameters']['sequence_len']}
            tasks.append({'task_id':receipt['task_id'],'physical_task_id':receipt['service_task_id'],
                'instance_id':config['instance_id'],'operation':receipt['method'],
                'configuration':config,'configuration_sha256':observation['binding']['configuration_sha256'],
                'parameter_contract_sha256':receipt['parameter_contract_sha256'],
                'requested_parameters':observation['requested_parameters'],
                'delivered_parameters':{k:receipt['delivered_query'][k] for k in config['parameters']},
                'observed_parameters':observation['observed_parameters'],'model':model,
                'reloaded_model_configuration_sha256':verified['saved_configuration_sha256'],
                'reloaded_model_configuration':verified['saved_configuration'],
                'implementation':observation['implementation'],'observation_basis':observation['basis'],
                'input_sha256':receipt['input_sha256'],'source_response_sha256':receipt['source_response_sha256'],
                'output_sha256':receipt['output_sha256'],'output_bytes':receipt['output_bytes'],
                'observation_sha256':receipt['runtime_observation_sha256'],
                'csv_observations':{k:receipt[k] for k in ('observed_sequence_count','csv_data_rows') if k in receipt},
                'independent_saved_model_reload_verified':True})
        train=next(t for t in tasks if t['operation']=='TrainModel');generate=next(t for t in tasks if t['operation']=='GenerateData')
        assert train['model']==generate['model'] and train['output_sha256']==generate['input_sha256']
        runs.append({'label':label,'workflow_id':record['workflow_id'],'solution_id':snapshot['submitted']['request']['solution_id'],
            'submission_id':snapshot['id'],'submitted_sha256':snapshot['submitted_sha256'],
            'selected_file':'DEVELOPMENT-SOFTWARE-FIXTURE.csv','tasks':tasks,
            'cross_owner_denials':record['other_designer_denied']})
    assert runs[0]['solution_id']==runs[1]['solution_id']
    assert runs[0]['tasks'][0]['model']['sha256']!=runs[1]['tasks'][0]['model']['sha256']
    identities=json.loads((directory/'runtime-identity.private.json').read_text(encoding='utf-8-sig'))
    containers=[{'id':v['id'],'name':v['name'],'image':v['image'],'status':v['status'],
        'mounts':[{'type':m['Type'],'destination':m['Destination'],'read_only':not m['RW']} for m in v['mounts']],
        'ports':v['ports']} for v in identities]
    document={'date':'2026-11-18','boundary':'Real local DGAN; normal browser Run as an independent designer account; synthetic software fixture, no scientific partner acceptance',
        'fixture':{'name':'DEVELOPMENT-SOFTWARE-FIXTURE.csv','sha256':hashlib.sha256(fixture).hexdigest(),
            'rows':32,'columns':['datetime','load','temperature'],'index':'datetime','finite_numeric_features':True},
        'runs':runs,'containers':containers,'first_run_unchanged_after_second':True,
        'invalid_epoch_zero_rejected_by_normal_save':True,'designer_execution_count':2,
        'paid_provider_calls':0,'actual_portuguese_provider_contracts_changed':0,
        'limitations':['Software fixture limits/defaults only','Browser automation as independent account; human acceptance not claimed',
            'SQLite development workspace, not PostgreSQL/staging/release acceptance','Assistant tests use an explicit double; genuine paid conversation pending']}
    output.mkdir(parents=True,exist_ok=True)
    (output/'windows-normal-designer-real-dgan-20261118.json').write_text(json.dumps(document,indent=2)+'\n')
    shutil.copyfile(directory/'browser-evidence/second-run-final.png',output/'windows-normal-designer-second-run-20261118.png')
    print(json.dumps({'sanitised_runs':len(runs),'fresh_models_verified':2,'selected_input_sha256':document['fixture']['sha256']}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--directory',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();publish(args.directory.resolve(),args.output.resolve())
