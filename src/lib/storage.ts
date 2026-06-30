import { seedExhibits } from '../data/seed';
import type { Exhibit } from '../types';

const storageKey = 'exhibit-atlas.records.v1';

export function loadExhibits(): Exhibit[] {
  const raw = window.localStorage.getItem(storageKey);
  if (!raw) return seedExhibits;

  try {
    return JSON.parse(raw) as Exhibit[];
  } catch {
    return seedExhibits;
  }
}

export function saveExhibits(items: Exhibit[]) {
  window.localStorage.setItem(storageKey, JSON.stringify(items));
}

export function resetExhibits() {
  saveExhibits(seedExhibits);
  return seedExhibits;
}
