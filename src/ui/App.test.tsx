import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { App } from './App';
import { mapExhibitToApiPayload, type ApiExhibit } from '../lib/api';
import type { Exhibit } from '../types';

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
        method: 'DELETE'
      });
    });
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
});
