import type { Exhibit, ExhibitFilters, SearchResult } from '../types';

const normalize = (value: string) => value.trim().toLowerCase();

const includesText = (haystack: string[], needle?: string) => {
  if (!needle) return true;
  const query = normalize(needle);
  return haystack.some((value) => normalize(value).includes(query));
};

const overlapsBudget = (item: Exhibit, range?: [number, number]) => {
  if (!range) return true;
  return item.budgetMax >= range[0] && item.budgetMin <= range[1];
};

export function formatBudget(item: Pick<Exhibit, 'budgetMin' | 'budgetMax'>) {
  return `${Math.round(item.budgetMin / 10000)}-${Math.round(item.budgetMax / 10000)} 万`;
}

export function filterExhibits(items: Exhibit[], filters: ExhibitFilters) {
  return items.filter((item) => {
    const searchable = [
      item.name,
      item.category,
      item.theme,
      item.venueType,
      item.owner,
      item.supplier,
      item.description,
      ...item.materials,
      ...item.interactions,
      ...item.tags
    ];

    return (
      includesText(searchable, filters.keyword) &&
      (!filters.category || item.category === filters.category) &&
      (!filters.theme || item.theme === filters.theme) &&
      (!filters.venueType || item.venueType === filters.venueType) &&
      (!filters.status || item.status === filters.status) &&
      overlapsBudget(item, filters.budgetRange) &&
      (!filters.material || item.materials.includes(filters.material)) &&
      (!filters.interaction || item.interactions.includes(filters.interaction))
    );
  });
}

const signalMap: Array<[string, string[]]> = [
  ['低龄儿童', ['低龄', '儿童', '亲子', '幼儿']],
  ['预算不高', ['预算不高', '低预算', '便宜', '不贵', '预算适中']],
  ['互动性强', ['互动', '动手', '机械', '多人', '竞赛', '协作']],
  ['力学', ['力学', '杠杆', '滑轮', '机械']],
  ['沉浸式', ['沉浸', '影院', '影像', '穹幕']],
  ['生态环境', ['生态', '水', '环保', '循环']],
  ['天文', ['宇宙', '天文', '星际', '太空']]
];

function collectText(item: Exhibit) {
  return [
    item.name,
    item.category,
    item.theme,
    item.venueType,
    item.owner,
    item.supplier,
    item.status,
    item.description,
    ...item.materials,
    ...item.interactions,
    ...item.tags
  ].join(' ');
}

function queryTokens(query: string) {
  const compact = normalize(query);
  const tokens = compact.match(/[\p{Script=Han}A-Za-z0-9]+/gu) ?? [];
  return [...new Set(tokens.flatMap((token) => [token, ...token.split(/[，,、\s]+/) ]).filter(Boolean))];
}

export function semanticSearch(items: Exhibit[], query: string): SearchResult[] {
  const tokens = queryTokens(query);
  const loweredQuery = normalize(query);

  return items
    .map((item) => {
      const text = normalize(collectText(item));
      const matchedSignals = signalMap
        .filter(([signal, aliases]) => {
          const signalAsked = loweredQuery.includes(signal) || aliases.some((alias) => loweredQuery.includes(alias));
          const signalPresent = text.includes(signal) || aliases.some((alias) => text.includes(alias));
          return signalAsked && signalPresent;
        })
        .map(([signal]) => signal);

      const tokenScore = tokens.reduce((score, token) => score + (text.includes(token) ? 1 : 0), 0);
      const budgetBoost =
        (loweredQuery.includes('预算不高') || loweredQuery.includes('低预算')) && item.budgetMax <= 500000 ? 2 : 0;
      const score = tokenScore + matchedSignals.length * 3 + budgetBoost;

      return { item, score, matchedSignals };
    })
    .sort((a, b) => b.score - a.score || a.item.budgetMax - b.item.budgetMax);
}
