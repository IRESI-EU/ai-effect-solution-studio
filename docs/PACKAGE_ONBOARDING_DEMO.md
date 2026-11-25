# Publish Service package demonstration

## Exact rehearsal package

Use the German WP3 package from the official repository at revision
`e8914565e966a2d78879c314f980574769d31b87`:

`use-cases/germany-node/germany-node.zip`

The package contains `blueprint.json`, `dockerinfo.json`, and three protobuf
definitions under `microservice/`. The imported logical names are
`data_provider1`, `villas_chronics1`, and `output_formatter1`; their declared
runtime hosts are separately preserved as `data-provider`, `villas-chronics`,
and `output-formatter`.

## Browser rehearsal

1. Sign in as a platform administrator or the German node manager.
2. Open **Publish service** and choose **Upload service package · Recommended**.
3. Select `germany-node.zip`, then choose **Inspect package**.
4. Confirm that all three services, images, runtime declarations, protobufs,
   exact operations/message names, and two connections are visible.
5. Existing production records may be reported as conflicts. This is expected:
   repeat uploads never overwrite catalogue records. For a clean staging
   rehearsal, use an empty test database.
6. For a new package, select the required services and edit catalogue names,
   descriptions, and categories. If a service exposes several operations,
   explicitly choose one supported operation.
7. Optionally select **Also create a draft solution from these connections**.
   If only part of a connected pipeline is selected, either select both sides
   of every connection or turn draft-solution creation off.
8. Acknowledge that registration does not deploy or activate containers, then
   submit. Verify the new services are **pending review**, runtime declarations
   are **unverified**, and the optional solution is **draft**.
9. In Admin, review the source and contract, verify the runtime separately, and
   confirm operation compatibility before approval. Do not execute a workflow
   as part of this import rehearsal.

## Expected safety demonstrations

- Re-uploading the same package reports stable service-ID conflicts and changes
  no existing record.
- Removing an input/output message name or mismatching the protobuf blocks the
  affected service with a specific operation-compatibility message.
- A ZIP with traversal paths, more than one blueprint/dockerinfo pair, too many
  files, or excessive expanded size is rejected before persistence.
- Independent services can be selected and registered without creating a
  solution.
