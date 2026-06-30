import { describe, expect, it } from 'vitest';
import { graphStats } from './graph';
import type { Exhibit } from '../types';

function exhibit(id: string, reviewStatus: Exhibit['reviewStatus']): Exhibit {
  return {
    id,
    name: id,
    category: id === 'water-cycle' ? '生态环境' : '基础科学',
    theme: '力学',
    venueType: '儿童科技馆',
    budgetMin: 100000,
    budgetMax: 300000,
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
});
