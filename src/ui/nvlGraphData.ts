import type { Node as NvlNode, Relationship as NvlRelationship } from '@neo4j-nvl/base';
import type { GraphEdge, GraphNode } from '../types';

const defaultNodeColor = '#607d75';

export const nvlGraphStyling = {
  defaultNodeColor,
  defaultRelationshipColor: '#8aa19a',
  nodeDefaultBorderColor: '#ffffff',
  selectedBorderColor: '#4f88ff',
  selectedInnerBorderColor: '#ffffff',
  dropShadowColor: '#1f4e79',
  disabledItemColor: '#c8d2cf',
  disabledItemFontColor: '#7d8c87',
  minimapViewportBoxColor: '#4f88ff'
};

const nodeBaseSizes: Record<string, number> = {
  exhibit: 42,
  project: 36,
  owner: 36,
  material: 34,
  supplier: 34,
  theme: 34,
  interaction: 34,
  document: 30
};

const nodeIconPaths: Record<string, string> = {
  exhibit: '<path d="M5 4h14v16H5zM8 8h8M8 12h8M8 16h5" stroke="black" stroke-width="2" fill="none" stroke-linecap="round"/>',
  project: '<path d="M4 7h16v12H4zM8 7V5h8v2" stroke="black" stroke-width="2" fill="none" stroke-linejoin="round"/>',
  owner: '<path d="M12 12a4 4 0 100-8 4 4 0 000 8zM5 21a7 7 0 0114 0" stroke="black" stroke-width="2" fill="none" stroke-linecap="round"/>',
  material: '<path d="M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3z" stroke="black" stroke-width="2" fill="none" stroke-linejoin="round"/>',
  supplier: '<path d="M4 8h16M6 8l2-4h8l2 4v12H6zM9 13h6" stroke="black" stroke-width="2" fill="none" stroke-linecap="round"/>',
  theme: '<path d="M12 3l2.5 5 5.5.8-4 3.9.9 5.5L12 15.6 7.1 18.2l.9-5.5-4-3.9 5.5-.8L12 3z" stroke="black" stroke-width="2" fill="none" stroke-linejoin="round"/>',
  interaction: '<path d="M8 12h8M12 8v8M4 12a8 8 0 1016 0 8 8 0 00-16 0z" stroke="black" stroke-width="2" fill="none" stroke-linecap="round"/>',
  document: '<path d="M7 3h7l5 5v13H7zM14 3v6h5M10 14h6M10 18h4" stroke="black" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
};

function buildSvgIcon(path: string) {
  return `data:image/svg+xml;utf8,${encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">${path}</svg>`
  )}`;
}

function graphNodeSize(kind: string, selected: boolean) {
  const baseSize = nodeBaseSizes[kind] ?? 32;
  return selected ? baseSize + 12 : baseSize;
}

export function collectGraphNeighborIds(graph: { nodes: GraphNode[]; edges: GraphEdge[] }, selectedNodeId: string | null) {
  const ids = new Set<string>();
  if (!selectedNodeId) return ids;
  ids.add(selectedNodeId);
  graph.edges.forEach((edge) => {
    if (edge.source === selectedNodeId) ids.add(edge.target);
    if (edge.target === selectedNodeId) ids.add(edge.source);
  });
  return ids;
}

export function buildNvlGraphData(
  graph: { nodes: GraphNode[]; edges: GraphEdge[] },
  selectedNodeId: string | null,
  nodeColors: Record<string, string>
) {
  const neighborIds = collectGraphNeighborIds(graph, selectedNodeId);
  const nodes: NvlNode[] = graph.nodes.map((node) => ({
    id: node.id,
    caption: node.label,
    color: nodeColors[node.kind] ?? defaultNodeColor,
    size: graphNodeSize(node.kind, node.id === selectedNodeId),
    selected: node.id === selectedNodeId,
    activated: node.id === selectedNodeId,
    disabled: Boolean(selectedNodeId) && !neighborIds.has(node.id),
    captionSize: node.id === selectedNodeId ? 13 : 11,
    icon: nodeIconPaths[node.kind] ? buildSvgIcon(nodeIconPaths[node.kind]) : undefined,
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
  const rels: NvlRelationship[] = graph.edges.map((edge, index) => {
    const highlighted = Boolean(selectedNodeId) && (edge.source === selectedNodeId || edge.target === selectedNodeId);
    const disabled = Boolean(selectedNodeId) && edge.source !== selectedNodeId && edge.target !== selectedNodeId;
    const relationshipType = edge.type ?? edge.label;

    return {
      id: `${edge.source}->${edge.target}:${relationshipType}:${index}`,
      from: edge.source,
      to: edge.target,
      type: relationshipType,
      caption: relationshipType,
      captionSize: highlighted ? 6 : 5,
      captionAlign: 'center',
      color: highlighted ? '#243f80' : '#8aa19a',
      width: highlighted ? 4 : disabled ? 1.5 : 2.4,
      disabled
    };
  });
  return { nodes, rels };
}
