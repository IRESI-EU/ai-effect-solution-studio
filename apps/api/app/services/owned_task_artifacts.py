"""Task-artifacts-v1: local SVG derivatives of an exact owned task output.

No service identifiers, arbitrary URLs or extra filesystem roots confer authority.
The existing immutable receipt table pins the parent for unconfigured operations;
configured producers must pass the existing actual-algorithm evidence validator.
"""
import hashlib
import json

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.models.execution_submission import InstanceEvidenceReceipt
from app.core.config import settings
from app.services.data_reference_service import resolve_artifact_file, preview_svg_bytes


def digest(raw):return hashlib.sha256(raw).hexdigest()


def inspect(submission,task,reference,requested,db):
    parent=resolve_artifact_file(reference['uri'])
    if parent is None or parent.suffix.lower()!='.json' or submission.workflow_id not in parent.parts:
        return None
    try:
        if parent.stat().st_size>5_000_000:return None
        raw=parent.read_bytes()
    except OSError:
        raise HTTPException(409,'Task artifact parent is unavailable') from None
    try:document=json.loads(raw)
    except (ValueError,UnicodeError):return None
    manifest=document.get('artifact_manifest') if isinstance(document,dict) else None
    if manifest is None:return None
    try:
        if submission.submitted.get('runtime_destination')!=settings.orchestrator_base_url:
            raise ValueError('Recorded runtime differs')
        if (manifest['schema_version']!='1.0' or manifest['kind']!='task-artifacts-v1'
            or manifest['workflow_id']!=submission.workflow_id or manifest['task_id']!=task['task_id']
            or task.get('status') not in {'complete','completed'} or not isinstance(manifest['files'],list) or len(manifest['files'])>100):
            raise ValueError('Artifact binding differs')
        nodes=submission.submitted['compiled']['solution_studio_metadata']['execution_instances']
        matches=[n for n in nodes if n['task_id']==task['task_id'] and n['node_key']==task['node_key']]
        if len(matches)!=1:raise ValueError('Submitted task differs')
        node=matches[0]
        wanted=[item for item in manifest['files'] if item.get('protocol')==requested.protocol and item.get('uri')==requested.uri]
        if len(wanted)!=1:return None
        item=wanted[0];path=resolve_artifact_file(item['uri'])
        if (item['protocol']!='file' or item['format']!='svg' or path is None or path.suffix.lower()!='.svg'
            or path.parent!=parent.parent or not path.name.startswith(task['task_id']+'_') or submission.workflow_id not in path.parts
            or type(item['bytes'])is not int or not 0<item['bytes']<=2_000_000 or path.stat().st_size!=item['bytes']):
            raise ValueError('Artifact leaves the owned task namespace')
        artifact=path.read_bytes()
        if len(artifact)!=item['bytes'] or digest(artifact)!=item['sha256']:raise ValueError('Artifact bytes differ')
        preview=preview_svg_bytes(artifact,requested.uri)
        if not preview['available']:raise ValueError('Artifact is not a safe SVG image')
        if node['configuration']:
            from app.services.native_instance_evidence import load
            proofs=load(submission,db)['instances']
            proof=next(p for p in proofs if p['task_id']==task['task_id'])
            if proof['state']!='available' or proof['output_sha256']!=digest(raw):raise ValueError('Producer evidence differs')
        else:
            # Keyed by the actual task, never a synthetic task or a workflow exception.
            canonical=json.dumps({'kind':'task-artifacts-v1','workflow_id':submission.workflow_id,'task_id':task['task_id'],
                'node_key':task['node_key'],'parent_sha256':digest(raw)},sort_keys=True,separators=(',',':')).encode()
            expected=digest(canonical);old=db.get(InstanceEvidenceReceipt,(submission.id,task['task_id']))
            if old and old.manifest_sha256!=expected:raise ValueError('Pinned parent changed')
            if old is None:
                db.add(InstanceEvidenceReceipt(submission_id=submission.id,task_id=task['task_id'],manifest_sha256=expected))
                try:db.commit()
                except IntegrityError:
                    db.rollback();old=db.get(InstanceEvidenceReceipt,(submission.id,task['task_id']))
                    if not old or old.manifest_sha256!=expected:raise ValueError('Concurrent parent changed')
        return preview
    except (ValueError,KeyError,TypeError,OSError,StopIteration,AttributeError):
        raise HTTPException(409,'Task artifact failed ownership, association or hash validation') from None
