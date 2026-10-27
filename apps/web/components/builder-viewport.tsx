"use client";

import { useEffect, useState } from "react";
import { getNodesBounds, useNodesInitialized, useOnViewportChange, useReactFlow, useStore } from "@xyflow/react";
import { BuilderViewportSession, layoutFingerprint, viewportKey } from "../lib/builder-viewport";

export default function BuilderViewport({ userId, solutionId }: { userId: string; solutionId: string | null }) {
  const ready = useNodesInitialized();
  const width = useStore(state => state.width);
  const height = useStore(state => state.height);
  const { getNodes, setViewport, viewportInitialized } = useReactFlow();
  const [session] = useState(() => new BuilderViewportSession({
    getItem: key => window.localStorage.getItem(key),
    setItem: (key, value) => window.localStorage.setItem(key, value),
  }, viewportKey(userId, solutionId)));

  useEffect(() => {
    const nodes = getNodes();
    session.initialize({ ready: ready && viewportInitialized, width, height,
      bounds: getNodesBounds(nodes), layout: layoutFingerprint(nodes) }, viewport => { void setViewport(viewport); });
  }, [session, ready, viewportInitialized, width, height, getNodes, setViewport]);

  // Includes pan, wheel/pinch, keyboard navigation and built-in control buttons.
  useOnViewportChange({ onEnd: viewport => session.remember(viewport) });
  return null;
}
