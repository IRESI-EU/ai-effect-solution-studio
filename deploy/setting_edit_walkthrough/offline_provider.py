"""Explicit scripted response replay, NOT an interpreter or language model.

Only this opt-in host walkthrough imports it; production startup never does.
Advertised catalogue contracts/current bases resolve the fixture references.
"""
import json
from pathlib import Path
from app.schemas.solution_assistant import SavedSolutionResponse

REQUESTS=[
    'Prepare the offline starting design for four layouts with Drawing A.',
    'Please cap the proposed layouts at two instead, leaving the other settings and connection alone.',
    'Keep the saved maximum at two. Does anything need to change?',
]

class OfflineProvider:
    name='OFFLINE setting action replay — NO MODEL';mode='test'
    def __init__(self,directory):self.directory=Path(directory)
    async def respond(self,c):
        path=self.directory/'responses.private.jsonl'
        n=len(path.read_text(encoding='utf-8').splitlines()) if path.exists() else 0
        if n>=len(REQUESTS) or c['request']!=REQUESTS[n]:
            raise ValueError('Only the three documented offline replay messages are supplied; no model was called')
        if n==0:
            if c['saved_design']['steps'] or c['pending_candidate']:raise ValueError('Start with a fresh empty solution')
            # Select only an actual compatible pair with the published fixture types.
            cards={x['service_id']:x for x in c['catalogue']['services']}
            choices=[]
            for pair in c['catalogue']['compatible_connections']:
                source=cards[pair['source_service_id']];sink=cards[pair['target_service_id']]
                definition=(source['contract'] or {}).get('definition',{}).get('execution_parameters',{})
                props=definition.get('properties',{})
                integer=[name for name,spec in props.items() if spec['type']=='integer' and spec.get('minimum',4)<=2 and spec.get('maximum',0)>=4]
                if len(integer)==1:choices.append((source['name'],sink['name'],pair,integer[0],props))
            if not choices:raise ValueError('No reviewed compatible fixture with supported integer values 2 and 4')
            _,_,pair,name,props=sorted(choices,key=lambda x:(x[0],x[1]))[0]
            parameters={name:4}
            flags=sorted(k for k,v in props.items() if v['type']=='boolean')
            if flags:parameters[flags[0]]=False  # Deliberate unrelated fixture override.
            edits=[dict(kind='add_service',value=json.dumps(dict(service_id=pair['source_service_id'],local_ref='source',parameters=parameters))),
                   dict(kind='add_service',value=json.dumps(dict(service_id=pair['target_service_id'],local_ref='drawing'))),
                   dict(kind='connect',value=json.dumps(dict(source='source',target='drawing',source_slot=pair['source_slot'],target_slot=pair['target_slot'])))]
            v=dict(outcome='proposal',message='OFFLINE SETUP REPLAY: review the source-derived fixture design with maximum four; no model interpretation or Run occurred.',clarification=None,solution_edits=edits,edit_base=c['edit_bases']['saved'],assumptions=['OFFLINE software fixture only; no partner scientific approval.'])
        else:
            base='pending' if c['pending_candidate'] else 'saved';projection=c['pending_candidate'] if base=='pending' else c['saved_design']
            candidates=[]
            for step in projection['steps']:
                props=(step['contract'] or {}).get('definition',{}).get('execution_parameters',{}).get('properties',{})
                for name,spec in props.items():
                    if spec['type']=='integer' and spec.get('minimum',4)<=2 and spec.get('maximum',0)>=4:candidates.append((step,name))
            if len(candidates)!=1:raise ValueError('The offline fixture requires exactly one eligible target; do not guess')
            step,name=candidates[0]
            v=dict(outcome='setting_edit',message=None,clarification=None,solution_edits=[],assumptions=[],edit_base=c['edit_bases'][base],parameter_action=dict(operation='set_parameters',target_ref=step['target_ref'],requested_values=[dict(name=name,value=2)]))
        response=SavedSolutionResponse.model_validate(v)
        with path.open('a',encoding='utf-8') as stream:stream.write(json.dumps(dict(offline=True,request=c['request'],response=response.model_dump(mode='json')),ensure_ascii=False)+'\n')
        return response
