import type { Exhibit, GraphEdge, GraphNode } from '../types';

export function buildGraph(exhibit: Exhibit, allExhibits: Exhibit[]) {
  const nodes = new Map<string, GraphNode>();
  const edges: GraphEdge[] = [];

  const addNode = (node: GraphNode) => nodes.set(node.id, node);
  const addEdge = (target: string, label: string) => edges.push({ source: exhibit.id, target, label });

  addNode({ id: exhibit.id, label: exhibit.name, kind: 'exhibit' });

  exhibit.relatedProjectIds.forEach((projectId) => {
    addNode({ id: projectId, label: projectId, kind: 'project' });
    addEdge(projectId, '所属项目');
  });

  addNode({ id: `owner:${exhibit.owner}`, label: exhibit.owner, kind: 'owner' });
  addEdge(`owner:${exhibit.owner}`, '业主');

  addNode({ id: `supplier:${exhibit.supplier}`, label: exhibit.supplier, kind: 'supplier' });
  addEdge(`supplier:${exhibit.supplier}`, '供应商');

  addNode({ id: `theme:${exhibit.theme}`, label: exhibit.theme, kind: 'theme' });
  addEdge(`theme:${exhibit.theme}`, '主题');

  exhibit.materials.slice(0, 4).forEach((material) => {
    addNode({ id: `material:${material}`, label: material, kind: 'material' });
    addEdge(`material:${material}`, '材料');
  });

  exhibit.relatedExhibitIds.forEach((id) => {
    const related = allExhibits.find((item) => item.id === id);
    if (related) {
      addNode({ id: related.id, label: related.name, kind: 'exhibit' });
      addEdge(related.id, '相似展项');
    }
  });

  return { nodes: [...nodes.values()], edges };
}

export function graphStats(items: Exhibit[]) {
  const categories = new Map<string, number>();
  const themes = new Map<string, number>();

  items.forEach((item) => {
    categories.set(item.category, (categories.get(item.category) ?? 0) + 1);
    themes.set(item.theme, (themes.get(item.theme) ?? 0) + 1);
  });

  return {
    total: items.length,
    landed: items.filter((item) => item.status === '已落地').length,
    avgBudget: Math.round(
      items.reduce((sum, item) => sum + (item.budgetMin + item.budgetMax) / 2, 0) / Math.max(items.length, 1) / 10000
    ),
    categories: [...categories.entries()],
    themes: [...themes.entries()].sort((a, b) => b[1] - a[1])
  };
}
