"""Six explicitly SCRIPTED responses for UI acceptance, not a language model.

Chooses only actual retrieved catalogue cards/candidates. No network, provider SDK,
runtime dispatch or saved-solution write is available to this double.
"""
import json
from pathlib import Path


class OfflineProvider:
    name='OFFLINE ASSISTANT TEST DOUBLE'
    mode='test'

    def __init__(self,directory):self.directory=Path(directory)

    async def respond(self,context):
        from app.schemas.design_ai import AssistantTurn,DiscoveryDecision
        catalogue=context['catalogue'];cards=catalogue['services'];steps=context['solution']['steps']
        request=context['request'].casefold()
        def card(operation):
            matches=[c for c in cards if c['operation_name']==operation]
            if not matches:raise ValueError('Scripted acceptance has no published matching catalogue card')
            return sorted(matches,key=lambda c:c['name'])
        generators=card('GenerateTopology');renderers=card('RenderTopologies')
        generator=generators[0];primary=renderers[0];alternative=renderers[-1]
        def edit(kind,value,node=None):return {'kind':kind,'node_id':node,'value':json.dumps(value) if isinstance(value,dict) else value}
        def connection(source,target,target_card):
            matches=[p for p in catalogue['compatible_connections'] if p['source_service_id']==generator['service_id'] and p['target_service_id']==target_card['service_id']]
            if len(matches)!=1:raise ValueError('No unique published compatible connection')
            return edit('connect',{'source':source,'target':target,'source_slot':matches[0]['source_slot'],'target_slot':matches[0]['target_slot']})
        edits=[];question=None;case=None
        if 'explain' in request:
            case='explanation'
            message='The proposed workflow enumerates district-heating candidates, then renders their drawings. A proposal is only a review until Apply and save. Builder separately validates compatibility, checks runtime readiness and requires Confirm deployment. This explanation changes nothing.'
        elif not steps and 'two options' not in request:
            case='fresh-goal-discovery-clarification'
            names=', '.join(c['name'] for c in [generator,primary,alternative])
            message='The current catalogue contains '+names+'. The generator enumerates candidate networks and the drawing service renders them. The fixture default is up to one layout; comparison needs your choice. Select the separate fixture input in Builder before Run.'
            question='How many candidate layouts would you like to compare?'
        elif not steps:
            case='connected-proposal'
            if not context.get('pending_clarification'):raise ValueError('The scripted short answer requires its real saved clarification')
            message='Review a connected generator and drawing view for up to two layouts. Published I/O definitions match. Defaults keep heat exchangers and bypasses enabled. Select the separate development fixture run configuration in Builder; nothing runs when you apply this proposal.'
            edits=[edit('rename','DEVELOPMENT SOFTWARE FIXTURE — conversational Danish design'),
                edit('add_service',{'service_id':generator['service_id'],'local_ref':'network-source','parameters':{'how_many':2}}),
                edit('add_service',{'service_id':primary['service_id'],'local_ref':'drawing-view'}),
                connection('network-source','drawing-view',primary)]
        elif 'workflow input and output' in request:
            case='workflow-boundary-repair'
            message='Review the standard workflow input/output scaffolding. Separate run data and the two-layout generator setting stay unchanged. Builder validates the completed path before Run.'
            edits=[edit('describe','Development software fixture comparing generated district-heating networks and drawings.')]
        elif 'limit to three' in request:
            case='follow-up-settings'
            target=next(s for s in steps if s['operation_name']=='GenerateTopology')
            message='Review changing only this generator’s how_many setting to three. Its other settings, selected input and connections stay unchanged. This is a maximum candidate count, not a guarantee.'
            edits=[edit('set_node_parameters',{'how_many':3},target['node_id'])]
        elif 'add a second' in request:
            case='compatible-add'
            target=next(s for s in steps if s['operation_name']=='GenerateTopology')
            if not any(c['source_node_id']==target['node_id'] and c['target_service_id']==primary['service_id'] for c in context['compatible_actions']['add_after']):raise ValueError('Add is not advertised compatible')
            message='Review a second drawing instance connected to the same generator’s whole output. Both views receive that run’s topology reference; this adds no merge or conversion.'
            edits=[edit('add_service',{'service_id':primary['service_id'],'local_ref':'second-view'}),
                edit('set_node_label','Second view','second-view'),connection(target['node_id'],'second-view',primary)]
        elif 'replace the second view' in request:
            case='compatible-replace'
            matches=[s for s in steps if s['label']=='Second view']
            if len(matches)!=1:raise ValueError('The requested instance is ambiguous')
            target=matches[0]
            if not any(c['node_id']==target['node_id'] and c['service_id']==alternative['service_id'] for c in context['compatible_actions']['replacements']):raise ValueError('Replacement is not advertised compatible')
            message='Review replacing only Second view with '+alternative['name']+'. Its logical instance and existing compatible input connection are retained. The alternative also has no editable settings.'
            edits=[edit('replace_service',{'service_id':alternative['service_id']},target['node_id'])]
        else:raise ValueError('This offline double only supports the documented acceptance script')
        turn=AssistantTurn(message='OFFLINE SCRIPTED RESPONSE — '+message,template_key=None,expected_revision=None,edits=[],solution_edits=edits,
            discovery=DiscoveryDecision(outcome='clarification_needed',question=question) if question else None)
        trace={'boundary':'EXPLICIT OFFLINE PROVIDER DOUBLE; no model inference or paid call','case':case,'context':context,'response':turn.model_dump(mode='json')}
        with (self.directory/'assistant-trace.private.jsonl').open('a',encoding='utf-8') as stream:stream.write(json.dumps(trace,ensure_ascii=False)+'\n')
        return turn
