"""Deterministic Builder input/output scaffolding, included in assistant review.

These edges select no data or algorithm settings and never reach WP3 as service
bindings. Only edges created by this helper are reconciled on later graph edits.
"""
from fastapi import HTTPException


def complete(nodes, edges):
    services=[n['id'] for n in nodes if n.get('data',{}).get('service')]
    if not services:return False
    before=([n['id'] for n in nodes],list(edges))
    boundaries={}
    for kind in ('input','output'):
        matches=[n for n in nodes if not n.get('data',{}).get('service') and (n.get('type')==kind or n.get('data',{}).get('node_kind')=='workflow_'+kind)]
        if len(matches)>1:raise HTTPException(422,'Review ambiguous workflow '+kind+' nodes in Builder')
        if matches:boundaries[kind]=matches[0]['id']
        else:
            identifier='assistant-workflow-'+kind
            if any(n['id']==identifier for n in nodes):raise HTTPException(422,'Workflow boundary identity is already in use')
            boundaries[kind]=identifier
            nodes.append({'id':identifier,'type':kind,'position':{'x':40 if kind=='input' else 760,'y':40},
                'data':{'node_kind':'workflow_'+kind,'label':'Workflow '+kind.title()}})
    edges[:]=[e for e in edges if (e.get('data') or {}).get('assistant_workflow_boundary') is not True]
    roots=[s for s in services if not any(e['target']==s and e['source'] in services for e in edges)]
    leaves=[s for s in services if not any(e['source']==s and e['target'] in services for e in edges)]
    for source,target in [(boundaries['input'],s) for s in roots]+[(s,boundaries['output']) for s in leaves]:
        if not any(e['source']==source and e['target']==target for e in edges):
            edges.append({'id':source+'-to-'+target,'source':source,'target':target,'data':{'assistant_workflow_boundary':True}})
    return before!=([n['id'] for n in nodes],edges)
