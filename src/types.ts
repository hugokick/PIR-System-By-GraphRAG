export type ExhibitStatus = '概念方案' | '深化设计' | '制作中' | '已落地' | '维护中';
export type ReviewStatus = '草稿' | '待审核' | '已审核' | '已退回';

export type MediaAsset = {
  id: string;
  type: 'image' | 'video' | 'drawing' | 'quote' | 'document';
  name: string;
  url: string;
  note?: string;
};

export type DocumentAsset = {
  id: string;
  name: string;
  fileType: string;
  url: string;
  sourceNote?: string;
  chunks?: {
    id: string;
    text: string;
    sequence: number;
  }[];
};

export type Exhibit = {
  id: string;
  name: string;
  category: string;
  theme: string;
  venueType: string;
  budgetMin: number;
  budgetMax: number;
  materials: string[];
  dimensions: string;
  interactions: string[];
  supplier: string;
  projectYear: number;
  owner: string;
  status: ExhibitStatus;
  reviewStatus: ReviewStatus;
  description: string;
  tags: string[];
  media: MediaAsset[];
  documents: DocumentAsset[];
  relatedProjectIds: string[];
  relatedExhibitIds: string[];
};

export type ExhibitFilters = {
  keyword?: string;
  category?: string;
  theme?: string;
  tag?: string;
  projectId?: string;
  owner?: string;
  supplier?: string;
  venueType?: string;
  budgetRange?: [number, number];
  material?: string;
  interaction?: string;
  status?: ExhibitStatus | '';
  reviewStatus?: ReviewStatus | '';
};

export type DashboardStats = {
  total: number;
  landed: number;
  pendingReview: number;
  rejectedReview: number;
  avgBudget: number;
  categories: Array<[string, number]>;
  budgetBands: Array<[string, number]>;
  themes: Array<[string, number]>;
  reviewStatuses: Array<[string, number]>;
};

export type SearchResult = {
  item: Exhibit;
  score: number;
  matchedSignals: string[];
};

export type SearchResults = {
  total: number;
  items: SearchResult[];
};

export type GraphNode = {
  id: string;
  label: string;
  kind: string;
};

export type GraphEdge = {
  source: string;
  target: string;
  label: string;
  type?: string;
};

export type GraphRagCitation = {
  sourceId: string;
  sourceType: string;
  title: string;
  snippet: string;
};

export type GraphRagHit = {
  exhibit: Exhibit;
  score: number;
  reasons: string[];
  citations: GraphRagCitation[];
  graph: {
    nodes: GraphNode[];
    edges: GraphEdge[];
  };
};

export type GraphRagAnswer = {
  query: string;
  answer: string;
  citations: GraphRagCitation[];
  items: GraphRagHit[];
};

export type RelationRecommendation = {
  relationType: string;
  sourceId: string;
  targetId: string;
  targetLabel: string;
  confidence: number;
  reasons: string[];
  evidenceRefs: string[];
  alreadyExists: boolean;
};

export type RelationRecommendationResult = {
  targetExhibitId: string | null;
  warnings: string[];
  recommendations: RelationRecommendation[];
};

export type SuggestedFieldSource = {
  documentId: string;
  fieldName: string;
  chunkId: string | null;
  sourceLocator: string | null;
  snippet: string;
  reason: string;
};

export type DocumentExtractionSuggestion = {
  documentId: string;
  fileName: string;
  fileType: string;
  sourceNote?: string;
  exhibitName?: string;
  category?: string;
  theme?: string;
  venueType?: string;
  budgetMin?: number;
  budgetMax?: number;
  materials: string[];
  interactions: string[];
  supplier?: string;
  owner?: string;
  projectYear?: number;
  tags: string[];
  summary: string;
  confidence: number;
  fieldSources: Record<string, SuggestedFieldSource[]>;
};

export type AuditLogEntry = {
  id: string;
  actorRole: string;
  action: string;
  resourceType: string;
  resourceId: string;
  summary: string;
  createdAt: string;
};

export type AuthUser = {
  username: string;
  role: 'admin' | 'editor' | 'viewer';
  displayName: string;
};

export type UserSession = {
  accessToken: string;
  tokenType: 'bearer';
  user: AuthUser;
};
