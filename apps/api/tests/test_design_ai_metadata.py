"""Exporter HTTP calls are mocked here; historical real exports are checked separately."""
import importlib.util
import json
from pathlib import Path


def test_live_export_ignores_boundaries_and_never_calls_seed_on_empty_catalogue(tmp_path,monkeypatch):
    path=Path(__file__).resolve().parents[1]/'scripts/design_ai_metadata.py'
    spec=importlib.util.spec_from_file_location('metadata_export',path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    credentials=tmp_path/'credentials.txt'
    credentials.write_text('URL: https://platform.example.test\nEmail: local@example.test\nTemporary password: unit-test-only\n')
    workspace={'id':'source','name':'Real selector fixture','created_by_user_id':'private-owner','nodes':[
        {'id':'input','type':'input','data':{}},
        {'id':'service','data':{'service':{'id':'catalogue-id'}}},
        {'id':'output','type':'output','data':{}}],
        'edges':[{'id':'a','source':'input','target':'service'},{'id':'b','source':'service','target':'output'}],
        'deployments':[]}
    reads=[]
    class Response:
        status_code=200
        def __init__(self,value): self.value=value
        def json(self): return self.value
    class Session:
        def post(self,url,**kwargs):
            assert kwargs['allow_redirects'] is False
            return Response({})
        def get(self,url,**kwargs):
            reads.append(url)
            assert kwargs['allow_redirects'] is False
            data={'/api/solutions':[{'id':'source','name':'Real selector fixture'}],
                  '/api/solutions/source/workspace':workspace,
                  '/api/services/catalogue-id':{'id':'catalogue-id','operation_name':'Run','created_by_user_id':'private-owner'},
                  '/api/services/catalogue-id/operation-contracts':[]}
            return Response(data[url.removeprefix('https://platform.example.test')])
        def close(self): pass
    monkeypatch.setattr(module.requests,'Session',Session)
    output=tmp_path/'metadata.json'
    module.export_metadata('https://platform.example.test',credentials,output,{'dutch':'source'})
    result=json.loads(output.read_text())
    assert len(result['services'])==1 and result['services'][0]['id']=='catalogue-id'
    assert result['solutions']['dutch']['edges']==workspace['edges']
    assert 'https://platform.example.test/api/services' not in reads
    assert 'unit-test-only' not in output.read_text() and 'private-owner' not in output.read_text()
