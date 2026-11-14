"""Complete initially omitted image metadata only in the unused sandbox registry."""
from app.db import SessionLocal
from app.core.config import settings
from app.models.service import Service
from app.models.execution_submission import ExecutionSubmission
from app.models.deployment import Deployment

assert settings.database_url.endswith('/pt_parameter_sandbox')
from app.main import app  # Register the complete existing ORM model graph.
with SessionLocal() as db:
    assert db.query(ExecutionSubmission).count()==0 and db.query(Deployment).count()==0
    records=db.query(Service).all()
    assert {r.id for r in records}=={'pt-experimental-GenerateData','pt-experimental-TrainModel'}
    assert all(r.adapter_type=='platform-experimental' and not r.image for r in records)
    for record in records:
        record.image='sha256:76f7eea8d48eff6aeb3182dc755cd70d195899404c17785ce73a5766b0352bba'
    db.commit()
print('Completed only isolated unused registry image metadata; no execution.')
