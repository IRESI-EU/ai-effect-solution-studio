"""EXPLICIT OFFLINE UI FIXTURE. Never imported by the genuine provider path."""
import json
from app.schemas.solution_assistant import SavedSolutionResponse


class DisclosureFixture:
    name = 'OFFLINE ASSUMPTION DISCLOSURE FIXTURE — NO MODEL'
    mode = 'test'

    async def respond(self, context):
        if context['pending_proposal']:
            return SavedSolutionResponse(outcome='answer', message='OFFLINE RESPONSE: the reviewed proposal uses a maximum of two candidates and the published heat-exchanger/bypass defaults. Its proposed assumption and settings remain available for review. Nothing has been applied or run.',
                clarification=None, solution_edits=[], assumptions=[])
        cards = context['catalogue']['services']
        generator = next(c for c in cards if c['operation_name'] == 'GenerateTopology')
        drawing = next(c for c in cards if c['operation_name'] == 'RenderTopologies')
        pair = next(p for p in context['catalogue']['compatible_connections'] if p['source_service_id'] == generator['service_id'] and p['target_service_id'] == drawing['service_id'])
        edits = [dict(kind='add_service', value=json.dumps({'service_id': generator['service_id'], 'local_ref': 'fixture-source', 'parameters': {'how_many': 2}})),
                 dict(kind='add_service', value=json.dumps({'service_id': drawing['service_id'], 'local_ref': 'fixture-view'})),
                 dict(kind='connect', value=json.dumps({'source': 'fixture-source', 'target': 'fixture-view', 'source_slot': pair['source_slot'], 'target_slot': pair['target_slot']}))]
        return SavedSolutionResponse(outcome='proposal', message='OFFLINE RESPONSE: review a connected generator and drawing view. This supplied response tests disclosure UI only; it is not model evidence.', clarification=None,
            edit_base=context['edit_bases']['saved'], solution_edits=edits, assumptions=['For this OFFLINE UI fixture, propose up to two layouts for comparison. This is a reversible proposed choice, not your prior choice or partner scientific approval.'])
