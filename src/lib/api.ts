import type { AuditLogEntry, Exhibit, ExhibitFilters, GraphEdge, GraphNode, GraphRagAnswer, MediaAsset, SearchResult, UserSession } from '../types';

export const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000';
export const importTemplateUrl = `${apiBaseUrl}/api/exhibits/import-template`;

export type UserRole = 'admin' | 'editor' | 'viewer';

let activeRole: UserRole = 'admin';
let activeSession: UserSession | null = null;

export function setApiRole(role: UserRole) {
  activeRole = role;
}

export function setApiSession(session: UserSession | null) {
  activeSession = session;
  if (session) {
    activeRole = session.user.role;
  }
}

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
  chunks?: {
    id: string;
    text: string;
    sequence: number;
  }[];
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

type ApiGraphRagCitation = {
  source_id: string;
  source_type: string;
  title: string;
  snippet: string;
};

type ApiGraphRagHit = {
  exhibit: ApiExhibit;
  score: number;
  reasons: string[];
  citations: ApiGraphRagCitation[];
  graph: ApiGraphResponse;
};

type ApiGraphRagAnswerResponse = {
  query: string;
  answer: string;
  citations: ApiGraphRagCitation[];
  items: ApiGraphRagHit[];
};

type ApiHybridSearchHit = {
  exhibit: ApiExhibit;
  score: number;
  reasons: string[];
};

type ApiHybridSearchResponse = {
  query: string;
  total: number;
  items: ApiHybridSearchHit[];
};

type ApiExhibitImportError = {
  row: number;
  field: string;
  message: string;
};

type ApiExhibitImportResponse = {
  total_rows: number;
  valid_rows: number;
  imported_count: number;
  errors: ApiExhibitImportError[];
  items: ApiExhibit[];
};

type ApiAuditLogEntry = {
  id: string;
  actor_role: string;
  action: string;
  resource_type: string;
  resource_id: string;
  summary: string;
  created_at: string;
};

type ApiAuditLogListResponse = {
  total: number;
  items: ApiAuditLogEntry[];
};

type ApiAuthLoginResponse = {
  access_token: string;
  token_type: 'bearer';
  user: {
    username: string;
    role: UserRole;
    display_name: string;
  };
};

export type ExhibitImportResult = {
  totalRows: number;
  validRows: number;
  importedCount: number;
  errors: ApiExhibitImportError[];
  items: Exhibit[];
};

const slugMap: Record<string, string> = {
  电磁学: 'dianci-xue',
  亚克力: 'yake-li',
  动手实验: 'dongshou-shiyan',
  启思互动工坊: 'qisi-hudong-gongfang',
  青禾儿童科技馆: 'qinghe-ertong-kejiguan'
};

function slugify(value: string) {
  return (
    slugMap[value] ??
    value
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9\u4e00-\u9fa5]+/g, '-')
      .replace(/^-+|-+$/g, '') ??
    `entity-${Date.now()}`
  );
}

function entityRef(name: string): ApiEntityRef {
  return {
    id: slugify(name),
    name
  };
}

function resolveBackendFileUrl(url: string) {
  if (!url.startsWith('/api/files/')) {
    return url;
  }
  return `${apiBaseUrl.replace(/\/$/, '')}${url}`;
}

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
      url: resolveBackendFileUrl(asset.url),
      note: asset.note ?? undefined
    })),
    documents: (item.documents ?? []).map(mapApiDocument),
    relatedProjectIds: [item.project.id],
    relatedExhibitIds: item.related_exhibit_ids
  };
}

function mapApiDocument(document: ApiDocumentAsset) {
  const mapped = {
    id: document.id,
    name: document.name,
    fileType: document.file_type,
    url: resolveBackendFileUrl(document.url),
    sourceNote: document.source_note ?? undefined
  };
  if (!document.chunks?.length) {
    return mapped;
  }
  return {
    ...mapped,
    chunks: document.chunks
  };
}

export function mapExhibitToApiPayload(item: Exhibit): ApiExhibit {
  const projectId = item.relatedProjectIds[0] || `${item.id}-project`;

  return {
    id: item.id,
    name: item.name,
    category: item.category,
    theme: entityRef(item.theme),
    venue_type: item.venueType,
    budget_min: item.budgetMin,
    budget_max: item.budgetMax,
    materials: item.materials.map(entityRef),
    dimensions: item.dimensions,
    interactions: item.interactions.map(entityRef),
    supplier: entityRef(item.supplier),
    project: {
      id: projectId,
      name: projectId
    },
    owner: entityRef(item.owner),
    project_year: item.projectYear,
    status: item.status,
    description: item.description,
    tags: item.tags,
    media_assets: item.media.map((asset) => ({
      id: asset.id,
      type: asset.type,
      name: asset.name,
      url: asset.url,
      note: asset.note ?? null
    })),
    documents: (item.documents ?? []).map((document) => ({
      id: document.id,
      name: document.name,
      file_type: document.fileType,
      url: document.url,
      source_note: document.sourceNote ?? null,
      chunks: document.chunks ?? []
    })),
    related_exhibit_ids: item.relatedExhibitIds
  };
}

export function buildExhibitQuery(filters: ExhibitFilters) {
  const query = new URLSearchParams();
  if (filters.keyword) query.set('keyword', filters.keyword);
  if (filters.venueType) query.set('venue_type', filters.venueType);
  if (filters.category) query.set('category', filters.category);
  if (filters.theme) query.set('theme', filters.theme);
  if (filters.projectId) query.set('project_id', filters.projectId);
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
      label: edge.label,
      type: edge.type
    }))
  };
}

function mapApiGraphRagCitation(citation: ApiGraphRagCitation) {
  return {
    sourceId: citation.source_id,
    sourceType: citation.source_type,
    title: citation.title,
    snippet: citation.snippet
  };
}

function mapApiGraphRagAnswer(payload: ApiGraphRagAnswerResponse): GraphRagAnswer {
  return {
    query: payload.query,
    answer: payload.answer,
    citations: payload.citations.map(mapApiGraphRagCitation),
    items: payload.items.map((item) => ({
      exhibit: mapApiExhibit(item.exhibit),
      score: item.score,
      reasons: item.reasons,
      citations: item.citations.map(mapApiGraphRagCitation),
      graph: mapApiGraph(item.graph)
    }))
  };
}

function mapApiAuditLogEntry(entry: ApiAuditLogEntry): AuditLogEntry {
  return {
    id: entry.id,
    actorRole: entry.actor_role,
    action: entry.action,
    resourceType: entry.resource_type,
    resourceId: entry.resource_id,
    summary: entry.summary,
    createdAt: entry.created_at
  };
}

function mapApiAuthSession(payload: ApiAuthLoginResponse): UserSession {
  return {
    accessToken: payload.access_token,
    tokenType: payload.token_type,
    user: {
      username: payload.user.username,
      role: payload.user.role,
      displayName: payload.user.display_name
    }
  };
}

function authHeaders(): Record<string, string> {
  if (activeSession) {
    return {
      Authorization: `Bearer ${activeSession.accessToken}`
    };
  }
  return {
    'X-User-Role': activeRole
  };
}

async function requestJson<T>(path: string): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`);
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

async function sendJson<T>(path: string, init: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
      ...(init.headers ?? {})
    }
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

export async function login(username: string, password: string): Promise<UserSession> {
  const response = await fetch(`${apiBaseUrl}/api/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ username, password })
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${response.statusText}`);
  }
  const session = mapApiAuthSession((await response.json()) as ApiAuthLoginResponse);
  setApiSession(session);
  return session;
}

export async function fetchExhibits(filters: ExhibitFilters = {}): Promise<Exhibit[]> {
  const query = buildExhibitQuery(filters);
  const suffix = query.size > 0 ? `?${query.toString()}` : '';
  const payload = await requestJson<ApiExhibitListResponse>(`/api/exhibits${suffix}`);
  return payload.items.map(mapApiExhibit);
}

export async function createExhibit(item: Exhibit): Promise<Exhibit> {
  const payload = await sendJson<ApiExhibit>('/api/exhibits', {
    method: 'POST',
    body: JSON.stringify(mapExhibitToApiPayload(item))
  });
  return mapApiExhibit(payload);
}

export async function updateExhibit(exhibitId: string, item: Exhibit): Promise<Exhibit> {
  const payload = await sendJson<ApiExhibit>(`/api/exhibits/${encodeURIComponent(exhibitId)}`, {
    method: 'PUT',
    body: JSON.stringify(mapExhibitToApiPayload(item))
  });
  return mapApiExhibit(payload);
}

export async function deleteExhibit(exhibitId: string): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/api/exhibits/${encodeURIComponent(exhibitId)}`, {
    method: 'DELETE',
    headers: authHeaders()
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${response.statusText}`);
  }
}

export async function uploadExhibitAsset(
  exhibitId: string,
  file: File,
  assetKind: 'media' | 'document' = 'media',
  note = ''
): Promise<Exhibit> {
  const form = new FormData();
  form.set('asset_kind', assetKind);
  if (note) form.set('note', note);
  form.set('file', file);

  const response = await fetch(`${apiBaseUrl}/api/exhibits/${encodeURIComponent(exhibitId)}/assets`, {
    method: 'POST',
    headers: authHeaders(),
    body: form
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${response.statusText}`);
  }
  const payload = (await response.json()) as ApiExhibit;
  return mapApiExhibit(payload);
}

export async function importExhibits(file: File, commit = true): Promise<ExhibitImportResult> {
  const form = new FormData();
  form.set('commit', String(commit));
  form.set('file', file);

  const response = await fetch(`${apiBaseUrl}/api/exhibits/import`, {
    method: 'POST',
    headers: authHeaders(),
    body: form
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${response.statusText}`);
  }
  const payload = (await response.json()) as ApiExhibitImportResponse;
  return {
    totalRows: payload.total_rows,
    validRows: payload.valid_rows,
    importedCount: payload.imported_count,
    errors: payload.errors,
    items: payload.items.map(mapApiExhibit)
  };
}

export async function fetchAuditLogs(limit = 8): Promise<AuditLogEntry[]> {
  const response = await fetch(`${apiBaseUrl}/api/admin/audit-logs?limit=${encodeURIComponent(String(limit))}`, {
    headers: authHeaders()
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${response.statusText}`);
  }
  const payload = (await response.json()) as ApiAuditLogListResponse;
  return payload.items.map(mapApiAuditLogEntry);
}

export async function fetchExhibitGraph(exhibitId: string) {
  const payload = await requestJson<ApiGraphResponse>(`/api/exhibits/${encodeURIComponent(exhibitId)}/graph`);
  return mapApiGraph(payload);
}

export async function fetchDemoGraph() {
  const payload = await requestJson<ApiGraphResponse>('/api/neo4j-demo/graph');
  return mapApiGraph(payload);
}

export async function askGraphRag(query: string, topK = 3): Promise<GraphRagAnswer> {
  const payload = await sendJson<ApiGraphRagAnswerResponse>('/api/graphrag/answer', {
    method: 'POST',
    body: JSON.stringify({ query, top_k: topK })
  });
  return mapApiGraphRagAnswer(payload);
}

export async function hybridSearchExhibits(
  query: string,
  filters: ExhibitFilters = {},
  limit = 4
): Promise<SearchResult[]> {
  const payload = await sendJson<ApiHybridSearchResponse>('/api/search/hybrid', {
    method: 'POST',
    body: JSON.stringify({
      query,
      limit,
      filters: mapHybridSearchFilters(filters)
    })
  });
  return payload.items.map((item) => ({
    item: mapApiExhibit(item.exhibit),
    score: item.score,
    matchedSignals: item.reasons
  }));
}

function mapHybridSearchFilters(filters: ExhibitFilters) {
  const payload: Record<string, string | number> = {};
  if (filters.category) payload.category = filters.category;
  if (filters.theme) payload.theme = filters.theme;
  if (filters.projectId) payload.project_id = filters.projectId;
  if (filters.material) payload.material = filters.material;
  if (filters.interaction) payload.interaction = filters.interaction;
  if (filters.venueType) payload.venue_type = filters.venueType;
  if (filters.status) payload.status = filters.status;
  if (filters.budgetRange) {
    payload.budget_min = filters.budgetRange[0];
    payload.budget_max = filters.budgetRange[1];
  }
  return payload;
}
