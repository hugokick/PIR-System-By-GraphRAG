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
  selectedNodeId: string | null;
  layoutVersion: number;
  nodeColors: Record<string, string>;
  onNodeSelect: (nodeId: string | null) => void;
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

function normalizeNodePositions(value: unknown, fallbackNodes: NvlNode[]) {
  const fallback = new Map(fallbackNodes.map((node) => [node.id, { x: node.x ?? 0, y: node.y ?? 0 }]));
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

function buildOverlayFrame(nodes: NvlNode[], rels: NvlRelationship[], instance: any): OverlayFrame {
  const viewport = readNvlViewport(instance);
  const positions = normalizeNodePositions(instance?.getNodePositions?.(), nodes);
  const nodeLabels = nodes.map((node) => {
    const screenPosition = worldToScreen(positions.get(node.id) ?? { x: 0, y: 0 }, viewport);
    return {
      id: node.id,
      label: node.caption ?? node.id,
      x: screenPosition.x,
      y: screenPosition.y + Number(node.size ?? 20) + 16,
      dimmed: Boolean(node.disabled)
    };
  });
  const edgeLabels = rels
    .filter((rel) => !rel.disabled)
    .map((rel) => {
      const source = worldToScreen(positions.get(rel.from) ?? { x: 0, y: 0 }, viewport);
      const target = worldToScreen(positions.get(rel.to) ?? { x: 0, y: 0 }, viewport);
      return {
        id: rel.id,
        label: rel.caption ?? rel.type ?? rel.id,
        x: (source.x + target.x) / 2,
        y: (source.y + target.y) / 2 - 8,
        dimmed: false
      };
    });
  return {
    width: viewport.width,
    height: viewport.height,
    nodes: nodeLabels,
    edges: edgeLabels
  };
}

export function NvlGraphView({ graph, selectedNodeId, layoutVersion, nodeColors, onNodeSelect }: NvlGraphViewProps) {
  const graphRef = useRef<any>(null);
  const overlayFrameRef = useRef<number | null>(null);
  const [minimapContainer, setMinimapContainer] = useState<HTMLDivElement | null>(null);
  const handleMinimapRef = useCallback((node: HTMLDivElement | null) => {
    setMinimapContainer(node);
  }, []);
  const graphData = useMemo(() => buildNvlGraphData(graph, selectedNodeId, nodeColors), [graph, nodeColors, selectedNodeId]);
  const [overlayFrame, setOverlayFrame] = useState<OverlayFrame>(() =>
    buildOverlayFrame(graphData.nodes, graphData.rels, null)
  );
  const syncOverlayFrame = useCallback(() => {
    setOverlayFrame(buildOverlayFrame(graphData.nodes, graphData.rels, graphRef.current));
  }, [graphData]);
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

  useEffect(() => {
    if (!nvlCanUseDomRenderer()) return;
    const timer = window.setTimeout(() => {
      graphRef.current?.fit?.(graph.nodes.map((node) => node.id));
      syncOverlayFrame();
    }, 120);
    return () => window.clearTimeout(timer);
  }, [graph.nodes, graph.edges, layoutVersion, syncOverlayFrame]);

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
    graphRef.current?.fit?.(graph.nodes.map((node) => node.id));
    scheduleOverlaySync();
  }, [layoutVersion, graph.nodes, scheduleOverlaySync]);

  useEffect(() => {
    syncOverlayFrame();
    return () => {
      if (overlayFrameRef.current !== null && typeof window !== 'undefined') {
        window.cancelAnimationFrame(overlayFrameRef.current);
      }
    };
  }, [syncOverlayFrame]);

  if (!nvlCanUseDomRenderer()) {
    return <div className="nvl-test-fallback">NVL 图谱将在浏览器中渲染</div>;
  }

  return (
    <div className="nvl-stage">
      <InteractiveNvlWrapper
        key={`nvl-${layoutVersion}`}
        ref={graphRef}
        nodes={graphData.nodes}
        rels={graphData.rels}
        positions={graphData.nodes}
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
          onNodeClick: (node) => onNodeSelect(node.id),
          onNodeDoubleClick: (node) => {
            onNodeSelect(node.id);
            graphRef.current?.fit?.([node.id], { outOnly: false });
            scheduleOverlaySync();
          },
          onCanvasClick: () => {
            onNodeSelect(null);
            graphRef.current?.fit?.(graph.nodes.map((node) => node.id), { outOnly: true });
            scheduleOverlaySync();
          },
          onDrag: scheduleOverlaySync,
          onDragEnd: scheduleOverlaySync,
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
