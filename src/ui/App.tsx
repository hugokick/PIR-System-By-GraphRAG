import { FormEvent, Suspense, SyntheticEvent, lazy, useEffect, useMemo, useState } from 'react';
import {
  BarChart3,
  Check,
  Database,
  Download,
  FilePlus2,
  FileText,
  Filter,
  GitBranch,
  ImageIcon,
  MessageSquareText,
  Pencil,
  RotateCcw,
  Search,
  Sparkles,
  Trash2,
  Upload
} from 'lucide-react';
import { buildGraph, graphStats } from '../lib/graph';
import {
  askGraphRag,
  createExhibit,
  deleteExhibit,
  deleteExhibitAsset,
  exportExhibitsCsv,
  exportAuditLogsCsv,
  fetchAuditLogs,
  fetchDashboardSummary,
  fetchDemoGraph,
  fetchDocumentExtractionSuggestions,
  fetchExhibitGraph,
  fetchExhibitRelationRecommendations,
  fetchExhibits,
  fetchSystemStatus,
  hybridSearchExhibits,
  importTemplateUrl,
  importExhibits,
  login,
  setApiRole,
  setApiSession,
  updateExhibit,
  updateExhibitRelatedExhibits,
  updateExhibitReviewStatus,
  uploadExhibitAsset,
  validateSession,
  type ExhibitImportResult,
  type UserRole
} from '../lib/api';
import { filterExhibits, formatBudget, semanticSearch } from '../lib/search';
import { loadExhibits, resetExhibits, saveExhibits } from '../lib/storage';
import type {
  AuditLogEntry,
  DashboardStats,
  DocumentAsset,
  DocumentExtractionSuggestion,
  Exhibit,
  ExhibitFilters,
  ExhibitStatus,
  GraphEdge,
  GraphNode,
  GraphRagAnswer,
  GraphRagCitation,
  MediaAsset,
  RelationRecommendation,
  SuggestedFieldSource,
  ReviewStatus,
  SearchResults,
  SystemStatus,
  UserSession
} from '../types';
import { AssetPreviewModal, type PreviewAsset } from './AssetPreviewModal';
import { CitationList } from './CitationList';
import { MediaThumbGrid } from './MediaThumbGrid';
import { nodeKindCaption } from './nvlGraphData';

const statuses: ExhibitStatus[] = ['概念方案', '深化设计', '制作中', '已落地', '维护中'];
const reviewStatuses: ReviewStatus[] = ['草稿', '待审核', '已审核', '已退回'];
const emptyFilters: ExhibitFilters = {
  keyword: '',
  category: '',
  theme: '',
  tag: '',
  projectId: '',
  owner: '',
  supplier: '',
  venueType: '',
  material: '',
  interaction: '',
  status: '',
  reviewStatus: ''
};

const documentExtensions = new Set([
  'pdf',
  'doc',
  'docx',
  'xls',
  'xlsx',
  'csv',
  'tsv',
  'ppt',
  'pptx',
  'txt',
  'md',
  'markdown',
  'json',
  'log'
]);
const uploadAcceptTypes = [
  'image/*',
  'video/*',
  '.pdf',
  '.doc',
  '.docx',
  '.xls',
  '.xlsx',
  '.csv',
  '.tsv',
  '.ppt',
  '.pptx',
  '.txt',
  '.md',
  '.markdown',
  '.json',
  '.log'
].join(',');
const userRoles: UserRole[] = ['admin', 'editor', 'viewer'];
const sessionStorageKey = 'pir-system-session';
const requireLoginForWrites = import.meta.env.VITE_REQUIRE_LOGIN === 'true';
const auditActionLabels: Record<string, string> = {
  create_exhibit: '新增档案',
  update_exhibit: '编辑档案',
  delete_exhibit: '删除档案',
  update_review_status: '更新审核',
  upload_document: '上传资料',
  upload_media: '上传媒体',
  delete_document: '删除资料',
  delete_media: '删除媒体',
  update_exhibit_relations: '更新相似关系',
  import_create_exhibit: '导入新增',
  import_update_exhibit: '导入更新',
  import_exhibits: '批量导入',
  import_batch: '批量导入'
};
const auditActionOptions = Object.entries(auditActionLabels);
const systemStatusLabels: Record<string, string> = {
  postgres: 'PostgreSQL',
  memory: '内存演示库',
  local: '本地文件',
  s3: '对象存储',
  ok: '正常'
};
const importErrorFieldLabels: Record<string, string> = {
  id: '展项编号',
  name: '展项名称',
  category: '类别',
  theme: '主题',
  venue_type: '适用场馆',
  budget_min: '造价下限',
  budget_max: '造价上限',
  materials: '材料',
  dimensions: '尺寸',
  interactions: '交互方式',
  supplier: '供应商',
  project_id: '项目编号',
  project_name: '项目名称',
  owner: '业主',
  project_year: '项目年份',
  status: '状态',
  description: '展项说明',
  tags: '标签',
  related_exhibit_ids: '相似展项',
  file: '文件内容'
};

function importErrorFieldLabel(field: string) {
  return importErrorFieldLabels[field] ?? field;
}

function importErrorRowLabel(row: number, field: string) {
  return field === 'file' ? '文件' : `第 ${row} 行`;
}

function importErrorMessage(message: string) {
  if (message === 'Required') return '必填字段不能为空';
  if (message === 'Must be an integer') return '必须填写整数';
  if (message === 'Must be greater than or equal to budget_min') return '必须大于或等于造价下限';
  if (message === 'No import rows found') return '没有找到可导入的数据行';
  if (message.startsWith('Duplicate exhibit id in import file: ')) {
    return `导入文件中存在重复展项编号：${message.replace('Duplicate exhibit id in import file: ', '')}`;
  }
  if (message.startsWith('Unknown or self-referencing exhibit id: ')) {
    return `相似展项编号不存在或引用了当前展项：${message.replace('Unknown or self-referencing exhibit id: ', '')}`;
  }
  return message;
}

function auditActionLabel(action: string) {
  return auditActionLabels[action] ?? action;
}

function systemStatusLabel(value: string) {
  return systemStatusLabels[value] ?? value;
}

function formatTokenTtl(seconds: number) {
  if (seconds < 60) return `${seconds} 秒`;
  const hours = seconds / 3600;
  if (Number.isInteger(hours)) return `${hours} 小时`;
  return `${Math.round(seconds / 60)} 分钟`;
}

function formatAuditTime(value?: string) {
  if (!value) return '时间未知';
  return value.replace('T', ' ').replace(/\.\d+/, '').replace(/([+-]\d{2}:\d{2}|Z)$/, '').slice(0, 16);
}

function readStoredSession(): UserSession | null {
  try {
    const raw = globalThis.localStorage?.getItem(sessionStorageKey);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as UserSession;
    if (
      parsed?.tokenType === 'bearer' &&
      typeof parsed.accessToken === 'string' &&
      parsed.accessToken &&
      parsed.user &&
      userRoles.includes(parsed.user.role)
    ) {
      return parsed;
    }
  } catch {
    // Ignore stale or unavailable storage and continue in demo role mode.
  }
  return null;
}

function storeSession(session: UserSession) {
  try {
    globalThis.localStorage?.setItem(sessionStorageKey, JSON.stringify(session));
  } catch {
    // Storage can be unavailable in restricted test/browser contexts.
  }
}

function clearStoredSession() {
  try {
    globalThis.localStorage?.removeItem(sessionStorageKey);
  } catch {
    // Storage can be unavailable in restricted test/browser contexts.
  }
}

const graphNodeColors: Record<string, string> = {
  exhibit: '#68bdf6',
  project: '#ffd86e',
  owner: '#6dce9e',
  material: '#f79767',
  supplier: '#de9bf9',
  theme: '#fb95af',
  interaction: '#ff928c',
  media_asset: '#7fb5ff',
  document: '#a5abb6'
};

const LazyNvlGraphView = lazy(() => import('./NvlGraphView'));

const fallbackImage =
  'data:image/svg+xml;utf8,' +
  encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 600"><rect width="900" height="600" fill="#dfe9e4"/><path d="M90 430h720v60H90z" fill="#0f8b78"/><circle cx="250" cy="250" r="90" fill="#f2b84b"/><rect x="430" y="170" width="230" height="170" rx="24" fill="#4361a8"/><text x="450" y="510" font-family="Arial" font-size="42" fill="#203b39">EXHIBIT ATLAS</text></svg>'
  );

function imageFallback(event: SyntheticEvent<HTMLImageElement>) {
  event.currentTarget.src = fallbackImage;
}

function uniqueValues(items: Exhibit[], getter: (item: Exhibit) => string | string[]) {
  return [...new Set(items.flatMap((item) => getter(item)))].filter(Boolean).sort();
}

function fileExtension(fileName: string) {
  return fileName.split('.').pop()?.toLowerCase() ?? 'file';
}

function assetKindForFile(file: File): 'media' | 'document' {
  if (file.type.startsWith('image/') || file.type.startsWith('video/')) return 'media';
  return documentExtensions.has(fileExtension(file.name)) ? 'document' : 'media';
}

function downloadUrl(url: string) {
  if (!url.includes('/api/files/')) return url;
  const nextUrl = new URL(url, globalThis.location?.origin ?? 'http://localhost');
  nextUrl.searchParams.set('download', '1');
  return nextUrl.toString();
}

function formatSuggestedBudget(min?: number, max?: number) {
  if (min !== undefined && max !== undefined) return `${Math.round(min / 10000)}-${Math.round(max / 10000)} 万`;
  if (min !== undefined) return `${Math.round(min / 10000)} 万以上`;
  if (max !== undefined) return `${Math.round(max / 10000)} 万以内`;
  return '';
}

function documentSuggestionFields(suggestion: DocumentExtractionSuggestion) {
  return [
    ['展项名称', suggestion.exhibitName],
    ['类别', suggestion.category],
    ['主题', suggestion.theme],
    ['适用场馆', suggestion.venueType],
    ['预算', formatSuggestedBudget(suggestion.budgetMin, suggestion.budgetMax)],
    ['材料', suggestion.materials.join('、')],
    ['互动方式', suggestion.interactions.join('、')],
    ['供应商', suggestion.supplier],
    ['业主', suggestion.owner],
    ['项目年份', suggestion.projectYear ? String(suggestion.projectYear) : undefined],
    ['标签', suggestion.tags.join('、')]
  ].filter((item): item is [string, string] => Boolean(item[1]));
}

function flattenSuggestionSources(suggestion: DocumentExtractionSuggestion): SuggestedFieldSource[] {
  return Object.values(suggestion.fieldSources).flat().slice(0, 3);
}

function mergeImportedExhibits(currentItems: Exhibit[], importedItems: Exhibit[]) {
  const importedIds = new Set(importedItems.map((item) => item.id));
  return [...importedItems, ...currentItems.filter((item) => !importedIds.has(item.id))];
}

function makeExhibitFromForm(form: HTMLFormElement, existingItem?: Exhibit): Exhibit {
  const data = new FormData(form);
  const list = (key: string) =>
    String(data.get(key) ?? '')
      .split(/[，,、]/)
      .map((item) => item.trim())
      .filter(Boolean);

  return {
    id: existingItem?.id ?? `exhibit-${Date.now()}`,
    name: String(data.get('name') ?? '').trim(),
    category: String(data.get('category') ?? '').trim(),
    theme: String(data.get('theme') ?? '').trim(),
    venueType: String(data.get('venueType') ?? '').trim(),
    budgetMin: Number(data.get('budgetMin') ?? 0),
    budgetMax: Number(data.get('budgetMax') ?? 0),
    materials: list('materials'),
    dimensions: String(data.get('dimensions') ?? '').trim(),
    interactions: list('interactions'),
    supplier: String(data.get('supplier') ?? '').trim(),
    projectName: String(data.get('projectName') ?? '').trim(),
    projectYear: Number(data.get('projectYear') ?? new Date().getFullYear()),
    owner: String(data.get('owner') ?? '').trim(),
    status: String(data.get('status') ?? '概念方案') as ExhibitStatus,
    reviewStatus: String(data.get('reviewStatus') ?? existingItem?.reviewStatus ?? '待审核') as ReviewStatus,
    description: String(data.get('description') ?? '').trim(),
    tags: list('tags'),
    media: existingItem?.media ?? [],
    documents: existingItem?.documents ?? [],
    relatedProjectIds: list('relatedProjectIds'),
    relatedExhibitIds: list('relatedExhibitIds')
  };
}

type ExhibitFormDraft = Partial<Record<string, string | number>>;
type SelectOption = string | { value: string; label: string };

function documentSuggestionFormDraft(suggestion: DocumentExtractionSuggestion): ExhibitFormDraft {
  const draft: ExhibitFormDraft = {};
  if (suggestion.exhibitName) draft.name = suggestion.exhibitName;
  if (suggestion.category) draft.category = suggestion.category;
  if (suggestion.theme) draft.theme = suggestion.theme;
  if (suggestion.venueType) draft.venueType = suggestion.venueType;
  if (suggestion.budgetMin !== undefined) draft.budgetMin = suggestion.budgetMin;
  if (suggestion.budgetMax !== undefined) draft.budgetMax = suggestion.budgetMax;
  if (suggestion.materials.length > 0) draft.materials = suggestion.materials.join(',');
  if (suggestion.interactions.length > 0) draft.interactions = suggestion.interactions.join(',');
  if (suggestion.supplier) draft.supplier = suggestion.supplier;
  if (suggestion.owner) draft.owner = suggestion.owner;
  if (suggestion.projectYear !== undefined) draft.projectYear = suggestion.projectYear;
  if (suggestion.tags.length > 0) draft.tags = suggestion.tags.join(',');
  if (suggestion.summary) draft.description = suggestion.summary;
  return draft;
}

function projectOptions(items: Exhibit[]): SelectOption[] {
  const options = new Map<string, string>();
  for (const item of items) {
    const projectId = item.relatedProjectIds[0];
    if (!projectId || options.has(projectId)) continue;
    options.set(projectId, item.projectName || projectId);
  }
  return [...options.entries()]
    .map(([value, label]) => ({ value, label }))
    .sort((left, right) => left.label.localeCompare(right.label, 'zh-Hans'));
}

export function App() {
  const [items, setItems] = useState<Exhibit[]>(() => loadExhibits());
  const [session, setSession] = useState<UserSession | null>(() => {
    const initialSession = readStoredSession();
    if (initialSession) {
      setApiSession(initialSession);
    }
    return initialSession;
  });
  const [role, setRole] = useState<UserRole>(() => {
    if (session) return session.user.role;
    const initialRole = requireLoginForWrites ? 'viewer' : 'admin';
    setApiRole(initialRole);
    return initialRole;
  });
  const [filters, setFilters] = useState<ExhibitFilters>(emptyFilters);
  const [budgetMinInput, setBudgetMinInput] = useState('');
  const [budgetMaxInput, setBudgetMaxInput] = useState('');
  const [semanticQuery, setSemanticQuery] = useState('找几个适合低龄儿童、预算不高、互动性强的力学展项');
  const [remoteSemanticResults, setRemoteSemanticResults] = useState<SearchResults | null>(null);
  const [isSemanticSearching, setIsSemanticSearching] = useState(false);
  const [semanticError, setSemanticError] = useState<string | null>(null);
  const [graphRagQuery, setGraphRagQuery] = useState('pulley-wall');
  const [graphRagAnswer, setGraphRagAnswer] = useState<GraphRagAnswer | null>(null);
  const [graphRagError, setGraphRagError] = useState<string | null>(null);
  const [isAskingGraphRag, setIsAskingGraphRag] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [selectedId, setSelectedId] = useState(items[0]?.id ?? '');
  const [showForm, setShowForm] = useState(false);
  const [dataSource, setDataSource] = useState<'loading' | 'api' | 'local'>('loading');
  const [loadError, setLoadError] = useState<string | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isExportingExhibits, setIsExportingExhibits] = useState(false);
  const [deletingAssetId, setDeletingAssetId] = useState<string | null>(null);
  const [previewAsset, setPreviewAsset] = useState<PreviewAsset | null>(null);
  const [isReviewing, setIsReviewing] = useState(false);
  const [isUpdatingRelations, setIsUpdatingRelations] = useState(false);
  const [selectedRelatedId, setSelectedRelatedId] = useState('');
  const [relationRecommendations, setRelationRecommendations] = useState<{
    exhibitId: string;
    items: RelationRecommendation[];
  } | null>(null);
  const [relationRecommendationError, setRelationRecommendationError] = useState<string | null>(null);
  const [isLoadingRelationRecommendations, setIsLoadingRelationRecommendations] = useState(false);
  const [documentExtractionSuggestion, setDocumentExtractionSuggestion] = useState<{
    documentId: string;
    result: DocumentExtractionSuggestion;
  } | null>(null);
  const [formDraft, setFormDraft] = useState<{
    exhibitId: string | null;
    version: number;
    values: ExhibitFormDraft;
  } | null>(null);
  const [documentExtractionError, setDocumentExtractionError] = useState<{
    documentId: string;
    message: string;
  } | null>(null);
  const [loadingDocumentExtractionId, setLoadingDocumentExtractionId] = useState<string | null>(null);
  const [isImporting, setIsImporting] = useState(false);
  const [importPreview, setImportPreview] = useState<{ file: File; result: ExhibitImportResult } | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [auditError, setAuditError] = useState<string | null>(null);
  const [isAuditLoading, setIsAuditLoading] = useState(false);
  const [isAuditExporting, setIsAuditExporting] = useState(false);
  const [auditActionFilter, setAuditActionFilter] = useState('');
  const [auditResourceIdFilter, setAuditResourceIdFilter] = useState('');
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [systemStatusError, setSystemStatusError] = useState<string | null>(null);
  const [isSystemStatusLoading, setIsSystemStatusLoading] = useState(false);
  const [dashboardSummary, setDashboardSummary] = useState<DashboardStats | null>(null);
  const [dashboardError, setDashboardError] = useState<string | null>(null);
  const [isDashboardLoading, setIsDashboardLoading] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [remoteGraph, setRemoteGraph] = useState<{
    exhibitId: string;
    nodes: GraphNode[];
    edges: GraphEdge[];
  } | null>(null);
  const [demoGraph, setDemoGraph] = useState<{
    nodes: GraphNode[];
    edges: GraphEdge[];
  } | null>(null);
  const [graphMode, setGraphMode] = useState<'current' | 'demo'>('current');
  const [graphError, setGraphError] = useState<string | null>(null);
  const [selectedGraphNodeIds, setSelectedGraphNodeIds] = useState<string[]>([]);
  const [graphHighlightDepth, setGraphHighlightDepth] = useState<1 | 2>(1);
  const [graphLayoutVersion, setGraphLayoutVersion] = useState(0);
  const [activeGraphNodeKind, setActiveGraphNodeKind] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setDataSource('loading');
    setDashboardSummary(null);
    setDashboardError(null);
    setIsDashboardLoading(true);

    fetchExhibits(filters)
      .then((nextItems) => {
        if (cancelled) return;
        setItems(nextItems);
        if (nextItems.length > 0 && !nextItems.some((item) => item.id === selectedId)) {
          setSelectedId(nextItems[0].id);
        }
        setDataSource('api');
        setLoadError(null);
      })
      .catch(() => {
        if (cancelled) return;
        const localItems = filterExhibits(loadExhibits(), filters);
        setItems(localItems);
        if (localItems.length > 0 && !localItems.some((item) => item.id === selectedId)) {
          setSelectedId(localItems[0].id);
        }
        setDataSource('local');
        setLoadError('后端未连接，已使用本地数据');
      });

    fetchDashboardSummary(filters)
      .then((summary) => {
        if (cancelled) return;
        setDashboardSummary(summary);
        setDashboardError(null);
      })
      .catch(() => {
        if (cancelled) return;
        setDashboardSummary(null);
        setDashboardError('数据看板暂不可用，已使用本地统计');
      })
      .finally(() => {
        if (cancelled) return;
        setIsDashboardLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [filters]);

  const options = useMemo(
    () => ({
      categories: uniqueValues(items, (item) => item.category),
      themes: uniqueValues(items, (item) => item.theme),
      tags: uniqueValues(items, (item) => item.tags),
      projects: projectOptions(items),
      owners: uniqueValues(items, (item) => item.owner),
      suppliers: uniqueValues(items, (item) => item.supplier),
      venueTypes: uniqueValues(items, (item) => item.venueType),
      materials: uniqueValues(items, (item) => item.materials),
      interactions: uniqueValues(items, (item) => item.interactions)
    }),
    [items]
  );

  const filteredItems = useMemo(() => filterExhibits(items, filters), [items, filters]);
  const localSemanticMatches = useMemo(() => semanticSearch(items, semanticQuery), [items, semanticQuery]);
  const localSemanticResults = useMemo<SearchResults>(
    () => ({
      total: localSemanticMatches.length,
      items: localSemanticMatches.slice(0, 4)
    }),
    [localSemanticMatches]
  );
  const semanticSearchResponse = remoteSemanticResults ?? localSemanticResults;
  const semanticResults = semanticSearchResponse.items;
  const selected = items.find((item) => item.id === selectedId) ?? filteredItems[0] ?? items[0];
  const editingItem = editingId ? items.find((item) => item.id === editingId) : undefined;
  const activeFormDraft = formDraft && formDraft.exhibitId === (editingId ?? null) ? formDraft.values : {};
  const formValue = (name: string, fallback: string | number) => activeFormDraft[name] ?? fallback;
  const fallbackGraph = useMemo(() => (selected ? buildGraph(selected, items) : { nodes: [], edges: [] }), [selected, items]);
  const isRemoteGraph = Boolean(remoteGraph && remoteGraph.exhibitId === selected?.id);
  const rawGraph =
    graphMode === 'demo'
      ? demoGraph ?? { nodes: [], edges: [] }
      : remoteGraph && remoteGraph.exhibitId === selected?.id
        ? remoteGraph
        : fallbackGraph;
  const graphKindOptions = useMemo(() => [...new Set(rawGraph.nodes.map((node) => node.kind))], [rawGraph]);
  const graphKindKey = graphKindOptions.join('\u0000');
  const graph = useMemo(() => {
    if (!activeGraphNodeKind) return rawGraph;
    const visibleNodes = rawGraph.nodes.filter((node) => node.kind === activeGraphNodeKind);
    const visibleNodeIds = new Set(visibleNodes.map((node) => node.id));
    return {
      nodes: visibleNodes,
      edges: rawGraph.edges.filter((edge) => visibleNodeIds.has(edge.source) && visibleNodeIds.has(edge.target))
    };
  }, [rawGraph, activeGraphNodeKind]);
  const graphSourceLabel = graphMode === 'demo' || isRemoteGraph ? 'Neo4j 图数据库' : '本地轻量图谱';
  const graphFilterLabel = activeGraphNodeKind ? nodeKindCaption(activeGraphNodeKind) : null;
  const graphNodeKey = graph.nodes.map((node) => node.id).join('\u0000');
  const selectedGraphNode =
    graph.nodes.find((node) => node.id === selectedGraphNodeIds[selectedGraphNodeIds.length - 1]) ?? null;
  const localStats = useMemo(() => graphStats(items), [items]);
  const stats = dashboardSummary ?? localStats;
  const canWrite = role !== 'viewer';
  const canDelete = role === 'admin';
  const canReview = role === 'admin';
  const hasNoGraphRagEvidence = Boolean(
    graphRagAnswer && graphRagAnswer.citations.length === 0
  );
  const isDeleteProtected = Boolean(selected && (selected.reviewStatus === '已审核' || selected.status === '已落地'));
  const deleteProtectionMessage = '已审核/已落地档案受保护，请先退回审核或变更状态后再删除';
  const relatedExhibits = useMemo(
    () =>
      selected
        ? selected.relatedExhibitIds
            .map((id) => items.find((item) => item.id === id))
            .filter((item): item is Exhibit => Boolean(item))
        : [],
    [items, selected]
  );
  const relationCandidates = useMemo(
    () =>
      selected
        ? items.filter((item) => item.id !== selected.id && !selected.relatedExhibitIds.includes(item.id))
        : [],
    [items, selected]
  );
  const recommendedSimilarRelations = useMemo(
    () =>
      selected && relationRecommendations?.exhibitId === selected.id
        ? relationRecommendations.items
            .filter(
              (item) =>
                item.relationType === 'similar_to' &&
                !item.alreadyExists &&
                !selected.relatedExhibitIds.includes(item.targetId)
            )
            .filter((item) => items.some((exhibit) => exhibit.id === item.targetId))
            .slice(0, 4)
        : [],
    [items, relationRecommendations, selected]
  );

  useEffect(() => {
    if (session) {
      setApiSession(session);
      storeSession(session);
    } else {
      setApiSession(null);
      setApiRole(requireLoginForWrites ? 'viewer' : role);
      clearStoredSession();
    }
  }, [role, session]);

  useEffect(() => {
    const restoredSession = session;
    if (!restoredSession) return;

    let cancelled = false;
    validateSession(restoredSession)
      .then((validatedSession) => {
        if (cancelled) return;
        setSession(validatedSession);
        setRole(validatedSession.user.role);
      })
      .catch(() => {
        if (cancelled) return;
        setSession(null);
        setApiSession(null);
        setRole('viewer');
        setAuthError('登录已失效，请重新登录');
      });

    return () => {
      cancelled = true;
    };
    // Validate only the session restored during initial page load.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!selected || !canWrite || dataSource !== 'api') {
      setRelationRecommendations(null);
      setRelationRecommendationError(null);
      setIsLoadingRelationRecommendations(false);
      return;
    }

    let cancelled = false;
    setIsLoadingRelationRecommendations(true);
    setRelationRecommendationError(null);
    fetchExhibitRelationRecommendations(selected.id)
      .then((result) => {
        if (cancelled) return;
        setRelationRecommendations({
          exhibitId: selected.id,
          items: result.recommendations
        });
      })
      .catch(() => {
        if (cancelled) return;
        setRelationRecommendations(null);
        setRelationRecommendationError('KG 关系推荐暂不可用');
      })
      .finally(() => {
        if (cancelled) return;
        setIsLoadingRelationRecommendations(false);
      });

    return () => {
      cancelled = true;
    };
  }, [canWrite, dataSource, selected?.id]);

  const refreshAuditLogs = async (
    overrideFilters?: {
      action?: string;
      resourceId?: string;
    }
  ) => {
    if (role !== 'admin') {
      setAuditLogs([]);
      setAuditError(null);
      setIsAuditLoading(false);
      return;
    }

    const nextFilters = overrideFilters ?? {
      action: auditActionFilter,
      resourceId: auditResourceIdFilter.trim()
    };
    setIsAuditLoading(true);
    await fetchAuditLogs(8, nextFilters)
      .then((logs) => {
        setAuditLogs(logs);
        setAuditError(null);
      })
      .catch(() => {
        setAuditLogs([]);
        setAuditError('操作日志暂不可用');
      })
      .finally(() => {
        setIsAuditLoading(false);
      });
  };

  const showSelectedAuditLogs = () => {
    if (role !== 'admin' || !selected) return;
    setAuditActionFilter('');
    setAuditResourceIdFilter(selected.id);
    void refreshAuditLogs({ resourceId: selected.id });
  };

  const handleExportAuditLogs = async () => {
    if (role !== 'admin') return;

    setIsAuditExporting(true);
    try {
      const blob = await exportAuditLogsCsv(500, {
        action: auditActionFilter,
        resourceId: auditResourceIdFilter.trim()
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'audit-logs.csv';
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setAuditError(null);
    } catch {
      setAuditError('操作日志导出暂不可用');
    } finally {
      setIsAuditExporting(false);
    }
  };

  const handleExportExhibits = async () => {
    if (!canWrite) return;

    setIsExportingExhibits(true);
    try {
      const blob = await exportExhibitsCsv(filters);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'exhibits.csv';
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setExportError(null);
    } catch {
      setExportError('档案导出暂不可用');
    } finally {
      setIsExportingExhibits(false);
    }
  };

  const refreshDashboardSummary = async () => {
    setIsDashboardLoading(true);
    await fetchDashboardSummary(filters)
      .then((summary) => {
        setDashboardSummary(summary);
        setDashboardError(null);
      })
      .catch(() => {
        setDashboardSummary(null);
        setDashboardError('数据看板暂不可用，已使用本地统计');
      })
      .finally(() => {
        setIsDashboardLoading(false);
      });
  };

  const refreshSystemStatus = async () => {
    if (role !== 'admin') {
      setSystemStatus(null);
      setSystemStatusError(null);
      setIsSystemStatusLoading(false);
      return;
    }

    setIsSystemStatusLoading(true);
    await fetchSystemStatus()
      .then((status) => {
        setSystemStatus(status);
        setSystemStatusError(null);
      })
      .catch(() => {
        setSystemStatus(null);
        setSystemStatusError('系统状态暂不可用');
      })
      .finally(() => {
        setIsSystemStatusLoading(false);
      });
  };

  useEffect(() => {
    void refreshAuditLogs();
  }, [role]);

  useEffect(() => {
    void refreshSystemStatus();
  }, [role]);

  useEffect(() => {
    const query = semanticQuery.trim();
    if (!query) {
      setRemoteSemanticResults({ total: 0, items: [] });
      setSemanticError(null);
      setIsSemanticSearching(false);
      return;
    }

    let cancelled = false;
    setIsSemanticSearching(true);
    hybridSearchExhibits(query, filters, 4)
      .then((results) => {
        if (cancelled) return;
        setRemoteSemanticResults(results);
        setSemanticError(null);
      })
      .catch(() => {
        if (cancelled) return;
        setRemoteSemanticResults(null);
        setSemanticError('后端混合检索暂不可用，已使用本地语义召回');
      })
      .finally(() => {
        if (cancelled) return;
        setIsSemanticSearching(false);
      });

    return () => {
      cancelled = true;
    };
  }, [semanticQuery, filters]);

  useEffect(() => {
    if (!selected) {
      setRemoteGraph(null);
      return;
    }

    let cancelled = false;
    fetchExhibitGraph(selected.id)
      .then((nextGraph) => {
        if (cancelled) return;
        setRemoteGraph({ exhibitId: selected.id, ...nextGraph });
      })
      .catch(() => {
        if (cancelled) return;
        setRemoteGraph(null);
      });

    return () => {
      cancelled = true;
    };
  }, [selected?.id]);

  useEffect(() => {
    if (graphMode !== 'demo' || demoGraph) return;

    let cancelled = false;
    fetchDemoGraph()
      .then((nextGraph) => {
        if (cancelled) return;
        setDemoGraph(nextGraph);
        setGraphError(null);
      })
      .catch(() => {
        if (cancelled) return;
        setDemoGraph(null);
        setGraphError('全库 Neo4j 演示图谱暂不可用');
      });

    return () => {
      cancelled = true;
    };
  }, [graphMode, demoGraph]);

  useEffect(() => {
    if (activeGraphNodeKind && !graphKindOptions.includes(activeGraphNodeKind)) {
      setActiveGraphNodeKind(null);
    }
  }, [activeGraphNodeKind, graphKindKey]);

  useEffect(() => {
    if (graph.nodes.length === 0) {
      setSelectedGraphNodeIds([]);
      return;
    }
    setSelectedGraphNodeIds((current) => {
      const availableIds = new Set(graph.nodes.map((node) => node.id));
      const next = current.filter((id) => availableIds.has(id));
      const normalized = next.length > 0 ? next : [graph.nodes[0].id];
      if (normalized.length === current.length && normalized.every((id, index) => id === current[index])) {
        return current;
      }
      return normalized;
    });
  }, [graphNodeKey]);

  useEffect(() => {
    setSelectedRelatedId('');
  }, [selected?.id]);

  const updateFilter = (key: keyof ExhibitFilters, value: string) => {
    setFilters((current) => ({ ...current, [key]: value }));
  };

  const updateBudgetFilter = (nextMin: string, nextMax: string) => {
    setBudgetMinInput(nextMin);
    setBudgetMaxInput(nextMax);
    const min = Number(nextMin);
    const max = Number(nextMax);
    setFilters((current) => {
      const next = { ...current };
      delete next.budgetRange;
      if (nextMin.trim() && nextMax.trim() && Number.isFinite(min) && Number.isFinite(max) && min >= 0 && max >= min) {
        return { ...next, budgetRange: [min, max] };
      }
      return next;
    });
  };

  const resetFilters = () => {
    setBudgetMinInput('');
    setBudgetMaxInput('');
    setFilters(emptyFilters);
  };

  const submitLogin = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (isLoggingIn) return;
    const data = new FormData(event.currentTarget);
    const username = String(data.get('username') ?? '').trim();
    const password = String(data.get('password') ?? '');
    if (!username || !password) return;
    setIsLoggingIn(true);
    setAuthError(null);
    try {
      const nextSession = await login(username, password);
      setSession(nextSession);
      setRole(nextSession.user.role);
    } catch {
      setSession(null);
      setApiSession(null);
      setAuthError('登录失败，请检查演示账号和密码');
    } finally {
      setIsLoggingIn(false);
    }
  };

  const logout = () => {
    setSession(null);
    setApiSession(null);
    setRole('viewer');
    setAuthError(null);
  };

  const addExhibit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!canWrite) return;
    const form = event.currentTarget;
    const currentEditingItem = editingId ? items.find((item) => item.id === editingId) : undefined;
    const next = makeExhibitFromForm(event.currentTarget, currentEditingItem);
    if (!next.name || !next.category || !next.theme) return;
    setIsSaving(true);

    try {
      const saved = editingId ? await updateExhibit(editingId, next) : await createExhibit(next);
      const updated = editingId
        ? items.map((item) => (item.id === editingId ? saved : item))
        : [saved, ...items.filter((item) => item.id !== saved.id)];
      setItems(updated);
      setSelectedId(saved.id);
      setDataSource('api');
      setLoadError(null);
      void refreshAuditLogs();
    } catch {
      const updated = editingId
        ? items.map((item) => (item.id === editingId ? next : item))
        : [next, ...items];
      setItems(updated);
      saveExhibits(updated);
      setSelectedId(next.id);
      setDataSource('local');
      setLoadError(editingId ? '后端更新失败，修改已暂存于本地' : '后端写入失败，新增档案已暂存于本地');
    } finally {
      setIsSaving(false);
      setEditingId(null);
      setShowForm(false);
      setFormDraft(null);
      form.reset();
    }
  };

  const attachMedia = async (event: FormEvent<HTMLInputElement>) => {
    if (!canWrite || !selected || !event.currentTarget.files?.length) return;
    const file = event.currentTarget.files[0];
    const assetKind = assetKindForFile(file);
    try {
      const updatedExhibit = await uploadExhibitAsset(selected.id, file, assetKind);
      const updated = items.map((item) => (item.id === selected.id ? updatedExhibit : item));
      setItems(updated);
      setDataSource('api');
      setLoadError(null);
      void refreshAuditLogs();
    } catch {
      const url = URL.createObjectURL(file);
      if (assetKind === 'document') {
        const document: DocumentAsset = {
          id: `document-${Date.now()}`,
          name: file.name,
          fileType: fileExtension(file.name),
          url,
          sourceNote: '本地临时文件'
        };
        const updated = items.map((item) =>
          item.id === selected.id
            ? {
                ...item,
                documents: [document, ...item.documents]
              }
            : item
        );
        setItems(updated);
        saveExhibits(updated);
        setDataSource('local');
        setLoadError('后端上传失败，文件已临时保存在本地会话');
        return;
      }
      const asset: MediaAsset = {
        id: `media-${Date.now()}`,
        type: file.type.startsWith('image/') ? 'image' : file.type.startsWith('video/') ? 'video' : 'document',
        name: file.name,
        url
      };
      const updated = items.map((item) =>
        item.id === selected.id
          ? {
              ...item,
              media: [asset, ...item.media]
            }
          : item
      );
      setItems(updated);
      saveExhibits(updated);
      setDataSource('local');
      setLoadError('后端上传失败，文件已临时保存在本地会话');
    }
  };

  const startEdit = (item: Exhibit) => {
    if (!canWrite) return;
    setEditingId(item.id);
    setFormDraft(null);
    setShowForm(true);
    setLoadError(null);
  };

  const deleteSelected = async () => {
    if (!canDelete || !selected || isDeleting || isDeleteProtected) return;
    setIsDeleting(true);
    const updated = items.filter((item) => item.id !== selected.id);

    try {
      await deleteExhibit(selected.id);
      setItems(updated);
      setSelectedId(updated[0]?.id ?? '');
      setDataSource('api');
      setLoadError(null);
      void refreshAuditLogs();
    } catch {
      setLoadError('删除失败，请检查权限或档案保护状态');
    } finally {
      setIsDeleting(false);
    }
  };

  const removeAsset = async (assetId: string) => {
    if (!canDelete || !selected || deletingAssetId || isDeleteProtected) return;
    setDeletingAssetId(assetId);

    try {
      const updatedExhibit = await deleteExhibitAsset(selected.id, assetId);
      const updated = items.map((item) => (item.id === updatedExhibit.id ? updatedExhibit : item));
      setItems(updated);
      setSelectedId(updatedExhibit.id);
      setDataSource('api');
      setLoadError(null);
      void refreshAuditLogs();
    } catch {
      setLoadError('资料删除失败，请检查权限或网络连接');
    } finally {
      setDeletingAssetId(null);
    }
  };

  const changeReviewStatus = async (reviewStatus: ReviewStatus) => {
    if (!canReview || !selected || isReviewing || selected.reviewStatus === reviewStatus) return;
    setIsReviewing(true);

    try {
      const updatedExhibit = await updateExhibitReviewStatus(selected.id, reviewStatus);
      const updated = items.map((item) => (item.id === updatedExhibit.id ? updatedExhibit : item));
      setItems(updated);
      setSelectedId(updatedExhibit.id);
      setDataSource('api');
      setLoadError(null);
      void refreshAuditLogs();
    } catch {
      setLoadError('审核状态更新失败，请检查权限或网络连接');
    } finally {
      setIsReviewing(false);
    }
  };

  const refreshSelectedGraph = (exhibitId: string) => {
    setRemoteGraph(null);
    setGraphLayoutVersion((version) => version + 1);
    fetchExhibitGraph(exhibitId)
      .then((nextGraph) => {
        setRemoteGraph({ exhibitId, ...nextGraph });
      })
      .catch(() => {
        setRemoteGraph(null);
      });
  };

  const changeRelatedExhibits = async (relatedExhibitIds: string[]) => {
    if (!canWrite || !selected || isUpdatingRelations) return;
    setIsUpdatingRelations(true);

    try {
      const updatedExhibit = await updateExhibitRelatedExhibits(selected.id, relatedExhibitIds);
      const updated = items.map((item) => (item.id === updatedExhibit.id ? updatedExhibit : item));
      setItems(updated);
      setSelectedId(updatedExhibit.id);
      setSelectedRelatedId('');
      setDataSource('api');
      setLoadError(null);
      refreshSelectedGraph(updatedExhibit.id);
      void refreshAuditLogs();
    } catch {
      setLoadError('相似展项关系更新失败，请检查目标展项或网络连接');
    } finally {
      setIsUpdatingRelations(false);
    }
  };

  const addRelatedExhibit = () => {
    if (!selected || !selectedRelatedId) return;
    changeRelatedExhibits([...selected.relatedExhibitIds, selectedRelatedId]);
  };

  const acceptRecommendedRelation = (targetId: string) => {
    if (!selected) return;
    changeRelatedExhibits(Array.from(new Set([...selected.relatedExhibitIds, targetId])));
  };

  const removeRelatedExhibit = (relatedId: string) => {
    if (!selected) return;
    changeRelatedExhibits(selected.relatedExhibitIds.filter((id) => id !== relatedId));
  };

  const requestDocumentExtractionSuggestion = async (document: DocumentAsset) => {
    if (!selected || !canWrite || loadingDocumentExtractionId) return;

    setLoadingDocumentExtractionId(document.id);
    setDocumentExtractionError(null);
    try {
      const result = await fetchDocumentExtractionSuggestions(selected.id, document.id);
      setDocumentExtractionSuggestion({ documentId: document.id, result });
    } catch {
      setDocumentExtractionSuggestion(null);
      setDocumentExtractionError({
        documentId: document.id,
        message: '字段抽取建议暂不可用'
      });
    } finally {
      setLoadingDocumentExtractionId(null);
    }
  };

  const applyDocumentExtractionSuggestion = (suggestion: DocumentExtractionSuggestion) => {
    if (!selected || !canWrite) return;
    setEditingId(selected.id);
    setFormDraft((current) => ({
      exhibitId: selected.id,
      version: (current?.version ?? 0) + 1,
      values: documentSuggestionFormDraft(suggestion)
    }));
    setShowForm(true);
    setLoadError(null);
  };

  const submitGraphRagQuestion = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const query = graphRagQuery.trim();
    if (!query || isAskingGraphRag) return;

    setIsAskingGraphRag(true);
    setGraphRagError(null);
    try {
      const answer = await askGraphRag(query, 3, filters);
      setGraphRagAnswer(answer);
    } catch {
      setGraphRagError('GraphRAG 问答接口暂不可用，请稍后重试');
    } finally {
      setIsAskingGraphRag(false);
    }
  };

  const selectGraphRagCitation = (citation: GraphRagCitation) => {
    if (citation.sourceType === 'exhibit') {
      setSelectedId(citation.sourceId);
      return;
    }

    const owningHit = graphRagAnswer?.items.find((hit) =>
      hit.citations.some(
        (itemCitation) =>
          itemCitation.sourceType === citation.sourceType && itemCitation.sourceId === citation.sourceId
      )
    );
    if (owningHit) {
      setSelectedId(owningHit.exhibit.id);
    }
  };

  const restoreSeed = () => {
    const restored = resetExhibits();
    setItems(restored);
    setSelectedId(restored[0].id);
    setDataSource('local');
    setLoadError('已恢复本地样例数据');
  };

  const importSpreadsheet = async (event: FormEvent<HTMLInputElement>) => {
    const input = event.currentTarget;
    const file = input.files?.[0];
    if (!canWrite || !file || isImporting) return;
    setIsImporting(true);
    try {
      const result = await importExhibits(file, false);
      setImportPreview({ file, result });
      if (result.errors.length > 0) {
        setDataSource('api');
        setLoadError(`导入校验发现 ${result.errors.length} 个问题，未写入数据`);
        return;
      }
      setDataSource('api');
      setLoadError(`导入预览完成：确认后写入 ${result.validRows} 条展项`);
    } catch (error) {
      setDataSource('local');
      setLoadError(error instanceof Error ? error.message : '表格导入失败，请检查字段模板和网络连接');
    } finally {
      setIsImporting(false);
      input.value = '';
    }
  };

  const confirmImportPreview = async () => {
    if (!importPreview || importPreview.result.errors.length > 0 || importPreview.result.validRows === 0 || isImporting) return;
    setIsImporting(true);
    try {
      const result = await importExhibits(importPreview.file, true);
      if (result.errors.length > 0) {
        setImportPreview({ file: importPreview.file, result });
        setDataSource('api');
        setLoadError(`导入校验发现 ${result.errors.length} 个问题，未写入数据`);
        return;
      }
      if (result.items.length > 0) {
        const updated = mergeImportedExhibits(items, result.items);
        setItems(updated);
        setSelectedId(result.items[0].id);
        setGraphMode('current');
        setSelectedGraphNodeIds([]);
        setGraphLayoutVersion((value) => value + 1);
      }
      setImportPreview(null);
      setDataSource('api');
      setLoadError('导入完成：已选中新展项，可在当前展项图谱核验关系');
      void refreshAuditLogs();
    } catch (error) {
      setDataSource('local');
      setLoadError(error instanceof Error ? error.message : '表格导入失败，请检查字段模板和网络连接');
    } finally {
      setIsImporting(false);
    }
  };

  const relayoutGraph = () => {
    setGraphLayoutVersion((value) => value + 1);
  };

  const toggleGraphNodeSelection = (nodeId: string | null) => {
    if (!nodeId) {
      setSelectedGraphNodeIds([]);
      return;
    }
    setSelectedGraphNodeIds((current) =>
      current.includes(nodeId) ? current.filter((id) => id !== nodeId) : [...current, nodeId]
    );
  };

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <Database size={24} />
          <div>
            <strong>展项图鉴</strong>
            <span>MVP 工作台</span>
          </div>
        </div>

        <section className="panel">
          <div className="panel-title">
            <Filter size={18} />
            <span>结构化筛选</span>
          </div>
          <label>
            关键词
            <input
              value={filters.keyword}
              onChange={(event) => updateFilter('keyword', event.target.value)}
              placeholder="名称、业主、供应商、标签"
            />
          </label>
          <Select label="场馆类型" value={filters.venueType} values={options.venueTypes} onChange={(value) => updateFilter('venueType', value)} />
          <Select label="类别" value={filters.category} values={options.categories} onChange={(value) => updateFilter('category', value)} />
          <Select label="主题" value={filters.theme} values={options.themes} onChange={(value) => updateFilter('theme', value)} />
          <Select label="标签" value={filters.tag} values={options.tags} onChange={(value) => updateFilter('tag', value)} />
          <Select label="项目案例" value={filters.projectId} values={options.projects} onChange={(value) => updateFilter('projectId', value)} />
          <Select label="业主" value={filters.owner} values={options.owners} onChange={(value) => updateFilter('owner', value)} />
          <Select label="供应商" value={filters.supplier} values={options.suppliers} onChange={(value) => updateFilter('supplier', value)} />
          <Select label="材料" value={filters.material} values={options.materials} onChange={(value) => updateFilter('material', value)} />
          <Select label="交互方式" value={filters.interaction} values={options.interactions} onChange={(value) => updateFilter('interaction', value)} />
          <Select label="状态" value={filters.status} values={statuses} onChange={(value) => updateFilter('status', value)} />
          <Select label="审核状态" value={filters.reviewStatus} values={reviewStatuses} onChange={(value) => updateFilter('reviewStatus', value)} />
          <div className="budget-range">
            <label>
              最低造价
              <input
                type="number"
                min="0"
                value={budgetMinInput}
                onChange={(event) => updateBudgetFilter(event.target.value, budgetMaxInput)}
                placeholder="如 200000"
              />
            </label>
            <label>
              最高造价
              <input
                type="number"
                min="0"
                value={budgetMaxInput}
                onChange={(event) => updateBudgetFilter(budgetMinInput, event.target.value)}
                placeholder="如 500000"
              />
            </label>
          </div>
          <div className="filter-actions">
            <button type="button" onClick={resetFilters}>
              <RotateCcw size={16} />
              重置
            </button>
          </div>
        </section>

        <section className="panel stats">
          <div className="panel-title">
            <BarChart3 size={18} />
            <span>数据看板</span>
            <button
              type="button"
              className="panel-refresh-action"
              onClick={() => void refreshDashboardSummary()}
              disabled={isDashboardLoading}
              aria-label="刷新数据看板"
            >
              <RotateCcw size={13} />
              {isDashboardLoading ? '刷新中' : '刷新'}
            </button>
          </div>
          {dashboardError && <p className="audit-error">{dashboardError}</p>}
          <div className="stat-grid">
            <Metric label="展项" value={stats.total} />
            <Metric label="已落地" value={stats.landed} />
            <Metric label="均价" value={`${stats.avgBudget}万`} />
          </div>
          <div className="review-summary" aria-label="审核状态概览">
            <button
              type="button"
              onClick={() => updateFilter('reviewStatus', '待审核')}
              aria-label={`筛选待审核档案，当前 ${stats.pendingReview} 条`}
            >
              待审 {stats.pendingReview}
            </button>
            <button
              type="button"
              onClick={() => updateFilter('reviewStatus', '已退回')}
              aria-label={`筛选已退回档案，当前 ${stats.rejectedReview} 条`}
            >
              退回 {stats.rejectedReview}
            </button>
          </div>
          <DashboardBars title="类别分布" items={stats.categories} />
          <DashboardBars title="预算区间" items={stats.budgetBands} />
          <DashboardBars title="热门主题" items={stats.themes.slice(0, 4)} />
          <div className="mini-bars">
            {stats.reviewStatuses.map(([label, count]) => (
              <span key={label}>
                <i style={{ width: `${Math.max(count * 34, 18)}px` }} />
                {label} {count}
              </span>
            ))}
          </div>
        </section>

        {role === 'admin' && (
          <section className="panel system-status-panel">
            <div className="panel-title">
              <Database size={18} />
              <span>系统状态</span>
              <button
                type="button"
                className="panel-refresh-action"
                onClick={() => void refreshSystemStatus()}
                disabled={isSystemStatusLoading}
                aria-label="刷新系统状态"
              >
                <RotateCcw size={13} />
                {isSystemStatusLoading ? '刷新中' : '刷新'}
              </button>
            </div>
            {systemStatusError && <p className="audit-error">{systemStatusError}</p>}
            {!systemStatusError && isSystemStatusLoading && !systemStatus && (
              <p className="audit-empty">正在检查运行环境...</p>
            )}
            {!systemStatusError && systemStatus && <SystemStatusCard status={systemStatus} />}
          </section>
        )}

        {role === 'admin' && (
          <section className="panel audit-panel">
            <div className="panel-title">
              <FileText size={18} />
              <span>操作日志</span>
              <div className="audit-actions">
                <button
                  type="button"
                  className="audit-refresh-action"
                  onClick={() => void handleExportAuditLogs()}
                  disabled={isAuditExporting}
                  aria-label="导出操作日志"
                >
                  <Download size={13} />
                  {isAuditExporting ? '导出中' : '导出'}
                </button>
                <button
                  type="button"
                  className="audit-refresh-action"
                  onClick={() => void refreshAuditLogs()}
                  disabled={isAuditLoading}
                  aria-label="刷新操作日志"
                >
                  <RotateCcw size={13} />
                  {isAuditLoading ? '刷新中' : '刷新'}
                </button>
              </div>
            </div>
            <div className="audit-filters">
              <label>
                日志动作
                <select value={auditActionFilter} onChange={(event) => setAuditActionFilter(event.target.value)}>
                  <option value="">全部动作</option>
                  {auditActionOptions.map(([action, label]) => (
                    <option key={action} value={action}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                资源编号
                <input
                  value={auditResourceIdFilter}
                  onChange={(event) => setAuditResourceIdFilter(event.target.value)}
                  placeholder="档案 ID / 文件名"
                />
              </label>
            </div>
            {auditError && <p className="audit-error">{auditError}</p>}
            {!auditError && isAuditLoading && auditLogs.length === 0 && <p className="audit-empty">正在加载操作日志...</p>}
            {!auditError && !isAuditLoading && auditLogs.length === 0 && <p className="audit-empty">暂无操作记录</p>}
            <div className="audit-list">
              {auditLogs.map((entry) => (
                <div className="audit-item" key={entry.id}>
                  <div>
                    <strong>{auditActionLabel(entry.action)}</strong>
                    <span>{entry.summary}</span>
                  </div>
                  <small>
                    {entry.actorRole} / {entry.resourceId} / {formatAuditTime(entry.createdAt)}
                  </small>
                </div>
              ))}
            </div>
          </section>
        )}
      </aside>

      <section className="content">
        <header className="topbar">
          <div>
            <h1>展项数字档案与智能检索</h1>
            <p>
              录入、筛选、语义召回和轻量关系图谱的第一条闭环
              <span className={`source-status ${dataSource}`}>
                {dataSource === 'api' ? '后端 API' : dataSource === 'loading' ? '连接中' : '本地兜底'}
              </span>
            </p>
            {loadError && <p className="load-note">{loadError}</p>}
            {exportError && <p className="load-note">{exportError}</p>}
          </div>
          <div className="top-actions">
            {session ? (
              <div className="auth-session">
                <span>
                  {session.user.displayName} / {session.user.role}
                </span>
                <button type="button" onClick={logout}>
                  退出
                </button>
              </div>
            ) : (
              <form className="auth-form" onSubmit={submitLogin}>
                <label>
                  用户名
                  <input name="username" defaultValue="editor" autoComplete="username" />
                </label>
                <label>
                  密码
                  <input name="password" type="password" defaultValue="editor123" autoComplete="current-password" />
                </label>
                <button type="submit" disabled={isLoggingIn}>
                  {isLoggingIn ? '登录中' : '登录'}
                </button>
                {authError && <small>{authError}</small>}
              </form>
            )}
            <button
              type="button"
              disabled={!canWrite}
              onClick={() => {
                setEditingId(null);
                setShowForm((value) => !value);
              }}
            >
              <FilePlus2 size={18} />
              新增展项
            </button>
            <button type="button" onClick={restoreSeed}>
              <RotateCcw size={18} />
              恢复样例
            </button>
            <button type="button" onClick={() => void handleExportExhibits()} disabled={!canWrite || isExportingExhibits}>
              <Download size={18} />
              {isExportingExhibits ? '导出中' : '导出档案'}
            </button>
            <label className="import-upload">
              <Upload size={18} />
              {isImporting ? '导入中' : '导入表格'}
              <input type="file" accept=".csv,.xlsx" onChange={importSpreadsheet} disabled={isImporting || !canWrite} />
            </label>
            <a className="template-download" href={importTemplateUrl} download="展项导入模板.xlsx" aria-label="下载模板">
              <Download size={18} />
              下载模板
              <small>模板含字段说明</small>
            </a>
          </div>
        </header>

        {importPreview && (
          <section className="import-preview">
            <div className="import-preview-header">
              <div>
                <span>导入预览</span>
                <strong>{importPreview.file.name}</strong>
              </div>
              <div className="import-preview-actions">
                <button type="button" onClick={confirmImportPreview} disabled={isImporting || importPreview.result.errors.length > 0 || importPreview.result.validRows === 0}>
                  确认导入
                </button>
                <button type="button" onClick={() => setImportPreview(null)} disabled={isImporting}>
                  取消
                </button>
              </div>
            </div>
            <div className="import-preview-stats">
              <span>总行数 {importPreview.result.totalRows}</span>
              <span>有效 {importPreview.result.validRows}</span>
              <span>错误 {importPreview.result.errors.length}</span>
            </div>
            {importPreview.result.errors.length > 0 && (
              <div className="import-preview-errors">
                {importPreview.result.errors.map((error) => (
                  <div key={`${error.row}-${error.field}-${error.message}`}>
                    <span>{importErrorRowLabel(error.row, error.field)}</span>
                    <strong>{importErrorFieldLabel(error.field)}</strong>
                    <em>{importErrorMessage(error.message)}</em>
                  </div>
                ))}
              </div>
            )}
            {importPreview.result.items.length > 0 && (
              <div className="import-preview-items">
                {importPreview.result.items.slice(0, 5).map((item) => (
                  <button type="button" key={item.id} onClick={() => setSelectedId(item.id)} disabled={!items.some((current) => current.id === item.id)}>
                    <strong>{item.name}</strong>
                    <span>{item.category} / {item.theme} / {formatBudget(item)}</span>
                  </button>
                ))}
              </div>
            )}
          </section>
        )}

        {showForm && (
          <form key={`${editingId ?? 'new-exhibit'}:${formDraft?.version ?? 0}`} className="create-form" onSubmit={addExhibit}>
            <input name="name" placeholder="展项名称" defaultValue={formValue('name', editingItem?.name ?? '')} required />
            <input name="category" placeholder="类别，如基础科学" defaultValue={formValue('category', editingItem?.category ?? '')} required />
            <input name="theme" placeholder="主题，如力学" defaultValue={formValue('theme', editingItem?.theme ?? '')} required />
            <input name="venueType" placeholder="适用场馆" defaultValue={formValue('venueType', editingItem?.venueType ?? '')} required />
            <input name="budgetMin" type="number" placeholder="最低造价" defaultValue={formValue('budgetMin', editingItem?.budgetMin ?? '')} required />
            <input name="budgetMax" type="number" placeholder="最高造价" defaultValue={formValue('budgetMax', editingItem?.budgetMax ?? '')} required />
            <input name="materials" placeholder="材料，用逗号分隔" defaultValue={formValue('materials', editingItem?.materials.join(',') ?? '')} />
            <input name="interactions" placeholder="交互方式，用逗号分隔" defaultValue={formValue('interactions', editingItem?.interactions.join(',') ?? '')} />
            <input name="dimensions" placeholder="尺寸" defaultValue={formValue('dimensions', editingItem?.dimensions ?? '')} />
            <input name="supplier" placeholder="供应商" defaultValue={formValue('supplier', editingItem?.supplier ?? '')} />
            <input name="projectName" placeholder="项目名称" defaultValue={formValue('projectName', editingItem?.projectName ?? '')} />
            <input name="owner" placeholder="业主" defaultValue={formValue('owner', editingItem?.owner ?? '')} />
            <input name="projectYear" type="number" defaultValue={formValue('projectYear', editingItem?.projectYear ?? new Date().getFullYear())} />
            <select name="status" defaultValue={editingItem?.status ?? statuses[0]}>
              {statuses.map((status) => (
                <option key={status}>{status}</option>
              ))}
            </select>
            {canReview && (
              <label className="form-field">
                档案审核状态
                <select name="reviewStatus" defaultValue={editingItem?.reviewStatus ?? reviewStatuses[1]}>
                  {reviewStatuses.map((status) => (
                    <option key={status}>{status}</option>
                  ))}
                </select>
              </label>
            )}
            <input name="tags" placeholder="标签，用逗号分隔" defaultValue={formValue('tags', editingItem?.tags.join(',') ?? '')} />
            <input name="relatedProjectIds" placeholder="项目编号，用逗号分隔" defaultValue={formValue('relatedProjectIds', editingItem?.relatedProjectIds.join(',') ?? '')} />
            <input
              name="relatedExhibitIds"
              placeholder="相似展项 ID，用逗号分隔"
              defaultValue={formValue('relatedExhibitIds', editingItem?.relatedExhibitIds.join(',') ?? '')}
            />
            <textarea name="description" placeholder="展项说明" defaultValue={formValue('description', editingItem?.description ?? '')} required />
            <button type="submit" disabled={isSaving || !canWrite}>{isSaving ? '保存中' : editingId ? '保存修改' : '保存档案'}</button>
          </form>
        )}

        <section className="semantic-panel">
          <div className="semantic-input">
            <Sparkles size={20} />
            <input value={semanticQuery} onChange={(event) => setSemanticQuery(event.target.value)} />
            {isSemanticSearching && <small>检索中</small>}
          </div>
          {semanticError && <p className="semantic-error">{semanticError}</p>}
          <small className="semantic-summary">
            共 {semanticSearchResponse.total} 条，显示 {semanticResults.length} 条
          </small>
          <div className="semantic-results">
            {semanticResults.map((result) => (
              <button type="button" key={result.item.id} onClick={() => setSelectedId(result.item.id)}>
                <Search size={16} />
                <span>{result.item.name}</span>
                <small>{result.matchedSignals.join(' / ') || `${result.score} 分`}</small>
              </button>
            ))}
          </div>
        </section>

        <section className="graphrag-panel">
          <form className="graphrag-form" onSubmit={submitGraphRagQuestion}>
            <label>
              GraphRAG 问答
              <div className="graphrag-input">
                <MessageSquareText size={20} />
                <input
                  value={graphRagQuery}
                  onChange={(event) => setGraphRagQuery(event.target.value)}
                  placeholder="例如：找适合低龄儿童、预算不高、互动性强的力学展项"
                />
                <button type="submit" disabled={isAskingGraphRag}>
                  {isAskingGraphRag ? '生成中' : '生成答案'}
                </button>
              </div>
            </label>
          </form>
          {graphRagError && <p className="graphrag-error">{graphRagError}</p>}
          {graphRagAnswer && (
            <div className="graphrag-answer">
              <p>{graphRagAnswer.answer}</p>
              <div className="graphrag-answer-meta">
                <span>置信度 {Math.round(graphRagAnswer.confidence * 100)}%</span>
                {graphRagAnswer.warnings.map((warning) => (
                  <em key={warning}>{warning}</em>
                ))}
              </div>
              {hasNoGraphRagEvidence && (
                <p className="graphrag-no-evidence" role="alert">
                  未找到可引用来源，请补充展项档案、上传资料，或调整筛选条件后重试。
                </p>
              )}
              {graphRagAnswer.items.length > 0 && (
                <div className="graphrag-hits">
                  {graphRagAnswer.items.map((hit) => (
                    <button type="button" key={hit.exhibit.id} onClick={() => setSelectedId(hit.exhibit.id)}>
                      <strong>{hit.exhibit.name}</strong>
                      <span>{hit.reasons.join(' / ') || `score ${hit.score}`}</span>
                    </button>
                  ))}
                </div>
              )}
              {graphRagAnswer.citations.length > 0 && (
                <CitationList
                  answer={graphRagAnswer}
                  citations={graphRagAnswer.citations}
                  onSelectCitation={selectGraphRagCitation}
                  downloadUrl={downloadUrl}
                />
              )}
            </div>
          )}
        </section>

        <div className="workspace">
          <section className="list">
            {filteredItems.map((item) => (
              <button
                type="button"
                key={item.id}
                className={item.id === selected?.id ? 'record active' : 'record'}
                onClick={() => setSelectedId(item.id)}
              >
                <img src={item.media[0]?.url ?? fallbackImage} alt="" onError={imageFallback} />
                <span>
                  <strong>{item.name}</strong>
                  <small>{item.category} / {item.theme} / {formatBudget(item)}</small>
                </span>
                <em>{item.status} / {item.reviewStatus}</em>
              </button>
            ))}
          </section>

          {selected && (
            <section className="detail">
              <div className="detail-hero">
                <img src={selected.media[0]?.url ?? fallbackImage} alt="" onError={imageFallback} />
                <div>
                  <span>{selected.venueType}</span>
                  <h2>{selected.name}</h2>
                  <p>{selected.description}</p>
                </div>
              </div>

              <div className="facts">
                <Fact label="造价区间" value={formatBudget(selected)} />
                <Fact label="项目年份" value={selected.projectYear} />
                <Fact label="项目案例" value={selected.projectName} />
                <Fact label="业主" value={selected.owner} />
                <Fact label="供应商" value={selected.supplier} />
                <Fact label="尺寸" value={selected.dimensions} />
                <Fact label="状态" value={selected.status} />
                <Fact label="审核状态" value={selected.reviewStatus} />
              </div>

              <div
                className="chips"
                aria-label="结构化关键词"
                title="这些关键词来自材料、交互方式和标签字段，会参与结构化筛选、语义检索、GraphRAG 匹配和看板统计。"
              >
                {[...selected.materials, ...selected.interactions, ...selected.tags].map((tag) => (
                  <span key={tag} title="结构化关键词">
                    {tag}
                  </span>
                ))}
              </div>

              <section className="detail-actions" aria-label="档案维护操作">
                <div className="media-row">
                  <button type="button" className="secondary-action" onClick={() => startEdit(selected)} disabled={!canWrite}>
                    <Pencil size={18} />
                    编辑档案
                  </button>
                  {role === 'admin' && (
                    <button type="button" className="secondary-action" onClick={showSelectedAuditLogs}>
                      <FileText size={18} />
                      查看此档案日志
                    </button>
                  )}
                  <div className="delete-action-wrap">
                    <button
                      type="button"
                      className="danger-action"
                      onClick={deleteSelected}
                      disabled={isDeleting || !canDelete || isDeleteProtected}
                    >
                      <Trash2 size={18} />
                      {isDeleting ? '删除中' : '删除档案'}
                    </button>
                    {isDeleteProtected && <span className="delete-protection-note">{deleteProtectionMessage}</span>}
                  </div>
                  {canReview && (
                    <div className="review-actions" aria-label="审核操作">
                      <button
                        type="button"
                        className="review-approve"
                        onClick={() => changeReviewStatus('已审核')}
                        disabled={isReviewing || selected.reviewStatus === '已审核'}
                      >
                        <Check size={18} />
                        通过审核
                      </button>
                      <button
                        type="button"
                        className="review-reject"
                        onClick={() => changeReviewStatus('已退回')}
                        disabled={isReviewing || selected.reviewStatus === '已退回'}
                      >
                        <RotateCcw size={18} />
                        退回
                      </button>
                    </div>
                  )}
                  <label className="upload">
                    <ImageIcon size={18} />
                    上传媒体
                    <input type="file" accept={uploadAcceptTypes} onChange={attachMedia} disabled={!canWrite} />
                  </label>
                </div>
              </section>

              <section className="detail-relation-assets" aria-label="资料与关系">
                <section className="similar-relations" aria-label="相似展项关系">
                  <div className="panel-title">
                    <GitBranch size={18} />
                    <span>相似展项关系</span>
                  </div>
                  <div className="similar-relations-body">
                    <div className="similar-relations-main">
                      <div className="similar-relation-list">
                        {relatedExhibits.length > 0 ? (
                          relatedExhibits.map((item) => (
                            <div key={item.id} className="similar-relation-item">
                              <span>{item.name}</span>
                              <small>{item.category} / {item.theme}</small>
                              <button
                                type="button"
                                onClick={() => removeRelatedExhibit(item.id)}
                                disabled={!canWrite || isUpdatingRelations}
                                aria-label={`移除${item.name}`}
                              >
                                移除
                              </button>
                            </div>
                          ))
                        ) : (
                          <span className="empty-relations">暂无相似展项</span>
                        )}
                      </div>
                      <div className="similar-relation-editor">
                        <label>
                          添加相似展项
                          <select
                            value={selectedRelatedId}
                            onChange={(event) => setSelectedRelatedId(event.target.value)}
                            disabled={!canWrite || isUpdatingRelations || relationCandidates.length === 0}
                          >
                            <option value="">选择展项</option>
                            {relationCandidates.map((item) => (
                              <option key={item.id} value={item.id}>
                                {item.name}
                              </option>
                            ))}
                          </select>
                        </label>
                        <button
                          type="button"
                          onClick={addRelatedExhibit}
                          disabled={!canWrite || isUpdatingRelations || !selectedRelatedId}
                        >
                          添加关系
                        </button>
                      </div>
                    </div>
                    {canWrite && (
                      <div className="relation-recommendations" aria-label="KG 关系推荐">
                        <div className="relation-recommendations-title">
                          <Sparkles size={16} />
                          <span>KG 关系推荐</span>
                          {isLoadingRelationRecommendations && <small>加载中</small>}
                        </div>
                        {relationRecommendationError ? (
                          <span className="empty-relations">{relationRecommendationError}</span>
                        ) : recommendedSimilarRelations.length > 0 ? (
                          <div className="relation-recommendation-list">
                            {recommendedSimilarRelations.map((item) => (
                              <div key={`${item.relationType}:${item.targetId}`} className="relation-recommendation-item">
                                <div>
                                  <strong>{item.targetLabel}</strong>
                                  <small>置信度 {Math.round(item.confidence * 100)}%</small>
                                </div>
                                {item.reasons.length > 0 && <p>{item.reasons.slice(0, 2).join('；')}</p>}
                                <button
                                  type="button"
                                  onClick={() => acceptRecommendedRelation(item.targetId)}
                                  disabled={isUpdatingRelations}
                                  aria-label={`采纳${item.targetLabel}为相似展项`}
                                >
                                  采纳
                                </button>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <span className="empty-relations">
                            {isLoadingRelationRecommendations ? '正在分析可采纳关系' : '暂无可采纳推荐'}
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                </section>

                {selected.media.length === 0 && selected.documents.length === 0 && (
                  <section className="asset-empty-panel" aria-label="资料状态">
                    <FileText size={18} />
                    <span>暂无媒体或资料</span>
                  </section>
                )}

              {previewAsset && (
                <AssetPreviewModal
                  asset={previewAsset}
                  onClose={() => setPreviewAsset(null)}
                  downloadUrl={downloadUrl}
                  imageFallback={imageFallback}
                />
              )}

                {(selected.media.length > 0 || selected.documents.length > 0) && (
                  <section className="media-gallery" aria-label="媒体档案">
                    <div className="panel-title">
                      <ImageIcon size={18} />
                      <span>媒体档案</span>
                    </div>
                    {isDeleteProtected && <span className="asset-protection-note">已审核/已落地档案资料受保护，请先退回审核或变更状态后再删除</span>}
                    <MediaThumbGrid
                      assets={selected.media}
                      documents={selected.documents}
                      canDelete={canDelete}
                      canWrite={canWrite}
                      deletingAssetId={deletingAssetId}
                      isDeleteProtected={isDeleteProtected}
                      onPreview={(asset) => setPreviewAsset({ ...asset, kind: 'media' })}
                      onPreviewDocument={(document) => setPreviewAsset({ ...document, kind: 'document' })}
                      onRemove={removeAsset}
                      onRequestDocumentExtraction={requestDocumentExtractionSuggestion}
                      downloadUrl={downloadUrl}
                      imageFallback={imageFallback}
                      loadingDocumentExtractionId={loadingDocumentExtractionId}
                      renderDocumentDetails={(document) => (
                        <>
                          {document.chunks && document.chunks.length > 0 && (
                            <div className="document-chunks">
                              <strong>引用片段</strong>
                              {document.chunks.slice(0, 3).map((chunk) => (
                                <blockquote key={chunk.id}>
                                  <span>#{chunk.sequence}</span>
                                  {chunk.text}
                                </blockquote>
                              ))}
                            </div>
                          )}
                          {documentExtractionError?.documentId === document.id && (
                            <span className="document-extraction-error">{documentExtractionError.message}</span>
                          )}
                          {documentExtractionSuggestion?.documentId === document.id && (
                            <div
                              className="document-extraction-panel"
                              aria-label={`字段抽取建议 ${document.name}`}
                            >
                              <div className="document-extraction-title">
                                <Sparkles size={16} />
                                <strong>字段抽取建议</strong>
                                <span>置信度 {Math.round(documentExtractionSuggestion.result.confidence * 100)}%</span>
                              </div>
                              <div className="document-extraction-fields">
                                {documentSuggestionFields(documentExtractionSuggestion.result).map(([label, value]) => (
                                  <div key={label}>
                                    <span>{label}</span>
                                    <strong>{value}</strong>
                                  </div>
                                ))}
                              </div>
                              {documentExtractionSuggestion.result.summary && (
                                <p>{documentExtractionSuggestion.result.summary}</p>
                              )}
                              {canWrite && (
                                <button
                                  type="button"
                                  className="document-extraction-apply"
                                  onClick={() => applyDocumentExtractionSuggestion(documentExtractionSuggestion.result)}
                                >
                                  <Check size={14} />
                                  套用建议到编辑表单
                                </button>
                              )}
                              {flattenSuggestionSources(documentExtractionSuggestion.result).length > 0 && (
                                <div className="document-extraction-sources">
                                  <strong>来源片段</strong>
                                  {flattenSuggestionSources(documentExtractionSuggestion.result).map((source) => (
                                    <blockquote key={`${source.fieldName}:${source.chunkId ?? source.snippet}`}>
                                      <span>{source.fieldName}</span>
                                      {source.snippet}
                                    </blockquote>
                                  ))}
                                </div>
                              )}
                            </div>
                          )}
                        </>
                      )}
                    />
                  </section>
                )}
              </section>

            </section>
          )}

          {selected && (
            <section className="graph graph-full-width">
                <div className="panel-title">
                  <GitBranch size={18} />
                  <span>Neo4j 知识图谱</span>
                </div>
                <div className="graph-mode-switch" aria-label="Neo4j graph mode">
                  <button
                    type="button"
                    className={graphMode === 'current' ? 'active' : ''}
                    onClick={() => setGraphMode('current')}
                  >
                    当前展项
                  </button>
                  <button
                    type="button"
                    className={graphMode === 'demo' ? 'active' : ''}
                    onClick={() => setGraphMode('demo')}
                  >
                    全库演示
                  </button>
                </div>
                <div className="graph-meta" aria-label="Neo4j graph metadata">
                  <span>数据源：{graphSourceLabel}</span>
                  <span>节点 {graph.nodes.length}{graphFilterLabel ? ` / ${rawGraph.nodes.length}` : ''}</span>
                  <span>关系 {graph.edges.length}{graphFilterLabel ? ` / ${rawGraph.edges.length}` : ''}</span>
                  {graphFilterLabel && <span>已筛选：{graphFilterLabel}</span>}
                  <div className="graph-highlight-depth" aria-label="graph highlight depth">
                    <span>高亮范围</span>
                    <button
                      type="button"
                      className={graphHighlightDepth === 1 ? 'active' : ''}
                      onClick={() => setGraphHighlightDepth(1)}
                    >
                      1跳
                    </button>
                    <button
                      type="button"
                      className={graphHighlightDepth === 2 ? 'active' : ''}
                      onClick={() => setGraphHighlightDepth(2)}
                    >
                      2跳
                    </button>
                  </div>
                  <button type="button" className="graph-layout-button" onClick={relayoutGraph}>
                    重新布局
                  </button>
                </div>
                {graphError && <div className="graph-error">{graphError}</div>}
                <div className="graph-enhanced">
                  <div className="nvl-canvas" role="img" aria-label="Neo4j 交互式知识图谱">
                    <Suspense fallback={<div className="nvl-test-fallback">加载 Neo4j 图谱...</div>}>
                      <LazyNvlGraphView
                        graph={graph}
                        selectedNodeIds={selectedGraphNodeIds}
                        highlightDepth={graphHighlightDepth}
                        layoutVersion={graphLayoutVersion}
                        nodeColors={graphNodeColors}
                        onNodeToggle={toggleGraphNodeSelection}
                      />
                    </Suspense>
                  </div>
                  <aside className="graph-inspector">
                    {selectedGraphNode && (
                      <div className="graph-node-detail">
                        <strong>节点详情</strong>
                        <dl>
                          <div>
                            <dt>id</dt>
                            <dd>{selectedGraphNode.id}</dd>
                          </div>
                          <div>
                            <dt>label</dt>
                            <dd>{selectedGraphNode.label}</dd>
                          </div>
                          <div>
                            <dt>type</dt>
                            <dd>{nodeKindCaption(selectedGraphNode.kind)}</dd>
                          </div>
                        </dl>
                      </div>
                    )}
                    <div className="graph-legend" aria-label="graph node type legend">
                      <button
                        type="button"
                        className={!activeGraphNodeKind ? 'active' : ''}
                        onClick={() => setActiveGraphNodeKind(null)}
                      >
                        全部
                      </button>
                      {graphKindOptions.map((kind) => (
                        <button
                          type="button"
                          key={kind}
                          className={activeGraphNodeKind === kind ? 'active' : ''}
                          onClick={() => setActiveGraphNodeKind((current) => (current === kind ? null : kind))}
                        >
                          <i style={{ background: graphNodeColors[kind] ?? '#607d75' }} />
                          {nodeKindCaption(kind)}
                        </button>
                      ))}
                    </div>
                    <div className="graph-node-list" aria-label="graph nodes">
                      {graph.nodes.map((node) => (
                        <button
                          type="button"
                          key={node.id}
                          className={selectedGraphNodeIds.includes(node.id) ? 'active' : ''}
                          onClick={() => toggleGraphNodeSelection(node.id)}
                        >
                          <span>{node.label}</span>
                          <small>{nodeKindCaption(node.kind)}</small>
                        </button>
                      ))}
                    </div>
                  </aside>
                </div>
            </section>
          )}
        </div>
      </section>
    </main>
  );
}

function Select({
  label,
  value,
  values,
  onChange
}: {
  label: string;
  value?: string;
  values: SelectOption[];
  onChange: (value: string) => void;
}) {
  return (
    <label>
      {label}
      <select value={value ?? ''} onChange={(event) => onChange(event.target.value)}>
        <option value="">全部</option>
        {values.map((item) => (
          <option key={typeof item === 'string' ? item : item.value} value={typeof item === 'string' ? item : item.value}>
            {typeof item === 'string' ? item : item.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

function SystemStatusCard({ status }: { status: SystemStatus }) {
  const authLabel = status.auth.roleHeaderAuthEnabled ? '演示角色头可用' : '仅登录令牌';
  const neo4jLabel = status.neo4jDemo.enabled
    ? status.neo4jDemo.configured
      ? '已配置'
      : '回退演示数据'
    : '未启用';

  return (
    <div className="system-status-grid" aria-label="系统状态详情">
      <div>
        <span>服务</span>
        <strong>{systemStatusLabel(status.status)}</strong>
      </div>
      <div>
        <span>仓储</span>
        <strong>{systemStatusLabel(status.repository.kind)}</strong>
        <small>{status.repository.databaseUrlConfigured ? '已配置数据库' : '未配置数据库'}</small>
      </div>
      <div>
        <span>文件存储</span>
        <strong>{systemStatusLabel(status.storage.backend)}</strong>
        <small>{status.storage.configuredBackend}</small>
      </div>
      <div>
        <span>认证</span>
        <strong>{authLabel}</strong>
        <small>令牌 {formatTokenTtl(status.auth.tokenTtlSeconds)}</small>
      </div>
      <div>
        <span>Neo4j 演示</span>
        <strong>{neo4jLabel}</strong>
        <small>{status.neo4jDemo.uriConfigured ? 'URI 已配置' : '使用内置回退'}</small>
      </div>
      <div>
        <span>数据量</span>
        <strong>{status.counts.exhibits} 展项</strong>
        <small>{status.counts.auditLogs} 条日志</small>
      </div>
    </div>
  );
}

function DashboardBars({ title, items }: { title: string; items: Array<[string, number]> }) {
  if (items.length === 0) return null;
  return (
    <div className="dashboard-group">
      <h3>{title}</h3>
      <div className="mini-bars">
        {items.map(([label, count]) => (
          <span key={label}>
            <i style={{ width: `${Math.max(count * 34, 18)}px` }} />
            {label} {count}
          </span>
        ))}
      </div>
    </div>
  );
}

function Fact({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
