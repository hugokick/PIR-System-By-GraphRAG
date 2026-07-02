import { describe, expect, it } from 'vitest';

import { seedExhibits } from './seed';

describe('seedExhibits', () => {
  it('contains a rich demo case library for public demonstrations', () => {
    expect(seedExhibits.length).toBeGreaterThanOrEqual(15);
    expect(new Set(seedExhibits.map((item) => item.id)).size).toBe(seedExhibits.length);
    expect(seedExhibits.some((item) => item.id === 'space-dome')).toBe(true);
    expect(new Set(seedExhibits.map((item) => item.theme)).size).toBeGreaterThanOrEqual(8);
    expect(new Set(seedExhibits.map((item) => item.venueType)).size).toBeGreaterThanOrEqual(4);
    expect(seedExhibits.some((item) => item.budgetMax <= 300000)).toBe(true);
    expect(seedExhibits.some((item) => item.budgetMin >= 800000)).toBe(true);
  });
});
