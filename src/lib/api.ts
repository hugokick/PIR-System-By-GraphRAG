import type { Exhibit, ExhibitFilters, GraphEdge, GraphNode, MediaAsset } from '../types';

export const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000';

type ApiEntityRef = {
  id: string;
  name: string;
};

type ApiMediaAsset = {
  id: string;
  type: MediaAsset['type'];
  name: string;
  url: string;
  note?: string | null;
};

type ApiDocumentAsset = {
  id: string;
  name: string;
  file_type: string;
  url: string;
  source_note?: string | null;
};

export type ApiExhibit = {
  id: string;
  name: string;
  category: string;
  theme: ApiEntityRef;
  venue_type: string;
  budget_min: number;
  budget_max: number;
  materials: ApiEntityRef[];
  dimensions: string;
  interactions: ApiEntityRef[];
  supplier: ApiEntityRef;
  project: ApiEntityRef;
  owner: ApiEntityRef;
  project_year: number;
  status: Exhibit['status'];
  description: string;
  tags: string[];
  media_assets: ApiMediaAsset[];
  documents: ApiDocumentAsset[];
  related_exhibit_ids: string[];
};

export type ApiExhibitListResponse = {
  total: number;
  items: ApiExhibit[];
};

type ApiGraphNode = {
  id: string;
  label: string;
  type: string;
};

type ApiGraphEdge = {
  source: string;
  target: string;
  label: string;
  type: string;
};

export type ApiGraphResponse = {
  nodes: ApiGraphNode[];
  edges: ApiGraphEdge[];
};

export function mapApiExhibit(item: ApiExhibit): Exhibit {
  return {
    id: item.id,
    name: item.name,
    category: item.category,
    theme: item.theme.name,
    venueType: item.venue_type,
    budgetMin: item.budget_min,
    budgetMax: item.budget_max,
    materials: item.materials.map((material) => material.name),
    dimensions: item.dimensions,
    interactions: item.interactions.map((interaction) => interaction.name),
    supplier: item.supplier.name,
    projectYear: item.project_year,
    owner: item.owner.name,
    status: item.status,
    description: item.description,
    tags: item.tags,
    media: item.media_assets.map((asset) => ({
      id: asset.id,
      type: asset.type,
      name: asset.name,
      url: asset.url,
      note: asset.note ?? undefined
    })),
    relatedProjectIds: [item.project.id],
    relatedExhibitIds: item.related_exhibit_ids
  };
}

export function buildExhibitQuery(filters: ExhibitFilters) {
  const query = new URLSearchParams();
  if (filters.keyword) query.set('keyword', filters.keyword);
  if (filters.venueType) query.set('venue_type', filters.venueType);
  if (filters.category) query.set('category', filters.category);
  if (filters.theme) query.set('theme', filters.theme);
  if (filters.material) query.set('material', filters.material);
  if (filters.interaction) query.set('interaction', filters.interaction);
  if (filters.status) query.set('status', filters.status);
  if (filters.budgetRange) {
    query.set('budget_min', String(filters.budgetRange[0]));
    query.set('budget_max', String(filters.budgetRange[1]));
  }
  return query;
}

export function mapApiGraph(payload: ApiGraphResponse): { nodes: GraphNode[]; edges: GraphEdge[] } {
  return {
    nodes: payload.nodes.map((node) => ({
      id: node.id,
      label: node.label,
      kind: node.type as GraphNode['kind']
    })),
    edges: payload.edges.map((edge) => ({
      source: edge.source,
      target: edge.target,
      label: edge.label
    }))
  };
}

async function requestJson<T>(path: string): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`);
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

export async function fetchExhibits(filters: ExhibitFilters = {}): Promise<Exhibit[]> {
  const query = buildExhibitQuery(filters);
  const suffix = query.size > 0 ? `?${query.toString()}` : '';
  const payload = await requestJson<ApiExhibitListResponse>(`/api/exhibits${suffix}`);
  return payload.items.map(mapApiExhibit);
}

export async function fetchExhibitGraph(exhibitId: string) {
  const payload = await requestJson<ApiGraphResponse>(`/api/exhibits/${encodeURIComponent(exhibitId)}/graph`);
  return mapApiGraph(payload);
}
