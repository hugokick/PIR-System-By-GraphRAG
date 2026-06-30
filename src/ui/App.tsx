import { FormEvent, SyntheticEvent, useEffect, useMemo, useState } from 'react';
import {
  BarChart3,
  Database,
  FilePlus2,
  Filter,
  GitBranch,
  ImageIcon,
  RotateCcw,
  Search,
  Sparkles
} from 'lucide-react';
import { buildGraph, graphStats } from '../lib/graph';
import { fetchExhibits } from '../lib/api';
import { filterExhibits, formatBudget, semanticSearch } from '../lib/search';
import { loadExhibits, resetExhibits, saveExhibits } from '../lib/storage';
import type { Exhibit, ExhibitFilters, ExhibitStatus, MediaAsset } from '../types';

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

function graphNodePosition(index: number, total: number) {
  if (index === 0) return { left: '50%', top: '50%' };
  const angle = ((index - 1) / Math.max(total - 1, 1)) * Math.PI * 2 - Math.PI / 2;
  return {
    left: `${50 + Math.cos(angle) * 34}%`,
    top: `${50 + Math.sin(angle) * 34}%`
  };
}

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

function makeExhibitFromForm(form: HTMLFormElement): Exhibit {
  const data = new FormData(form);
  const list = (key: string) =>
    String(data.get(key) ?? '')
      .split(/[，,、]/)
      .map((item) => item.trim())
      .filter(Boolean);

  return {
    id: `exhibit-${Date.now()}`,
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
    media: [],
    relatedProjectIds: list('relatedProjectIds'),
    relatedExhibitIds: []
  };
}

export function App() {
  const [items, setItems] = useState<Exhibit[]>(() => loadExhibits());
  const [filters, setFilters] = useState<ExhibitFilters>(emptyFilters);
  const [semanticQuery, setSemanticQuery] = useState('找几个适合低龄儿童、预算不高、互动性强的力学展项');
  const [selectedId, setSelectedId] = useState(items[0]?.id ?? '');
  const [showForm, setShowForm] = useState(false);
  const [dataSource, setDataSource] = useState<'loading' | 'api' | 'local'>('loading');
  const [loadError, setLoadError] = useState<string | null>(null);

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
  const graph = selected ? buildGraph(selected, items) : { nodes: [], edges: [] };
  const stats = useMemo(() => graphStats(items), [items]);

  const updateFilter = (key: keyof ExhibitFilters, value: string) => {
    setFilters((current) => ({ ...current, [key]: value }));
  };

  const addExhibit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const next = makeExhibitFromForm(event.currentTarget);
    if (!next.name || !next.category || !next.theme) return;
    const updated = [next, ...items];
    setItems(updated);
    saveExhibits(updated);
    setSelectedId(next.id);
    setDataSource('local');
    setLoadError('新增档案暂存于本地，后端写入接口将在下一阶段接入');
    setShowForm(false);
    event.currentTarget.reset();
  };

  const attachMedia = (event: FormEvent<HTMLInputElement>) => {
    if (!selected || !event.currentTarget.files?.length) return;
    const file = event.currentTarget.files[0];
    const url = URL.createObjectURL(file);
    const asset: MediaAsset = {
      id: `media-${Date.now()}`,
      type: file.type.startsWith('image/') ? 'image' : 'document',
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
  };

  const restoreSeed = () => {
    const restored = resetExhibits();
    setItems(restored);
    setSelectedId(restored[0].id);
    setDataSource('local');
    setLoadError('已恢复本地样例数据');
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
            <button type="button" onClick={() => setShowForm((value) => !value)}>
              <FilePlus2 size={18} />
              新增展项
            </button>
            <button type="button" onClick={restoreSeed}>
              <RotateCcw size={18} />
              恢复样例
            </button>
          </div>
        </header>

        {showForm && (
          <form className="create-form" onSubmit={addExhibit}>
            <input name="name" placeholder="展项名称" required />
            <input name="category" placeholder="类别，如基础科学" required />
            <input name="theme" placeholder="主题，如力学" required />
            <input name="venueType" placeholder="适用场馆" required />
            <input name="budgetMin" type="number" placeholder="最低造价" required />
            <input name="budgetMax" type="number" placeholder="最高造价" required />
            <input name="materials" placeholder="材料，用逗号分隔" />
            <input name="interactions" placeholder="交互方式，用逗号分隔" />
            <input name="dimensions" placeholder="尺寸" />
            <input name="supplier" placeholder="供应商" />
            <input name="owner" placeholder="业主" />
            <input name="projectYear" type="number" defaultValue={new Date().getFullYear()} />
            <select name="status" defaultValue="概念方案">
              {statuses.map((status) => (
                <option key={status}>{status}</option>
              ))}
            </select>
            <input name="tags" placeholder="标签，用逗号分隔" />
            <input name="relatedProjectIds" placeholder="项目编号，用逗号分隔" />
            <textarea name="description" placeholder="展项说明" required />
            <button type="submit">保存档案</button>
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
                <label className="upload">
                  <ImageIcon size={18} />
                  上传媒体
                  <input type="file" accept="image/*,.pdf,.doc,.docx,.xlsx" onChange={attachMedia} />
                </label>
                {selected.media.map((asset) => (
                  <a key={asset.id} href={asset.url} target="_blank" rel="noreferrer">
                    {asset.name}
                  </a>
                ))}
              </div>

              <section className="graph">
                <div className="panel-title">
                  <GitBranch size={18} />
                  <span>轻量知识图谱</span>
                </div>
                <div className="graph-canvas">
                  {graph.nodes.map((node, index) => (
                    <div className={`graph-node ${node.kind}`} key={node.id} style={graphNodePosition(index, graph.nodes.length)}>
                      {node.label}
                    </div>
                  ))}
                </div>
                <div className="edge-list">
                  {graph.edges.map((edge) => (
                    <span key={`${edge.source}-${edge.target}-${edge.label}`}>
                      {edge.label} {'->'} {graph.nodes.find((node) => node.id === edge.target)?.label}
                    </span>
                  ))}
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
