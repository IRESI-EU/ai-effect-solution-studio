# Run input and SVG output

The Builder accepts optional input at **run time**. In Prompt mode it sends
`{"prompt": "..."}`; in JSON mode it sends the entered object unchanged. Studio
encodes the object as an inline JSON DataReference and passes it as the WP3
orchestrator's initial `inputs` list. The first service in a workflow must
understand that object's fields. Empty input preserves the service's default
behavior. The input is limited to 64 KiB. This is a per-run input; it is not
stored in the reusable solution design.

In Run details, a file DataReference ending in `.svg` can be viewed as an
image. JSON output with a `drawings` array containing SVG `uri` values also
offers a **View drawing** button for each image. The API reads these files from
`ARTIFACT_BASE_PATH` (default `/wp3-artifacts`) and any comma-separated roots
in `ARTIFACT_BASE_PATHS`; a node path `/data/...` is searched within those
read-only mounts. The same shared Docker volume must be attached to the node
services and Studio API. JSON, CSV, text and SVG previews use the same
restricted resolver. The API only serves files within configured artifact
mounts, and SVG files have a 2 MiB preview limit. SVG markup is shown through
an image element, not inserted into the document as HTML. Missing volumes and
remote artifact URLs need separate storage integration.

For the Danish local Compose stack, the named volume is `denmark-node-data`.
The default Studio Compose file mounts it read-only at `/denmark-artifacts`
and includes that path in `ARTIFACT_BASE_PATHS`. It retains the separate
`wp3_artifacts` mount for other local services. If a deployment uses a
different node stack, add that stack's artifact volume as another read-only
mount and append its container path to `ARTIFACT_BASE_PATHS`. For example:

```yaml
services:
  api:
    environment:
      ARTIFACT_BASE_PATHS: /denmark-artifacts,/another-node-artifacts

The production Compose profile mounts the German node's `germany-node_shared-data`
volume read-only at `/shared`. German task references identify output directories;
the preview first lists their files and then allows an operator to open an
individual CSV or JSON artifact.
    volumes:
      - another-node-data:/another-node-artifacts:ro
    networks:
      - default
      - ai-effect-services
volumes:
  another-node-data:
    external: true
networks:
  ai-effect-services:
    external: true
```

For the Danish use case, enter a prompt in the Builder, confirm deployment,
then open the run details. Preview the drawing service's JSON output and use
the drawing buttons. This does not implement the Danish UI's topology
confirmation step or long-running interactive workflow suspension.
