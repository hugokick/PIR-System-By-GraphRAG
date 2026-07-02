import { describe, expect, it } from 'vitest';
import { filterExhibits, semanticSearch } from './search';
import type { Exhibit } from '../types';

const fixtures: Exhibit[] = [
  {
    id: 'lever-play',
    name: '杠杆乐园',
    category: '基础科学',
    theme: '力学',
    venueType: '儿童科技馆',
    budgetMin: 200000,
    budgetMax: 350000,
    materials: ['金属', '木作'],
    dimensions: '4200x2600x2200mm',
    interactions: ['机械互动', '亲子协作'],
    supplier: '启思互动工坊',
    projectName: '青禾儿童科技馆更新项目',
    projectYear: 2024,
    owner: '青禾儿童科技馆',
    status: '已落地',
    reviewStatus: '已审核',
    description: '面向低龄儿童的力学互动展项，通过推拉、配重和跷跷板结构理解杠杆原理。',
    tags: ['低龄儿童', '力学', '预算适中'],
    media: [],
    documents: [],
    relatedProjectIds: ['qinghe-2024'],
    relatedExhibitIds: ['pulley-wall']
  },
  {
    id: 'space-dome',
    name: '星际穹幕影院',
    category: '宇宙探索',
    theme: '天文',
    venueType: '综合科技馆',
    budgetMin: 900000,
    budgetMax: 1600000,
    materials: ['钢结构', '投影幕'],
    dimensions: '直径9000mm',
    interactions: ['沉浸影像'],
    supplier: '星图数字',
    projectName: '江北科技馆宇宙探索展区',
    projectYear: 2023,
    owner: '江北科技馆',
    status: '已落地',
    reviewStatus: '已审核',
    description: '沉浸式球幕内容播放空间，适合天文科普课程。',
    tags: ['沉浸式', '天文'],
    media: [],
    documents: [],
    relatedProjectIds: ['jiangbei-2023'],
    relatedExhibitIds: []
  }
];

describe('filterExhibits', () => {
  it('matches structured budget, venue, material, and interaction filters', () => {
    const result = filterExhibits(fixtures, {
      venueType: '儿童科技馆',
      budgetRange: [200000, 500000],
      material: '金属',
      interaction: '机械互动'
    });

    expect(result.map((item) => item.id)).toEqual(['lever-play']);
  });
});

describe('semanticSearch', () => {
  it('ranks low-budget children mechanics exhibits above unrelated immersive exhibits', () => {
    const result = semanticSearch(
      fixtures,
      '找几个适合低龄儿童、预算不高、互动性强的力学展项'
    );

    expect(result[0].item.id).toBe('lever-play');
    expect(result[0].score).toBeGreaterThan(result[1].score);
    expect(result[0].matchedSignals).toContain('低龄儿童');
  });
});
