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
  disabledItemColor: '#536274',
  disabledItemFontColor: '#c4ccd7',
  minimapViewportBoxColor: '#68bdf6'
};

const nodeBaseSizes: Record<string, number> = {
  exhibit: 22,
  project: 18,
  owner: 18,
  material: 18,
  supplier: 18,
  theme: 18,
  interaction: 18,
  document: 16
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
  has_interaction: '交互方式',
  has_theme: '主题',
  owned_by: '业主',
  similar_to: '相似展项',
  supplied_by: '供应商',
  supports_theme: '支持主题',
  uses_material: '使用材料'
};

const nodeKindCaptions: Record<string, string> = {
  exhibit: '展项',
  project: '项目',
  owner: '业主',
  supplier: '供应商',
  theme: '主题',
  material: '材料',
  interaction: '交互方式',
  document: '资料文档',
  media_asset: '媒体资产'
};

function buildSvgIcon(path: string) {
  return `data:image/svg+xml;utf8,${encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">${path}</svg>`
  )}`;
}

type HighlightDepth = 1 | 2;

type BuildNvlGraphDataOptions = {
  includeInitialPositions?: boolean;
};

function graphNodeSize(kind: string, selected: boolean) {
  const baseSize = nodeBaseSizes[kind] ?? 24;
  return selected ? baseSize + 8 : baseSize;
}

function relationshipCaption(value: string) {
  const key = value.trim().toLowerCase();
  return relationshipCaptions[key] ?? value;
}

export function nodeKindCaption(kind: string) {
  return nodeKindCaptions[kind] ?? kind;
}

function duplicateNodeLabels(nodes: GraphNode[]) {
  const counts = new Map<string, number>();
  nodes.forEach((node) => {
    const key = node.label.trim();
    counts.set(key, (counts.get(key) ?? 0) + 1);
  });
  return counts;
}

function readableNodeCaption(node: GraphNode, labelCounts: Map<string, number>) {
  const label = node.label.trim() || node.id;
  if ((labelCounts.get(label) ?? 0) <= 1) return label;
  return `${label} · ${nodeKindCaption(node.kind)}`;
}

function initialNodePosition(index: number, total: number) {
  if (total <= 1) return { x: 0, y: 0 };
  const radius = Math.min(520, 180 + total * 7);
  const angle = -Math.PI / 2 + (2 * Math.PI * index) / total;
  return {
    x: Math.round(Math.cos(angle) * radius),
    y: Math.round(Math.sin(angle) * radius)
  };
}

function normalizeSelectedNodeIds(selectedNodeIds: string[] | string | null) {
  if (!selectedNodeIds) return [];
  return Array.isArray(selectedNodeIds) ? selectedNodeIds : [selectedNodeIds];
}

export function collectGraphNeighborIds(
  graph: { nodes: GraphNode[]; edges: GraphEdge[] },
  selectedNodeIds: string[] | string | null,
  depth: HighlightDepth = 1
) {
  const ids = new Set<string>();
  const seeds = normalizeSelectedNodeIds(selectedNodeIds);
  if (seeds.length === 0) return ids;

  const adjacency = new Map<string, Set<string>>();
  const connect = (source: string, target: string) => {
    if (!adjacency.has(source)) adjacency.set(source, new Set());
    adjacency.get(source)?.add(target);
  };
  graph.edges.forEach((edge) => {
    connect(edge.source, edge.target);
    connect(edge.target, edge.source);
  });

  let frontier = new Set(seeds);
  seeds.forEach((id) => ids.add(id));
  for (let distance = 0; distance < depth; distance += 1) {
    const next = new Set<string>();
    frontier.forEach((id) => {
      adjacency.get(id)?.forEach((neighborId) => {
        if (!ids.has(neighborId)) next.add(neighborId);
        ids.add(neighborId);
      });
    });
    frontier = next;
  }

  return ids;
}

export function buildNvlGraphData(
  graph: { nodes: GraphNode[]; edges: GraphEdge[] },
  selectedNodeIds: string[] | string | null,
  highlightDepth: HighlightDepth,
  nodeColors: Record<string, string>,
  options: BuildNvlGraphDataOptions = {}
) {
  const selectedIds = new Set(normalizeSelectedNodeIds(selectedNodeIds));
  const neighborIds = collectGraphNeighborIds(graph, [...selectedIds], highlightDepth);
  const hasSelection = selectedIds.size > 0;
  const labelCounts = duplicateNodeLabels(graph.nodes);
  const nodes: NvlNode[] = graph.nodes.map((node, index) => {
    const position = initialNodePosition(index, graph.nodes.length);
    const selected = selectedIds.has(node.id);
    const disabled = hasSelection && !neighborIds.has(node.id);
    const displayCaption = readableNodeCaption(node, labelCounts);

    return {
      id: node.id,
      caption: displayCaption,
      color: nodeColors[node.kind] ?? defaultNodeColor,
      size: graphNodeSize(node.kind, selected),
      pinned: true,
      selected,
      activated: selected,
      disabled,
      captionSize: selected ? 11 : 10,
      captionAlign: 'bottom',
      ...(options.includeInitialPositions === false ? {} : { x: position.x, y: position.y }),
      icon: nodeIconPaths[node.kind] ? buildSvgIcon(nodeIconPaths[node.kind]) : undefined,
      captions: [
        {
          value: displayCaption,
          styles: ['bold']
        },
        {
          value: nodeKindCaption(node.kind)
        }
      ]
    };
  });
  const rels: NvlRelationship[] = graph.edges.map((edge, index) => {
    const highlighted = hasSelection && neighborIds.has(edge.source) && neighborIds.has(edge.target);
    const disabled = hasSelection && !highlighted;
    const relationshipType = edge.type ?? edge.label;
    const readableCaption = relationshipCaption(relationshipType);

    return {
      id: `${edge.source}->${edge.target}:${relationshipType}:${index}`,
      from: edge.source,
      to: edge.target,
      type: relationshipType,
      caption: readableCaption,
      captionSize: highlighted ? 9 : 8,
      captionAlign: 'center',
      color: highlighted ? '#f79767' : disabled ? '#7d8798' : '#8f9bad',
      width: highlighted ? 3.4 : disabled ? 1.4 : 2,
      disabled
    };
  });
  return { nodes, rels };
}
