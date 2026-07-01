import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { Layout, Node as NvlNode, Relationship as NvlRelationship } from '@neo4j-nvl/base';
import { InteractiveNvlWrapper } from '@neo4j-nvl/react';
import type { GraphEdge, GraphNode } from '../types';
import { buildNvlGraphData, nvlGraphStyling } from './nvlGraphData';

type NvlGraphViewProps = {
  graph: {
    nodes: GraphNode[];
    edges: GraphEdge[];
  };
  selectedNodeIds: string[];
  highlightDepth: 1 | 2;
  layoutVersion: number;
  nodeColors: Record<string, string>;
  onNodeToggle: (nodeId: string | null) => void;
};

const nvlForceDirectedLayout = 'd3Force' as Layout;

type OverlayNodeLabel = {
  id: string;
  label: string;
  x: number;
  y: number;
  dimmed: boolean;
};

type OverlayEdgeLabel = {
  id: string;
  label: string;
  x: number;
  y: number;
  dimmed: boolean;
};

type OverlayFrame = {
  width: number;
  height: number;
  nodes: OverlayNodeLabel[];
  edges: OverlayEdgeLabel[];
};

function nvlCanUseDomRenderer() {
  if (typeof navigator !== 'undefined' && navigator.userAgent.toLowerCase().includes('jsdom')) return false;
  if (typeof document === 'undefined') return false;
  return true;
}

function normalizeNodePositions(
  value: unknown,
  fallbackNodes: NvlNode[],
  fallbackPositions: { id: string; x?: number; y?: number }[] = []
) {
  const fallback = new Map(
    (fallbackPositions.length > 0 ? fallbackPositions : fallbackNodes).map((node) => [
      node.id,
      { x: node.x ?? 0, y: node.y ?? 0 }
    ])
  );
  if (Array.isArray(value)) {
    value.forEach((node) => {
      if (node && typeof node.id === 'string') {
        fallback.set(node.id, { x: Number(node.x ?? 0), y: Number(node.y ?? 0) });
      }
    });
    return fallback;
  }
  if (value && typeof value === 'object') {
    Object.entries(value as Record<string, { x?: number; y?: number }>).forEach(([id, position]) => {
      fallback.set(id, { x: Number(position?.x ?? 0), y: Number(position?.y ?? 0) });
    });
  }
  return fallback;
}

function readNvlViewport(instance: any) {
  const rect = instance?.getContainer?.()?.getBoundingClientRect?.();
  const width = Number(rect?.width) || 1000;
  const height = Number(rect?.height) || 560;
  const scale = Number(instance?.getScale?.()) || 1;
  const pan = instance?.getPan?.() ?? { x: 0, y: 0 };
  const devicePixelRatio = typeof window === 'undefined' ? 1 : window.devicePixelRatio || 1;
  return {
    width,
    height,
    scale,
    pan: { x: Number(pan.x ?? 0), y: Number(pan.y ?? 0) },
    devicePixelRatio
  };
}

function worldToScreen(position: { x: number; y: number }, viewport: ReturnType<typeof readNvlViewport>) {
  return {
    x: ((position.x - viewport.pan.x) * viewport.scale) / viewport.devicePixelRatio + viewport.width / 2,
    y: ((position.y - viewport.pan.y) * viewport.scale) / viewport.devicePixelRatio + viewport.height / 2
  };
}

function isPointInViewport(point: { x: number; y: number }, viewport: ReturnType<typeof readNvlViewport>, padding = 64) {
  return (
    point.x >= -padding &&
    point.x <= viewport.width + padding &&
    point.y >= -padding &&
    point.y <= viewport.height + padding
  );
}

function buildOverlayFrame(
  nodes: NvlNode[],
  rels: NvlRelationship[],
  instance: any,
  fallbackPositions: { id: string; x?: number; y?: number }[] = []
): OverlayFrame {
  const viewport = readNvlViewport(instance);
  const positions = normalizeNodePositions(instance?.getNodePositions?.(), nodes, fallbackPositions);
  const nodeLabels = nodes
    .map((node) => {
      const screenPosition = worldToScreen(positions.get(node.id) ?? { x: 0, y: 0 }, viewport);
      return {
        id: node.id,
        label: node.caption ?? node.id,
        x: screenPosition.x,
        y: screenPosition.y + Number(node.size ?? 20) + 16,
        dimmed: Boolean(node.disabled)
      };
    })
    .filter((node) => isPointInViewport(node, viewport));
  const edgeLabels = rels
    .filter((rel) => !rel.disabled)
    .flatMap((rel) => {
      const source = worldToScreen(positions.get(rel.from) ?? { x: 0, y: 0 }, viewport);
      const target = worldToScreen(positions.get(rel.to) ?? { x: 0, y: 0 }, viewport);
      const midpoint = {
        x: (source.x + target.x) / 2,
        y: (source.y + target.y) / 2 - 8
      };
      if (
        !isPointInViewport(source, viewport) ||
        !isPointInViewport(target, viewport) ||
        !isPointInViewport(midpoint, viewport, 24)
      ) {
        return [];
      }
      return [{
        id: rel.id,
        label: rel.caption ?? rel.type ?? rel.id,
        x: midpoint.x,
        y: midpoint.y,
        dimmed: false
      }];
    });
  return {
    width: viewport.width,
    height: viewport.height,
    nodes: nodeLabels,
    edges: edgeLabels
  };
}

export function NvlGraphView({
  graph,
  selectedNodeIds,
  highlightDepth,
  layoutVersion,
  nodeColors,
  onNodeToggle
}: NvlGraphViewProps) {
  const graphRef = useRef<any>(null);
  const overlayFrameRef = useRef<number | null>(null);
  const overlayTrackingRef = useRef<number | null>(null);
  const [minimapContainer, setMinimapContainer] = useState<HTMLDivElement | null>(null);
  const handleMinimapRef = useCallback((node: HTMLDivElement | null) => {
    setMinimapContainer(node);
  }, []);
  const graphTopologyKey = useMemo(
    () =>
      JSON.stringify({
        nodes: graph.nodes.map((node) => node.id),
        edges: graph.edges.map((edge) => [edge.source, edge.target, edge.type ?? edge.label])
      }),
    [graph.nodes, graph.edges]
  );
  const graphNodeIds = useMemo(() => graph.nodes.map((node) => node.id), [graphTopologyKey]);
  const selectionKey = selectedNodeIds.join('\u0000');
  const graphData = useMemo(
    () => buildNvlGraphData(graph, selectedNodeIds, highlightDepth, nodeColors, { includeInitialPositions: false }),
    [graph, nodeColors, selectionKey, highlightDepth]
  );
  const initialPositions = useMemo(
    () =>
      buildNvlGraphData(graph, [], 1, nodeColors).nodes.map((node) => ({
        id: node.id,
        x: node.x,
        y: node.y
      })),
    [graphTopologyKey, nodeColors]
  );
  const graphDataRef = useRef(graphData);
  const initialPositionsRef = useRef(initialPositions);
  const [overlayFrame, setOverlayFrame] = useState<OverlayFrame>(() =>
    buildOverlayFrame(graphData.nodes, graphData.rels, null, initialPositions)
  );
  const syncOverlayFrame = useCallback(() => {
    const latestGraphData = graphDataRef.current;
    setOverlayFrame(
      buildOverlayFrame(latestGraphData.nodes, latestGraphData.rels, graphRef.current, initialPositionsRef.current)
    );
  }, []);
  const scheduleOverlaySync = useCallback(() => {
    if (typeof window === 'undefined') {
      syncOverlayFrame();
      return;
    }
    if (overlayFrameRef.current !== null) {
      window.cancelAnimationFrame(overlayFrameRef.current);
    }
    overlayFrameRef.current = window.requestAnimationFrame(() => {
      overlayFrameRef.current = null;
      syncOverlayFrame();
    });
  }, [syncOverlayFrame]);
  const trackOverlayDuringLayout = useCallback(
    (frames = 90) => {
      if (typeof window === 'undefined') {
        syncOverlayFrame();
        return;
      }
      if (overlayTrackingRef.current !== null) {
        window.cancelAnimationFrame(overlayTrackingRef.current);
      }
      let remainingFrames = frames;
      const tick = () => {
        syncOverlayFrame();
        remainingFrames -= 1;
        if (remainingFrames > 0) {
          overlayTrackingRef.current = window.requestAnimationFrame(tick);
          return;
        }
        overlayTrackingRef.current = null;
      };
      overlayTrackingRef.current = window.requestAnimationFrame(tick);
    },
    [syncOverlayFrame]
  );

  useEffect(() => {
    graphDataRef.current = graphData;
    initialPositionsRef.current = initialPositions;
    syncOverlayFrame();
  }, [graphData, initialPositions, syncOverlayFrame]);

  useEffect(() => {
    if (!nvlCanUseDomRenderer()) return;
    const timer = window.setTimeout(() => {
      graphRef.current?.fit?.(graphNodeIds);
      trackOverlayDuringLayout(45);
    }, 120);
    return () => window.clearTimeout(timer);
  }, [graphTopologyKey, graphNodeIds, layoutVersion, trackOverlayDuringLayout]);

  useEffect(() => {
    if (!nvlCanUseDomRenderer()) return;
    graphRef.current?.setLayout?.(nvlForceDirectedLayout);
    graphRef.current?.restart?.(
      {
        layout: nvlForceDirectedLayout,
        styling: nvlGraphStyling
      },
      false
    );
    graphRef.current?.fit?.(graphNodeIds);
    trackOverlayDuringLayout();
  }, [layoutVersion, graphTopologyKey, graphNodeIds, trackOverlayDuringLayout]);

  useEffect(() => {
    syncOverlayFrame();
    return () => {
      if (overlayFrameRef.current !== null && typeof window !== 'undefined') {
        window.cancelAnimationFrame(overlayFrameRef.current);
      }
      if (overlayTrackingRef.current !== null && typeof window !== 'undefined') {
        window.cancelAnimationFrame(overlayTrackingRef.current);
      }
    };
  }, [syncOverlayFrame]);

  if (!nvlCanUseDomRenderer()) {
    return <div className="nvl-test-fallback">NVL 图谱将在浏览器中渲染</div>;
  }

  return (
    <div className="nvl-stage">
      <InteractiveNvlWrapper
        key={`nvl-${layoutVersion}-${graphTopologyKey}`}
        ref={graphRef}
        nodes={graphData.nodes}
        rels={graphData.rels}
        positions={initialPositions}
        layout={nvlForceDirectedLayout}
        nvlOptions={{
          disableTelemetry: true,
          renderer: 'canvas',
          minZoom: 0.12,
          maxZoom: 4.5,
          initialZoom: 1,
          allowDynamicMinZoom: true,
          relationshipThreshold: 1000,
          minimapContainer,
          styling: nvlGraphStyling
        }}
        mouseEventCallbacks={{
          onNodeClick: (node) => onNodeToggle(node.id),
          onNodeDoubleClick: (node) => {
            onNodeToggle(node.id);
            scheduleOverlaySync();
          },
          onCanvasClick: () => {
            onNodeToggle(null);
            scheduleOverlaySync();
          },
          onDrag: () => trackOverlayDuringLayout(8),
          onDragEnd: () => trackOverlayDuringLayout(12),
          onPan: scheduleOverlaySync,
          onZoom: scheduleOverlaySync,
          onZoomAndPan: scheduleOverlaySync
        }}
        interactionOptions={{ selectOnClick: true }}
      />
      <svg
        className="nvl-readable-overlay"
        viewBox={`0 0 ${overlayFrame.width} ${overlayFrame.height}`}
        aria-hidden="true"
      >
        {overlayFrame.edges.map((edge) => (
          <text key={edge.id} className="nvl-edge-caption" x={edge.x} y={edge.y} textAnchor="middle">
            {edge.label}
          </text>
        ))}
        {overlayFrame.nodes.map((node) => (
          <text
            key={node.id}
            className={node.dimmed ? 'nvl-node-caption dimmed' : 'nvl-node-caption'}
            x={node.x}
            y={node.y}
            textAnchor="middle"
          >
            {node.label}
          </text>
        ))}
      </svg>
      <div className="nvl-minimap" ref={handleMinimapRef} aria-hidden="true" />
    </div>
  );
}

export default NvlGraphView;
