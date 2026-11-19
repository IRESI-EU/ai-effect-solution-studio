"""EXPLICIT OFFLINE responses for pending revision UI; no SDK or runtime dispatch."""
import json
from pathlib import Path
from app.schemas.solution_assistant import SavedSolutionResponse


class OfflineProvider:
    name='OFFLINE PENDING REVISION FIXTURE — NO MODEL'
    mode='test'
    def __init__(self,directory):self.directory=Path(directory)

    async def respond(self,context):
        request=context['request'].casefold(); pending=context['pending_candidate']
        cards=context['catalogue']['services']
        generator=next(c for c in cards if c['operation_name']=='GenerateTopology')
        drawings=sorted([c for c in cards if c['operation_name']=='RenderTopologies'],key=lambda c:c['name'])
        def edit(kind,value,node=None):return dict(kind=kind,node_id=node,value=json.dumps(value) if isinstance(value,dict) else value)
        edits=[];assumptions=[];base='pending' if pending else 'saved'
        if 'confirm' in request or 'explain' in request:
            if not pending:raise ValueError('An actual pending review is required')
            message='The complete pending design below is retained exactly. No changes have been applied or run.'
        elif pending and 'three' in request:
            step=next(s for s in pending['steps'] if s['service_id']==generator['service_id'])
            edits=[edit('set_node_parameters',{'how_many':3},step['target_ref'])]
            message='Review changing the maximum to three. All other proposed instances, connections and separate saved input are retained.'
        elif pending and 'replace' in request:
            step=next(s for s in pending['steps'] if s['operation_name']=='RenderTopologies')
            replacement=next(c for c in drawings if c['service_id']!=step['service_id'])
            edits=[edit('replace_service',{'service_id':replacement['service_id']},step['target_ref'])]
            message='Review the alternative drawing service. The proposed drawing instance identity and compatible connection are retained. This operation has no editable settings.'
        elif not pending and not context['saved_design']['steps']:
            pair=next(p for p in context['catalogue']['compatible_connections'] if p['source_service_id']==generator['service_id'] and p['target_service_id']==drawings[0]['service_id'])
            edits=[edit('add_service',{'service_id':generator['service_id'],'local_ref':'source','parameters':{'how_many':2}}),
                edit('add_service',{'service_id':drawings[0]['service_id'],'local_ref':'view'}),
                edit('connect',{'source':'source','target':'view','source_slot':pair['source_slot'],'target_slot':pair['target_slot']})]
            assumptions=['OFFLINE fixture chooses drawing A for review, not a published drawing-view default or scientific approval.']
            message='Review a connected generator and drawing for up to two layouts. Published boolean defaults are shown separately. Data selection stays in Builder.'
        else:raise ValueError('Only the documented offline revision walkthrough is supported')
        response=SavedSolutionResponse(outcome='proposal' if edits else 'answer',message='EXPLICIT OFFLINE RESPONSE — '+message,
            clarification=None,solution_edits=edits,assumptions=assumptions,edit_base=context['edit_bases'][base] if edits else None)
        with (self.directory/'responses.private.jsonl').open('a',encoding='utf-8') as stream:
            stream.write(json.dumps({'offline':True,'context':context,'response':response.model_dump()},ensure_ascii=False)+'\n')
        return response
