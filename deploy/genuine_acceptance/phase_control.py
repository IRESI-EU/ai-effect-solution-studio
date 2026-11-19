"""Operator-only two-phase binding/gate and read-only per-case capture.

Never sends chat, applies a proposal, dispatches a workflow or replaces a ledger.
All paid messages and reviewed edits happen in the normal browser.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
from types import SimpleNamespace
import scope as scoped
from app.schemas.solution_assistant import SavedSolutionResponse
from app.services.design_ai_provider import SAVED_SOLUTION_SYSTEM
from app.services.provider_evidence import digest, response_format


def write(path, value):
    with path.open('x', encoding='utf-8') as stream: json.dump(value, stream, indent=2, ensure_ascii=False)


def load(path): return json.loads(path.read_text(encoding='utf-8'))


def snapshot(directory, solution_id):
    p, client, _ = scoped.load(directory)
    solution = scoped.get(client, p, '/solutions/' + solution_id)
    conversation = scoped.get(client, p, '/design-ai/solutions/' + solution_id)
    with sqlite3.connect((directory/'portal.sqlite').as_uri()+'?mode=ro', uri=True) as db:
        count = db.execute('SELECT COUNT(*) FROM execution_submissions').fetchone()[0]
        rows = db.execute('SELECT state FROM design_ai_drafts WHERE owner_id=?', (solution['created_by_user_id'],)).fetchall()
    states = [json.loads(r[0]) for r in rows]
    state = next((s for s in states if s.get('solution_id') == solution_id), None)
    return {'solution': solution, 'conversation': conversation, 'stored_state': state, 'submissions': count}


def prepare(root, directories, identifiers, authorization):
    phases = {}
    for phase, directory, identifier in zip(('I','J'), directories, identifiers):
        p, _, _ = scoped.load(directory)
        assert not p.get('offline_ui_fixture') and not (directory/'acceptance.private.sqlite').exists()
        snap = snapshot(directory, identifier)
        assert not snap['solution']['nodes'] and not snap['conversation']['messages']
        assert load(directory/'preflight.private.json')['passed']
        phases[phase] = {'directory': str(directory), 'solution_id': identifier,
            'binding': scoped.binding(SimpleNamespace(database_url='sqlite:///'+(directory/'portal.sqlite').as_posix()), snap['solution']['created_by_user_id'], identifier),
            'serving_commit': load(directory/'serving.private.json')['portal_base']}
    assert phases['I']['binding'] != phases['J']['binding']
    assert phases['I']['serving_commit'] == phases['J']['serving_commit']
    manifest = {'authorization_sha256': hashlib.sha256(authorization.read_bytes()).hexdigest(), 'aggregate_requests': 12, 'aggregate_limit_usd': .90,
        'per_phase_requests': 6, 'per_phase_limit_usd': .45, 'phases': phases,
        'prompt_sha256': hashlib.sha256(SAVED_SOLUTION_SYSTEM.encode()).hexdigest(),
        'wire_schema_sha256': digest(response_format(SavedSolutionResponse)['schema']),
        'scoring_sha256': hashlib.sha256((scoped.ROOT/'docs/SAVED_SOLUTION_CONVERSATION_EVALUATION_2026-11-19.md').read_bytes()).hexdigest()}
    write(root/'exercise.private.json', manifest)
    print(json.dumps({'both_bindings_recorded': True, 'aggregate_requests': 12, 'aggregate_limit_usd': .90, 'ledgers_created': 0}))


def activate(root, phase):
    m = load(root/'exercise.private.json'); record = m['phases'][phase]
    assert not (root/'hard-stop.private.json').exists()
    assert m['aggregate_requests'] == 12 and m['aggregate_limit_usd'] == .90
    assert m['prompt_sha256'] == hashlib.sha256(SAVED_SOLUTION_SYSTEM.encode()).hexdigest()
    assert m['wire_schema_sha256'] == digest(response_format(SavedSolutionResponse)['schema'])
    assert m['scoring_sha256'] == hashlib.sha256((scoped.ROOT/'docs/SAVED_SOLUTION_CONVERSATION_EVALUATION_2026-11-19.md').read_bytes()).hexdigest()
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=scoped.ROOT,text=True).strip() == record['serving_commit']
    if phase == 'J':
        prior = Path(m['phases']['I']['directory'])
        summary = load(prior/'closed-summary.private.json')
        assert summary['closed'] and summary['usage_complete']
        cases = [load(p) for p in prior.glob('case-I*.after.private.json')]
        assert cases and all(c['audit_hash_verified'] for c in cases)
        assert any(c['response']['outcome']=='proposal' and any(x['action']=='connect' for x in (c['after']['conversation']['pending'] or {}).get('changes', [])) for c in cases), 'Phase J requires an actual validated connected proposal'
    directory = Path(record['directory'])
    snap = snapshot(directory, record['solution_id'])
    current = scoped.binding(SimpleNamespace(database_url='sqlite:///'+(directory/'portal.sqlite').as_posix()), snap['solution']['created_by_user_id'], record['solution_id'])
    assert current == record['binding']
    scoped.activate(directory, record['solution_id'])


def capture(root, phase, case, after=False):
    m = load(root/'exercise.private.json'); record = m['phases'][phase]; directory = Path(record['directory'])
    assert case in [phase+str(n) for n in range(1,7)]
    snap = snapshot(directory, record['solution_id'])
    audits = [json.loads(line) for line in (directory/'provider-audit.private.jsonl').read_text(encoding='utf-8').splitlines()]
    if not after:
        write(directory/('case-'+case+'.before.private.json'), {'snapshot': snap, 'audit_count': len(audits)})
        print(json.dumps({'case': case, 'revision': snap['conversation']['conversation_revision'], 'nodes': len(snap['solution']['nodes']),
            'pending': snap['conversation']['pending'], 'clarification': snap['conversation']['clarification'], 'prior_messages': len(snap['conversation']['messages'])}))
        return
    before = load(directory/('case-'+case+'.before.private.json'))
    try:
        assert len(audits) == before['audit_count']+1
        audit = audits[-1]
        assert snap['solution'] == before['snapshot']['solution'] and snap['submissions'] == before['snapshot']['submissions']
        assert snap['conversation']['conversation_revision'] == before['snapshot']['conversation']['conversation_revision']+1
        reply = snap['conversation']['messages'][-1]
        pending = snap['stored_state'].get('pending')
        response = dict(outcome=reply['outcome'], message=reply['content'], clarification=reply.get('question'), assumptions=reply['assumptions'],
            solution_edits=pending['edits'] if reply['outcome']=='proposal' else [])
        response = SavedSolutionResponse.model_validate(response).model_dump(mode='json')
        assert digest(response) == audit['validated_response_sha256']
        assert audit['response_schema_sha256'] == m['wire_schema_sha256']
        assert audit['returned_model'] == scoped.MODEL and audit['returned_service_tier'] in (None,'default')
        assert audit['usage'] is not None
        value = {'case': case, 'before': before['snapshot'], 'after': snap, 'response': response,
            'response_sha256': digest(response), 'audit_hash_verified': True, 'audit': audit}
        write(directory/('case-'+case+'.after.private.json'), value)
        print(json.dumps({'case': case, 'response': response, 'audit_hash_verified': True, 'usage': audit['usage'], 'chat_mutated_or_executed': False}, ensure_ascii=False))
    except Exception:
        write(root/'hard-stop.private.json', {'phase': phase, 'case': case, 'reason': 'Case response, authority, accounting or preservation check failed'})
        scoped.close(directory)
        raise


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('action',choices=['prepare','activate','before','after'])
    parser.add_argument('--root',type=Path,required=True);parser.add_argument('--directories',type=Path,nargs=2);parser.add_argument('--solutions',nargs=2)
    parser.add_argument('--authorization',type=Path);parser.add_argument('--phase',choices=['I','J']);parser.add_argument('--case')
    args=parser.parse_args();root=args.root.resolve()
    if args.action=='prepare':prepare(root,[p.resolve() for p in args.directories],args.solutions,args.authorization)
    elif args.action=='activate':activate(root,args.phase)
    else:capture(root,args.phase,args.case,args.action=='after')
