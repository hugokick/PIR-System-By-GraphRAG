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
  it('prefills the selected exhibit and submits edits through the backend API', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (_input, init) => {
      if (init && init.method === 'PUT') {
        const body = JSON.parse(String(init.body));
        return okJson(body);
      }
      return okJson({ total: 1, items: [apiExhibit()] });
    });

    render(<App />);

    await screen.findByRole('heading', { name: '磁力迷宫' });
    fireEvent.click(screen.getByRole('button', { name: /编辑档案/ }));
    fireEvent.change(screen.getByPlaceholderText('展项名称'), { target: { value: '磁力迷宫 Pro' } });
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
});
