import { describe, expect, it } from 'vitest';
import { buildExhibitQuery, mapApiExhibit, mapApiGraph, type ApiExhibit } from './api';

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
  });
});

describe('buildExhibitQuery', () => {
  it('serializes structured filters with backend parameter names', () => {
    const query = buildExhibitQuery({
      keyword: '力学',
      venueType: '儿童科技馆',
      material: '金属',
      interaction: '机械互动',
      budgetRange: [200000, 500000],
      status: '已落地'
    });

    expect(query.toString()).toBe(
      'keyword=%E5%8A%9B%E5%AD%A6&venue_type=%E5%84%BF%E7%AB%A5%E7%A7%91%E6%8A%80%E9%A6%86&material=%E9%87%91%E5%B1%9E&interaction=%E6%9C%BA%E6%A2%B0%E4%BA%92%E5%8A%A8&status=%E5%B7%B2%E8%90%BD%E5%9C%B0&budget_min=200000&budget_max=500000'
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
        label: '使用材料'
      }
    ]);
  });
});
