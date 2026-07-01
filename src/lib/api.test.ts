import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  askGraphRag,
  buildExhibitQuery,
  createExhibit,
  deleteExhibit,
  fetchAuditLogs,
  fetchDashboardSummary,
  fetchDemoGraph,
  hybridSearchExhibits,
  importExhibits,
  login,
  mapApiExhibit,
  mapApiGraph,
  mapExhibitToApiPayload,
  setApiRole,
  setApiSession,
  updateExhibit,
  updateExhibitRelatedExhibits,
  updateExhibitReviewStatus,
  uploadExhibitAsset,
  type ApiExhibit
} from './api';
import type { Exhibit } from '../types';

const apiExhibit: ApiExhibit = {
  id: 'lever-play',
  name: '杠杆乐园',
  category: '基础科学',
  theme: { id: 'mechanics', name: '力学' },
  venue_type: '儿童科技馆',
  budget_min: 200000,
  budget_max: 350000,
  materials: [
    { id: 'metal', name: '金属' },
    { id: 'woodwork', name: '木作' }
  ],
  dimensions: '4200x2600x2200mm',
  interactions: [{ id: 'mechanical', name: '机械互动' }],
  supplier: { id: 'qisi', name: '启思互动工坊' },
  project: { id: 'qinghe-2024', name: '青禾儿童科技馆更新项目' },
  owner: { id: 'qinghe-owner', name: '青禾儿童科技馆' },
  project_year: 2024,
  status: '已落地',
  review_status: '已审核',
  description: '通过推拉、配重和跷跷板结构帮助低龄儿童理解杠杆原理。',
  tags: ['低龄儿童', '力学'],
  media_assets: [
    {
      id: 'lever-render',
      type: 'image',
      name: '展项效果图',
      url: 'https://picsum.photos/seed/exhibit-lever/900/600',
      note: '示意图'
    }
  ],
  documents: [
    {
      id: 'lever-brief',
      name: '杠杆乐园展项说明',
      file_type: 'pdf',
      url: '/files/lever-brief.pdf',
      source_note: '样例文档'
    }
  ],
  related_exhibit_ids: ['pulley-wall']
};

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

afterEach(() => {
  vi.restoreAllMocks();
  setApiRole('admin');
  setApiSession(null);
});

describe('mapApiExhibit', () => {
  it('converts backend snake_case exhibit payloads into frontend exhibit records', () => {
    const mapped = mapApiExhibit(apiExhibit);

    expect(mapped).toMatchObject({
      id: 'lever-play',
      name: '杠杆乐园',
      theme: '力学',
      venueType: '儿童科技馆',
      budgetMin: 200000,
      budgetMax: 350000,
      supplier: '启思互动工坊',
      projectYear: 2024,
      owner: '青禾儿童科技馆',
      reviewStatus: '已审核',
      relatedProjectIds: ['qinghe-2024'],
      relatedExhibitIds: ['pulley-wall']
    });
    expect(mapped.materials).toEqual(['金属', '木作']);
    expect(mapped.interactions).toEqual(['机械互动']);
    expect(mapped.media[0]).toEqual({
      id: 'lever-render',
      type: 'image',
      name: '展项效果图',
      url: 'https://picsum.photos/seed/exhibit-lever/900/600',
      note: '示意图'
    });
    expect(mapped.documents[0]).toEqual({
      id: 'lever-brief',
      name: '杠杆乐园展项说明',
      fileType: 'pdf',
      url: '/files/lever-brief.pdf',
      sourceNote: '样例文档'
    });
  });

  it('resolves backend file URLs against the API base URL', () => {
    const mapped = mapApiExhibit({
      ...apiExhibit,
      media_assets: [
        {
          id: 'uploaded-image',
          type: 'image',
          name: '现场图.png',
          url: '/api/files/uploaded-image',
          note: null
        }
      ],
      documents: [
        {
          id: 'uploaded-pdf',
          name: '说明.pdf',
          file_type: 'pdf',
          url: '/api/files/uploaded-pdf',
          source_note: null
        }
      ]
    });

    expect(mapped.media[0].url).toBe('http://127.0.0.1:8000/api/files/uploaded-image');
    expect(mapped.documents[0].url).toBe('http://127.0.0.1:8000/api/files/uploaded-pdf');
  });
});

describe('mapExhibitToApiPayload', () => {
  it('converts frontend exhibit records into backend write payloads', () => {
    const payload = mapExhibitToApiPayload(frontendExhibit);

    expect(payload).toMatchObject({
      id: 'magnet-maze',
      name: '磁力迷宫',
      theme: { id: 'dianci-xue', name: '电磁学' },
      venue_type: '儿童科技馆',
      budget_min: 180000,
      budget_max: 320000,
      supplier: { id: 'qisi-hudong-gongfang', name: '启思互动工坊' },
      project: { id: 'qinghe-2024', name: 'qinghe-2024' },
      owner: { id: 'qinghe-ertong-kejiguan', name: '青禾儿童科技馆' },
      project_year: 2024,
      review_status: '待审核',
      related_exhibit_ids: ['lever-play']
    });
    expect(payload.materials).toEqual([{ id: 'yake-li', name: '亚克力' }]);
    expect(payload.interactions).toEqual([{ id: 'dongshou-shiyan', name: '动手实验' }]);
    expect(payload.documents).toEqual([]);
  });

  it('keeps manually curated similar exhibit relationships in write payloads', () => {
    const payload = mapExhibitToApiPayload({
      ...frontendExhibit,
      relatedExhibitIds: ['lever-play', 'water-cycle']
    });

    expect(payload.related_exhibit_ids).toEqual(['lever-play', 'water-cycle']);
  });
});

describe('buildExhibitQuery', () => {
  it('serializes structured filters with backend parameter names', () => {
    const query = buildExhibitQuery({
      keyword: '力学',
      venueType: '儿童科技馆',
      projectId: 'qinghe-2024',
      reviewStatus: '待审核',
      material: '金属',
      interaction: '机械互动',
      budgetRange: [200000, 500000],
      status: '已落地'
    });

    expect(query.toString()).toBe(
      'keyword=%E5%8A%9B%E5%AD%A6&venue_type=%E5%84%BF%E7%AB%A5%E7%A7%91%E6%8A%80%E9%A6%86&project_id=qinghe-2024&review_status=%E5%BE%85%E5%AE%A1%E6%A0%B8&material=%E9%87%91%E5%B1%9E&interaction=%E6%9C%BA%E6%A2%B0%E4%BA%92%E5%8A%A8&status=%E5%B7%B2%E8%90%BD%E5%9C%B0&budget_min=200000&budget_max=500000'
    );
  });
});

describe('mapApiGraph', () => {
  it('preserves backend graph nodes and edges for visualization', () => {
    const mapped = mapApiGraph({
      nodes: [{ id: 'exhibit:lever-play', label: '杠杆乐园', type: 'exhibit' }],
      edges: [
        {
          source: 'exhibit:lever-play',
          target: 'material:metal',
          label: '使用材料',
          type: 'uses_material'
        }
      ]
    });

    expect(mapped.nodes).toEqual([{ id: 'exhibit:lever-play', label: '杠杆乐园', kind: 'exhibit' }]);
    expect(mapped.edges).toEqual([
      {
        source: 'exhibit:lever-play',
        target: 'material:metal',
        type: 'uses_material',
        label: '使用材料'
      }
    ]);
  });
});

describe('fetchDemoGraph', () => {
  it('loads the full Neo4j demo graph from the demo endpoint', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({
        nodes: [
          { id: 'exhibit:lever-play', label: 'Lever Play', type: 'exhibit' },
          { id: 'exhibit:space-dome', label: 'Space Dome', type: 'exhibit' }
        ],
        edges: [
          {
            source: 'exhibit:lever-play',
            target: 'exhibit:space-dome',
            label: 'similar',
            type: 'similar_to'
          }
        ]
      })
    } as Response);

    const result = await fetchDemoGraph();

    expect(fetchMock).toHaveBeenCalledWith('http://127.0.0.1:8000/api/neo4j-demo/graph');
    expect(result.nodes.map((node) => node.id)).toEqual(['exhibit:lever-play', 'exhibit:space-dome']);
    expect(result.edges[0].type).toBe('similar_to');
  });
});

describe('fetchDashboardSummary', () => {
  it('loads filtered dashboard metrics from the backend summary endpoint', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({
        total: 9,
        landed: 4,
        avg_budget: 38,
        pending_review: 2,
        rejected_review: 1,
        categories: [{ label: '基础科学', count: 5 }],
        budget_bands: [{ label: '20-50万', count: 6 }],
        themes: [{ label: '力学', count: 4 }],
        review_statuses: [{ label: '待审核', count: 2 }]
      })
    } as Response);

    const result = await fetchDashboardSummary({
      projectId: 'qinghe-2024',
      reviewStatus: frontendExhibit.reviewStatus
    });

    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/api/dashboard/summary?project_id=qinghe-2024&review_status=%E5%BE%85%E5%AE%A1%E6%A0%B8'
    );
    expect(result).toEqual({
      total: 9,
      landed: 4,
      avgBudget: 38,
      pendingReview: 2,
      rejectedReview: 1,
      categories: [['基础科学', 5]],
      budgetBands: [['20-50万', 6]],
      themes: [['力学', 4]],
      reviewStatuses: [['待审核', 2]]
    });
  });
});

describe('login', () => {
  it('posts credentials and maps the authenticated session', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({
        access_token: 'signed-token',
        token_type: 'bearer',
        user: {
          username: 'editor',
          role: 'editor',
          display_name: '编辑员'
        }
      })
    } as Response);

    const session = await login('editor', 'editor123');

    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/api/auth/login',
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: 'editor', password: 'editor123' })
      })
    );
    expect(session).toEqual({
      accessToken: 'signed-token',
      tokenType: 'bearer',
      user: {
        username: 'editor',
        role: 'editor',
        displayName: '编辑员'
      }
    });
  });
});

describe('createExhibit', () => {
  it('sends the active user role with write requests', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => mapExhibitToApiPayload(frontendExhibit)
    } as Response);

    setApiRole('editor');
    await createExhibit(frontendExhibit);

    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/api/exhibits',
      expect.objectContaining({
        headers: {
          'Content-Type': 'application/json',
          'X-User-Role': 'editor'
        }
      })
    );
  });

  it('sends a bearer token when an authenticated session is active', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => mapExhibitToApiPayload(frontendExhibit)
    } as Response);

    setApiSession({
      accessToken: 'signed-token',
      tokenType: 'bearer',
      user: { username: 'editor', role: 'editor', displayName: '编辑员' }
    });
    await createExhibit(frontendExhibit);

    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/api/exhibits',
      expect.objectContaining({
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer signed-token'
        }
      })
    );
  });

  it('posts backend write payloads and maps the response back to frontend records', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => mapExhibitToApiPayload(frontendExhibit)
    } as Response);

    const result = await createExhibit(frontendExhibit);

    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/api/exhibits',
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-User-Role': 'admin' },
        body: JSON.stringify(mapExhibitToApiPayload(frontendExhibit))
      })
    );
    expect(result).toMatchObject({
      id: 'magnet-maze',
      name: '磁力迷宫',
      theme: '电磁学',
      venueType: '儿童科技馆'
    });
  });
});

describe('updateExhibit', () => {
  it('puts backend write payloads and maps the updated response', async () => {
    const updated = { ...frontendExhibit, name: '磁力迷宫 Pro' };
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => mapExhibitToApiPayload(updated)
    } as Response);

    const result = await updateExhibit('magnet-maze', updated);

    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/api/exhibits/magnet-maze',
      expect.objectContaining({
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'X-User-Role': 'admin' },
        body: JSON.stringify(mapExhibitToApiPayload(updated))
      })
    );
    expect(result.name).toBe('磁力迷宫 Pro');
  });
});

describe('updateExhibitReviewStatus', () => {
  it('patches only the exhibit review status and maps the updated record', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({
        ...apiExhibit,
        review_status: '已审核'
      })
    } as Response);

    const result = await updateExhibitReviewStatus('lever-play', '已审核');

    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/api/exhibits/lever-play/review-status',
      expect.objectContaining({
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', 'X-User-Role': 'admin' },
        body: JSON.stringify({ review_status: '已审核' })
      })
    );
    expect(result.reviewStatus).toBe('已审核');
  });
});

describe('updateExhibitRelatedExhibits', () => {
  it('patches only curated similar exhibit relationships and maps the updated record', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({
        ...apiExhibit,
        related_exhibit_ids: ['pulley-wall', 'water-cycle']
      })
    } as Response);

    const result = await updateExhibitRelatedExhibits('lever-play', ['pulley-wall', 'water-cycle']);

    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/api/exhibits/lever-play/related-exhibits',
      expect.objectContaining({
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', 'X-User-Role': 'admin' },
        body: JSON.stringify({ related_exhibit_ids: ['pulley-wall', 'water-cycle'] })
      })
    );
    expect(result.relatedExhibitIds).toEqual(['pulley-wall', 'water-cycle']);
  });
});

describe('deleteExhibit', () => {
  it('sends a DELETE request for the selected exhibit', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true
    } as Response);

    await deleteExhibit('magnet-maze');

    expect(fetchMock).toHaveBeenCalledWith('http://127.0.0.1:8000/api/exhibits/magnet-maze', {
      method: 'DELETE',
      headers: { 'X-User-Role': 'admin' }
    });
  });
});

describe('fetchAuditLogs', () => {
  it('loads admin audit log entries with the active role header', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({
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
      })
    } as Response);

    const result = await fetchAuditLogs(10);

    expect(fetchMock).toHaveBeenCalledWith('http://127.0.0.1:8000/api/admin/audit-logs?limit=10', {
      headers: { 'X-User-Role': 'admin' }
    });
    expect(result).toEqual([
      {
        id: 'audit-1',
        actorRole: 'admin',
        action: 'delete_exhibit',
        resourceType: 'exhibit',
        resourceId: 'magnet-maze',
        summary: 'Deleted exhibit magnet-maze',
        createdAt: '2026-07-01T00:00:00+00:00'
      }
    ]);
  });
});

describe('askGraphRag', () => {
  it('posts GraphRAG answer requests and maps the exhibit hits', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({
        query: 'lever-play',
        answer: 'Based on exhibit records and graph context.',
        citations: [
          {
            source_id: 'lever-play',
            source_type: 'exhibit',
            title: '杠杆乐园',
            snippet: '通过推拉、配重理解杠杆原理。'
          }
        ],
        items: [
          {
            exhibit: apiExhibit,
            score: 9,
            reasons: ['matched identity'],
            citations: [],
            graph: {
              nodes: [{ id: 'exhibit:lever-play', label: '杠杆乐园', type: 'exhibit' }],
              edges: []
            }
          }
        ]
      })
    } as Response);

    const result = await askGraphRag('lever-play', 2);

    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/api/graphrag/answer',
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-User-Role': 'admin' },
        body: JSON.stringify({ query: 'lever-play', top_k: 2 })
      })
    );
    expect(result.answer).toBe('Based on exhibit records and graph context.');
    expect(result.items[0].exhibit.id).toBe('lever-play');
    expect(result.citations[0].sourceId).toBe('lever-play');
  });
});

describe('hybridSearchExhibits', () => {
  it('posts hybrid search requests and maps scored exhibit hits', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({
        query: '低龄儿童 力学 互动',
        total: 1,
        items: [
          {
            exhibit: apiExhibit,
            score: 14,
            reasons: ['匹配人群：低龄儿童', '筛选互动：机械互动']
          }
        ]
      })
    } as Response);

    const result = await hybridSearchExhibits('低龄儿童 力学 互动', {
      venueType: '儿童科技馆',
      theme: '力学',
      material: '金属',
      interaction: '机械互动',
      reviewStatus: '待审核',
      budgetRange: [0, 350000]
    });

    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/api/search/hybrid',
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-User-Role': 'admin' }
      })
    );
    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body))).toEqual({
      query: '低龄儿童 力学 互动',
      limit: 4,
      filters: {
        venue_type: '儿童科技馆',
        theme: '力学',
        material: '金属',
        interaction: '机械互动',
        review_status: '待审核',
        budget_min: 0,
        budget_max: 350000
      }
    });
    expect(result[0].item.id).toBe('lever-play');
    expect(result[0].matchedSignals).toEqual(['匹配人群：低龄儿童', '筛选互动：机械互动']);
  });
});

describe('uploadExhibitAsset', () => {
  it('uploads files as multipart form data and maps the updated exhibit', async () => {
    const updatedPayload = {
      ...mapExhibitToApiPayload(frontendExhibit),
      media_assets: [
        {
          id: 'media-uploaded',
          type: 'image',
          name: 'scene.png',
          url: '/api/files/uploaded',
          note: '现场照片'
        }
      ]
    };
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => updatedPayload
    } as Response);
    const file = new File(['fake image bytes'], 'scene.png', { type: 'image/png' });

    const result = await uploadExhibitAsset('magnet-maze', file, 'media', '现场照片');

    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/api/exhibits/magnet-maze/assets',
      expect.objectContaining({
        method: 'POST',
        body: expect.any(FormData)
      })
    );
    const body = fetchMock.mock.calls[0][1]?.body as FormData;
    expect(body.get('asset_kind')).toBe('media');
    expect(body.get('note')).toBe('现场照片');
    expect(body.get('file')).toBe(file);
    expect(result.media[0]).toEqual({
      id: 'media-uploaded',
      type: 'image',
      name: 'scene.png',
      url: 'http://127.0.0.1:8000/api/files/uploaded',
      note: '现场照片'
    });
  });

  it('uploads document files as document assets and maps the returned documents', async () => {
    const updatedPayload = {
      ...mapExhibitToApiPayload(frontendExhibit),
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
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => updatedPayload
    } as Response);
    const file = new File(['fake pdf bytes'], 'quote.pdf', { type: 'application/pdf' });

    const result = await uploadExhibitAsset('magnet-maze', file, 'document', '报价资料');

    const body = fetchMock.mock.calls[0][1]?.body as FormData;
    expect(body.get('asset_kind')).toBe('document');
    expect(body.get('note')).toBe('报价资料');
    expect(body.get('file')).toBe(file);
    expect(result.documents[0]).toEqual({
      id: 'document-uploaded',
      name: 'quote.pdf',
      fileType: 'pdf',
      url: 'http://127.0.0.1:8000/api/files/uploaded-document',
      sourceNote: '报价资料'
    });
  });
});

describe('importExhibits', () => {
  it('uploads spreadsheet files and maps imported exhibit rows', async () => {
    const importedPayload = {
      total_rows: 1,
      valid_rows: 1,
      imported_count: 1,
      errors: [],
      items: [mapExhibitToApiPayload(frontendExhibit)]
    };
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => importedPayload
    } as Response);
    const file = new File(['id,name\nmagnet-maze,磁力迷宫'], 'exhibits.csv', { type: 'text/csv' });

    const result = await importExhibits(file, true);

    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/api/exhibits/import',
      expect.objectContaining({
        method: 'POST',
        body: expect.any(FormData)
      })
    );
    const body = fetchMock.mock.calls[0][1]?.body as FormData;
    expect(body.get('commit')).toBe('true');
    expect(body.get('file')).toBe(file);
    expect(result.importedCount).toBe(1);
    expect(result.items[0].id).toBe('magnet-maze');
  });
});
