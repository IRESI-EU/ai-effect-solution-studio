"""Owned live catalogue retrieval and existing-validator compatible edit choices."""
import re
import json

from fastapi import HTTPException
from pydantic import ValidationError

from app.schemas.operation_contract import OperationContractDefinition
from app.schemas.design_ai import SolutionEdit
from app.services.capability_bindings import whole_output_compatible


def connections(cards):
    result = []
    definitions = {}
    for card in cards:
        try:
            definition = OperationContractDefinition.model_validate(card['contract']['definition']).model_dump(exclude_none=True)
            if definition.get('binding_transport') == 'whole-output-v1' and len(definition['inputs']) <= 1 and len(definition['outputs']) <= 1:
                definitions[card['service_id']] = definition
        except (TypeError, KeyError, ValidationError):
            continue
    for source in cards:
        for target in cards:
            left, right = definitions.get(source['service_id']), definitions.get(target['service_id'])
            if not left or not right or not left['outputs'] or not right['inputs']: continue
            output, slot = left['outputs'][0], right['inputs'][0]
            if whole_output_compatible(output, slot):
                result.append({'source_service_id':source['service_id'], 'target_service_id':target['service_id'],
                    'source_slot':output['name'], 'target_slot':slot['name'], 'schema_ref':output['schema_ref']})
    return result


def retrieve(db, user, solution, row, message):
    from app.models.service import Service
    from app.services.solution_design import can_reference_service
    from app.services.solution_assistant import active_contract, selectable
    # Search against the current goal AND short follow-up/history. Never read data selections.
    goal = (solution.design_metadata or {}).get('assistant_goal', '')
    goal = goal[:4000] if isinstance(goal, str) else ''
    history = [m['content'] for m in (row.state.get('messages', []) if row else []) if m['role'] == 'user'][-4:]
    words = set(re.findall(r'\w{3,}', ' '.join([goal, *history, message]).casefold()))
    services = [s for s in db.query(Service).filter(Service.status.in_(['approved','validated'])).all()
                if selectable(s) and can_reference_service(user, s)]
    def rank(service):
        text = ' '.join([service.name, service.description or '', service.category, service.operation_name]).casefold()
        return (-sum(word in text for word in words), service.name.casefold(), service.id)
    current_ids={n.get('data',{}).get('service',{}).get('id') for n in solution.nodes}
    services.sort(key=lambda s:(s.id not in current_ids,*rank(s)))
    cards = []
    for service in services[:40]:
        contract = active_contract(service, db)
        cards.append({'service_id':service.id,'name':service.name,'description':(service.description or '')[:1200],
            'operation_name':service.operation_name,'service_version':service.version,
            'contract':({'contract_id':contract.id,'contract_version':contract.contract_version,'definition':contract.definition} if contract else None)})
    return {'services':cards,'truncated':len(services)>40,'total_accessible':len(services),
            'search_method':'Current approved catalogue ranked by goal and conversation terms',
            'compatible_connections':connections(cards)}


def actions(solution, catalogue, db, user):
    from app.services.solution_assistant import candidate
    nodes = [n for n in solution.nodes if isinstance(n.get('data',{}).get('service'),dict)]
    additions = []
    for node in nodes:
        for pair in catalogue['compatible_connections']:
            if pair['source_service_id'] == node['data']['service']['id']:
                additions.append({'source_node_id':node['id'], **pair})
    replacements = []; truncated = False
    # Use the SAME candidate/registry validator, including every retained connection.
    for node in nodes:
        for card in catalogue['services']:
            if node['data']['service']['id'] == card['service_id']: continue
            if not card['contract'] or card['contract']['definition'].get('binding_transport') != 'whole-output-v1': continue
            if len(replacements) >= 40: truncated = True; break
            edit = SolutionEdit(kind='replace_service', node_id=node['id'], value=json.dumps({'service_id':card['service_id']}))
            try: candidate(solution,[edit],{},db,user)
            except HTTPException: continue
            replacements.append({'node_id':node['id'],'service_id':card['service_id'],
                'contract_id':card['contract']['contract_id'] if card['contract'] else None,
                'retained_connections_verified':True,'settings':'Published defaults only; requested overrides require validation'})
    return {'add_after':additions[:40], 'replacements':replacements,
            'truncated':truncated or len(additions)>40,
            'limits':'Whole-output compatibility only; no runtime readiness or scientific approval. Required settings and the final proposed graph are validated again.'}
