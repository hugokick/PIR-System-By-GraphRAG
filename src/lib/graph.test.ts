import { describe, expect, it } from 'vitest';
import { graphStats } from './graph';
import type { Exhibit } from '../types';

function exhibit(
  id: string,
  reviewStatus: Exhibit['reviewStatus'],
  overrides: Partial<Pick<Exhibit, 'theme' | 'budgetMin' | 'budgetMax'>> = {}
): Exhibit {
  return {
    id,
    name: id,
    category: id === 'water-cycle' ? '生态环境' : '基础科学',
    theme: overrides.theme ?? '力学',
    venueType: '儿童科技馆',
    budgetMin: overrides.budgetMin ?? 100000,
    budgetMax: overrides.budgetMax ?? 300000,
    materials: ['金属'],
    dimensions: '1000x1000x1000mm',
    interactions: ['机械互动'],
    supplier: '启思互动工坊',
    projectYear: 2024,
    owner: '青禾儿童科技馆',
    status: id === 'lever-play' ? '已落地' : '制作中',
    reviewStatus,
    description: '测试展项',
    tags: [],
    media: [],
    documents: [],
    relatedProjectIds: ['qinghe-2024'],
    relatedExhibitIds: []
  };
}

describe('graphStats', () => {
  it('summarizes exhibit review status distribution for the dashboard', () => {
    const stats = graphStats([
      exhibit('lever-play', '已审核'),
      exhibit('pulley-wall', '待审核'),
      exhibit('water-cycle', '已退回')
    ]);

    expect(stats.reviewStatuses).toEqual([
      ['已审核', 1],
      ['待审核', 1],
      ['已退回', 1]
    ]);
    expect(stats.pendingReview).toBe(1);
    expect(stats.rejectedReview).toBe(1);
  });

  it('summarizes budget bands and hot themes for the dashboard', () => {
    const stats = graphStats([
      exhibit('hands-on-low', '已审核', { theme: '力学', budgetMin: 80000, budgetMax: 120000 }),
      exhibit('pulley-mid', '待审核', { theme: '力学', budgetMin: 200000, budgetMax: 500000 }),
      exhibit('space-high', '已审核', { theme: '天文', budgetMin: 900000, budgetMax: 1600000 })
    ]);

    expect(stats.budgetBands).toEqual([
      ['20万以下', 1],
      ['20-50万', 1],
      ['50万以上', 1]
    ]);
    expect(stats.themes).toEqual([
      ['力学', 2],
      ['天文', 1]
    ]);
  });
});
