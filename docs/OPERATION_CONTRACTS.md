# Operation Contract Registry V1

## Purpose

An operation contract is the governed, versioned declaration of the data an
executable service operation requires and produces. It provides formal
metadata for future deterministic workflow compatibility checks.

Operation Contract Registry V1 introduces persistence, strict request
validation, lifecycle management, and API access. It does not change Builder
validation, runtime readiness, workflow compilation, or WP3 submission.
Blocking semantic workflow validation is not implemented yet.

## Operation contracts and interface contracts

The two contract types have different responsibilities:

- An **interface contract** describes how a service is invoked, such as
  `interface_type`, `proto_uri`, `contract_uri`, HTTP paths, protobuf messages,
  or sidecar metadata.
- An **operation contract** describes what an executable operation consumes
  and produces, including semantic concepts, representations, DataReference
  protocols, content types, schemas, cardinality, and input source
  requirements.

Operation contracts are stored separately from `Service.interface_contract`.
Legacy `input_type` and `output_type` strings are not operation contracts and
are never used to synthesize one.

## Persisted entity

The `operation_contracts` table contains:

| Field | Required | Description |
|---|---:|---|
| `id` | Yes | String UUID primary key |
| `service_id` | Yes | Indexed foreign key to `services.id` |
| `operation_identity` | Yes | Stable URI or URN |
| `runtime_operation_name` | Yes | Existing runtime operation/method name |
| `contract_version` | Yes | Semantic version |
| `schema_version` | Yes | Contract schema version; only `1.0` is accepted |
| `status` | Yes | `draft`, `active`, `deprecated`, or `withdrawn` |
| `source_kind` | Yes | `manual`, `manifest`, `wp3_package`, or `demo` |
| `source_reference` | No | Traceability reference |
| `definition` | Yes | PostgreSQL JSONB contract definition |
| `created_at` | Yes | Creation timestamp |
| `updated_at` | Yes | Last mutation timestamp |
| `activated_at` | No | First activation timestamp |
| `deprecated_at` | No | Deprecation timestamp |
| `withdrawn_at` | No | Withdrawal timestamp |

The database prevents duplicate combinations of `service_id`,
`operation_identity`, and `contract_version`.

## Definition vocabulary

Every definition declares an `operation_role`:

- `source`
- `transformer`
- `analyzer`
- `model`
- `reporter`
- `adapter`
- `sink`
- `other`

The definition contains one `inputs` array and one `outputs` array.

Input slots declare:

- `name`
- `required`
- `semantic_concept`
- `value_representation`: `data_reference`, `inline_value`, or
  `structured_object`
- `data_reference_protocols`
- `content_types`
- optional `schema_ref`
- `min_cardinality`
- nullable `max_cardinality`
- `source_requirement`: `upstream_operation`, `workflow_input`,
  `upstream_or_workflow_input`, or `none`
- `compatibility_notes`

Output slots use the same data-description and cardinality fields without
`required` or `source_requirement`.

Definitions can also include JSON-object `adapter_capabilities` and top-level
`compatibility_notes`. Adapter capability semantics are reserved for a later
compatibility-validation slice.

### Strict validation

All defined request, definition, input, and output models reject unknown
fields. A misspelled field produces HTTP 422 rather than being discarded.
Objects inside the deliberately extensible `adapter_capabilities` array remain
opaque JSON objects in V1.

Operation identities must be:

- a URI with a valid scheme and no spaces, control characters, or malformed
  percent escapes; or
- an RFC-style URN with a conservative two-to-32-character namespace
  identifier and a non-empty namespace-specific string.

Malformed values such as `urn:bad`, invalid namespaces, `%G1`, or a trailing
`%` are rejected.

Contract versions use deterministic semantic-version syntax. Schema version
must equal `1.0`. Input and output names must be unique within their arrays.
Cardinalities must be non-negative, maximum cardinality cannot be below the
minimum, required inputs need a minimum of at least one, and optional inputs
use a zero minimum. Protocol and content-type arrays cannot contain blank
entries.

## Request and response bodies

### Create a draft

`POST /services/{service_id}/operation-contracts`

The Service is selected exclusively by the path. `service_id`, lifecycle
status, IDs, and timestamps are not accepted in the request.

```json
{
  "operation_identity": "urn:ai-effect:operation:analyze-data",
  "runtime_operation_name": "AnalyzeData",
  "contract_version": "1.0.0",
  "schema_version": "1.0",
  "source_kind": "manual",
  "source_reference": "consortium-review-2026",
  "definition": {
    "operation_role": "analyzer",
    "inputs": [],
    "outputs": [],
    "adapter_capabilities": [],
    "compatibility_notes": []
  }
}
```

Successful creation returns HTTP 201 and the complete persisted contract.

### Replace editable draft metadata

`PUT /operation-contracts/{contract_id}`

PUT requires the complete create-body shape and replaces every editable draft
field: operation identity, runtime operation name, contract version, schema
version, source kind, source reference, and definition. It cannot change
`service_id`, status, ID, or timestamps. Only drafts can be updated.

### Contract response

Read, create, update, and lifecycle endpoints return:

```json
{
  "id": "contract-uuid",
  "service_id": "service-id",
  "operation_identity": "urn:ai-effect:operation:analyze-data",
  "runtime_operation_name": "AnalyzeData",
  "contract_version": "1.0.0",
  "schema_version": "1.0",
  "status": "active",
  "source_kind": "manual",
  "source_reference": "consortium-review-2026",
  "definition": {
    "operation_role": "analyzer",
    "inputs": [],
    "outputs": [],
    "adapter_capabilities": [],
    "compatibility_notes": []
  },
  "created_at": "2026-07-30T12:00:00Z",
  "updated_at": "2026-07-30T12:05:00Z",
  "activated_at": "2026-07-30T12:05:00Z",
  "deprecated_at": null,
  "withdrawn_at": null
}
```

## Lifecycle and endpoints

Allowed transitions are:

1. `draft -> active`
2. `draft -> withdrawn`
3. `active -> deprecated`
4. `deprecated -> withdrawn`

Active, deprecated, and withdrawn contracts are immutable. An active contract
must be deprecated before withdrawal. Service approval never activates a
contract automatically.

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/services/{service_id}/operation-contracts` | List every version |
| `POST` | `/services/{service_id}/operation-contracts` | Create a draft |
| `GET` | `/operation-contracts/{contract_id}` | Read one contract |
| `PUT` | `/operation-contracts/{contract_id}` | Replace all editable draft metadata |
| `POST` | `/operation-contracts/{contract_id}/activate` | Activate a draft |
| `POST` | `/operation-contracts/{contract_id}/deprecate` | Deprecate an active contract |
| `POST` | `/operation-contracts/{contract_id}/withdraw` | Withdraw a draft or deprecated contract |
| `GET` | `/services/{service_id}/operation-contract-resolution` | Resolve active or unknown |

Activation requires an approved or legacy validated Service that is not
archived or rejected. Invalid transitions and duplicate versions return HTTP
409, missing resources return 404, and invalid request bodies return 422.

## Locking and single-active behavior

Every contract mutation uses the same order:

1. Identify and lock the referenced Service row with `SELECT ... FOR UPDATE`.
2. Re-read and lock the target contract.
3. Revalidate its current status.
4. Apply the mutation and commit.

Activation then locks and deprecates any currently active contract before
activating the target in the same transaction. The Service-row lock serializes
registry mutations made through this application and provides the MVP
single-active guarantee.

There is no PostgreSQL partial unique index enforcing one active contract.
Direct database writes or future code paths that bypass the registry service
could violate the invariant. A partial unique index remains a future
hardening measure.

## Unknown fallback

Existing services are not backfilled. No contract is inferred from legacy
types, interface metadata, workflow topology, operation names, or WP3 package
connectivity.

When a Service has no active contract, resolution returns:

```json
{
  "resolution": "unknown",
  "reason": "no_active_contract",
  "contract": null
}
```

The fallback is computed and does not create a database record.

## Isolated backend tests

Operation-contract tests require a dedicated PostgreSQL database. They fail
immediately when `TEST_DATABASE_URL` is missing, identifies the normal
`DATABASE_URL`, or uses a database name that does not end in `_test`.

Example:

```text
TEST_DATABASE_URL=postgresql+psycopg://solution_studio:REDACTED@postgres:5432/solution_studio_test
```

From `apps/api`, install and run:

```powershell
python -m pip install -r requirements-test.txt
$env:DATABASE_URL = "postgresql+psycopg://solution_studio:solution_studio@localhost:15432/solution_studio"
$env:TEST_DATABASE_URL = "postgresql+psycopg://solution_studio:solution_studio@localhost:15432/solution_studio_test"
pytest -q app/tests
```

The test database must already exist. At test-session startup its tables are
dropped and recreated, so it must never contain non-test data. The suite
overrides the FastAPI database dependency and never imports or uses the
application `SessionLocal`.

For containerized execution, build the test-only image with
`apps/api/Dockerfile.test`; the production API Dockerfile continues to install
only `requirements.txt`.

## Current limitations

- Blocking semantic workflow validation is not implemented.
- Builder, runtime readiness, compiler, and WP3 behavior are unchanged.
- Operation contracts are not accepted by service manifests or WP3 package
  imports yet.
- The application still uses SQLAlchemy `create_all` rather than migrations.
- The one-active invariant is application-enforced rather than protected by a
  partial unique database index.
- Adapter capabilities are stored but not semantically evaluated.
