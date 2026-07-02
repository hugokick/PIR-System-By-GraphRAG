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
  projectName: '青禾儿童科技馆更新项目',
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
    expect(screen.getAllByText('材料').length).toBeGreaterThan(0);
    expect(screen.queryByText('material')).toBeNull();
    expect(fetchMock).toHaveBeenCalledWith('http://127.0.0.1:8000/api/exhibits/magnet-maze/graph');
  });

  it('renders graph node types in Chinese and filters the graph by clicked type', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith('/api/exhibits/magnet-maze/graph')) {
        return okJson({
          nodes: [
            { id: 'exhibit:magnet-maze', label: '磁力迷宫', type: 'exhibit' },
            { id: 'material:acrylic', label: '亚克力', type: 'material' },
            { id: 'material:metal', label: '金属', type: 'material' },
            { id: 'supplier:qisi', label: '启思互动工坊', type: 'supplier' },
            { id: 'interaction:hands-on', label: '动手实验', type: 'interaction' },
            { id: 'document:design-note', label: '设计说明', type: 'document' }
          ],
          edges: [
            { source: 'exhibit:magnet-maze', target: 'material:acrylic', label: '使用材料', type: 'uses_material' },
            { source: 'exhibit:magnet-maze', target: 'material:metal', label: '使用材料', type: 'uses_material' },
            { source: 'exhibit:magnet-maze', target: 'supplier:qisi', label: '供应商', type: 'supplied_by' },
            { source: 'exhibit:magnet-maze', target: 'interaction:hands-on', label: '交互方式', type: 'has_interaction' },
            { source: 'exhibit:magnet-maze', target: 'document:design-note', label: '资料文档', type: 'has_document' }
          ]
        });
      }
      return okJson({ total: 1, items: [apiExhibit()] });
    });

    render(<App />);

    expect(await screen.findByText('节点 6')).toBeTruthy();
    const legend = await screen.findByLabelText('graph node type legend');
    expect(within(legend).getByRole('button', { name: '展项' })).toBeTruthy();
    expect(within(legend).getByRole('button', { name: '材料' })).toBeTruthy();
    expect(within(legend).getByRole('button', { name: '供应商' })).toBeTruthy();
    expect(within(legend).getByRole('button', { name: '交互方式' })).toBeTruthy();
    expect(within(legend).getByRole('button', { name: '资料文档' })).toBeTruthy();
    expect(within(legend).queryByText('material')).toBeNull();
    expect(within(legend).queryByText('interaction')).toBeNull();
    expect(within(legend).queryByText('document')).toBeNull();

    fireEvent.click(within(legend).getByRole('button', { name: '材料' }));

    expect(await screen.findByText('节点 2 / 6')).toBeTruthy();
    expect(screen.getByText('关系 0 / 5')).toBeTruthy();
    expect(screen.getByText('已筛选：材料')).toBeTruthy();
    expect(screen.getByRole('button', { name: /亚克力/ })).toBeTruthy();
    expect(screen.getByRole('button', { name: /金属/ })).toBeTruthy();
    expect(screen.queryByRole('button', { name: /启思互动工坊/ })).toBeNull();
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
    fireEvent.change(screen.getByPlaceholderText('项目名称'), { target: { value: '青禾儿童科技馆二期更新' } });
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
    expect(updatedPayload?.project).toEqual({
      id: 'qinghe-2024',
      name: '青禾儿童科技馆二期更新'
    });
  });

  it('hides review status from editor edit forms and preserves the existing workflow state', async () => {
    let updatedPayload: ApiExhibit | undefined;
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (_input, init) => {
      const url = String(_input);
      if (url.endsWith('/api/auth/login')) {
        return okJson({
          access_token: 'editor-token',
          token_type: 'bearer',
          user: {
            username: 'editor',
            role: 'editor',
            display_name: '编辑员'
          }
        });
      }
      if (init && init.method === 'PUT') {
        const body = JSON.parse(String(init.body));
        updatedPayload = body;
        return okJson(body);
      }
      return okJson({ total: 1, items: [apiExhibit()] });
    });

    render(<App />);

    await screen.findByRole('heading', { name: '磁力迷宫' });
    expect(screen.queryByLabelText('Role')).toBeNull();
    fireEvent.change(screen.getByLabelText('用户名'), { target: { value: 'editor' } });
    fireEvent.change(screen.getByLabelText('密码'), { target: { value: 'editor123' } });
    fireEvent.click(screen.getByRole('button', { name: '登录' }));
    expect(await screen.findByText(/编辑员/)).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: /编辑档案/ }));

    expect(screen.queryByLabelText('档案审核状态')).toBeNull();

    fireEvent.change(screen.getByPlaceholderText('展项名称'), { target: { value: '磁力迷宫 Editor Draft' } });
    fireEvent.click(screen.getByRole('button', { name: '保存修改' }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        'http://127.0.0.1:8000/api/exhibits/magnet-maze',
        expect.objectContaining({
          method: 'PUT',
          body: expect.stringContaining('磁力迷宫 Editor Draft')
        })
      );
    });
    expect(updatedPayload?.review_status).toBe('待审核');
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
    expect(screen.getAllByText('已审核/已落地档案资料受保护，请先退回审核或变更状态后再删除')).toHaveLength(1);
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
    const projectSelect = screen.getByLabelText('项目案例');
    expect(within(projectSelect).getByRole('option', { name: '青禾儿童科技馆更新项目' })).toBeTruthy();
    fireEvent.change(screen.getByLabelText('项目案例'), { target: { value: 'qinghe-2024' } });

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(([input]) =>
          String(input).includes('/api/exhibits?project_id=qinghe-2024')
        )
      ).toBe(true);
    });
  });

  it('filters exhibits by tag through backend query parameters', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async () => okJson({ total: 1, items: [apiExhibit()] }));

    render(<App />);

    await screen.findByRole('heading', { name: '磁力迷宫' });
    fireEvent.change(screen.getByLabelText('标签'), { target: { value: '低龄儿童' } });

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(([input]) =>
          String(input).includes('/api/exhibits?tag=%E4%BD%8E%E9%BE%84%E5%84%BF%E7%AB%A5')
        )
      ).toBe(true);
    });
  });

  it('filters exhibits by owner and supplier through backend query parameters', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async () => okJson({ total: 1, items: [apiExhibit()] }));

    render(<App />);

    await screen.findByRole('heading', { name: '磁力迷宫' });
    fireEvent.change(screen.getByLabelText('业主'), { target: { value: '青禾儿童科技馆' } });
    fireEvent.change(screen.getByLabelText('供应商'), { target: { value: '启思互动工坊' } });

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(([input]) =>
          String(input).includes(
            '/api/exhibits?owner=%E9%9D%92%E7%A6%BE%E5%84%BF%E7%AB%A5%E7%A7%91%E6%8A%80%E9%A6%86&supplier=%E5%90%AF%E6%80%9D%E4%BA%92%E5%8A%A8%E5%B7%A5%E5%9D%8A'
          )
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

  it('uses review workload metrics as quick filters for review queues', async () => {
    const pending = apiExhibit({ ...frontendExhibit, id: 'pending-demo', name: '待审展项', reviewStatus: '待审核' });
    const rejected = apiExhibit({ ...frontendExhibit, id: 'rejected-demo', name: '退回展项', reviewStatus: '已退回' });
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (url.includes('/api/exhibits?review_status=%E5%BE%85%E5%AE%A1%E6%A0%B8')) {
        return okJson({ total: 1, items: [pending] });
      }
      return okJson({ total: 2, items: [pending, rejected] });
    });

    render(<App />);

    const dashboardPanel = (await screen.findByText('数据看板')).closest('section') as HTMLElement;
    fireEvent.click(within(dashboardPanel).getByRole('button', { name: '筛选待审核档案，当前 1 条' }));

    expect((screen.getByLabelText('审核状态') as HTMLSelectElement).value).toBe('待审核');
    await waitFor(() => {
      expect(screen.getAllByText('待审展项').length).toBeGreaterThan(0);
      expect(screen.queryAllByText('退回展项')).toHaveLength(0);
    });
    expect(
      fetchMock.mock.calls.some(([input]) =>
        String(input).includes('/api/exhibits?review_status=%E5%BE%85%E5%AE%A1%E6%A0%B8')
      )
    ).toBe(true);
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

  it('renders KG relation recommendations and lets editors accept a similar exhibit', async () => {
    const primary = { ...frontendExhibit, relatedExhibitIds: [] };
    const recommended = {
      ...frontendExhibit,
      id: 'lever-play',
      name: '杠杆乐园',
      theme: '力学',
      relatedExhibitIds: []
    };
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith('/api/exhibits/magnet-maze/relation-recommendations')) {
        return okJson({
          target_exhibit_id: 'magnet-maze',
          warnings: [],
          recommendations: [
            {
              relation_type: 'similar_to',
              source_id: 'magnet-maze',
              target_id: 'lever-play',
              target_label: '杠杆乐园',
              confidence: 0.72,
              reasons: ['共同主题：力学', '共同互动（1）：动手实验'],
              evidence_refs: ['theme:mechanics'],
              already_exists: false
            },
            {
              relation_type: 'uses_material',
              source_id: 'magnet-maze',
              target_id: 'acrylic',
              target_label: '亚克力',
              confidence: 1,
              reasons: ['已存在的图谱边：uses_material'],
              evidence_refs: ['material:acrylic'],
              already_exists: true
            }
          ]
        });
      }
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
      return okJson({ total: 2, items: [apiExhibit(primary), apiExhibit(recommended)] });
    });

    render(<App />);

    await screen.findByRole('heading', { name: '磁力迷宫' });
    const recommendationPanel = await screen.findByLabelText('KG 关系推荐');
    const relationPanel = screen.getByLabelText('相似展项关系');
    expect(relationPanel.querySelector('.similar-relations-body')).toBeTruthy();
    expect(relationPanel.querySelector('.similar-relations-main')).toBeTruthy();
    expect(within(recommendationPanel).getByText('杠杆乐园')).toBeTruthy();
    expect(within(recommendationPanel).getByText('置信度 72%')).toBeTruthy();
    expect(within(recommendationPanel).getByText(/共同主题/)).toBeTruthy();
    expect(within(recommendationPanel).queryByText('亚克力')).toBeNull();

    fireEvent.click(within(recommendationPanel).getByRole('button', { name: '采纳杠杆乐园为相似展项' }));

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

  it('groups detail maintenance controls separately from relation and asset panels', async () => {
    const exhibitWithMedia = {
      ...frontendExhibit,
      media: [{ id: 'layout-media', type: 'image' as const, name: '布局缩略图', url: 'http://assets.test/layout.png' }]
    };
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () => okJson({ total: 1, items: [apiExhibit(exhibitWithMedia)] }));

    render(<App />);

    await screen.findByRole('heading', { name: '磁力迷宫' });
    const maintenancePanel = screen.getByLabelText('档案维护操作');
    const relationAssetPanel = screen.getByLabelText('资料与关系');

    expect(within(maintenancePanel).getByRole('button', { name: /编辑档案/ })).toBeTruthy();
    expect(within(maintenancePanel).getByText('上传媒体')).toBeTruthy();
    expect(within(relationAssetPanel).getByLabelText('相似展项关系')).toBeTruthy();
    expect(within(relationAssetPanel).getByLabelText('媒体档案')).toBeTruthy();
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
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith('/api/auth/login')) {
        return okJson({
          access_token: 'viewer-token',
          token_type: 'bearer',
          user: {
            username: 'viewer',
            role: 'viewer',
            display_name: '只读访客'
          }
        });
      }
      return okJson({ total: 1, items: [apiExhibit()] });
    });

    render(<App />);

    await screen.findByRole('heading', { name: frontendExhibit.name });
    expect(screen.queryByLabelText('Role')).toBeNull();
    fireEvent.change(screen.getByLabelText('用户名'), { target: { value: 'viewer' } });
    fireEvent.change(screen.getByLabelText('密码'), { target: { value: 'viewer123' } });
    fireEvent.click(screen.getByRole('button', { name: '登录' }));
    expect(await screen.findByText(/只读访客/)).toBeTruthy();

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
    const auditList = auditPanel.querySelector('.audit-list') as HTMLElement;
    expect(auditPanel).toBeTruthy();
    expect(within(auditList).getByText('删除档案')).toBeTruthy();
    expect(within(auditList).getByText('更新相似关系')).toBeTruthy();
    expect(within(auditList).getByText('批量导入')).toBeTruthy();
    expect(within(auditPanel).queryByText('delete_exhibit')).toBeNull();
    expect(within(auditPanel).queryByText('update_exhibit_relations')).toBeNull();
    expect(within(auditPanel).queryByText('import_batch')).toBeNull();
    expect(within(auditPanel).getByText(/2026-07-01 00:00/)).toBeTruthy();
    expect(screen.getAllByText(/magnet-maze/).length).toBeGreaterThan(0);
    expect(within(auditList).getByText(/admin \/ magnet-maze/)).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/api/admin/audit-logs?limit=8',
      expect.objectContaining({ headers: { 'X-User-Role': 'admin' } })
    );
  });

  it('shows compact runtime system status to admins', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith('/api/admin/system-status')) {
        return okJson({
          status: 'ok',
          service: 'exhibit-atlas-api',
          repository: {
            kind: 'postgres',
            database_url_configured: true
          },
          storage: {
            backend: 'local',
            configured_backend: 'local',
            s3_bucket_configured: false
          },
          auth: {
            role_header_auth_enabled: false,
            token_ttl_seconds: 28800
          },
          neo4j_demo: {
            enabled: true,
            configured: true,
            uri_configured: true,
            credentials_configured: true
          },
          counts: {
            exhibits: 16,
            audit_logs: 12
          }
        });
      }
      if (url.endsWith('/api/admin/audit-logs?limit=8')) {
        return okJson({ total: 0, items: [] });
      }
      return okJson({ total: 1, items: [apiExhibit()] });
    });

    render(<App />);

    const systemPanel = (await screen.findByText('系统状态')).closest('section') as HTMLElement;
    expect(systemPanel).toBeTruthy();
    expect(within(systemPanel).getByText('PostgreSQL')).toBeTruthy();
    expect(within(systemPanel).getByText('本地文件')).toBeTruthy();
    expect(within(systemPanel).getByText('仅登录令牌')).toBeTruthy();
    expect(within(systemPanel).getByText('令牌 8 小时')).toBeTruthy();
    expect(within(systemPanel).getByText('16 展项')).toBeTruthy();
    expect(within(systemPanel).getByText('12 条日志')).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/api/admin/system-status',
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
    const auditList = auditPanel.querySelector('.audit-list') as HTMLElement;
    fireEvent.click(within(auditPanel).getByRole('button', { name: '刷新操作日志' }));

    expect(await within(auditPanel).findAllByText(/manual-refresh-demo/)).toHaveLength(2);
    expect(within(auditList).getByText('删除档案')).toBeTruthy();
    expect(fetchMock.mock.calls.filter(([input]) => String(input).endsWith('/api/admin/audit-logs?limit=8'))).toHaveLength(2);
  });

  it('lets admins filter audit logs by action and resource id', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (
        url.includes('/api/admin/audit-logs?')
        && url.includes('action=delete_exhibit')
        && url.includes('resource_id=magnet-maze')
      ) {
        return okJson({
          total: 1,
          items: [
            {
              id: 'audit-filtered-delete',
              actor_role: 'admin',
              action: 'delete_exhibit',
              resource_type: 'exhibit',
              resource_id: 'magnet-maze',
              summary: '删除档案 magnet-maze',
              created_at: '2026-07-01T00:30:00+00:00'
            }
          ]
        });
      }
      if (url.endsWith('/api/admin/audit-logs?limit=8')) {
        return okJson({ total: 0, items: [] });
      }
      return okJson({ total: 1, items: [apiExhibit()] });
    });

    render(<App />);

    const auditPanel = (await screen.findByText('操作日志')).closest('section') as HTMLElement;
    fireEvent.change(within(auditPanel).getByLabelText('日志动作'), { target: { value: 'delete_exhibit' } });
    fireEvent.change(within(auditPanel).getByLabelText('资源编号'), { target: { value: 'magnet-maze' } });
    fireEvent.click(within(auditPanel).getByRole('button', { name: '刷新操作日志' }));

    expect(await within(auditPanel).findByText('删除档案')).toBeTruthy();
    expect(within(auditPanel).getAllByText(/magnet-maze/).length).toBeGreaterThan(0);
    expect(
      fetchMock.mock.calls.some(([input]) => {
        const url = String(input);
        return (
          url.includes('/api/admin/audit-logs?')
          && url.includes('limit=8')
          && url.includes('action=delete_exhibit')
          && url.includes('resource_id=magnet-maze')
        );
      })
    ).toBe(true);
  });

  it('lets admins jump from the selected exhibit to its audit log history', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (url.includes('/api/admin/audit-logs?') && url.includes('resource_id=magnet-maze')) {
        return okJson({
          total: 1,
          items: [
            {
              id: 'audit-selected-exhibit',
              actor_role: 'editor',
              action: 'update_exhibit',
              resource_type: 'exhibit',
              resource_id: 'magnet-maze',
              summary: '编辑档案 magnet-maze',
              created_at: '2026-07-01T02:10:00+00:00'
            }
          ]
        });
      }
      if (url.endsWith('/api/admin/audit-logs?limit=8')) {
        return okJson({ total: 0, items: [] });
      }
      return okJson({ total: 1, items: [apiExhibit()] });
    });

    render(<App />);

    const maintenancePanel = await screen.findByLabelText('档案维护操作');
    fireEvent.click(within(maintenancePanel).getByRole('button', { name: '查看此档案日志' }));

    const auditPanel = (await screen.findByText('操作日志')).closest('section') as HTMLElement;
    const auditList = auditPanel.querySelector('.audit-list') as HTMLElement;
    expect((within(auditPanel).getByLabelText('资源编号') as HTMLInputElement).value).toBe('magnet-maze');
    expect(await within(auditList).findByText('编辑档案')).toBeTruthy();
    expect(within(auditList).getAllByText(/magnet-maze/).length).toBeGreaterThan(0);
    expect(
      fetchMock.mock.calls.some(([input]) => {
        const url = String(input);
        return url.includes('/api/admin/audit-logs?') && url.includes('resource_id=magnet-maze');
      })
    ).toBe(true);
  });

  it('lets admins export filtered audit logs as CSV', async () => {
    const blob = new Blob(['日志编号,摘要\n1,删除档案'], { type: 'text/csv;charset=utf-8' });
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (url.includes('/api/admin/audit-logs/export?')) {
        return {
          ok: true,
          blob: async () => blob
        } as Response;
      }
      if (url.endsWith('/api/admin/audit-logs?limit=8')) {
        return okJson({ total: 0, items: [] });
      }
      return okJson({ total: 1, items: [apiExhibit()] });
    });
    const createObjectUrl = vi.fn(() => 'blob:audit-logs');
    const revokeObjectUrl = vi.fn();
    Object.defineProperty(globalThis.URL, 'createObjectURL', {
      configurable: true,
      value: createObjectUrl
    });
    Object.defineProperty(globalThis.URL, 'revokeObjectURL', {
      configurable: true,
      value: revokeObjectUrl
    });
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined);

    render(<App />);

    const auditPanel = (await screen.findByText('操作日志')).closest('section') as HTMLElement;
    fireEvent.change(within(auditPanel).getByLabelText('日志动作'), { target: { value: 'delete_exhibit' } });
    fireEvent.change(within(auditPanel).getByLabelText('资源编号'), { target: { value: 'magnet-maze' } });
    fireEvent.click(within(auditPanel).getByRole('button', { name: '导出操作日志' }));

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(([input]) => {
          const url = String(input);
          return (
            url.includes('/api/admin/audit-logs/export?')
            && url.includes('limit=500')
            && url.includes('action=delete_exhibit')
            && url.includes('resource_id=magnet-maze')
          );
        })
      ).toBe(true);
    });
    expect(createObjectUrl).toHaveBeenCalledWith(blob);
    expect(clickSpy).toHaveBeenCalled();
    expect(revokeObjectUrl).toHaveBeenCalledWith('blob:audit-logs');
  });

  it('lets editors export the currently filtered exhibit list as CSV', async () => {
    const blob = new Blob(['展项编号,展项名称\nwater-cycle,城市水循环沙盘'], { type: 'text/csv;charset=utf-8' });
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (url.includes('/api/exhibits/export?')) {
        return {
          ok: true,
          blob: async () => blob
        } as Response;
      }
      if (url.endsWith('/api/admin/audit-logs?limit=8')) {
        return okJson({ total: 0, items: [] });
      }
      return okJson({ total: 1, items: [apiExhibit()] });
    });
    const createObjectUrl = vi.fn(() => 'blob:exhibits');
    const revokeObjectUrl = vi.fn();
    Object.defineProperty(globalThis.URL, 'createObjectURL', {
      configurable: true,
      value: createObjectUrl
    });
    Object.defineProperty(globalThis.URL, 'revokeObjectURL', {
      configurable: true,
      value: revokeObjectUrl
    });
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined);

    render(<App />);

    fireEvent.change(await screen.findByLabelText('关键词'), { target: { value: '水循环' } });
    fireEvent.click(await screen.findByRole('button', { name: '导出档案' }));

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(([input]) => {
          const url = String(input);
          return url.includes('/api/exhibits/export?') && url.includes('keyword=%E6%B0%B4%E5%BE%AA%E7%8E%AF');
        })
      ).toBe(true);
    });
    expect(createObjectUrl).toHaveBeenCalledWith(blob);
    expect(clickSpy).toHaveBeenCalled();
    expect(revokeObjectUrl).toHaveBeenCalledWith('blob:exhibits');
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
    const auditList = auditPanel.querySelector('.audit-list') as HTMLElement;
    expect(await within(auditList).findByText('删除档案')).toBeTruthy();
    expect(fetchMock.mock.calls.filter(([input]) => String(input).endsWith('/api/admin/audit-logs?limit=8'))).toHaveLength(2);
  });

  it('hides audit log entries from viewers', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith('/api/auth/login')) {
        return okJson({
          access_token: 'viewer-token',
          token_type: 'bearer',
          user: {
            username: 'viewer',
            role: 'viewer',
            display_name: '只读访客'
          }
        });
      }
      return okJson({ total: 1, items: [apiExhibit()] });
    });

    render(<App />);

    await screen.findByRole('heading', { name: frontendExhibit.name });
    fetchMock.mockClear();
    fireEvent.change(screen.getByLabelText('用户名'), { target: { value: 'viewer' } });
    fireEvent.change(screen.getByLabelText('密码'), { target: { value: 'viewer123' } });
    fireEvent.click(screen.getByRole('button', { name: '登录' }));
    expect(await screen.findByText(/只读访客/)).toBeTruthy();

    expect(screen.queryByText('操作日志')).toBeNull();
    expect(screen.queryByText('系统状态')).toBeNull();
    expect(
      fetchMock.mock.calls.some(([input]) => String(input).includes('/api/admin/audit-logs'))
    ).toBe(false);
    expect(
      fetchMock.mock.calls.some(([input]) => String(input).includes('/api/admin/system-status'))
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
          confidence: 0.76,
          warnings: ['来源片段较少，请人工核验'],
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
              reasons: ['匹配展项：magnet-maze', '低预算'],
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
    expect(screen.getByText('置信度 76%')).toBeTruthy();
    expect(screen.getByText('来源片段较少，请人工核验')).toBeTruthy();
    expect(screen.getAllByText('磁力迷宫').length).toBeGreaterThan(0);
    const citationButton = screen.getByRole('button', { name: '引用来源 [1] 磁力迷宫' });
    const citationCard = citationButton.closest('.graphrag-citation-card') as HTMLElement;
    expect(within(citationCard).getByText('[1]')).toBeTruthy();
    expect(within(citationCard).getByText('来源类型：展项档案')).toBeTruthy();
    expect(within(citationCard).queryByText('source_type: exhibit')).toBeNull();
    expect(within(citationCard).getByText('对应展项：磁力迷宫')).toBeTruthy();
    const hits = document.querySelector('.graphrag-hits') as HTMLElement;
    const hitButton = within(hits).getByRole('button', { name: /磁力迷宫/ });
    expect(within(hitButton).getByText('匹配原因')).toBeTruthy();
    expect(within(hitButton).getByText('匹配展项：magnet-maze')).toBeTruthy();
    expect(within(hitButton).getByText('低预算')).toBeTruthy();
    expect(within(hitButton).queryByText(/匹配展项：magnet-maze \/ 低预算/)).toBeNull();
    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/api/graphrag/answer',
      expect.objectContaining({ method: 'POST' })
    );
  });

  it('shows a localized GraphRAG score fallback when a hit has no reasons', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith('/api/graphrag/answer')) {
        expect(init?.method).toBe('POST');
        return okJson({
          query: 'force',
          answer: '可参考该展项。',
          citations: [],
          items: [
            {
              exhibit: apiExhibit(),
              score: 7.25,
              reasons: [],
              citations: [],
              graph: { nodes: [], edges: [] }
            }
          ]
        });
      }
      return okJson({ total: 1, items: [apiExhibit()] });
    });

    render(<App />);

    await screen.findByRole('heading', { name: frontendExhibit.name });
    fireEvent.change(screen.getByLabelText(/GraphRAG/), { target: { value: 'force' } });
    fireEvent.click(screen.getByRole('button', { name: '生成答案' }));

    await screen.findByText('可参考该展项。');
    const hits = document.querySelector('.graphrag-hits') as HTMLElement;
    const hitButton = within(hits).getByRole('button', { name: /磁力迷宫/ });
    expect(within(hitButton).getByText('匹配原因')).toBeTruthy();
    expect(within(hitButton).getByText('匹配分数：7.25')).toBeTruthy();
    expect(within(hitButton).queryByText(/score 7.25/)).toBeNull();
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
              reasons: ['匹配资料：thermal-plan.pdf'],
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

    const citationCard = await screen.findByRole('button', { name: '引用来源 [1] thermal-plan.pdf' });
    expect(within(document.querySelector('.detail') as HTMLElement).getByRole('heading', { name: frontendExhibit.name })).toBeTruthy();
    fireEvent.click(citationCard);

    await waitFor(() => {
      expect(within(document.querySelector('.detail') as HTMLElement).getByRole('heading', { name: 'Thermal Studio' })).toBeTruthy();
    });
  });

  it('renders original document actions on GraphRAG document citations', async () => {
    const citedExhibit: Exhibit = {
      ...frontendExhibit,
      id: 'thermal-studio',
      name: 'Thermal Studio',
      documents: [
        {
          id: 'doc-thermal-plan',
          name: 'thermal-plan.pdf',
          fileType: 'pdf',
          url: '/api/files/source-file',
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
              reasons: ['匹配资料：thermal-plan.pdf'],
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

    const citationButton = await screen.findByRole('button', { name: '引用来源 [1] thermal-plan.pdf' });
    const citationCard = citationButton.closest('.graphrag-citation-card') as HTMLElement;
    const openLink = within(citationCard).getByRole('link', { name: '打开资料' });
    const downloadLink = within(citationCard).getByRole('link', { name: '下载资料' });

    expect(openLink.getAttribute('href')).toContain('/api/files/source-file');
    expect(openLink.getAttribute('target')).toBe('_blank');
    expect(downloadLink.getAttribute('href')).toContain('/api/files/source-file');
    expect(downloadLink.getAttribute('href')).toContain('download=1');
    expect(downloadLink.getAttribute('download')).toBe('thermal-plan.pdf');
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

  it('shows no-evidence guidance when GraphRAG returns candidates without citations', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith('/api/graphrag/answer')) {
        expect(init?.method).toBe('POST');
        return okJson({
          query: 'candidate without sources',
          answer: '未找到依据：库内资料命中了候选展项，但没有可引用来源支撑“candidate without sources”。',
          citations: [],
          items: [
            {
              exhibit: apiExhibit(),
              score: 7,
              reasons: ['候选展项与查询语义匹配'],
              citations: [],
              graph: { nodes: [], edges: [] }
            }
          ]
        });
      }
      return okJson({ total: 1, items: [apiExhibit()] });
    });

    render(<App />);

    await screen.findByRole('heading', { name: frontendExhibit.name });
    fireEvent.change(screen.getByLabelText(/GraphRAG/), { target: { value: 'candidate without sources' } });
    fireEvent.click(screen.getByRole('button', { name: '生成答案' }));

    const notice = await screen.findByRole('alert');
    expect(notice.textContent).toContain('未找到可引用来源');
    expect(screen.getByText('候选展项与查询语义匹配')).toBeTruthy();
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

    expect(await screen.findByRole('button', { name: '预览资料 报价清单.pdf' })).toBeTruthy();
    expect(screen.getByText('报价资料')).toBeTruthy();
  });

  it('shows an empty asset state when an exhibit has no media or documents', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () => okJson({ total: 1, items: [apiExhibit()] }));

    render(<App />);

    expect(await screen.findByText('暂无媒体或资料')).toBeTruthy();
  });

  it('opens PDF document previews with extracted citation chunks', async () => {
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

    fireEvent.click(await screen.findByRole('button', { name: '预览资料 气压演示说明.pdf' }));
    expect(screen.getByRole('dialog', { name: '气压演示说明.pdf' })).toBeTruthy();
    expect(screen.getByTitle('气压演示说明.pdf 预览')).toBeTruthy();
    expect(screen.getByText('引用片段')).toBeTruthy();
    expect(screen.getByText(/伯努利气流环道/)).toBeTruthy();
  });

  it('opens PDF document previews when the document title is clicked', async () => {
    const withDocument = {
      ...apiExhibit(),
      documents: [
        {
          id: 'preview-title-doc',
          name: '点击预览说明.pdf',
          file_type: 'pdf',
          url: '/api/files/preview-title-doc',
          source_note: 'PDF 说明资料'
        }
      ]
    };
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () => okJson({ total: 1, items: [withDocument] }));

    render(<App />);

    fireEvent.click(await screen.findByRole('button', { name: '点击预览说明.pdf' }));

    expect(screen.getByRole('dialog', { name: '点击预览说明.pdf' })).toBeTruthy();
    expect(screen.getByTitle('点击预览说明.pdf 预览')).toBeTruthy();
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
    expect(screen.getByText('未生成引用片段')).toBeTruthy();
  });

  it('renders read-only document extraction suggestions for uploaded documents', async () => {
    const withDocument = {
      ...apiExhibit(),
      documents: [
        {
          id: 'field-note-doc',
          name: 'field-note.txt',
          file_type: 'txt',
          url: '/api/files/field-note-doc',
          source_note: '现场记录',
          chunks: [{ id: 'field-note-doc:chunk-1', text: '展项名称：风洞实验台。预算：20-35 万。', sequence: 1 }]
        }
      ]
    };
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith('/api/exhibits/magnet-maze/documents/field-note-doc/extraction-suggestions')) {
        expect(init?.headers).toEqual({ 'X-User-Role': 'admin' });
        return okJson({
          document_id: 'field-note-doc',
          file_name: 'field-note.txt',
          file_type: 'txt',
          source_note: '现场记录',
          exhibit_name: '风洞实验台',
          category: '基础科学',
          theme: '力学',
          venue_type: null,
          budget_min: 200000,
          budget_max: 350000,
          materials: ['亚克力'],
          interactions: ['按钮互动'],
          supplier: '启思互动工坊',
          owner: '青禾儿童科技馆',
          project_year: 2024,
          tags: ['低龄儿童'],
          summary: '适合低龄儿童体验气流变化。',
          confidence: 0.76,
          field_sources: {
            exhibit_name: [
              {
                document_id: 'field-note-doc',
                field_name: 'exhibit_name',
                chunk_id: 'field-note-doc:chunk-1',
                source_locator: null,
                snippet: '展项名称：风洞实验台。预算：20-35 万。',
                reason: 'matched exhibit name'
              }
            ]
          }
        });
      }
      return okJson({ total: 1, items: [withDocument] });
    });

    render(<App />);

    expect(await screen.findByRole('link', { name: 'field-note.txt' })).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: '抽取字段建议 field-note.txt' }));

    const suggestionPanel = await screen.findByLabelText('字段抽取建议 field-note.txt');
    expect(within(suggestionPanel).getByText('风洞实验台')).toBeTruthy();
    expect(within(suggestionPanel).getByText('力学')).toBeTruthy();
    expect(within(suggestionPanel).getByText('20-35 万')).toBeTruthy();
    expect(within(suggestionPanel).getByText('置信度 76%')).toBeTruthy();
    expect(within(suggestionPanel).getByText(/展项名称：风洞实验台/)).toBeTruthy();
    expect(screen.getByRole('heading', { name: '磁力迷宫' })).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/api/exhibits/magnet-maze/documents/field-note-doc/extraction-suggestions',
      expect.objectContaining({ headers: { 'X-User-Role': 'admin' } })
    );
  });

  it('applies document extraction suggestions to the edit form without saving automatically', async () => {
    const withDocument = {
      ...apiExhibit(),
      documents: [
        {
          id: 'field-apply-doc',
          name: 'field-apply.txt',
          file_type: 'txt',
          url: '/api/files/field-apply-doc',
          source_note: '现场记录',
          chunks: [{ id: 'field-apply-doc:chunk-1', text: '展项名称：风洞实验台。预算：20-35 万。', sequence: 1 }]
        }
      ]
    };
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith('/api/exhibits/magnet-maze/documents/field-apply-doc/extraction-suggestions')) {
        return okJson({
          document_id: 'field-apply-doc',
          file_name: 'field-apply.txt',
          file_type: 'txt',
          source_note: '现场记录',
          exhibit_name: '风洞实验台',
          category: '基础科学',
          theme: '力学',
          venue_type: '儿童科技馆',
          budget_min: 200000,
          budget_max: 350000,
          materials: ['亚克力', '风机'],
          interactions: ['按钮互动'],
          supplier: '启思互动工坊',
          owner: '青禾儿童科技馆',
          project_year: 2024,
          tags: ['低龄儿童', '气流'],
          summary: '适合低龄儿童体验气流变化。',
          confidence: 0.82,
          field_sources: {}
        });
      }
      if (url.endsWith('/api/exhibits/magnet-maze') && init?.method === 'PUT') {
        return okJson(JSON.parse(String(init.body)));
      }
      return okJson({ total: 1, items: [withDocument] });
    });

    render(<App />);

    expect(await screen.findByRole('link', { name: 'field-apply.txt' })).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: '抽取字段建议 field-apply.txt' }));
    const suggestionPanel = await screen.findByLabelText('字段抽取建议 field-apply.txt');
    fireEvent.click(within(suggestionPanel).getByRole('button', { name: '套用建议到编辑表单' }));

    expect((screen.getByPlaceholderText('展项名称') as HTMLInputElement).value).toBe('风洞实验台');
    expect((screen.getByPlaceholderText('主题，如力学') as HTMLInputElement).value).toBe('力学');
    expect((screen.getByPlaceholderText('最低造价') as HTMLInputElement).value).toBe('200000');
    expect((screen.getByPlaceholderText('最高造价') as HTMLInputElement).value).toBe('350000');
    expect((screen.getByPlaceholderText('材料，用逗号分隔') as HTMLInputElement).value).toBe('亚克力,风机');
    expect((screen.getByPlaceholderText('标签，用逗号分隔') as HTMLInputElement).value).toBe('低龄儿童,气流');
    expect((screen.getByPlaceholderText('展项说明') as HTMLTextAreaElement).value).toBe('适合低龄儿童体验气流变化。');
    expect(fetchMock.mock.calls.some(([input, init]) => String(input).endsWith('/api/exhibits/magnet-maze') && init?.method === 'PUT')).toBe(false);
  });

  it('uses explicit download URLs while keeping PDF preview URLs inline in the modal', async () => {
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

    fireEvent.click(await screen.findByRole('button', { name: '预览资料 quote.pdf' }));
    const link = screen.getByRole('link', { name: '下载原文件' });

    expect(link.getAttribute('href')).toBe('http://127.0.0.1:8000/api/files/quote-download-doc?download=1');
    expect(link.getAttribute('download')).toBe('quote.pdf');
    const preview = screen.getByTitle('quote.pdf 预览') as HTMLIFrameElement;
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

    expect(await screen.findByRole('button', { name: 'scene.png' })).toBeTruthy();
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

    fireEvent.click(within(imageDialog).getByRole('button', { name: '关闭预览' }));
    expect(screen.queryByRole('dialog', { name: 'preview-image.png' })).toBeNull();

    fireEvent.click(screen.getByRole('button', { name: '预览媒体 preview-video.mp4' }));
    const videoDialog = screen.getByRole('dialog', { name: 'preview-video.mp4' });
    const video = within(videoDialog).getByLabelText('preview-video.mp4 播放器') as HTMLVideoElement;
    expect(video.tagName).toBe('VIDEO');
    expect(video.controls).toBe(true);
  });

  it('renders PDF documents inside the compact media archive grid and opens previews from thumbnails', async () => {
    const withDocument = apiExhibit({
      ...frontendExhibit,
      documents: [
        {
          id: 'quote-pdf',
          name: '报价说明.pdf',
          fileType: 'pdf',
          url: 'http://assets.test/quote.pdf',
          sourceNote: '报价文件',
          chunks: [{ id: 'quote-1', text: '预算 20-30 万', sequence: 1 }]
        }
      ]
    });
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () => okJson({ total: 1, items: [withDocument] }));

    render(<App />);

    const mediaArchive = await screen.findByLabelText('媒体档案');
    expect(within(mediaArchive).getByRole('button', { name: '预览资料 报价说明.pdf' })).toBeTruthy();
    expect(within(mediaArchive).getByText('已生成 1 个引用片段')).toBeTruthy();
    expect(screen.queryByText('资料文档')).toBeNull();

    fireEvent.click(within(mediaArchive).getByRole('button', { name: '预览资料 报价说明.pdf' }));

    const dialog = screen.getByRole('dialog', { name: '报价说明.pdf' });
    expect(within(dialog).getByTitle('报价说明.pdf 预览')).toBeTruthy();
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

    expect(await screen.findByRole('button', { name: '预览资料 quote.pdf' })).toBeTruthy();
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

  it('shows backend import parse errors with filename guidance', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith('/api/exhibits/import')) {
        return {
          ok: false,
          status: 400,
          statusText: 'Bad Request',
          json: async () => ({
            detail: {
              error: 'InvalidImportFile',
              message: 'Import file could not be parsed',
              details: {
                filename: 'broken.xlsx',
                supported_formats: ['csv', 'xlsx']
              }
            }
          })
        } as Response;
      }
      return okJson({ total: 1, items: [apiExhibit()] });
    });

    render(<App />);

    await screen.findByRole('heading', { name: '磁力迷宫' });
    const input = document.querySelector('.import-upload input') as HTMLInputElement;
    const file = new File(['broken'], 'broken.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    });
    fireEvent.change(input, { target: { files: [file] } });

    expect(await screen.findByText('导入文件 broken.xlsx 无法解析，请上传 csv / xlsx 格式文件')).toBeTruthy();
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
    expect(screen.getByText('造价下限')).toBeTruthy();
    expect(screen.getByText('必须填写整数')).toBeTruthy();
    expect(screen.queryByText('budget_min')).toBeNull();
    expect(screen.queryByText('Must be an integer')).toBeNull();
    expect((screen.getByRole('button', { name: '确认导入' }) as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByRole('heading', { name: '磁力迷宫' })).toBeTruthy();
  });

  it('shows empty import file errors in business language', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith('/api/exhibits/import')) {
        expect(init?.method).toBe('POST');
        return okJson({
          total_rows: 0,
          valid_rows: 0,
          imported_count: 0,
          errors: [{ row: 1, field: 'file', message: 'No import rows found' }],
          items: []
        });
      }
      return okJson({ total: 1, items: [apiExhibit()] });
    });

    render(<App />);

    await screen.findByRole('heading', { name: '磁力迷宫' });
    const input = document.querySelector('.import-upload input') as HTMLInputElement;
    const file = new File(['id,name'], 'empty.csv', { type: 'text/csv' });
    fireEvent.change(input, { target: { files: [file] } });

    expect(await screen.findByText('导入校验发现 1 个问题，未写入数据')).toBeTruthy();
    const errorPanel = document.querySelector('.import-preview-errors') as HTMLElement;
    expect(within(errorPanel).getByText('文件')).toBeTruthy();
    expect(within(errorPanel).getByText('文件内容')).toBeTruthy();
    expect(within(errorPanel).getByText('没有找到可导入的数据行')).toBeTruthy();
    expect(within(errorPanel).queryByText('第 1 行')).toBeNull();
    expect(screen.queryByText('No import rows found')).toBeNull();
  });
});
