"use client";

import { useEffect, useState } from "react";

type Instance = {node_id:string;label:string;resolution:string;limitation?:string;definition?:{properties:Record<string,{title:string;description?:string;type:string;minimum?:number;maximum?:number;default?:unknown}>}};
type Design = {run_input:Record<string,unknown>|null;nodes:{id:string;data:Record<string,any>}[]};

export default function RegisteredConfiguration({revision,proposalId,design,appliedInput,instances,dataset,busy,onReview}:{
  revision:number;proposalId?:string;design:Design;appliedInput:Record<string,unknown>|null;instances:Instance[];
  dataset:{label:string;dataset_ref:string}|null;busy:boolean;
  onReview:(value:{settings:Record<string,Record<string,unknown>>;run_input:Record<string,unknown>|null})=>void;
}) {
  const [selected,setSelected]=useState("");
  const [values,setValues]=useState<Record<string,Record<string,unknown>>>({});
  useEffect(()=>{
    setSelected(String(design.run_input?.dataset_ref||""));
    setValues(Object.fromEntries(instances.map(item=>[item.node_id,{...(design.nodes.find(n=>n.id===item.node_id)?.data.configuration?.parameters||{})}])));
  },[revision,proposalId]);
  return <details className="ai-registered-settings" open><summary>Configure registered workflow</summary><section className="ai-guided-settings" aria-label="Registered workflow configuration">
    <p>INSPECTION ONLY · Explicit controls; no AI request or execution. Settings come from the pinned operation contracts.</p>
    <p>Current applied training CSV: {appliedInput ? dataset?.label || "Unavailable" : "Not selected"}.</p>
    <label htmlFor="registered-training-csv">Training CSV</label>
    <select id="registered-training-csv" value={selected} disabled={busy||!dataset} onChange={e=>setSelected(e.target.value)}>
      <option value="">Select a training CSV</option>{dataset && <option value={dataset.dataset_ref}>{dataset.label}</option>}
    </select>
    {!selected && <p role="status">Select a training CSV before validating.</p>}
    {!dataset && <p role="alert">An authorized training CSV is unavailable. This workflow cannot be configured.</p>}
    {instances.map(item=><fieldset key={item.node_id} disabled={busy||item.resolution!=="active"}>
      <legend>{item.label}</legend>{item.limitation && <p role="alert">{item.limitation}</p>}
      {Object.entries(item.definition?.properties||{}).map(([name,spec])=><label key={name}>
        {spec.title}<input aria-label={`${item.label}: ${spec.title}`} type="number" step={spec.type==="integer"?1:"any"}
          min={spec.minimum} max={spec.maximum} value={String(values[item.node_id]?.[name]??"")}
          onChange={e=>setValues(old=>({...old,[item.node_id]:{...old[item.node_id],[name]:e.target.value===""?null:Number(e.target.value)}}))}/>
        <small>{spec.description} Declared default: {String(spec.default??"none")}. Supported range: {spec.minimum}–{spec.maximum}.</small>
      </label>)}
    </fieldset>)}
    <button disabled={busy||!dataset||!selected||instances.some(i=>i.resolution!=="active")} onClick={()=>onReview({settings:values,run_input:selected?{dataset_ref:selected}:null})}>Review configuration changes</button>
    <p>Apply and Undo change this draft only. Save then Open in Builder preserves the selected data, settings and model connection. No results exist for a new design.</p>
  </section></details>;
}
