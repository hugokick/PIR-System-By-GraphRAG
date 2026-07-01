import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { Layout } from '@neo4j-nvl/base';
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

function nvlCanUseDomRenderer() {
  if (typeof navigator !== 'undefined' && navigator.userAgent.toLowerCase().includes('jsdom')) return false;
  if (typeof document === 'undefined') return false;
  return true;
}

export function NvlGraphView({ graph, selectedNodeId, layoutVersion, nodeColors, onNodeSelect }: NvlGraphViewProps) {
  const graphRef = useRef<any>(null);
  const [minimapContainer, setMinimapContainer] = useState<HTMLDivElement | null>(null);
  const handleMinimapRef = useCallback((node: HTMLDivElement | null) => {
    setMinimapContainer(node);
  }, []);
  const graphData = useMemo(() => buildNvlGraphData(graph, selectedNodeId, nodeColors), [graph, nodeColors, selectedNodeId]);
  const fitGraph = useCallback(() => {
    graphRef.current?.fit?.(graph.nodes.map((node) => node.id));
  }, [graph.nodes]);

  useEffect(() => {
    if (!nvlCanUseDomRenderer()) return;
    const timer = window.setTimeout(() => {
      fitGraph();
    }, 120);
    return () => window.clearTimeout(timer);
  }, [fitGraph, graph.edges, layoutVersion]);

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
    fitGraph();
  }, [layoutVersion, fitGraph]);

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
          relationshipThreshold: 10000,
          minimapContainer,
          styling: nvlGraphStyling
        }}
        mouseEventCallbacks={{
          onNodeClick: (node) => onNodeSelect(node.id),
          onNodeDoubleClick: (node) => {
            onNodeSelect(node.id);
            graphRef.current?.fit?.([node.id], { outOnly: false });
          },
          onCanvasClick: () => {
            onNodeSelect(null);
            graphRef.current?.fit?.(graph.nodes.map((node) => node.id), { outOnly: true });
          },
          onDrag: () => undefined,
          onDragEnd: () => undefined,
          onPan: () => undefined,
          onZoom: () => undefined,
          onZoomAndPan: () => undefined
        }}
        interactionOptions={{ selectOnClick: true }}
      />
      <div className="nvl-minimap" ref={handleMinimapRef} aria-hidden="true" />
    </div>
  );
}

export default NvlGraphView;
