import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { render } from '@testing-library/react';
import React from 'react';
import { describe, expect, it, vi } from 'vitest';
import type { GraphEdge, GraphNode } from '../types';
import { buildNvlGraphData, nvlGraphStyling } from './nvlGraphData';

let lastNvlProps: {
  layout?: string;
  layoutOptions?: Record<string, unknown>;
  nvlOptions?: Record<string, unknown>;
  positions?: { id: string; x?: number; y?: number; caption?: string }[];
} | null = null;

vi.mock('@neo4j-nvl/react', () => ({
  InteractiveNvlWrapper: React.forwardRef(
    (
      props: {
        layout?: string;
        layoutOptions?: Record<string, unknown>;
        nvlOptions?: Record<string, unknown>;
        positions?: { id: string; x?: number; y?: number; caption?: string }[];
      },
      _ref
    ) => {
      lastNvlProps = props;
      return <div data-testid="mock-interactive-nvl" />;
    }
  )
}));

const graph: { nodes: GraphNode[]; edges: GraphEdge[] } = {
  nodes: [
    { id: 'exhibit:magnet-maze', label: 'Magnet Maze', kind: 'exhibit' },
    { id: 'material:acrylic', label: 'Acrylic', kind: 'material' },
    { id: 'supplier:qisi', label: 'Qisi Interactive', kind: 'supplier' },
    { id: 'theme:optics', label: 'Optics', kind: 'theme' }
  ],
  edges: [
    {
      source: 'exhibit:magnet-maze',
      target: 'material:acrylic',
      label: 'uses material',
      type: 'USES_MATERIAL'
    },
    {
      source: 'supplier:qisi',
      target: 'theme:optics',
      label: 'supports',
      type: 'SUPPORTS_THEME'
    }
  ]
};

const lowercaseRelationGraph: { nodes: GraphNode[]; edges: GraphEdge[] } = {
  nodes: [
    { id: 'exhibit:water-cycle', label: '城市水循环沙盘', kind: 'exhibit' },
    { id: 'interaction:model-demo', label: '模型演示', kind: 'interaction' },
    { id: 'material:led', label: 'LED', kind: 'material' }
  ],
  edges: [
    {
      source: 'exhibit:water-cycle',
      target: 'interaction:model-demo',
      label: 'has_interaction',
      type: 'has_interaction'
    },
    {
      source: 'exhibit:water-cycle',
      target: 'material:led',
      label: 'uses_material',
      type: 'uses_material'
    }
  ]
};

const nodeColors: Record<string, string> = {
  exhibit: '#68bdf6',
  material: '#ffd86e',
  supplier: '#de9bf9',
  theme: '#fb95af'
};

describe('NvlGraphView graph mapping', () => {
  it('passes Neo4j-style node emphasis and relationship captions to NVL', () => {
    const { nodes, rels } = buildNvlGraphData(graph, 'exhibit:magnet-maze', nodeColors);

    expect(nodes.find((node) => node.id === 'exhibit:magnet-maze')).toMatchObject({
      caption: 'Magnet Maze',
      color: '#68bdf6',
      size: 22,
      selected: true,
      activated: true,
      pinned: true,
      captionSize: 13,
      captionAlign: 'bottom',
      disabled: false
    });
    expect(nodes.find((node) => node.id === 'material:acrylic')).toMatchObject({
      disabled: false,
      size: 14,
      captionSize: 12
    });
    expect(nodes.find((node) => node.id === 'material:acrylic')?.captions?.map((caption) => caption.value)).toEqual([
      'Acrylic',
      'material'
    ]);
    expect(nodes.find((node) => node.id === 'supplier:qisi')).toMatchObject({
      disabled: true
    });
    expect(Math.max(...nodes.map((node) => Math.hypot(node.x ?? 0, node.y ?? 0)))).toBeGreaterThanOrEqual(360);
    expect(new Set(nodes.map((node) => `${Math.round(node.x ?? 0)},${Math.round(node.y ?? 0)}`)).size).toBe(nodes.length);

    const selectedRelationship = rels.find((rel) => rel.type === 'USES_MATERIAL');
    expect(selectedRelationship).toMatchObject({
      caption: '使用材料',
      color: '#f79767',
      width: 3.4,
      captionSize: 12,
      captionAlign: 'center',
      disabled: false
    });
    expect(rels.find((rel) => rel.type === 'SUPPORTS_THEME')).toMatchObject({
      caption: '支持主题',
      disabled: true,
      color: '#6f7d8f',
      width: 1,
      captionSize: 11
    });
  });

  it('uses readable Chinese relationship captions for Neo4j relationship types', () => {
    const { rels } = buildNvlGraphData(lowercaseRelationGraph, 'exhibit:water-cycle', nodeColors);

    expect(rels.map((rel) => rel.caption)).toEqual(['交互形式', '使用材料']);
  });

  it('uses stable Neo4j canvas styling options', () => {
    expect(nvlGraphStyling).toMatchObject({
      defaultNodeColor: '#a5abb6',
      defaultRelationshipColor: '#8f9bad',
      selectedBorderColor: '#f79767',
      selectedInnerBorderColor: '#ffffff',
      dropShadowColor: '#68bdf6',
      disabledItemColor: '#2b3442'
    });
  });

  it('passes explicit initial positions to the NVL wrapper', async () => {
    vi.stubGlobal('navigator', { userAgent: 'Chrome' });
    const { NvlGraphView } = await import('./NvlGraphView');

    render(
      <NvlGraphView
        graph={graph}
        selectedNodeId="exhibit:magnet-maze"
        layoutVersion={0}
        nodeColors={nodeColors}
        onNodeSelect={() => undefined}
      />
    );

    expect(lastNvlProps?.layout).toBe('d3Force');
    expect(lastNvlProps?.nvlOptions).toMatchObject({
      initialZoom: 1,
      relationshipThreshold: 10000,
      renderer: 'canvas'
    });
    expect(lastNvlProps?.positions).toHaveLength(graph.nodes.length);
    expect(new Set(lastNvlProps?.positions?.map((node) => `${node.x},${node.y}`)).size).toBe(graph.nodes.length);
  });

  it('spreads the full demo graph far enough for readable relationship lengths', () => {
    const denseGraph = {
      nodes: Array.from({ length: 42 }, (_, index) => ({
        id: `node:${index}`,
        label: `Node ${index}`,
        kind: index === 0 ? 'exhibit' : 'material'
      })),
      edges: []
    };

    const { nodes } = buildNvlGraphData(denseGraph, 'node:0', nodeColors);
    const radii = nodes.map((node) => Math.hypot(node.x ?? 0, node.y ?? 0));

    expect(Math.min(...radii)).toBeGreaterThanOrEqual(720);
    expect(Math.max(...nodes.map((node) => node.size ?? 0))).toBeLessThanOrEqual(22);
  });

  it('passes readable node and relationship labels directly to the NVL canvas renderer', async () => {
    vi.stubGlobal('navigator', { userAgent: 'Chrome' });
    const { NvlGraphView } = await import('./NvlGraphView');

    const { container } = render(
      <NvlGraphView
        graph={graph}
        selectedNodeId="exhibit:magnet-maze"
        layoutVersion={0}
        nodeColors={nodeColors}
        onNodeSelect={() => undefined}
      />
    );

    expect(lastNvlProps?.positions).toHaveLength(graph.nodes.length);
    expect(container.querySelector('.nvl-readable-overlay')).toBeNull();
    expect(lastNvlProps?.nvlOptions).toMatchObject({
      renderer: 'canvas',
      relationshipThreshold: 10000
    });
    expect(lastNvlProps?.positions?.find((node) => node.id === 'exhibit:magnet-maze')).toMatchObject({
      caption: 'Magnet Maze'
    });
    expect(lastNvlProps?.positions?.find((node) => node.id === 'material:acrylic')).toMatchObject({
      caption: 'Acrylic'
    });
    expect(buildNvlGraphData(graph, 'exhibit:magnet-maze', nodeColors).rels.map((rel) => rel.caption)).toContain('使用材料');
  });

  it('keeps unrelated dense relationships dimmed while leaving their captions on the graph data', async () => {
    vi.stubGlobal('navigator', { userAgent: 'Chrome' });
    const denseGraph = {
      nodes: [
        { id: 'exhibit:center', label: 'Center', kind: 'exhibit' },
        ...Array.from({ length: 20 }, (_, index) => ({
          id: `material:item-${index}`,
          label: `Item ${index}`,
          kind: 'material'
        }))
      ],
      edges: Array.from({ length: 20 }, (_, index) => ({
        source: index === 19 ? 'material:item-18' : 'exhibit:center',
        target: `material:item-${index}`,
        label: index === 19 ? 'unrelated' : `selected ${index}`,
        type: index === 19 ? 'UNRELATED_EDGE' : `SELECTED_EDGE_${index}`
      }))
    };
    const { NvlGraphView } = await import('./NvlGraphView');

    const { container } = render(
      <NvlGraphView
        graph={denseGraph}
        selectedNodeId="exhibit:center"
        layoutVersion={0}
        nodeColors={nodeColors}
        onNodeSelect={() => undefined}
      />
    );

    expect(container.querySelector('.nvl-readable-overlay')).toBeNull();
    expect(buildNvlGraphData(denseGraph, 'exhibit:center', nodeColors).rels.find((rel) => rel.type === 'UNRELATED_EDGE')).toMatchObject({
      caption: 'UNRELATED_EDGE',
      disabled: true
    });
  });

  it('expands the graph viewport and keeps media assets as small thumbnails', () => {
    const styles = readFileSync(resolve(process.cwd(), 'src/styles.css'), 'utf8');

    expect(styles).toContain('--graph-viewport-height: clamp(960px, 120vh, 1440px);');
    expect(styles).toContain('height: var(--graph-viewport-height);');
    expect(styles).toContain('max-height: var(--graph-viewport-height);');
    expect(styles).not.toContain('.nvl-readable-overlay');
    expect(styles).toContain('grid-template-columns: repeat(auto-fill, minmax(88px, 112px));');
    expect(styles).toContain('aspect-ratio: 1 / 1;');
    expect(styles).toContain('overflow: auto;');
  });
});
