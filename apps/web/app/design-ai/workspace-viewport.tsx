"use client";

import {useEffect} from "react";
import {useNodesInitialized,useReactFlow,useStore} from "@xyflow/react";

/** Fit a newly visible/resized canvas, without graph setters or Save callbacks.
 * Selection and ordinary pan/zoom do not change these dependencies.
 */
export default function WorkspaceViewport() {
  const ready=useNodesInitialized();
  const width=useStore(state=>state.width), height=useStore(state=>state.height);
  const {fitView,viewportInitialized}=useReactFlow();
  useEffect(()=>{
    if(ready && viewportInitialized && width>0 && height>0)
      void fitView({padding:.18,minZoom:.5,maxZoom:1,duration:0});
  },[ready,viewportInitialized,width,height,fitView]);
  return null;
}
