"""One-shot bootstrap confined to the fresh PostgreSQL sandbox, never a migration."""
import json
from pathlib import Path
import uuid
from sqlalchemy import inspect
from app.db import Base, engine, SessionLocal
from app.models.user import User
from app.models.service import Service
from app.models.operation_contract import OperationContract
from app.schemas.operation_contract import OperationContractWrite
from app.core.security import hash_password
from app.core.config import settings

def main():
    if not settings.database_url.endswith('/pt_parameter_sandbox'):
        raise RuntimeError('Separate sandbox database required')
    if inspect(engine).get_table_names():
        raise RuntimeError('Bootstrap requires a fresh database; never overwrite an existing profile')
    # Importing main registers all models and initializes only this verified fresh DB.
    from app.main import app
    private=json.loads(Path('/private/credentials.json').read_text())
    records=json.loads(Path('/review/contracts.json').read_text())
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        db.add(User(id=private['owner_id'],email=private['email'],display_name='EXPERIMENTAL Portuguese sandbox designer',
            password_hash=hash_password(private['password']),role='solution_designer',status='active'))
        for record in records:
            value=OperationContractWrite.model_validate({k:v for k,v in record.items() if k not in {'id','service_id'}})
            db.add(Service(id=record['service_id'],name='EXPERIMENTAL Portuguese '+value.runtime_operation_name,
                provider='Platform-controlled sandbox; no partner approval',category='experimental-portuguese',
                description='Actual retained Portuguese API through a parameter-aware experimental sidecar. Synthetic test data only.',
                status='approved',lifecycle_status='active',operation_name=value.runtime_operation_name,
                container_name='pt-'+value.runtime_operation_name, interface_type='control',orchestration_mode='sidecar',
                adapter_type='platform-experimental',contract_uri=value.operation_identity,
                internal_host='pt-adapter',internal_port='8080',health_path='/health',
                input_type='opaque authorized reference',output_type='CSV sequences' if value.runtime_operation_name=='GenerateData' else 'model reference',
                created_by_user_id=private['owner_id']))
            db.flush()
            values=value.model_dump()
            values['definition']=value.definition.model_dump(mode='json',exclude_none=True)
            db.add(OperationContract(id=record['id'],service_id=record['service_id'],status='active',**values))
        db.commit()
    print('Fresh isolated designer and two experimental contracts created; no workflow submitted.')

if __name__=='__main__': main()
