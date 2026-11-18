# Parameter review files are not service import manifests

`portugal-source-openapi.json` is a source-derived **OpenAPI interface description**. **Do not paste it into Publish → Advanced import → Paste JSON.** That field requires a complete AI-EFFECT manifest containing `service`, `runtime` and `interface`, including actual runtime/container details.

The parameter-onboarding workflow is implemented on the isolated development branch. A production OpenAPI check on 18 November 2026 did not expose its routes/schema. This file cannot enable parameterisation on the live production site, and the development instructions are not an invitation to register an unverified replacement service there.

On a deployment containing the feature, select an existing owned service in Publish and use **Adjustable service settings → Supply an interface description → Interface description file**. Select the actual OpenAPI operation, review candidates and save a draft. Confirm actual runtime consumption and normal/invalid checks, obtain normal service approval, then publish the reviewed version. Only that published definition drives Builder and Design with AI controls.

A complete development service manifest may contain this document under `interface.openapi` and identify one operation using `interface.openapi_operation_id`. It must still supply the real service and runtime metadata. There is no production-ready Portuguese manifest in this folder; runtime mappings, availability and provider-approved limits remain unqualified.

The Portuguese source describes candidate training settings `sequence_len`, `batch_size`, `epochs`, and generation setting `number_of_examples`. Source defaults are observations, not provider approval. `denmark-candidates.schema.json` is likewise candidate-review material, not a service manifest or an activated runtime contract.

See [the corrected development walkthrough](../DAILY_DELIVERY_2026-11-18_PORTUGUESE_ONBOARDING.md).
