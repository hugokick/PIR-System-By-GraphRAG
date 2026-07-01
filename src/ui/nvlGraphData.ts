import type { Node as NvlNode, Relationship as NvlRelationship } from '@neo4j-nvl/base';
import type { GraphEdge, GraphNode } from '../types';

const defaultNodeColor = '#a5abb6';

export const nvlGraphStyling = {
  defaultNodeColor,
  defaultRelationshipColor: '#8f9bad',
  nodeDefaultBorderColor: '#ffffff',
  selectedBorderColor: '#f79767',
  selectedInnerBorderColor: '#ffffff',
  dropShadowColor: '#68bdf6',
  disabledItemColor: '#2b3442',
  disabledItemFontColor: '#778395',
  minimapViewportBoxColor: '#68bdf6'
};

const nodeBaseSizes: Record<string, number> = {
  exhibit: 18,
  project: 14,
  owner: 14,
  material: 14,
  supplier: 14,
  theme: 14,
  interaction: 14,
  document: 13
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

const relationshipCaptions: Record<string, string> = {
  belongs_to_project: '所属项目',
  has_document: '资料文档',
  has_interaction: '交互形式',
  has_theme: '主题领域',
  owned_by: '业主',
  similar_to: '相似展项',
  supplied_by: '供应商',
  supports_theme: '支持主题',
  uses_material: '使用材料'
};

function buildSvgIcon(path: string) {
  return `data:image/svg+xml;utf8,${encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">${path}</svg>`
  )}`;
}

function graphNodeSize(kind: string, selected: boolean) {
  const baseSize = nodeBaseSizes[kind] ?? 24;
  return selected ? baseSize + 4 : baseSize;
}

function relationshipCaption(value: string) {
  const key = value.trim().toLowerCase();
  return relationshipCaptions[key] ?? value;
}

function initialNodePosition(index: number, total: number) {
  if (total <= 1) return { x: 0, y: 0 };
  const radius = Math.min(920, 320 + total * 12);
  const angle = -Math.PI / 2 + (2 * Math.PI * index) / total;
  return {
    x: Math.round(Math.cos(angle) * radius),
    y: Math.round(Math.sin(angle) * radius)
  };
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
  const nodes: NvlNode[] = graph.nodes.map((node, index) => {
    const position = initialNodePosition(index, graph.nodes.length);

    return {
      id: node.id,
      caption: node.label,
      color: nodeColors[node.kind] ?? defaultNodeColor,
      size: graphNodeSize(node.kind, node.id === selectedNodeId),
      pinned: true,
      selected: node.id === selectedNodeId,
      activated: node.id === selectedNodeId,
      disabled: Boolean(selectedNodeId) && !neighborIds.has(node.id),
      captionSize: node.id === selectedNodeId ? 13 : 12,
      captionAlign: 'bottom',
      x: position.x,
      y: position.y,
      icon: nodeIconPaths[node.kind] ? buildSvgIcon(nodeIconPaths[node.kind]) : undefined,
      captions: [
        {
          value: node.label,
          styles: ['bold']
        }
      ]
    };
  });
  const rels: NvlRelationship[] = graph.edges.map((edge, index) => {
    const highlighted = Boolean(selectedNodeId) && (edge.source === selectedNodeId || edge.target === selectedNodeId);
    const disabled = Boolean(selectedNodeId) && edge.source !== selectedNodeId && edge.target !== selectedNodeId;
    const relationshipType = edge.type ?? edge.label;
    const readableCaption = relationshipCaption(relationshipType);

    return {
      id: `${edge.source}->${edge.target}:${relationshipType}:${index}`,
      from: edge.source,
      to: edge.target,
      type: relationshipType,
      caption: readableCaption,
      captions: [
        {
          value: readableCaption,
          styles: ['bold']
        }
      ],
      captionSize: highlighted ? 12 : 11,
      captionAlign: 'top',
      color: highlighted ? '#f79767' : disabled ? '#6f7d8f' : '#8f9bad',
      width: highlighted ? 3.4 : disabled ? 1 : 2,
      disabled
    };
  });
  return { nodes, rels };
}
