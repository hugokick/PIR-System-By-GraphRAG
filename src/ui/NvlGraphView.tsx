import { useEffect, useMemo, useRef } from 'react';
import type { Layout, Node as NvlNode, Relationship as NvlRelationship } from '@neo4j-nvl/base';
import { InteractiveNvlWrapper } from '@neo4j-nvl/react';
import type { GraphEdge, GraphNode } from '../types';

type NvlGraphViewProps = {
  graph: {
    nodes: GraphNode[];
    edges: GraphEdge[];
  };
  selectedNodeId: string | null;
  layoutVersion: number;
  nodeColors: Record<string, string>;
  onNodeSelect: (nodeId: string) => void;
};

const nvlForceDirectedLayout = 'forceDirected' as Layout;

function nvlCanUseDomRenderer() {
  if (typeof navigator !== 'undefined' && navigator.userAgent.toLowerCase().includes('jsdom')) return false;
  if (typeof document === 'undefined') return false;
  return true;
}

function collectGraphNeighborIds(graph: { nodes: GraphNode[]; edges: GraphEdge[] }, selectedNodeId: string | null) {
  const ids = new Set<string>();
  if (!selectedNodeId) return ids;
  ids.add(selectedNodeId);
  graph.edges.forEach((edge) => {
    if (edge.source === selectedNodeId) ids.add(edge.target);
    if (edge.target === selectedNodeId) ids.add(edge.source);
  });
  return ids;
}

function buildNvlGraphData(
  graph: { nodes: GraphNode[]; edges: GraphEdge[] },
  selectedNodeId: string | null,
  nodeColors: Record<string, string>
) {
  const neighborIds = collectGraphNeighborIds(graph, selectedNodeId);
  const nodes: NvlNode[] = graph.nodes.map((node) => ({
    id: node.id,
    caption: node.label,
    color: nodeColors[node.kind] ?? '#607d75',
    size: node.id === selectedNodeId ? 44 : 34,
    selected: node.id === selectedNodeId,
    disabled: Boolean(selectedNodeId) && !neighborIds.has(node.id),
    captions: [
      {
        value: node.label,
        styles: ['bold']
      },
      {
        value: node.kind
      }
    ]
  }));
  const rels: NvlRelationship[] = graph.edges.map((edge) => ({
    id: `${edge.source}->${edge.target}:${edge.type ?? edge.label}`,
    from: edge.source,
    to: edge.target,
    type: edge.type ?? edge.label,
    caption: edge.type ?? edge.label,
    color: Boolean(selectedNodeId) && (edge.source === selectedNodeId || edge.target === selectedNodeId) ? '#4361a8' : '#9aaba5',
    width: Boolean(selectedNodeId) && (edge.source === selectedNodeId || edge.target === selectedNodeId) ? 3 : 2,
    disabled: Boolean(selectedNodeId) && edge.source !== selectedNodeId && edge.target !== selectedNodeId
  }));
  return { nodes, rels };
}

export function NvlGraphView({ graph, selectedNodeId, layoutVersion, nodeColors, onNodeSelect }: NvlGraphViewProps) {
  const graphRef = useRef<any>(null);
  const graphData = useMemo(() => buildNvlGraphData(graph, selectedNodeId, nodeColors), [graph, nodeColors, selectedNodeId]);

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
    graphRef.current?.restart?.();
    graphRef.current?.fit?.(graph.nodes.map((node) => node.id));
  }, [layoutVersion, graph.nodes]);

  if (!nvlCanUseDomRenderer()) {
    return <div className="nvl-test-fallback">NVL 图谱将在浏览器中渲染</div>;
  }

  return (
    <InteractiveNvlWrapper
      key={`nvl-${layoutVersion}`}
      ref={graphRef}
      nodes={graphData.nodes}
      rels={graphData.rels}
      layout={nvlForceDirectedLayout}
      nvlOptions={{
        disableTelemetry: true,
        renderer: 'canvas',
        minZoom: 0.2,
        maxZoom: 4
      }}
      mouseEventCallbacks={{
        onNodeClick: (node) => onNodeSelect(node.id),
        onNodeDoubleClick: (node) => {
          onNodeSelect(node.id);
          graphRef.current?.fit?.([node.id]);
        },
        onDrag: true,
        onPan: true,
        onZoom: true
      }}
      interactionOptions={{ selectOnClick: true }}
    />
  );
}

export default NvlGraphView;
