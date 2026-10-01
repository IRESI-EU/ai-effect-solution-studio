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

For the Danish use case, enter a prompt in the Builder, confirm deployment,
then open the run details. Preview the drawing service's JSON output and use
the drawing buttons. This does not implement the Danish UI's topology
confirmation step or long-running interactive workflow suspension.
