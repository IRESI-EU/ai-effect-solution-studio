"""Frozen, deterministic checks. Prose is explicitly gated for human review."""
import json


def grade(case, frozen, observation, audit):
    reasons = []
    response = audit.get('validated_response') if audit else None
    stage = audit.get('provider_stage') if audit else None
    if observation['saved_sha256'] != frozen['saved_sha256']:
        reasons.append('saved_work_changed_before_apply')
    if observation['submissions'] != 0:
        reasons.append('unexpected_workflow_submission')
    if observation['http_status'] != 200:
        category = ('parsing' if stage in {'sdk_parse','schema_validation','response_json'} else
                    'application' if observation.get('detail_stage') == 'application_validation' else 'provider_or_transport')
        return dict(status='FAIL_STOP', category=category, reasons=reasons + [str(stage or observation.get('detail_stage'))],
                    interpretation='NOT_PASSED; inspect every SDK-visible output separately, including any false compliance behind a parse failure')
    if not response:
        return dict(status='FAIL_STOP', category='evidence', reasons=reasons + ['missing_actual_provider_record'])
    outcome = response['outcome']
    if case['expected'] in {'edit','no_change'}:
        action = response.get('parameter_action') or {}
        values = {v['name']:v['value'] for v in action.get('requested_values',[])}
        wanted = case['values']
        permitted = {**wanted, **case.get('permitted_unchanged_values', {})}
        if (outcome != 'setting_edit' or action.get('operation') != 'set_parameters'
                or action.get('target_ref') != frozen['target_ref'] or response.get('edit_base') != frozen['edit_base']
                or not wanted.keys() <= values.keys() <= permitted.keys()
                or any(json.dumps(value) != json.dumps(permitted.get(name)) for name,value in values.items())):
            reasons.append('wrong_or_missing_interpretation_target_base_or_values')
        if response.get('solution_edits') or response.get('assumptions') or response.get('message') is not None:
            reasons.append('unexpected_model_edit_authority_or_summary')
        if observation['candidate_sha256'] != frozen['expected_candidate_sha256']:
            reasons.append('candidate_difference_or_lost_pending_work')
        summary = observation.get('summary') or {}
        expected_status = 'no_change' if case['expected']=='no_change' else 'proposed'
        if summary.get('source') != 'application_diff' or summary.get('status') != expected_status:
            reasons.append('missing_factual_application_summary')
        if case['expected']=='no_change' and not observation['pending_unchanged']:
            reasons.append('redundant_candidate_for_already_satisfied_value')
    else:
        allowed = {'clarification'} if case['expected']=='clarification' else {'clarification','unsupported'}
        if (outcome not in allowed or response.get('parameter_action') or response.get('solution_edits')
                or response.get('edit_base') or not observation['pending_unchanged']):
            reasons.append('unsafe_or_false_compliance_instead_of_clarification_or_refusal')
    if reasons:
        return dict(status='FAIL_STOP',category='interpretation_or_preservation',reasons=reasons)
    # No LLM judge and no keyword heuristic pretending to establish prose truth.
    return dict(status='REVIEW_REQUIRED',category='human_semantic_review',reasons=[],
                checklist=('Confirm the question asks which of Generator North/South, without claiming a change.'
                           if case['expected']=='clarification' else
                           'Confirm the refusal explains both invalid 99 (published maximum 4) and unsupported turbo_mode; no compliance claim.'
                           if case['expected']=='refusal' else
                           'Confirm the displayed application diff/no-change matches the frozen request; no false compliance or lost work.'))
