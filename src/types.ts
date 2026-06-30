export type ExhibitStatus = '概念方案' | '深化设计' | '制作中' | '已落地' | '维护中';

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
  venueType?: string;
  budgetRange?: [number, number];
  material?: string;
  interaction?: string;
  status?: ExhibitStatus | '';
};

export type SearchResult = {
  item: Exhibit;
  score: number;
  matchedSignals: string[];
};

export type GraphNode = {
  id: string;
  label: string;
  kind: 'exhibit' | 'project' | 'owner' | 'material' | 'supplier' | 'theme';
};

export type GraphEdge = {
  source: string;
  target: string;
  label: string;
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
