# Service settings: inventory and format

Updated 23 November 2026. Source: read-only inspection of the service containers running on the production server, not just the repository copies.

## How a service can receive settings today

| Channel | How it works | When the value can change | Platform work needed |
| --- | --- | --- | --- |
| **`parameters`** | The service reads `request.parameters` in `/control/execute`. | Every run, and per node | The orchestrator must forward `parameters` again (WP3 branch `fix/control-client-parameters`). The blueprint must carry it per node. |
| **Run input** | The service decodes a JSON object from its first inline input (`inputs[0]`). | Every run, but **only for start nodes**, because downstream nodes receive upstream outputs instead | Already possible: the portal supports per-run inputs. Needs a form instead of raw JSON. |
| **Environment** | `os.environ` read at container start. | Only when the container is redeployed | Out of scope for per-run settings. These are mostly hosts, ports and keys. |
| **Fixed** | Value written in the code. | Never, without the node changing its code | None. Shown to designers as "fixed settings". |

## Inventory of running services

| Catalogue entry | Node | Channel | User-adjustable settings (default) |
| --- | --- | --- | --- |
| villas_chronics1 / GenerateChronics | Germany | `parameters` | `round_decimals` (3), `compress` (false) |
| config_assistant1 / BuildRunConfig | Denmark | `parameters` | Any run-config key; values are merged over the assistant's generated config |
| data_loader1 / ExecuteQuery | Portugal | Run input (start node) | `file_path`, `sql_query`, `max_rows` (1000), `output_format` ("json"), `rename_columns` ({}) |
| grid_synth_service / ConfigureAndSynthesize | Netherlands | Run input (start node) | `seed`, `loading_level`, `ref_sys_id`, `level_specs`, `connection_specs` (service defaults) |
| benchmark-runner / RunBenchmark | Netherlands | Run input; to confirm whether it is only used as a start node | `env_name`, `max_steps`, `algorithm`, `benchmark`, `scenarios`, `kpis`, `time_series_ids`, `topology` |
| topology_generator1 / GenerateTopology | Denmark | Upstream output (from the config assistant) | Not set directly; adjust through the config assistant |
| model_trainer1 / TrainModel | Portugal | Fixed | DGAN epochs and batch size are fixed in code |
| data_provider1, output_formatter1, draw_topology1, feature_engineer1, data_generator1 | DE / DK / PT | None found | — |

The `pkg-*` and `svc-pt-*` entries in the catalogue are published duplicates of the same images, so they inherit the row of their image.

## Settings format

Settings are declared per operation inside the existing operation contract definition (`OperationContractDefinition`), next to `inputs` and `outputs`:

```json
"settings": {
  "channel": "parameters",
  "schema": {
    "type": "object",
    "properties": {
      "round_decimals": {"type": "integer", "title": "Decimal places", "default": 3, "minimum": 0, "maximum": 10},
      "compress": {"type": "boolean", "title": "Compress output", "default": false}
    },
    "additionalProperties": false
  }
}
```

- `channel` is `parameters` or `run_input`. `run_input` settings are only offered when the node is a start node.
- `schema` is standard JSON Schema. The Builder draws its form from it, the API validates values against it, and Design with AI reads it to fill values.
- A missing `settings` block means fixed settings. Nothing changes for that service.
- The provider (or an administrator on their behalf) declares settings at publish time. Values are saved per node in the solution, and can be overridden for a single run.
