/** Presentation only. Never returns a graph that is sent to the API. */
export type WorkspaceArea = "library" | "canvas" | "assistant";
export function designStage(draft: {pending: unknown; dirty: boolean; saved_solution_id: string|null} | null) {
  return !draft ? "Empty" : draft.pending ? "Proposed" : !draft.dirty && draft.saved_solution_id ? "Saved" : "Applied · unsaved";
}
export function nodeReview(node: {id:string;data:Record<string,unknown>}) {
  const service = node.data.service as {name?:string;description?:string}|undefined;
  const configuration = node.data.configuration as {parameters?:Record<string,unknown>}|undefined;
  return {title:String(node.data.label || service?.name || "Workflow step"),
    purpose:service?.description || "No purpose declared in the catalogue.", settings:configuration?.parameters || {}};
}
export function supportedExamples(scope: string|undefined, chatEnabled:boolean, registered:boolean) {
  if (!chatEnabled) return [];
  if (scope === "catalogue_pair") return ["Explain the proposed steps, settings and connection"];
  if (scope === "append_bound_operation") return ["Explain the supported connection and its limitations"];
  if (scope === "instance_settings") return ["Which instance settings are available?"];
  return registered ? ["Explain the current design and supported settings"] : ["Which authorised catalogue capabilities match my objective?"];
}
export function nextWorkspaceArea(current:WorkspaceArea,key:string):WorkspaceArea {
  const areas:WorkspaceArea[]=["library","canvas","assistant"];
  const index=areas.indexOf(current);
  return key==="Home"?areas[0]:key==="End"?areas[2]:key==="ArrowRight"?areas[(index+1)%3]:key==="ArrowLeft"?areas[(index+2)%3]:current;
}
