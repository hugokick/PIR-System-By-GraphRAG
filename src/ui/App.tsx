import { FormEvent, Suspense, SyntheticEvent, lazy, useEffect, useMemo, useState } from 'react';
import {
  BarChart3,
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
  fetchAuditLogs,
  fetchDemoGraph,
  fetchExhibitGraph,
  fetchExhibits,
  importTemplateUrl,
  importExhibits,
  login,
  setApiRole,
  setApiSession,
  updateExhibit,
  uploadExhibitAsset,
  type ExhibitImportResult,
  type UserRole
} from '../lib/api';
import { filterExhibits, formatBudget, semanticSearch } from '../lib/search';
import { loadExhibits, resetExhibits, saveExhibits } from '../lib/storage';
import type {
  AuditLogEntry,
  DocumentAsset,
  Exhibit,
  ExhibitFilters,
  ExhibitStatus,
  GraphEdge,
  GraphNode,
  GraphRagAnswer,
  MediaAsset,
  UserSession
} from '../types';

const statuses: ExhibitStatus[] = ['概念方案', '深化设计', '制作中', '已落地', '维护中'];
const emptyFilters: ExhibitFilters = {
  keyword: '',
  category: '',
  theme: '',
  venueType: '',
  material: '',
  interaction: '',
  status: ''
};

const documentExtensions = new Set(['pdf', 'doc', 'docx', 'xls', 'xlsx', 'csv', 'ppt', 'pptx']);
const userRoles: UserRole[] = ['admin', 'editor', 'viewer'];

function readInitialRole(): UserRole {
  let stored: string | null = null;
  try {
    stored = globalThis.localStorage?.getItem('pir-system-role') ?? null;
  } catch {
    stored = null;
  }
  return userRoles.includes(stored as UserRole) ? (stored as UserRole) : 'admin';
}

function storeRole(role: UserRole) {
  try {
    globalThis.localStorage?.setItem('pir-system-role', role);
  } catch {
    // Storage can be unavailable in restricted test/browser contexts.
  }
}

const graphNodeColors: Record<string, string> = {
  exhibit: '#0f8b78',
  project: '#d18a24',
  owner: '#4361a8',
  material: '#6b7a30',
  supplier: '#7a4f9f',
  theme: '#8b4d2f',
  interaction: '#c05621',
  document: '#50677d'
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

function isPdfDocument(document: DocumentAsset) {
  return document.fileType.toLowerCase() === 'pdf';
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
    projectYear: Number(data.get('projectYear') ?? new Date().getFullYear()),
    owner: String(data.get('owner') ?? '').trim(),
    status: String(data.get('status') ?? '概念方案') as ExhibitStatus,
    description: String(data.get('description') ?? '').trim(),
    tags: list('tags'),
    media: existingItem?.media ?? [],
    documents: existingItem?.documents ?? [],
    relatedProjectIds: list('relatedProjectIds'),
    relatedExhibitIds: list('relatedExhibitIds')
  };
}

export function App() {
  const [items, setItems] = useState<Exhibit[]>(() => loadExhibits());
  const [role, setRole] = useState<UserRole>(() => {
    const initialRole = readInitialRole();
    setApiRole(initialRole);
    return initialRole;
  });
  const [filters, setFilters] = useState<ExhibitFilters>(emptyFilters);
  const [semanticQuery, setSemanticQuery] = useState('找几个适合低龄儿童、预算不高、互动性强的力学展项');
  const [graphRagQuery, setGraphRagQuery] = useState('pulley-wall');
  const [graphRagAnswer, setGraphRagAnswer] = useState<GraphRagAnswer | null>(null);
  const [graphRagError, setGraphRagError] = useState<string | null>(null);
  const [isAskingGraphRag, setIsAskingGraphRag] = useState(false);
  const [session, setSession] = useState<UserSession | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [selectedId, setSelectedId] = useState(items[0]?.id ?? '');
  const [showForm, setShowForm] = useState(false);
  const [dataSource, setDataSource] = useState<'loading' | 'api' | 'local'>('loading');
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [importPreview, setImportPreview] = useState<{ file: File; result: ExhibitImportResult } | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [auditError, setAuditError] = useState<string | null>(null);
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
  const [selectedGraphNodeId, setSelectedGraphNodeId] = useState<string | null>(null);
  const [graphLayoutVersion, setGraphLayoutVersion] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setDataSource('loading');

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

    return () => {
      cancelled = true;
    };
  }, [filters]);

  const options = useMemo(
    () => ({
      categories: uniqueValues(items, (item) => item.category),
      themes: uniqueValues(items, (item) => item.theme),
      venueTypes: uniqueValues(items, (item) => item.venueType),
      materials: uniqueValues(items, (item) => item.materials),
      interactions: uniqueValues(items, (item) => item.interactions)
    }),
    [items]
  );

  const filteredItems = useMemo(() => filterExhibits(items, filters), [items, filters]);
  const semanticResults = useMemo(() => semanticSearch(items, semanticQuery).slice(0, 4), [items, semanticQuery]);
  const selected = items.find((item) => item.id === selectedId) ?? filteredItems[0] ?? items[0];
  const editingItem = editingId ? items.find((item) => item.id === editingId) : undefined;
  const fallbackGraph = useMemo(() => (selected ? buildGraph(selected, items) : { nodes: [], edges: [] }), [selected, items]);
  const isRemoteGraph = Boolean(remoteGraph && remoteGraph.exhibitId === selected?.id);
  const graph =
    graphMode === 'demo'
      ? demoGraph ?? { nodes: [], edges: [] }
      : remoteGraph && remoteGraph.exhibitId === selected?.id
        ? remoteGraph
        : fallbackGraph;
  const graphSourceLabel = graphMode === 'demo' || isRemoteGraph ? 'Neo4j 图数据库' : '本地轻量图谱';
  const selectedGraphNode = graph.nodes.find((node) => node.id === selectedGraphNodeId) ?? graph.nodes[0] ?? null;
  const stats = useMemo(() => graphStats(items), [items]);
  const canWrite = role !== 'viewer';
  const canDelete = role === 'admin';

  useEffect(() => {
    if (session) {
      setApiSession(session);
    } else {
      setApiSession(null);
      setApiRole(role);
    }
    storeRole(role);
  }, [role, session]);

  useEffect(() => {
    if (role !== 'admin') {
      setAuditLogs([]);
      setAuditError(null);
      return;
    }

    let cancelled = false;
    fetchAuditLogs(8)
      .then((logs) => {
        if (cancelled) return;
        setAuditLogs(logs);
        setAuditError(null);
      })
      .catch(() => {
        if (cancelled) return;
        setAuditLogs([]);
        setAuditError('操作日志暂不可用');
      });

    return () => {
      cancelled = true;
    };
  }, [role]);

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
    if (graph.nodes.length === 0) {
      setSelectedGraphNodeId(null);
      return;
    }
    if (!selectedGraphNodeId || !graph.nodes.some((node) => node.id === selectedGraphNodeId)) {
      setSelectedGraphNodeId(graph.nodes[0].id);
    }
  }, [graph.nodes, selectedGraphNodeId]);

  const updateFilter = (key: keyof ExhibitFilters, value: string) => {
    setFilters((current) => ({ ...current, [key]: value }));
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
    setShowForm(true);
    setLoadError(null);
  };

  const deleteSelected = async () => {
    if (!canDelete || !selected || isDeleting) return;
    setIsDeleting(true);
    const updated = items.filter((item) => item.id !== selected.id);

    try {
      await deleteExhibit(selected.id);
      setItems(updated);
      setSelectedId(updated[0]?.id ?? '');
      setDataSource('api');
      setLoadError(null);
    } catch {
      setItems(updated);
      saveExhibits(updated);
      setSelectedId(updated[0]?.id ?? '');
      setDataSource('local');
      setLoadError('后端删除失败，已仅从本地列表移除');
    } finally {
      setIsDeleting(false);
    }
  };

  const submitGraphRagQuestion = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const query = graphRagQuery.trim();
    if (!query || isAskingGraphRag) return;

    setIsAskingGraphRag(true);
    setGraphRagError(null);
    try {
      const answer = await askGraphRag(query, 3);
      setGraphRagAnswer(answer);
      if (answer.items[0]) {
        setSelectedId(answer.items[0].exhibit.id);
      }
    } catch {
      setGraphRagError('GraphRAG 问答接口暂不可用，请稍后重试');
    } finally {
      setIsAskingGraphRag(false);
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
    } catch {
      setDataSource('local');
      setLoadError('表格导入失败，请检查字段模板和网络连接');
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
        setSelectedGraphNodeId(null);
        setGraphLayoutVersion((value) => value + 1);
      }
      setImportPreview(null);
      setDataSource('api');
      setLoadError('导入完成：已选中新展项，可在当前展项图谱核验关系');
    } catch {
      setDataSource('local');
      setLoadError('表格导入失败，请检查字段模板和网络连接');
    } finally {
      setIsImporting(false);
    }
  };

  const relayoutGraph = () => {
    setGraphLayoutVersion((value) => value + 1);
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
          <Select label="材料" value={filters.material} values={options.materials} onChange={(value) => updateFilter('material', value)} />
          <Select label="交互方式" value={filters.interaction} values={options.interactions} onChange={(value) => updateFilter('interaction', value)} />
          <Select label="状态" value={filters.status} values={statuses} onChange={(value) => updateFilter('status', value)} />
          <div className="filter-actions">
            <button type="button" onClick={() => setFilters(emptyFilters)}>
              <RotateCcw size={16} />
              重置
            </button>
          </div>
        </section>

        <section className="panel stats">
          <div className="panel-title">
            <BarChart3 size={18} />
            <span>数据看板</span>
          </div>
          <div className="stat-grid">
            <Metric label="展项" value={stats.total} />
            <Metric label="已落地" value={stats.landed} />
            <Metric label="均价" value={`${stats.avgBudget}万`} />
          </div>
          <div className="mini-bars">
            {stats.categories.map(([label, count]) => (
              <span key={label}>
                <i style={{ width: `${Math.max(count * 34, 18)}px` }} />
                {label} {count}
              </span>
            ))}
          </div>
        </section>

        {role === 'admin' && (
          <section className="panel audit-panel">
            <div className="panel-title">
              <FileText size={18} />
              <span>操作日志</span>
            </div>
            {auditError && <p className="audit-error">{auditError}</p>}
            {!auditError && auditLogs.length === 0 && <p className="audit-empty">暂无操作记录</p>}
            <div className="audit-list">
              {auditLogs.map((entry) => (
                <div className="audit-item" key={entry.id}>
                  <div>
                    <strong>{entry.action}</strong>
                    <span>{entry.summary}</span>
                  </div>
                  <small>
                    {entry.actorRole} / {entry.resourceId}
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
            <label className="role-select">
              Role
              <select
                value={role}
                onChange={(event) => {
                  setSession(null);
                  setApiSession(null);
                  setRole(event.target.value as UserRole);
                }}
              >
                {userRoles.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </label>
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
                    <span>第 {error.row} 行</span>
                    <strong>{error.field}</strong>
                    <em>{error.message}</em>
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
          <form key={editingId ?? 'new-exhibit'} className="create-form" onSubmit={addExhibit}>
            <input name="name" placeholder="展项名称" defaultValue={editingItem?.name ?? ''} required />
            <input name="category" placeholder="类别，如基础科学" defaultValue={editingItem?.category ?? ''} required />
            <input name="theme" placeholder="主题，如力学" defaultValue={editingItem?.theme ?? ''} required />
            <input name="venueType" placeholder="适用场馆" defaultValue={editingItem?.venueType ?? ''} required />
            <input name="budgetMin" type="number" placeholder="最低造价" defaultValue={editingItem?.budgetMin ?? ''} required />
            <input name="budgetMax" type="number" placeholder="最高造价" defaultValue={editingItem?.budgetMax ?? ''} required />
            <input name="materials" placeholder="材料，用逗号分隔" defaultValue={editingItem?.materials.join(',') ?? ''} />
            <input name="interactions" placeholder="交互方式，用逗号分隔" defaultValue={editingItem?.interactions.join(',') ?? ''} />
            <input name="dimensions" placeholder="尺寸" defaultValue={editingItem?.dimensions ?? ''} />
            <input name="supplier" placeholder="供应商" defaultValue={editingItem?.supplier ?? ''} />
            <input name="owner" placeholder="业主" defaultValue={editingItem?.owner ?? ''} />
            <input name="projectYear" type="number" defaultValue={editingItem?.projectYear ?? new Date().getFullYear()} />
            <select name="status" defaultValue={editingItem?.status ?? statuses[0]}>
              {statuses.map((status) => (
                <option key={status}>{status}</option>
              ))}
            </select>
            <input name="tags" placeholder="标签，用逗号分隔" defaultValue={editingItem?.tags.join(',') ?? ''} />
            <input name="relatedProjectIds" placeholder="项目编号，用逗号分隔" defaultValue={editingItem?.relatedProjectIds.join(',') ?? ''} />
            <input
              name="relatedExhibitIds"
              placeholder="相似展项 ID，用逗号分隔"
              defaultValue={editingItem?.relatedExhibitIds.join(',') ?? ''}
            />
            <textarea name="description" placeholder="展项说明" defaultValue={editingItem?.description ?? ''} required />
            <button type="submit" disabled={isSaving || !canWrite}>{isSaving ? '保存中' : editingId ? '保存修改' : '保存档案'}</button>
          </form>
        )}

        <section className="semantic-panel">
          <div className="semantic-input">
            <Sparkles size={20} />
            <input value={semanticQuery} onChange={(event) => setSemanticQuery(event.target.value)} />
          </div>
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
                <div className="graphrag-citations">
                  {graphRagAnswer.citations.map((citation) => (
                    <span key={`${citation.sourceType}-${citation.sourceId}`}>
                      <strong>{citation.title}</strong>
                      {citation.snippet}
                    </span>
                  ))}
                </div>
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
                <em>{item.status}</em>
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
                <Fact label="业主" value={selected.owner} />
                <Fact label="供应商" value={selected.supplier} />
                <Fact label="尺寸" value={selected.dimensions} />
                <Fact label="状态" value={selected.status} />
              </div>

              <div className="chips">
                {[...selected.materials, ...selected.interactions, ...selected.tags].map((tag) => (
                  <span key={tag}>{tag}</span>
                ))}
              </div>

              <div className="media-row">
                <button type="button" className="secondary-action" onClick={() => startEdit(selected)} disabled={!canWrite}>
                  <Pencil size={18} />
                  编辑档案
                </button>
                <button type="button" className="danger-action" onClick={deleteSelected} disabled={isDeleting || !canDelete}>
                  <Trash2 size={18} />
                  {isDeleting ? '删除中' : '删除档案'}
                </button>
                <label className="upload">
                  <ImageIcon size={18} />
                  上传媒体
                  <input type="file" accept="image/*,.pdf,.doc,.docx,.xlsx" onChange={attachMedia} disabled={!canWrite} />
                </label>
                {selected.media.map((asset) => (
                  <a key={asset.id} href={asset.url} target="_blank" rel="noreferrer">
                    {asset.name}
                  </a>
                ))}
              </div>

              {selected.documents.length > 0 && (
                <div className="document-list">
                  <div className="panel-title">
                    <FileText size={18} />
                    <span>资料文档</span>
                  </div>
                  <div className="document-items">
                    {selected.documents.map((document) => (
                      <div className="document-item" key={document.id}>
                        <div className="document-heading">
                          <a href={document.url} target="_blank" rel="noreferrer">
                            <FileText size={16} />
                            <span>{document.name}</span>
                          </a>
                          {document.sourceNote && <small>{document.sourceNote}</small>}
                        </div>
                        {isPdfDocument(document) && (
                          <iframe
                            className="document-preview"
                            src={document.url}
                            title={`${document.name} 预览`}
                          />
                        )}
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
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <section className="graph">
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
                  <span>节点 {graph.nodes.length}</span>
                  <span>关系 {graph.edges.length}</span>
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
                        selectedNodeId={selectedGraphNodeId}
                        layoutVersion={graphLayoutVersion}
                        nodeColors={graphNodeColors}
                        onNodeSelect={setSelectedGraphNodeId}
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
                            <dd>{selectedGraphNode.kind}</dd>
                          </div>
                        </dl>
                      </div>
                    )}
                    <div className="graph-legend" aria-label="graph node type legend">
                      {[...new Set(graph.nodes.map((node) => node.kind))].map((kind) => (
                        <span key={kind}>
                          <i style={{ background: graphNodeColors[kind] ?? '#607d75' }} />
                          {kind}
                        </span>
                      ))}
                    </div>
                    <div className="graph-node-list" aria-label="graph nodes">
                      {graph.nodes.map((node) => (
                        <button
                          type="button"
                          key={node.id}
                          className={node.id === selectedGraphNode?.id ? 'active' : ''}
                          onClick={() => setSelectedGraphNodeId(node.id)}
                        >
                          <span>{node.label}</span>
                          <small>{node.kind}</small>
                        </button>
                      ))}
                    </div>
                    <div className="edge-list">
                      {graph.edges.map((edge) => (
                        <span key={`${edge.source}-${edge.target}-${edge.label}`}>
                          <strong>{edge.type ?? edge.label}</strong>
                          {' ->'} {graph.nodes.find((node) => node.id === edge.target)?.label}
                        </span>
                      ))}
                    </div>
                  </aside>
                </div>
              </section>
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
  values: string[];
  onChange: (value: string) => void;
}) {
  return (
    <label>
      {label}
      <select value={value ?? ''} onChange={(event) => onChange(event.target.value)}>
        <option value="">全部</option>
        {values.map((item) => (
          <option key={item} value={item}>
            {item}
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

function Fact({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
