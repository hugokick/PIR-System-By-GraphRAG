import { fireEvent, render, screen, waitFor } from '@testing-library/react';
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

afterEach(() => {
  vi.restoreAllMocks();
});

describe('App exhibit management', () => {
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

  it('renders Neo4j graph metadata, relationship types, and selected node details', async () => {
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
    expect(screen.getByText('USES_MATERIAL')).toBeTruthy();
    expect(screen.getByText('SUPPLIED_BY')).toBeTruthy();
    expect(screen.getByRole('button', { name: '重新布局' })).toBeTruthy();

    fireEvent.click(await screen.findByRole('button', { name: /Backend Material/ }));

    expect(screen.getByText('material:backend-only')).toBeTruthy();
    expect(screen.getAllByText('Backend Material').length).toBeGreaterThan(0);
    expect(screen.getAllByText('material').length).toBeGreaterThan(0);
    expect(fetchMock).toHaveBeenCalledWith('http://127.0.0.1:8000/api/exhibits/magnet-maze/graph');
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

  it('shows audit log entries to admins', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith('/api/admin/audit-logs?limit=8')) {
        return okJson({
          total: 1,
          items: [
            {
              id: 'audit-1',
              actor_role: 'admin',
              action: 'delete_exhibit',
              resource_type: 'exhibit',
              resource_id: 'magnet-maze',
              summary: 'Deleted exhibit magnet-maze',
              created_at: '2026-07-01T00:00:00+00:00'
            }
          ]
        });
      }
      return okJson({ total: 1, items: [apiExhibit()] });
    });

    render(<App />);

    expect(await screen.findByText('操作日志')).toBeTruthy();
    expect(screen.getByText('delete_exhibit')).toBeTruthy();
    expect(screen.getAllByText(/magnet-maze/).length).toBeGreaterThan(0);
    expect(screen.getAllByText('admin').length).toBeGreaterThan(0);
    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/api/admin/audit-logs?limit=8',
      expect.objectContaining({ headers: { 'X-User-Role': 'admin' } })
    );
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
        expect(init?.body).toBe(JSON.stringify({ query: 'lever-play', top_k: 3 }));
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
    fireEvent.change(screen.getByLabelText(/GraphRAG/), { target: { value: 'lever-play' } });
    fireEvent.click(screen.getByRole('button', { name: '生成答案' }));

    expect(await screen.findByText('Based on exhibit records and graph context.')).toBeTruthy();
    expect(screen.getAllByText('磁力迷宫').length).toBeGreaterThan(0);
    expect(screen.getByText(/matched identity/)).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/api/graphrag/answer',
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

  it('imports spreadsheet rows through the backend and renders the imported exhibit', async () => {
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
        expect(body.get('commit')).toBe('true');
        return okJson({
          total_rows: 1,
          valid_rows: 1,
          imported_count: 1,
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

    expect(await screen.findByRole('heading', { name: 'Imported Demo' })).toBeTruthy();
    expect(screen.getByText('已导入 1 条展项')).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/api/exhibits/import',
      expect.objectContaining({ method: 'POST' })
    );
  });

  it('shows import validation errors without changing the selected exhibit', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith('/api/exhibits/import')) {
        expect(init?.method).toBe('POST');
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
    expect(screen.getByRole('heading', { name: '磁力迷宫' })).toBeTruthy();
  });
});
