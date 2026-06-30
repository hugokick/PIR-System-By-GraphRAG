import { seedExhibits } from '../data/seed';
import type { Exhibit } from '../types';

const storageKey = 'exhibit-atlas.records.v1';

function normalizeExhibit(item: Exhibit): Exhibit {
  return {
    ...item,
    media: item.media ?? [],
    documents: item.documents ?? []
  };
}

export function loadExhibits(): Exhibit[] {
  const raw = window.localStorage.getItem(storageKey);
  if (!raw) return seedExhibits.map(normalizeExhibit);

  try {
    return (JSON.parse(raw) as Exhibit[]).map(normalizeExhibit);
  } catch {
    return seedExhibits.map(normalizeExhibit);
  }
}

export function saveExhibits(items: Exhibit[]) {
  window.localStorage.setItem(storageKey, JSON.stringify(items));
}

export function resetExhibits() {
  saveExhibits(seedExhibits);
  return seedExhibits.map(normalizeExhibit);
}
