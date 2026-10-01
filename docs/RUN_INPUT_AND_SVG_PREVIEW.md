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
`ARTIFACT_BASE_PATH` (default `/wp3-artifacts`); a node path `/data/...` maps
to that mount. The same shared Docker volume must be attached to the node
services and Studio API. The API only serves SVGs within the artifact mount,
with a 2 MiB preview limit. SVG markup is shown through an image element, not
inserted into the document as HTML. Missing volumes and remote artifact URLs
need separate storage integration.

For the Danish local Compose stack, the named volume is `denmark-node-data`.
If it is mounted in Studio API at `/data` (as in the existing local override),
also set `ARTIFACT_BASE_PATH=/data` for the Studio API. The default Studio
Compose file instead points to the separate `wp3_artifacts` volume at
`/wp3-artifacts`, which does **not** contain Danish drawings. For example,
add the following to a local Compose override:

```yaml
services:
  api:
    environment:
      ARTIFACT_BASE_PATH: /data
    volumes:
      - denmark-node-data:/data:ro
    networks:
      - default
      - ai-effect-services
volumes:
  denmark-node-data:
    external: true
networks:
  ai-effect-services:
    external: true
```

For the Danish use case, enter a prompt in the Builder, confirm deployment,
then open the run details. Preview the drawing service's JSON output and use
the drawing buttons. This does not implement the Danish UI's topology
confirmation step or long-running interactive workflow suspension.
