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

function positionPercent(value: number, min: number, max: number) {
  const span = Math.max(max - min, 1);
  return 18 + ((value - min) / span) * 64;
}

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
  const overlayLabels = useMemo(() => {
    const xs = graphData.nodes.map((node) => node.x ?? 0);
    const ys = graphData.nodes.map((node) => node.y ?? 0);
    const minX = Math.min(...xs, 0);
    const maxX = Math.max(...xs, 0);
    const minY = Math.min(...ys, 0);
    const maxY = Math.max(...ys, 0);
    const nodePositions = new Map(
      graphData.nodes.map((node) => [
        node.id,
        {
          x: node.x ?? 0,
          y: node.y ?? 0,
          left: positionPercent(node.x ?? 0, minX, maxX),
          top: positionPercent(node.y ?? 0, minY, maxY)
        }
      ])
    );

    return {
      nodes: graphData.nodes.map((node) => {
        const position = nodePositions.get(node.id);
        return {
          id: node.id,
          label: node.caption ?? node.id,
          left: position?.left ?? 50,
          top: position?.top ?? 50,
          selected: node.id === selectedNodeId
        };
      }),
      edges: graphData.rels.flatMap((rel) => {
        const from = nodePositions.get(rel.from);
        const to = nodePositions.get(rel.to);
        if (!from || !to) return [];
        const midpointX = (from.x + to.x) / 2;
        const midpointY = (from.y + to.y) / 2;
        return [
          {
            id: rel.id,
            label: rel.caption ?? rel.type ?? rel.id,
            left: positionPercent(midpointX, minX, maxX),
            top: positionPercent(midpointY, minY, maxY),
            disabled: rel.disabled
          }
        ];
      })
    };
  }, [graphData, selectedNodeId]);

  useEffect(() => {
    if (!nvlCanUseDomRenderer()) return;
    const timer = window.setTimeout(() => {
      graphRef.current?.fit?.(graph.nodes.map((node) => node.id));
    }, 120);
    return () => window.clearTimeout(timer);
  }, [graph.nodes, graph.edges, layoutVersion]);

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
  }, [layoutVersion, graph.nodes]);

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
          },
          onCanvasClick: () => {
            onNodeSelect(null);
            graphRef.current?.fit?.(graph.nodes.map((node) => node.id), { outOnly: true });
          },
          onDrag: true,
          onPan: true,
          onZoom: true
        }}
        interactionOptions={{ selectOnClick: true }}
      />
      <div className="nvl-readable-overlay" aria-hidden="true">
        {overlayLabels.edges
          .filter((edge) => graph.edges.length <= 16 || !edge.disabled)
          .map((edge) => (
          <span
            key={edge.id}
            className={`nvl-edge-caption${edge.disabled ? ' disabled' : ''}`}
            style={{ left: `${edge.left}%`, top: `${edge.top}%` }}
          >
            {edge.label}
          </span>
          ))}
        {overlayLabels.nodes.map((node) => (
          <span
            key={node.id}
            className={`nvl-node-caption${node.selected ? ' selected' : ''}`}
            style={{ left: `${node.left}%`, top: `${node.top}%` }}
          >
            {node.label}
          </span>
        ))}
      </div>
      <div className="nvl-minimap" ref={handleMinimapRef} aria-hidden="true" />
    </div>
  );
}

export default NvlGraphView;
