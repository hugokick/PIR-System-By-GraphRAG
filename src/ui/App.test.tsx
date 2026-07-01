import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { App } from './App';
import { mapExhibitToApiPayload, type ApiExhibit } from '../lib/api';
import type { Exhibit } from '../types';

vi.mock('@neo4j-nvl/react', () => ({
  InteractiveNvlWrapper: ({ nodes, rels }: { nodes: { id: string; caption?: string }[]; rels: { id: string; caption?: string }[] }) => (
    <div data-testid="mock-nvl">
      {nodes.map((node) => (
        <span key={node.id}>{node.caption ?? node.id}</span>
      ))}
      {rels.map((rel) => (
        <span key={rel.id}>{rel.caption ?? rel.id}</span>
      ))}
    </div>
  )
}));

vi.mock('../lib/storage', () => ({
  loadExhibits: () => [],
  resetExhibits: () => [],
  saveExhibits: vi.fn()
}));

const frontendExhibit: Exhibit = {
  id: 'magnet-maze',
  name: '磁力迷宫',
  category: '基础科学',
  theme: '电磁学',
  venueType: '儿童科技馆',
  budgetMin: 180000,
  budgetMax: 320000,
  materials: ['亚克力'],
  dimensions: '3600x1800x1800mm',
  interactions: ['动手实验'],
  supplier: '启思互动工坊',
  projectYear: 2024,
  owner: '青禾儿童科技馆',
  status: '概念方案',
  reviewStatus: '待审核',
  description: '通过磁铁和轨道迷宫演示磁力吸引与排斥。',
  tags: ['低龄儿童', '电磁学'],
  media: [],
  documents: [],
  relatedProjectIds: ['qinghe-2024'],
  relatedExhibitIds: ['lever-play']
};

function apiExhibit(item: Exhibit = frontendExhibit): ApiExhibit {
  return mapExhibitToApiPayload(item);
}

function okJson(payload: unknown): Response {
  return {
    ok: true,
    json: async () => payload
  } as Response;
}

function installMemoryStorage() {
  const entries = new Map<string, string>();
  const storage = {
    getItem: vi.fn((key: string) => entries.get(key) ?? null),
    setItem: vi.fn((key: string, value: string) => {
      entries.set(key, value);
    }),
    removeItem: vi.fn((key: string) => {
      entries.delete(key);
    }),
    clear: vi.fn(() => {
      entries.clear();
    })
  };
  vi.stubGlobal('localStorage', storage);
  return storage;
}

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('App exhibit management', () => {
  it('shows a lightweight placeholder while the Neo4j graph renderer is lazy loaded', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith('/api/exhibits/magnet-maze/graph')) {
        return okJson({
          nodes: [{ id: 'exhibit:magnet-maze', label: 'Current Exhibit', type: 'exhibit' }],
          edges: []
        });
      }
      return okJson({ total: 1, items: [apiExhibit()] });
    });

    render(<App />);

    expect(await screen.findByText('加载 Neo4j 图谱...')).toBeTruthy();
  });

  it('renders graph nodes from the backend graph API', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith('/api/exhibits/magnet-maze/graph')) {
        return okJson({
          nodes: [
            { id: 'exhibit:magnet-maze', label: '磁力迷宫', type: 'exhibit' },
            { id: 'material:backend-only', label: '后端图谱材料', type: 'material' }
          ],
          edges: [
            {
              source: 'exhibit:magnet-maze',
              target: 'material:backend-only',
              label: '使用材料',
              type: 'uses_material'
            }
          ]
        });
      }
      return okJson({ total: 1, items: [apiExhibit()] });
    });

    render(<App />);

    expect(await screen.findByText('后端图谱材料')).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledWith('http://127.0.0.1:8000/api/exhibits/magnet-maze/graph');
  });

  it('renders Neo4j graph metadata and selected node details without a duplicated relationship list', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith('/api/exhibits/magnet-maze/graph')) {
        return okJson({
          nodes: [
            { id: 'exhibit:magnet-maze', label: '纾佸姏杩峰', type: 'exhibit' },
            { id: 'material:backend-only', label: 'Backend Material', type: 'material' },
            { id: 'supplier:neo4j-demo', label: 'Neo4j Demo Supplier', type: 'supplier' }
          ],
          edges: [
            {
              source: 'exhibit:magnet-maze',
              target: 'material:backend-only',
              label: '浣跨敤鏉愭枡',
              type: 'USES_MATERIAL'
            },
            {
              source: 'exhibit:magnet-maze',
              target: 'supplier:neo4j-demo',
              label: '供应商',
              type: 'SUPPLIED_BY'
            }
          ]
        });
      }
      return okJson({ total: 1, items: [apiExhibit()] });
    });

    render(<App />);

    expect(await screen.findByText('Neo4j 知识图谱')).toBeTruthy();
    expect(await screen.findByText('数据源：Neo4j 图数据库')).toBeTruthy();
    expect(await screen.findByText('节点 3')).toBeTruthy();
    expect(await screen.findByText('关系 2')).toBeTruthy();
    expect(screen.queryByText('USES_MATERIAL')).toBeNull();
    expect(screen.queryByText('SUPPLIED_BY')).toBeNull();
    expect(document.body.querySelector('.edge-list')).toBeNull();
    expect(screen.getByRole('button', { name: '重新布局' })).toBeTruthy();

    fireEvent.click(await screen.findByRole('button', { name: /Backend Material/ }));

    expect(screen.getByText('material:backend-only')).toBeTruthy();
    expect(screen.getAllByText('Backend Material').length).toBeGreaterThan(0);
    expect(screen.getAllByText('material').length).toBeGreaterThan(0);
    expect(fetchMock).toHaveBeenCalledWith('http://127.0.0.1:8000/api/exhibits/magnet-maze/graph');
  });

  it('marks the Neo4j graph panel as a full-width detail section', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith('/api/exhibits/magnet-maze/graph')) {
        return okJson({
          nodes: [{ id: 'exhibit:magnet-maze', label: 'Magnet Maze', type: 'exhibit' }],
          edges: []
        });
      }
      return okJson({ total: 1, items: [apiExhibit()] });
    });

    render(<App />);

    const title = await screen.findByText('Neo4j 知识图谱');
    expect(title.closest('section')?.classList.contains('graph-full-width')).toBe(true);
  });

  it('switches the graph panel to the full Neo4j demo graph', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith('/api/exhibits/magnet-maze/graph')) {
        return okJson({
          nodes: [
            { id: 'exhibit:magnet-maze', label: 'Current Exhibit', type: 'exhibit' },
            { id: 'material:current-only', label: 'Current Material', type: 'material' }
          ],
          edges: [
            {
              source: 'exhibit:magnet-maze',
              target: 'material:current-only',
              label: 'material',
              type: 'uses_material'
            }
          ]
        });
      }
      if (url.endsWith('/api/neo4j-demo/graph')) {
        return okJson({
          nodes: [
            { id: 'exhibit:lever-play', label: 'Lever Play', type: 'exhibit' },
            { id: 'exhibit:pulley-wall', label: 'Pulley Wall', type: 'exhibit' },
            { id: 'exhibit:water-cycle', label: 'Water Cycle', type: 'exhibit' },
            { id: 'exhibit:space-dome', label: 'Space Dome', type: 'exhibit' },
            { id: 'supplier:qisi', label: 'Qisi Supplier', type: 'supplier' }
          ],
          edges: [
            {
              source: 'exhibit:lever-play',
              target: 'supplier:qisi',
              label: 'supplier',
              type: 'supplied_by'
            },
            {
              source: 'exhibit:space-dome',
              target: 'supplier:qisi',
              label: 'supplier',
              type: 'supplied_by'
            }
          ]
        });
      }
      return okJson({ total: 1, items: [apiExhibit()] });
    });

    render(<App />);

    expect(await screen.findByText('Current Material')).toBeTruthy();

    fireEvent.click(screen.getByRole('button', { name: '全库演示' }));

    expect(await screen.findByText('Space Dome')).toBeTruthy();
    expect(await screen.findByText('节点 5')).toBeTruthy();
    expect(await screen.findByText('关系 2')).toBeTruthy();
    expect(await screen.findByText('数据源：Neo4j 图数据库')).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledWith('http://127.0.0.1:8000/api/neo4j-demo/graph');
  });

  it('prefills the selected exhibit and submits edits through the backend API', async () => {
    let updatedPayload: ApiExhibit | undefined;
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (_input, init) => {
      if (init && init.method === 'PUT') {
        const body = JSON.parse(String(init.body));
        updatedPayload = body;
        return okJson(body);
      }
      return okJson({ total: 1, items: [apiExhibit()] });
    });

    render(<App />);

    await screen.findByRole('heading', { name: '磁力迷宫' });
    fireEvent.click(screen.getByRole('button', { name: /编辑档案/ }));
    fireEvent.change(screen.getByPlaceholderText('展项名称'), { target: { value: '磁力迷宫 Pro' } });
    fireEvent.change(screen.getByLabelText('档案审核状态'), { target: { value: '已审核' } });
    fireEvent.change(screen.getByPlaceholderText('相似展项 ID，用逗号分隔'), { target: { value: 'lever-play,water-cycle' } });
    fireEvent.click(screen.getByRole('button', { name: '保存修改' }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        'http://127.0.0.1:8000/api/exhibits/magnet-maze',
        expect.objectContaining({
          method: 'PUT',
          body: expect.stringContaining('磁力迷宫 Pro')
        })
      );
    });
    expect(updatedPayload?.related_exhibit_ids).toEqual(['lever-play', 'water-cycle']);
    expect(updatedPayload?.review_status).toBe('已审核');
  });

  it('deletes the selected exhibit through the backend API', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (_input, init) => {
      if (init && init.method === 'DELETE') {
        return { ok: true } as Response;
      }
      return okJson({ total: 1, items: [apiExhibit()] });
    });

    render(<App />);

    await screen.findByRole('heading', { name: '磁力迷宫' });
    fireEvent.click(screen.getByRole('button', { name: /删除档案/ }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith('http://127.0.0.1:8000/api/exhibits/magnet-maze', {
        method: 'DELETE',
        headers: { 'X-User-Role': 'admin' }
      });
    });
  });

  it('protects approved or landed exhibits from direct deletion', async () => {
    const protectedExhibit = {
      ...frontendExhibit,
      status: '已落地',
      reviewStatus: '已审核'
    } satisfies Exhibit;
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockImplementation(async () => okJson({ total: 1, items: [apiExhibit(protectedExhibit)] }));

    render(<App />);

    await screen.findByRole('heading', { name: protectedExhibit.name });
    const deleteButton = document.querySelector('.danger-action') as HTMLButtonElement;

    expect(deleteButton.disabled).toBe(true);
    expect(screen.getByText('已审核/已落地档案受保护，请先退回审核或变更状态后再删除')).toBeTruthy();
    fireEvent.click(deleteButton);
    expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'DELETE')).toBe(false);
  });

  it('protects media and document assets on approved or landed exhibits from deletion', async () => {
    const protectedExhibit = apiExhibit({
      ...frontendExhibit,
      status: '已落地',
      reviewStatus: '已审核',
      media: [
        {
          id: 'protected-media',
          type: 'image',
          name: 'protected-scene.png',
          url: '/api/files/protected-scene',
          note: '受保护图片'
        }
      ],
      documents: [
        {
          id: 'protected-document',
          name: 'protected-note.txt',
          fileType: 'txt',
          url: '/api/files/protected-note',
          sourceNote: '受保护资料'
        }
      ]
    });
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async () => okJson({ total: 1, items: [protectedExhibit] }));

    render(<App />);

    const mediaDelete = await screen.findByRole('button', { name: '删除媒体 protected-scene.png' });
    const documentDelete = screen.getByRole('button', { name: '删除资料 protected-note.txt' });

    expect((mediaDelete as HTMLButtonElement).disabled).toBe(true);
    expect((documentDelete as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getAllByText('已审核/已落地档案资料受保护，请先退回审核或变更状态后再删除')).toHaveLength(2);
    fireEvent.click(mediaDelete);
    fireEvent.click(documentDelete);
    expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'DELETE')).toBe(false);
  });

  it('keeps the exhibit visible when backend deletion fails', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (_input, init) => {
      if (init && init.method === 'DELETE') {
        return {
          ok: false,
          status: 409,
          json: async () => ({
            detail: {
              error: 'ProtectedExhibit',
              message: 'Important exhibit records cannot be deleted directly',
              details: {}
            }
          })
        } as Response;
      }
      return okJson({ total: 1, items: [apiExhibit()] });
    });

    render(<App />);

    await screen.findByRole('heading', { name: frontendExhibit.name });
    fireEvent.click(screen.getByRole('button', { name: /删除档案/ }));

    expect(await screen.findByText('删除失败，请检查权限或档案保护状态')).toBeTruthy();
    expect(screen.getByRole('heading', { name: frontendExhibit.name })).toBeTruthy();
  });

  it('filters exhibits by budget range through backend query parameters', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async () => okJson({ total: 1, items: [apiExhibit()] }));

    render(<App />);

    await screen.findByRole('heading', { name: '磁力迷宫' });
    fireEvent.change(screen.getByLabelText('最低造价'), { target: { value: '200000' } });
    fireEvent.change(screen.getByLabelText('最高造价'), { target: { value: '500000' } });

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(([input]) =>
          String(input).includes('/api/exhibits?budget_min=200000&budget_max=500000')
        )
      ).toBe(true);
    });
  });

  it('filters exhibits by project case through backend query parameters', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async () => okJson({ total: 1, items: [apiExhibit()] }));

    render(<App />);

    await screen.findByRole('heading', { name: '磁力迷宫' });
    fireEvent.change(screen.getByLabelText('项目案例'), { target: { value: 'qinghe-2024' } });

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(([input]) =>
          String(input).includes('/api/exhibits?project_id=qinghe-2024')
        )
      ).toBe(true);
    });
  });

  it('renders and filters exhibits by review status through backend query parameters', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async () => okJson({ total: 1, items: [apiExhibit()] }));

    render(<App />);

    await screen.findByRole('heading', { name: '磁力迷宫' });
    expect(screen.getAllByText('待审核').length).toBeGreaterThan(0);
    fireEvent.change(screen.getByLabelText('审核状态'), { target: { value: '待审核' } });

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(([input]) =>
          String(input).includes('/api/exhibits?review_status=%E5%BE%85%E5%AE%A1%E6%A0%B8')
        )
      ).toBe(true);
    });
  });

  it('shows review workload metrics in the dashboard', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () =>
      okJson({
        total: 2,
        items: [
          apiExhibit({ ...frontendExhibit, id: 'pending-demo', name: '待审展项', reviewStatus: '待审核' }),
          apiExhibit({ ...frontendExhibit, id: 'rejected-demo', name: '退回展项', reviewStatus: '已退回' })
        ]
      })
    );

    render(<App />);

    expect((await screen.findAllByText('待审展项')).length).toBeGreaterThan(0);
    expect(screen.getAllByText('待审核').length).toBeGreaterThan(0);
    expect(screen.getAllByText('已退回').length).toBeGreaterThan(0);
    expect(screen.getByText('待审 1')).toBeTruthy();
    expect(screen.getByText('退回 1')).toBeTruthy();
  });

  it('lets admins approve the selected exhibit from the detail panel', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith('/api/exhibits/magnet-maze/review-status') && init?.method === 'PATCH') {
        expect(init.body).toBe(JSON.stringify({ review_status: '已审核' }));
        return okJson(apiExhibit({ ...frontendExhibit, reviewStatus: '已审核' }));
      }
      return okJson({ total: 1, items: [apiExhibit()] });
    });

    render(<App />);

    await screen.findByRole('heading', { name: '磁力迷宫' });
    fireEvent.click(screen.getByRole('button', { name: '通过审核' }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        'http://127.0.0.1:8000/api/exhibits/magnet-maze/review-status',
        expect.objectContaining({
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json', 'X-User-Role': 'admin' }
        })
      );
    });
    expect(screen.getAllByText('已审核').length).toBeGreaterThan(0);
  });

  it('lets users add a curated similar exhibit relation from the detail panel', async () => {
    const primary = { ...frontendExhibit, relatedExhibitIds: [] };
    const related = {
      ...frontendExhibit,
      id: 'lever-play',
      name: '杠杆乐园',
      relatedExhibitIds: []
    };
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith('/api/exhibits/magnet-maze/related-exhibits') && init?.method === 'PATCH') {
        expect(init.body).toBe(JSON.stringify({ related_exhibit_ids: ['lever-play'] }));
        return okJson(apiExhibit({ ...primary, relatedExhibitIds: ['lever-play'] }));
      }
      if (url.endsWith('/api/exhibits/magnet-maze/graph')) {
        return okJson({
          nodes: [{ id: 'exhibit:magnet-maze', label: '磁力迷宫', type: 'exhibit' }],
          edges: []
        });
      }
      return okJson({ total: 2, items: [apiExhibit(primary), apiExhibit(related)] });
    });

    render(<App />);

    await screen.findByRole('heading', { name: '磁力迷宫' });
    fireEvent.change(screen.getByLabelText('添加相似展项'), { target: { value: 'lever-play' } });
    fireEvent.click(screen.getByRole('button', { name: '添加关系' }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        'http://127.0.0.1:8000/api/exhibits/magnet-maze/related-exhibits',
        expect.objectContaining({
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json', 'X-User-Role': 'admin' }
        })
      );
    });
    expect(within(screen.getByLabelText('相似展项关系')).getByText('杠杆乐园')).toBeTruthy();
  });

  it('shows budget bands and hot themes in the dashboard', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () =>
      okJson({
        total: 3,
        items: [
          apiExhibit({
            ...frontendExhibit,
            id: 'low-budget-demo',
            name: '低预算展项',
            theme: '力学',
            budgetMin: 80000,
            budgetMax: 120000
          }),
          apiExhibit({
            ...frontendExhibit,
            id: 'mid-budget-demo',
            name: '中预算展项',
            theme: '力学',
            budgetMin: 200000,
            budgetMax: 500000
          }),
          apiExhibit({
            ...frontendExhibit,
            id: 'high-budget-demo',
            name: '高预算展项',
            theme: '天文',
            budgetMin: 900000,
            budgetMax: 1600000
          })
        ]
      })
    );

    render(<App />);

    expect((await screen.findAllByText('低预算展项')).length).toBeGreaterThan(0);
    expect(screen.getByText('预算区间')).toBeTruthy();
    expect(screen.getByText('20万以下 1')).toBeTruthy();
    expect(screen.getByText('20-50万 1')).toBeTruthy();
    expect(screen.getByText('50万以上 1')).toBeTruthy();
    expect(screen.getByText('热门主题')).toBeTruthy();
    expect(screen.getByText('力学 2')).toBeTruthy();
    expect(screen.getByText('天文 1')).toBeTruthy();
  });

  it('uses backend dashboard summary metrics when the API is available', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (url.includes('/api/dashboard/summary')) {
        return okJson({
          total: 9,
          landed: 4,
          avg_budget: 38,
          pending_review: 2,
          rejected_review: 1,
          categories: [{ label: '后端类别', count: 7 }],
          budget_bands: [{ label: '后端预算', count: 6 }],
          themes: [{ label: '后端主题', count: 5 }],
          review_statuses: [{ label: '后端审核', count: 2 }]
        });
      }
      return okJson({ total: 1, items: [apiExhibit()] });
    });

    render(<App />);

    expect(await screen.findByText('后端类别 7')).toBeTruthy();
    expect(screen.getByText('后端预算 6')).toBeTruthy();
    expect(screen.getByText('后端主题 5')).toBeTruthy();
    expect(screen.getByText('待审 2')).toBeTruthy();
    expect(screen.getByText('退回 1')).toBeTruthy();
    expect(screen.getByText('38万')).toBeTruthy();
    expect(fetchMock.mock.calls.some(([input]) => String(input).includes('/api/dashboard/summary'))).toBe(true);
  });

  it('lets users manually refresh backend dashboard summary metrics', async () => {
    let dashboardCalls = 0;
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (url.includes('/api/dashboard/summary')) {
        dashboardCalls += 1;
        return okJson({
          total: dashboardCalls > 1 ? 12 : 9,
          landed: dashboardCalls > 1 ? 6 : 4,
          avg_budget: dashboardCalls > 1 ? 52 : 38,
          pending_review: 2,
          rejected_review: 1,
          categories: [{ label: dashboardCalls > 1 ? 'Dashboard Fresh' : 'Dashboard Initial', count: dashboardCalls > 1 ? 8 : 7 }],
          budget_bands: [{ label: 'Budget Fresh', count: dashboardCalls > 1 ? 9 : 6 }],
          themes: [{ label: 'Theme Fresh', count: dashboardCalls > 1 ? 4 : 3 }],
          review_statuses: [{ label: 'Review Fresh', count: 2 }]
        });
      }
      return okJson({ total: 1, items: [apiExhibit()] });
    });

    render(<App />);

    const dashboardPanel = (await screen.findByText('数据看板')).closest('section') as HTMLElement;
    expect(await within(dashboardPanel).findByText('Dashboard Initial 7')).toBeTruthy();
    fireEvent.click(within(dashboardPanel).getByRole('button', { name: '刷新数据看板' }));

    expect(await within(dashboardPanel).findByText('Dashboard Fresh 8')).toBeTruthy();
    expect(within(dashboardPanel).getByText('52万')).toBeTruthy();
    expect(fetchMock.mock.calls.filter(([input]) => String(input).includes('/api/dashboard/summary'))).toHaveLength(2);
  });

  it('disables write controls after switching to viewer role', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () => okJson({ total: 1, items: [apiExhibit()] }));

    render(<App />);

    await screen.findByRole('heading', { name: frontendExhibit.name });
    fireEvent.change(screen.getByLabelText('Role'), { target: { value: 'viewer' } });

    expect((screen.getByRole('button', { name: '新增展项' }) as HTMLButtonElement).disabled).toBe(true);
    expect((document.querySelector('.secondary-action') as HTMLButtonElement).disabled).toBe(true);
    expect((document.querySelector('.danger-action') as HTMLButtonElement).disabled).toBe(true);
    expect((document.querySelector('.upload input') as HTMLInputElement).disabled).toBe(true);
  });

  it('logs in with demo credentials and uses the returned bearer token for writes', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith('/api/auth/login')) {
        expect(init?.method).toBe('POST');
        expect(init?.body).toBe(JSON.stringify({ username: 'editor', password: 'editor123' }));
        return okJson({
          access_token: 'signed-token',
          token_type: 'bearer',
          user: {
            username: 'editor',
            role: 'editor',
            display_name: '编辑员'
          }
        });
      }
      if (init && init.method === 'PUT') {
        return okJson(JSON.parse(String(init.body)));
      }
      return okJson({ total: 1, items: [apiExhibit()] });
    });

    render(<App />);

    await screen.findByRole('heading', { name: frontendExhibit.name });
    fireEvent.change(screen.getByLabelText('用户名'), { target: { value: 'editor' } });
    fireEvent.change(screen.getByLabelText('密码'), { target: { value: 'editor123' } });
    fireEvent.click(screen.getByRole('button', { name: '登录' }));

    expect(await screen.findByText(/编辑员/)).toBeTruthy();

    fireEvent.click(screen.getByRole('button', { name: /编辑档案/ }));
    fireEvent.click(screen.getByRole('button', { name: '保存修改' }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        'http://127.0.0.1:8000/api/exhibits/magnet-maze',
        expect.objectContaining({
          method: 'PUT',
          headers: expect.objectContaining({ Authorization: 'Bearer signed-token' })
        })
      );
    });
  });

  it('restores a saved login session and uses its bearer token after reload', async () => {
    const storage = installMemoryStorage();
    storage.setItem(
      'pir-system-session',
      JSON.stringify({
        accessToken: 'persisted-token',
        tokenType: 'bearer',
        user: {
          username: 'admin',
          role: 'admin',
          displayName: '管理员'
        }
      })
    );

    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      if (init && init.method === 'PUT') {
        return okJson(JSON.parse(String(init.body)));
      }
      return okJson({ total: 1, items: [apiExhibit()] });
    });

    render(<App />);

    expect(await screen.findByText(/管理员/)).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: /编辑档案/ }));
    fireEvent.click(screen.getByRole('button', { name: '保存修改' }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        'http://127.0.0.1:8000/api/exhibits/magnet-maze',
        expect.objectContaining({
          method: 'PUT',
          headers: expect.objectContaining({ Authorization: 'Bearer persisted-token' })
        })
      );
    });
  });

  it('clears the saved login session when logging out', async () => {
    const storage = installMemoryStorage();
    storage.setItem(
      'pir-system-session',
      JSON.stringify({
        accessToken: 'persisted-token',
        tokenType: 'bearer',
        user: {
          username: 'admin',
          role: 'admin',
          displayName: '管理员'
        }
      })
    );
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () => okJson({ total: 1, items: [apiExhibit()] }));

    render(<App />);

    expect(await screen.findByText(/管理员/)).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: '退出' }));

    await waitFor(() => {
      expect(storage.removeItem).toHaveBeenCalledWith('pir-system-session');
    });
    expect(screen.getByRole('button', { name: '登录' })).toBeTruthy();
  });

  it('clears a saved login session when token validation fails', async () => {
    const storage = installMemoryStorage();
    storage.setItem(
      'pir-system-session',
      JSON.stringify({
        accessToken: 'stale-token',
        tokenType: 'bearer',
        user: {
          username: 'admin',
          role: 'admin',
          displayName: '管理员'
        }
      })
    );
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith('/api/auth/me')) {
        return { ok: false, status: 401, statusText: 'Unauthorized' } as Response;
      }
      return okJson({ total: 1, items: [apiExhibit()] });
    });

    render(<App />);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith('http://127.0.0.1:8000/api/auth/me', {
        headers: { Authorization: 'Bearer stale-token' }
      });
    });
    await waitFor(() => {
      expect(storage.removeItem).toHaveBeenCalledWith('pir-system-session');
    });
    expect(screen.getByRole('button', { name: '登录' })).toBeTruthy();
  });

  it('shows readable audit log entries to admins', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith('/api/admin/audit-logs?limit=8')) {
        return okJson({
          total: 3,
          items: [
            {
              id: 'audit-1',
              actor_role: 'admin',
              action: 'delete_exhibit',
              resource_type: 'exhibit',
              resource_id: 'magnet-maze',
              summary: 'Deleted exhibit magnet-maze',
              created_at: '2026-07-01T00:00:00+00:00'
            },
            {
              id: 'audit-2',
              actor_role: 'editor',
              action: 'update_exhibit_relations',
              resource_type: 'exhibit',
              resource_id: 'lever-play',
              summary: 'Updated related exhibits for lever-play',
              created_at: '2026-07-01T00:10:00+00:00'
            },
            {
              id: 'audit-3',
              actor_role: 'editor',
              action: 'import_batch',
              resource_type: 'exhibit',
              resource_id: 'exhibits.xlsx',
              summary: 'Imported spreadsheet exhibits.xlsx',
              created_at: '2026-07-01T00:20:00+00:00'
            }
          ]
        });
      }
      return okJson({ total: 1, items: [apiExhibit()] });
    });

    render(<App />);

    const auditPanel = (await screen.findByText('操作日志')).closest('section') as HTMLElement;
    expect(auditPanel).toBeTruthy();
    expect(within(auditPanel).getByText('删除档案')).toBeTruthy();
    expect(within(auditPanel).getByText('更新相似关系')).toBeTruthy();
    expect(within(auditPanel).getByText('批量导入')).toBeTruthy();
    expect(within(auditPanel).queryByText('delete_exhibit')).toBeNull();
    expect(within(auditPanel).queryByText('update_exhibit_relations')).toBeNull();
    expect(within(auditPanel).queryByText('import_batch')).toBeNull();
    expect(within(auditPanel).getByText(/2026-07-01 00:00/)).toBeTruthy();
    expect(screen.getAllByText(/magnet-maze/).length).toBeGreaterThan(0);
    expect(screen.getAllByText('admin').length).toBeGreaterThan(0);
    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/api/admin/audit-logs?limit=8',
      expect.objectContaining({ headers: { 'X-User-Role': 'admin' } })
    );
  });

  it('lets admins manually refresh audit log entries', async () => {
    let auditCalls = 0;
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith('/api/admin/audit-logs?limit=8')) {
        auditCalls += 1;
        return okJson({
          total: auditCalls > 1 ? 1 : 0,
          items:
            auditCalls > 1
              ? [
                  {
                    id: 'audit-refresh-manual',
                    actor_role: 'admin',
                    action: 'delete_exhibit',
                    resource_type: 'exhibit',
                    resource_id: 'manual-refresh-demo',
                    summary: 'Deleted exhibit manual-refresh-demo',
                    created_at: '2026-07-01T01:15:00+00:00'
                  }
                ]
              : []
        });
      }
      return okJson({ total: 1, items: [apiExhibit()] });
    });

    render(<App />);

    expect(await screen.findByText('暂无操作记录')).toBeTruthy();
    const auditPanel = screen.getByText('操作日志').closest('section') as HTMLElement;
    fireEvent.click(within(auditPanel).getByRole('button', { name: '刷新操作日志' }));

    expect(await within(auditPanel).findAllByText(/manual-refresh-demo/)).toHaveLength(2);
    expect(within(auditPanel).getByText('删除档案')).toBeTruthy();
    expect(fetchMock.mock.calls.filter(([input]) => String(input).endsWith('/api/admin/audit-logs?limit=8'))).toHaveLength(2);
  });

  it('refreshes audit log entries after admin mutations', async () => {
    let auditCalls = 0;
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith('/api/admin/audit-logs?limit=8')) {
        auditCalls += 1;
        return okJson({
          total: auditCalls > 1 ? 1 : 0,
          items:
            auditCalls > 1
              ? [
                  {
                    id: 'audit-delete-refresh',
                    actor_role: 'admin',
                    action: 'delete_exhibit',
                    resource_type: 'exhibit',
                    resource_id: 'magnet-maze',
                    summary: 'Deleted exhibit magnet-maze',
                    created_at: '2026-07-01T00:00:00+00:00'
                  }
                ]
              : []
        });
      }
      if (init?.method === 'DELETE') {
        return { ok: true } as Response;
      }
      return okJson({ total: 1, items: [apiExhibit()] });
    });

    render(<App />);

    expect(await screen.findByText('暂无操作记录')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: /删除档案/ }));

    const auditPanel = (await screen.findByText('操作日志')).closest('section') as HTMLElement;
    expect(await within(auditPanel).findByText('删除档案')).toBeTruthy();
    expect(fetchMock.mock.calls.filter(([input]) => String(input).endsWith('/api/admin/audit-logs?limit=8'))).toHaveLength(2);
  });

  it('hides audit log entries from viewers', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async () => okJson({ total: 1, items: [apiExhibit()] }));

    render(<App />);

    await screen.findByRole('heading', { name: frontendExhibit.name });
    fetchMock.mockClear();
    fireEvent.change(screen.getByLabelText('Role'), { target: { value: 'viewer' } });

    expect(screen.queryByText('操作日志')).toBeNull();
    expect(
      fetchMock.mock.calls.some(([input]) => String(input).includes('/api/admin/audit-logs'))
    ).toBe(false);
  });

  it('submits GraphRAG questions and renders answers with citations', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith('/api/graphrag/answer')) {
        expect(init?.method).toBe('POST');
        expect(JSON.parse(String(init?.body))).toEqual({
          query: 'lever-play',
          top_k: 3,
          filters: {
            review_status: '待审核'
          }
        });
        return okJson({
          query: 'lever-play',
          answer: 'Based on exhibit records and graph context.',
          citations: [
            {
              source_id: 'magnet-maze',
              source_type: 'exhibit',
              title: '磁力迷宫',
              snippet: '通过磁铁和轨道迷宫演示磁力吸引与排斥。'
            }
          ],
          items: [
            {
              exhibit: apiExhibit(),
              score: 8,
              reasons: ['matched identity'],
              citations: [],
              graph: {
                nodes: [{ id: 'exhibit:magnet-maze', label: '磁力迷宫', type: 'exhibit' }],
                edges: []
              }
            }
          ]
        });
      }
      return okJson({ total: 1, items: [apiExhibit()] });
    });

    render(<App />);

    await screen.findByRole('heading', { name: '磁力迷宫' });
    fireEvent.change(screen.getByLabelText('审核状态'), { target: { value: '待审核' } });
    fireEvent.change(screen.getByLabelText(/GraphRAG/), { target: { value: 'lever-play' } });
    fireEvent.click(screen.getByRole('button', { name: '生成答案' }));

    expect(await screen.findByText('Based on exhibit records and graph context.')).toBeTruthy();
    expect(screen.getAllByText('磁力迷宫').length).toBeGreaterThan(0);
    const citationCard = screen.getByLabelText('引用来源 [1]');
    expect(within(citationCard).getByText('[1]')).toBeTruthy();
    expect(within(citationCard).getByText('exhibit')).toBeTruthy();
    expect(screen.getByText(/matched identity/)).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/api/graphrag/answer',
      expect.objectContaining({ method: 'POST' })
    );
  });

  it('opens the exhibit that owns a GraphRAG document citation only after the citation is clicked', async () => {
    const citedExhibit: Exhibit = {
      ...frontendExhibit,
      id: 'thermal-studio',
      name: 'Thermal Studio',
      theme: '热学',
      documents: [
        {
          id: 'doc-thermal-plan',
          name: 'thermal-plan.pdf',
          fileType: 'pdf',
          url: 'http://assets.test/thermal-plan.pdf',
          sourceNote: '方案说明',
          chunks: [{ id: 'doc-thermal-plan:chunk-1', text: '热学互动方案依据', sequence: 1 }]
        }
      ]
    };
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith('/api/graphrag/answer')) {
        expect(init?.method).toBe('POST');
        return okJson({
          query: 'thermal',
          answer: 'Use the cited document to verify the thermal exhibit.',
          citations: [
            {
              source_id: 'doc-thermal-plan',
              source_type: 'document',
              title: 'thermal-plan.pdf',
              snippet: '热学互动方案依据'
            }
          ],
          items: [
            {
              exhibit: apiExhibit(citedExhibit),
              score: 9,
              reasons: ['document citation'],
              citations: [
                {
                  source_id: 'doc-thermal-plan',
                  source_type: 'document',
                  title: 'thermal-plan.pdf',
                  snippet: '热学互动方案依据'
                }
              ],
              graph: { nodes: [], edges: [] }
            }
          ]
        });
      }
      return okJson({ total: 2, items: [apiExhibit(), apiExhibit(citedExhibit)] });
    });

    render(<App />);

    await screen.findByRole('heading', { name: frontendExhibit.name });
    fireEvent.change(screen.getByLabelText(/GraphRAG/), { target: { value: 'thermal' } });
    fireEvent.click(screen.getByRole('button', { name: '生成答案' }));

    const citationCard = await screen.findByLabelText('引用来源 [1]');
    expect(within(document.querySelector('.detail') as HTMLElement).getByRole('heading', { name: frontendExhibit.name })).toBeTruthy();
    fireEvent.click(citationCard);

    await waitFor(() => {
      expect(within(document.querySelector('.detail') as HTMLElement).getByRole('heading', { name: 'Thermal Studio' })).toBeTruthy();
    });
  });

  it('shows a clear no-evidence state when GraphRAG cannot find grounded sources', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith('/api/graphrag/answer')) {
        expect(init?.method).toBe('POST');
        return okJson({
          query: 'unknown exhibit',
          answer: '未找到依据：库内资料暂未命中“unknown exhibit”。',
          citations: [],
          items: []
        });
      }
      return okJson({ total: 1, items: [apiExhibit()] });
    });

    render(<App />);

    await screen.findByRole('heading', { name: frontendExhibit.name });
    fireEvent.change(screen.getByLabelText(/GraphRAG/), { target: { value: 'unknown exhibit' } });
    fireEvent.click(screen.getByRole('button', { name: '生成答案' }));

    const notice = await screen.findByRole('alert');
    expect(notice.textContent).toContain('未找到可引用来源');
    expect(screen.queryByLabelText('引用来源 [1]')).toBeNull();
  });

  it('renders backend hybrid search reasons in semantic recommendations', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith('/api/search/hybrid')) {
        expect(init?.method).toBe('POST');
        expect(JSON.parse(String(init?.body)).query).toContain('低龄儿童');
        return okJson({
          query: '找几个适合低龄儿童、预算不高、互动性强的力学展项',
          total: 3,
          items: [
            {
              exhibit: apiExhibit(),
              score: 14,
              reasons: ['匹配人群：低龄儿童', '筛选互动：机械互动']
            }
          ]
        });
      }
      return okJson({ total: 1, items: [apiExhibit()] });
    });

    render(<App />);

    expect(await screen.findByText(/筛选互动：机械互动/)).toBeTruthy();
    expect(await screen.findByText('共 3 条，显示 1 条')).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/api/search/hybrid',
      expect.objectContaining({ method: 'POST' })
    );
  });

  it('renders document assets returned by the backend', async () => {
    const withDocument = {
      ...apiExhibit(),
      documents: [
        {
          id: 'quote-doc',
          name: '报价清单.pdf',
          file_type: 'pdf',
          url: '/api/files/quote-doc',
          source_note: '报价资料'
        }
      ]
    };
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () => okJson({ total: 1, items: [withDocument] }));

    render(<App />);

    expect(await screen.findByRole('link', { name: '报价清单.pdf' })).toBeTruthy();
    expect(screen.getByText('报价资料')).toBeTruthy();
  });

  it('renders PDF document previews with extracted citation chunks', async () => {
    const withDocument = {
      ...apiExhibit(),
      documents: [
        {
          id: 'pressure-doc',
          name: '气压演示说明.pdf',
          file_type: 'pdf',
          url: '/api/files/pressure-doc',
          source_note: 'PDF 说明资料',
          chunks: [
            {
              id: 'pressure-doc:chunk-1',
              text: '伯努利气流环道用于解释可观察的气压差现象。',
              sequence: 1
            }
          ]
        }
      ]
    };
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () => okJson({ total: 1, items: [withDocument] }));

    render(<App />);

    expect(await screen.findByTitle('气压演示说明.pdf 预览')).toBeTruthy();
    expect(screen.getByText('引用片段')).toBeTruthy();
    expect(screen.getByText(/伯努利气流环道/)).toBeTruthy();
  });

  it('shows document GraphRAG indexing status for indexed and unindexed files', async () => {
    const withDocuments = {
      ...apiExhibit(),
      documents: [
        {
          id: 'indexed-doc',
          name: 'indexed-plan.docx',
          file_type: 'docx',
          url: '/api/files/indexed-doc',
          source_note: '方案资料',
          chunks: [{ id: 'indexed-doc:chunk-1', text: '可检索的方案片段', sequence: 1 }]
        },
        {
          id: 'legacy-doc',
          name: 'legacy-plan.doc',
          file_type: 'doc',
          url: '/api/files/legacy-doc',
          source_note: '旧版资料',
          chunks: []
        }
      ]
    };
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () => okJson({ total: 1, items: [withDocuments] }));

    render(<App />);

    expect(await screen.findByRole('link', { name: 'indexed-plan.docx' })).toBeTruthy();
    expect(screen.getByRole('link', { name: 'legacy-plan.doc' })).toBeTruthy();
    expect(screen.getByText('已生成 1 个引用片段')).toBeTruthy();
    expect(screen.getByText('未生成引用片段，仅可下载/预览')).toBeTruthy();
  });

  it('uses explicit download URLs while keeping PDF preview URLs inline', async () => {
    const withDocument = {
      ...apiExhibit(),
      documents: [
        {
          id: 'quote-download-doc',
          name: 'quote.pdf',
          file_type: 'pdf',
          url: '/api/files/quote-download-doc',
          source_note: 'Quote file'
        }
      ]
    };
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () => okJson({ total: 1, items: [withDocument] }));

    render(<App />);

    const link = await screen.findByRole('link', { name: 'quote.pdf' });
    const preview = screen.getByTitle('quote.pdf 预览') as HTMLIFrameElement;

    expect(link.getAttribute('href')).toBe('http://127.0.0.1:8000/api/files/quote-download-doc?download=1');
    expect(link.getAttribute('download')).toBe('quote.pdf');
    expect(preview.getAttribute('src')).toBe('http://127.0.0.1:8000/api/files/quote-download-doc');
  });

  it('lets admins remove uploaded document assets from the detail panel', async () => {
    const withDocument = apiExhibit({
      ...frontendExhibit,
      documents: [
        {
          id: 'document-remove-demo',
          name: 'remove-me.txt',
          fileType: 'txt',
          url: '/api/files/remove-me',
          sourceNote: '误传资料'
        }
      ]
    });
    const withoutDocument = { ...withDocument, documents: [] };
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith('/api/exhibits/magnet-maze/assets/document-remove-demo')) {
        expect(init?.method).toBe('DELETE');
        return okJson(withoutDocument);
      }
      if (url.endsWith('/api/admin/audit-logs?limit=8')) {
        return okJson({ total: 0, items: [] });
      }
      return okJson({ total: 1, items: [withDocument] });
    });

    render(<App />);

    expect(await screen.findByRole('link', { name: 'remove-me.txt' })).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: '删除资料 remove-me.txt' }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        'http://127.0.0.1:8000/api/exhibits/magnet-maze/assets/document-remove-demo',
        { method: 'DELETE', headers: { 'X-User-Role': 'admin' } }
      );
    });
    expect(screen.queryByRole('link', { name: 'remove-me.txt' })).toBeNull();
  });

  it('uploads selected media through the backend and renders the returned asset link', async () => {
    const updated = {
      ...apiExhibit(),
      media_assets: [
        ...apiExhibit().media_assets,
        {
          id: 'media-uploaded',
          type: 'image',
          name: 'scene.png',
          url: '/api/files/uploaded',
          note: '现场照片'
        }
      ]
    };
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith('/api/exhibits/magnet-maze/assets')) {
        expect(init?.method).toBe('POST');
        expect(init?.body).toBeInstanceOf(FormData);
        return okJson(updated);
      }
      return okJson({ total: 1, items: [apiExhibit()] });
    });

    render(<App />);

    await screen.findByRole('heading', { name: '磁力迷宫' });
    const input = document.querySelector('.upload input') as HTMLInputElement;
    const file = new File(['fake image bytes'], 'scene.png', { type: 'image/png' });
    fireEvent.change(input, { target: { files: [file] } });

    expect(await screen.findByRole('link', { name: 'scene.png' })).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/api/exhibits/magnet-maze/assets',
      expect.objectContaining({ method: 'POST' })
    );
  });

  it('renders media assets as compact thumbnails that open previews or downloads', async () => {
    const withMedia = apiExhibit({
      ...frontendExhibit,
      media: [
        {
          id: 'render-image',
          type: 'image',
          name: '展项效果图.png',
          url: 'http://assets.test/render.png',
          note: '效果图'
        },
        {
          id: 'walkthrough-video',
          type: 'video',
          name: '互动演示.mp4',
          url: 'http://assets.test/demo.mp4',
          note: '现场演示'
        },
        {
          id: 'quote-file',
          type: 'quote',
          name: '报价清单.xlsx',
          url: 'http://assets.test/quote.xlsx',
          note: '报价文件'
        }
      ]
    });
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () => okJson({ total: 1, items: [withMedia] }));

    render(<App />);
    await screen.findByText('媒体档案');
    expect(document.querySelector('.media-gallery-grid')?.classList.contains('thumbnail-grid')).toBe(true);
    expect(document.querySelectorAll('.media-thumbnail')).toHaveLength(2);

    expect(await screen.findByText('媒体档案')).toBeTruthy();
    expect(screen.getByAltText('展项效果图.png')).toBeTruthy();
    const video = screen.getByLabelText('互动演示.mp4 视频预览') as HTMLVideoElement;
    expect(video.tagName).toBe('VIDEO');
    expect(video.controls).toBe(false);
    expect(screen.getByRole('link', { name: '报价清单.xlsx' }).getAttribute('href')).toBe('http://assets.test/quote.xlsx');
    expect(screen.getByText('效果图')).toBeTruthy();
    expect(screen.getByText('现场演示')).toBeTruthy();
  });

  it('opens image and video media assets in an in-page preview dialog', async () => {
    const withMedia = apiExhibit({
      ...frontendExhibit,
      media: [
        {
          id: 'preview-image',
          type: 'image',
          name: 'preview-image.png',
          url: 'http://assets.test/preview.png',
          note: 'render'
        },
        {
          id: 'preview-video',
          type: 'video',
          name: 'preview-video.mp4',
          url: 'http://assets.test/preview.mp4',
          note: 'walkthrough'
        }
      ]
    });
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () => okJson({ total: 1, items: [withMedia] }));

    render(<App />);

    fireEvent.click(await screen.findByRole('button', { name: '预览媒体 preview-image.png' }));
    const imageDialog = screen.getByRole('dialog', { name: 'preview-image.png' });
    expect(within(imageDialog).getByAltText('preview-image.png')).toBeTruthy();

    fireEvent.click(within(imageDialog).getByRole('button', { name: '关闭媒体预览' }));
    expect(screen.queryByRole('dialog', { name: 'preview-image.png' })).toBeNull();

    fireEvent.click(screen.getByRole('button', { name: '预览媒体 preview-video.mp4' }));
    const videoDialog = screen.getByRole('dialog', { name: 'preview-video.mp4' });
    const video = within(videoDialog).getByLabelText('preview-video.mp4 播放器') as HTMLVideoElement;
    expect(video.tagName).toBe('VIDEO');
    expect(video.controls).toBe(true);
  });

  it('uploads PDF files as document assets and renders the returned document link', async () => {
    const updated = {
      ...apiExhibit(),
      documents: [
        {
          id: 'document-uploaded',
          name: 'quote.pdf',
          file_type: 'pdf',
          url: '/api/files/uploaded-document',
          source_note: '报价资料'
        }
      ]
    };
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith('/api/exhibits/magnet-maze/assets')) {
        expect(init?.method).toBe('POST');
        expect(init?.body).toBeInstanceOf(FormData);
        const body = init?.body as FormData;
        expect(body.get('asset_kind')).toBe('document');
        return okJson(updated);
      }
      return okJson({ total: 1, items: [apiExhibit()] });
    });

    render(<App />);

    await screen.findByRole('heading', { name: '磁力迷宫' });
    const input = document.querySelector('.upload input') as HTMLInputElement;
    const file = new File(['fake pdf bytes'], 'quote.pdf', { type: 'application/pdf' });
    fireEvent.change(input, { target: { files: [file] } });

    expect(await screen.findByRole('link', { name: 'quote.pdf' })).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/api/exhibits/magnet-maze/assets',
      expect.objectContaining({ method: 'POST' })
    );
  });

  it('uploads text files as document assets for RAG sources', async () => {
    const updated = {
      ...apiExhibit(),
      documents: [
        {
          id: 'document-text-uploaded',
          name: 'operation-note.txt',
          file_type: 'txt',
          url: '/api/files/uploaded-text-document',
          source_note: 'RAG 资料'
        }
      ]
    };
    const uploadBodies: FormData[] = [];
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith('/api/exhibits/magnet-maze/assets')) {
        expect(init?.method).toBe('POST');
        expect(init?.body).toBeInstanceOf(FormData);
        uploadBodies.push(init?.body as FormData);
        return okJson(updated);
      }
      return okJson({ total: 1, items: [apiExhibit()] });
    });

    render(<App />);

    await screen.findByRole('heading', { name: '磁力迷宫' });
    const input = document.querySelector('.upload input') as HTMLInputElement;
    expect(input.accept).toContain('video/*');
    expect(input.accept).toContain('.txt');
    const file = new File(['airflow citation note'], 'operation-note.txt', { type: 'text/plain' });
    fireEvent.change(input, { target: { files: [file] } });

    expect(await screen.findByRole('link', { name: 'operation-note.txt' })).toBeTruthy();
    expect(uploadBodies).toHaveLength(1);
    expect(uploadBodies[0].get('asset_kind')).toBe('document');
    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/api/exhibits/magnet-maze/assets',
      expect.objectContaining({ method: 'POST' })
    );
  });

  it('previews spreadsheet rows before committing the import', async () => {
    const importedExhibit = {
      ...frontendExhibit,
      id: 'imported-demo',
      name: 'Imported Demo',
      theme: 'Mechanics',
      materials: ['Metal'],
      interactions: ['Hands-on'],
      relatedExhibitIds: ['magnet-maze']
    };
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith('/api/exhibits/import')) {
        expect(init?.method).toBe('POST');
        expect(init?.body).toBeInstanceOf(FormData);
        const body = init?.body as FormData;
        const commit = body.get('commit');
        expect(commit === 'false' || commit === 'true').toBe(true);
        return okJson({
          total_rows: 1,
          valid_rows: 1,
          imported_count: commit === 'true' ? 1 : 0,
          errors: [],
          items: [apiExhibit(importedExhibit)]
        });
      }
      return okJson({ total: 1, items: [apiExhibit()] });
    });

    render(<App />);

    await screen.findByRole('heading', { name: '磁力迷宫' });
    const input = document.querySelector('.import-upload input') as HTMLInputElement;
    const file = new File(['id,name\nimported-demo,Imported Demo'], 'exhibits.csv', { type: 'text/csv' });
    fireEvent.change(input, { target: { files: [file] } });

    expect(await screen.findByText('导入预览')).toBeTruthy();
    expect(screen.getByText('总行数 1')).toBeTruthy();
    expect(screen.getByText('有效 1')).toBeTruthy();
    expect(screen.getByText('Imported Demo')).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/api/exhibits/import',
      expect.objectContaining({ method: 'POST' })
    );
    const importCalls = fetchMock.mock.calls.filter(([input]) => String(input).endsWith('/api/exhibits/import'));
    expect((importCalls[0][1]?.body as FormData).get('commit')).toBe('false');

    fireEvent.click(screen.getByRole('button', { name: '确认导入' }));

    expect(await screen.findByRole('heading', { name: 'Imported Demo' })).toBeTruthy();
    expect(screen.getByText('导入完成：已选中新展项，可在当前展项图谱核验关系')).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/api/exhibits/import',
      expect.objectContaining({ method: 'POST' })
    );
    const committedImportCalls = fetchMock.mock.calls.filter(([input]) => String(input).endsWith('/api/exhibits/import'));
    expect((committedImportCalls[1][1]?.body as FormData).get('commit')).toBe('true');
  });

  it('switches back to the current exhibit graph after committing an import', async () => {
    const importedExhibit = {
      ...frontendExhibit,
      id: 'imported-graph-demo',
      name: 'Imported Graph Demo',
      materials: ['Imported Graph Material'],
      relatedExhibitIds: ['magnet-maze']
    };
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith('/api/neo4j-demo/graph')) {
        return okJson({
          nodes: [{ id: 'exhibit:demo-only', label: 'Full Demo Only', type: 'exhibit' }],
          edges: []
        });
      }
      if (url.endsWith('/api/exhibits/imported-graph-demo/graph')) {
        return okJson({
          nodes: [
            { id: 'exhibit:imported-graph-demo', label: 'Imported Graph Demo', type: 'exhibit' },
            { id: 'material:imported-graph-material', label: 'Imported Graph Material', type: 'material' }
          ],
          edges: [
            {
              source: 'exhibit:imported-graph-demo',
              target: 'material:imported-graph-material',
              label: 'material',
              type: 'uses_material'
            }
          ]
        });
      }
      if (url.endsWith('/api/exhibits/magnet-maze/graph')) {
        return okJson({
          nodes: [{ id: 'exhibit:magnet-maze', label: '磁力迷宫', type: 'exhibit' }],
          edges: []
        });
      }
      if (url.endsWith('/api/exhibits/import')) {
        const commit = (init?.body as FormData).get('commit');
        return okJson({
          total_rows: 1,
          valid_rows: 1,
          imported_count: commit === 'true' ? 1 : 0,
          errors: [],
          items: [apiExhibit(importedExhibit)]
        });
      }
      return okJson({ total: 1, items: [apiExhibit()] });
    });

    render(<App />);

    await screen.findByRole('heading', { name: '磁力迷宫' });
    fireEvent.click(screen.getByRole('button', { name: '全库演示' }));
    expect((await screen.findAllByText('Full Demo Only')).length).toBeGreaterThan(0);

    const input = document.querySelector('.import-upload input') as HTMLInputElement;
    const file = new File(['id,name\nimported-graph-demo,Imported Graph Demo'], 'exhibits.csv', { type: 'text/csv' });
    fireEvent.change(input, { target: { files: [file] } });

    expect(await screen.findByText('导入预览')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: '确认导入' }));

    expect(await screen.findByRole('heading', { name: 'Imported Graph Demo' })).toBeTruthy();
    expect(await within(screen.getByLabelText('graph nodes')).findByText('Imported Graph Material')).toBeTruthy();
    expect(screen.getByText('导入完成：已选中新展项，可在当前展项图谱核验关系')).toBeTruthy();
    expect(screen.getByRole('button', { name: '当前展项' }).className).toBe('active');
    expect(fetchMock).toHaveBeenCalledWith('http://127.0.0.1:8000/api/exhibits/imported-graph-demo/graph');
  });

  it('shows a spreadsheet template download entry near the import control', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(okJson({ total: 1, items: [apiExhibit()] }));

    render(<App />);

    await screen.findByRole('heading', { name: '磁力迷宫' });
    const templateLink = screen.getByRole('link', { name: '下载模板' });

    expect(templateLink).toBeTruthy();
    expect(templateLink.getAttribute('href')).toBe('http://127.0.0.1:8000/api/exhibits/import-template');
    expect(templateLink.getAttribute('download')).toBe('展项导入模板.xlsx');
    expect(screen.getByText('模板含字段说明')).toBeTruthy();
  });

  it('shows import validation preview errors without changing the selected exhibit', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith('/api/exhibits/import')) {
        expect(init?.method).toBe('POST');
        expect((init?.body as FormData).get('commit')).toBe('false');
        return okJson({
          total_rows: 1,
          valid_rows: 0,
          imported_count: 0,
          errors: [{ row: 2, field: 'budget_min', message: 'Must be an integer' }],
          items: []
        });
      }
      return okJson({ total: 1, items: [apiExhibit()] });
    });

    render(<App />);

    await screen.findByRole('heading', { name: '磁力迷宫' });
    const input = document.querySelector('.import-upload input') as HTMLInputElement;
    const file = new File(['bad csv'], 'bad.csv', { type: 'text/csv' });
    fireEvent.change(input, { target: { files: [file] } });

    expect(await screen.findByText('导入校验发现 1 个问题，未写入数据')).toBeTruthy();
    expect(screen.getByText('导入预览')).toBeTruthy();
    expect(screen.getByText('第 2 行')).toBeTruthy();
    expect(screen.getByText('budget_min')).toBeTruthy();
    expect(screen.getByText('Must be an integer')).toBeTruthy();
    expect((screen.getByRole('button', { name: '确认导入' }) as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByRole('heading', { name: '磁力迷宫' })).toBeTruthy();
  });
});
