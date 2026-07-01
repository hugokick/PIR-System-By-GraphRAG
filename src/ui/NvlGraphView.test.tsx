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
  positions?: { id: string; x?: number; y?: number }[];
  mouseEventCallbacks?: {
    onNodeClick?: (node: { id: string }) => void;
    onNodeDoubleClick?: (node: { id: string }) => void;
    onCanvasClick?: () => void;
  };
} | null = null;
let lastNvlApi = createMockNvlApi();

function createMockNvlApi() {
  return {
    fit: vi.fn(),
    restart: vi.fn(),
    setLayout: vi.fn(),
    getContainer: vi.fn(() => ({
      getBoundingClientRect: () => ({ width: 1000, height: 560 })
    })),
    getNodePositions: vi.fn(() => []),
    getPan: vi.fn(() => ({ x: 0, y: 0 })),
    getScale: vi.fn(() => 1)
  };
}

vi.mock('@neo4j-nvl/react', () => ({
  InteractiveNvlWrapper: React.forwardRef(
    (
      props: {
        layout?: string;
        layoutOptions?: Record<string, unknown>;
        nvlOptions?: Record<string, unknown>;
        positions?: { id: string; x?: number; y?: number }[];
        mouseEventCallbacks?: {
          onNodeClick?: (node: { id: string }) => void;
          onNodeDoubleClick?: (node: { id: string }) => void;
          onCanvasClick?: () => void;
        };
      },
      ref
    ) => {
      lastNvlProps = props;
      React.useImperativeHandle(ref, () => lastNvlApi);
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
    const { nodes, rels } = buildNvlGraphData(graph, ['exhibit:magnet-maze'], 1, nodeColors);

    expect(nodes.find((node) => node.id === 'exhibit:magnet-maze')).toMatchObject({
      caption: 'Magnet Maze',
      color: '#68bdf6',
      size: 30,
      selected: true,
      activated: true,
      pinned: true,
      captionSize: 11,
      captionAlign: 'bottom',
      disabled: false
    });
    expect(nodes.find((node) => node.id === 'material:acrylic')).toMatchObject({
      disabled: false,
      size: 18,
      captionSize: 10
    });
    expect(nodes.find((node) => node.id === 'material:acrylic')?.captions?.map((caption) => caption.value)).toEqual([
      'Acrylic',
      'material'
    ]);
    expect(nodes.find((node) => node.id === 'supplier:qisi')).toMatchObject({
      disabled: true
    });
    expect(Math.max(...nodes.map((node) => Math.hypot(node.x ?? 0, node.y ?? 0)))).toBeGreaterThanOrEqual(190);
    expect(new Set(nodes.map((node) => `${Math.round(node.x ?? 0)},${Math.round(node.y ?? 0)}`)).size).toBe(nodes.length);

    const selectedRelationship = rels.find((rel) => rel.type === 'USES_MATERIAL');
    expect(selectedRelationship).toMatchObject({
      caption: '使用材料',
      color: '#f79767',
      width: 3.4,
      captionSize: 9,
      captionAlign: 'center',
      disabled: false
    });
    expect(rels.find((rel) => rel.type === 'SUPPORTS_THEME')).toMatchObject({
      caption: '支持主题',
      disabled: true,
      color: '#7d8798',
      width: 1.4,
      captionSize: 8
    });
  });

  it('uses readable Chinese relationship captions for Neo4j relationship types', () => {
    const { rels } = buildNvlGraphData(lowercaseRelationGraph, ['exhibit:water-cycle'], 1, nodeColors);

    expect(rels.map((rel) => rel.caption)).toEqual(['交互方式', '使用材料']);
  });

  it('uses stable Neo4j canvas styling options', () => {
    expect(nvlGraphStyling).toMatchObject({
      defaultNodeColor: '#a5abb6',
      defaultRelationshipColor: '#8f9bad',
      selectedBorderColor: '#f79767',
      selectedInnerBorderColor: '#ffffff',
      dropShadowColor: '#68bdf6',
      disabledItemColor: '#536274',
      disabledItemFontColor: '#c4ccd7'
    });
  });

  it('passes explicit initial positions to the NVL wrapper', async () => {
    vi.stubGlobal('navigator', { userAgent: 'Chrome' });
    const { NvlGraphView } = await import('./NvlGraphView');

    render(
      <NvlGraphView
        graph={graph}
        selectedNodeIds={['exhibit:magnet-maze']}
        highlightDepth={1}
        layoutVersion={0}
        nodeColors={nodeColors}
        onNodeToggle={() => undefined}
      />
    );

    expect(lastNvlProps?.layout).toBe('d3Force');
    expect(lastNvlProps?.nvlOptions).toMatchObject({
      initialZoom: 1,
      relationshipThreshold: 1000,
      renderer: 'canvas'
    });
    expect(lastNvlProps?.positions).toHaveLength(graph.nodes.length);
    expect(new Set(lastNvlProps?.positions?.map((node) => `${node.x},${node.y}`)).size).toBe(graph.nodes.length);
  });

  it('does not restart or refit the graph when only the selected node changes', async () => {
    vi.stubGlobal('navigator', { userAgent: 'Chrome' });
    lastNvlApi = createMockNvlApi();
    const { NvlGraphView } = await import('./NvlGraphView');

    const { rerender } = render(
      <NvlGraphView
        graph={graph}
        selectedNodeIds={['exhibit:magnet-maze']}
        highlightDepth={1}
        layoutVersion={0}
        nodeColors={nodeColors}
        onNodeToggle={() => undefined}
      />
    );
    await new Promise((resolve) => window.setTimeout(resolve, 160));
    const restartCount = lastNvlApi.restart.mock.calls.length;
    const fitCount = lastNvlApi.fit.mock.calls.length;

    rerender(
      <NvlGraphView
        graph={graph}
        selectedNodeIds={['material:acrylic']}
        highlightDepth={1}
        layoutVersion={0}
        nodeColors={nodeColors}
        onNodeToggle={() => undefined}
      />
    );
    await new Promise((resolve) => window.setTimeout(resolve, 160));

    expect(lastNvlApi.restart).toHaveBeenCalledTimes(restartCount);
    expect(lastNvlApi.fit).toHaveBeenCalledTimes(fitCount);
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

    const { nodes } = buildNvlGraphData(denseGraph, ['node:0'], 1, nodeColors);
    const radii = nodes.map((node) => Math.hypot(node.x ?? 0, node.y ?? 0));

    expect(Math.min(...radii)).toBeGreaterThanOrEqual(400);
    expect(Math.max(...nodes.map((node) => node.size ?? 0))).toBeLessThanOrEqual(30);
  });

  it('renders readable node and relationship labels inside the graph viewport', async () => {
    vi.stubGlobal('navigator', { userAgent: 'Chrome' });
    const { NvlGraphView } = await import('./NvlGraphView');

    const { container } = render(
      <NvlGraphView
        graph={graph}
        selectedNodeIds={['exhibit:magnet-maze']}
        highlightDepth={1}
        layoutVersion={0}
        nodeColors={nodeColors}
        onNodeToggle={() => undefined}
      />
    );

    expect(lastNvlProps?.positions).toHaveLength(graph.nodes.length);
    expect(container.querySelector('.nvl-readable-overlay')).toBeTruthy();
    expect([...container.querySelectorAll('.nvl-node-caption')].map((node) => node.textContent)).toContain('Magnet Maze');
    expect([...container.querySelectorAll('.nvl-node-caption')].map((node) => node.textContent)).toContain('Acrylic');
    expect([...container.querySelectorAll('.nvl-edge-caption')].map((node) => node.textContent)).toContain('使用材料');
  });

  it('hides unrelated relationship labels when the graph is dense', async () => {
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
        selectedNodeIds={['exhibit:center']}
        highlightDepth={1}
        layoutVersion={0}
        nodeColors={nodeColors}
        onNodeToggle={() => undefined}
      />
    );

    expect(container.querySelector('.nvl-readable-overlay')).toBeTruthy();
    const visibleEdgeLabels = [...container.querySelectorAll('.nvl-edge-caption')].map((node) => node.textContent);
    expect(visibleEdgeLabels.length).toBeGreaterThan(0);
    expect(visibleEdgeLabels).not.toContain('unrelated');
    expect(buildNvlGraphData(denseGraph, ['exhibit:center'], 1, nodeColors).rels.find((rel) => rel.type === 'UNRELATED_EDGE')).toMatchObject({
      disabled: true
    });
  });

  it('supports accumulated selected nodes without making unrelated graph objects too faint', () => {
    const { nodes, rels } = buildNvlGraphData(graph, ['exhibit:magnet-maze', 'supplier:qisi'], 1, nodeColors);

    expect(nodes.find((node) => node.id === 'exhibit:magnet-maze')).toMatchObject({
      selected: true,
      disabled: false
    });
    expect(nodes.find((node) => node.id === 'supplier:qisi')).toMatchObject({
      selected: true,
      disabled: false
    });
    expect(nodes.find((node) => node.id === 'material:acrylic')).toMatchObject({
      disabled: false
    });
    expect(nodes.find((node) => node.id === 'theme:optics')).toMatchObject({
      disabled: false
    });
    expect(rels.find((rel) => rel.type === 'USES_MATERIAL')).toMatchObject({
      disabled: false,
      width: 3.4
    });
    expect(rels.find((rel) => rel.type === 'SUPPORTS_THEME')).toMatchObject({
      disabled: false,
      width: 3.4
    });
  });

  it('can expand highlighted nodes and relationships to two hops', () => {
    const chainGraph = {
      nodes: [
        { id: 'a', label: 'A', kind: 'exhibit' },
        { id: 'b', label: 'B', kind: 'material' },
        { id: 'c', label: 'C', kind: 'supplier' }
      ],
      edges: [
        { source: 'a', target: 'b', label: 'a-b', type: 'FIRST_HOP' },
        { source: 'b', target: 'c', label: 'b-c', type: 'SECOND_HOP' }
      ]
    };

    expect(buildNvlGraphData(chainGraph, ['a'], 1, nodeColors).nodes.find((node) => node.id === 'c')).toMatchObject({
      disabled: true
    });
    expect(buildNvlGraphData(chainGraph, ['a'], 1, nodeColors).rels.find((rel) => rel.type === 'SECOND_HOP')).toMatchObject({
      disabled: true
    });

    const twoHop = buildNvlGraphData(chainGraph, ['a'], 2, nodeColors);
    expect(twoHop.nodes.find((node) => node.id === 'c')).toMatchObject({
      disabled: false
    });
    expect(twoHop.rels.find((rel) => rel.type === 'SECOND_HOP')).toMatchObject({
      disabled: false,
      width: 3.4
    });
  });

  it('only reports selection changes on graph clicks and does not reset the layout', async () => {
    vi.stubGlobal('navigator', { userAgent: 'Chrome' });
    lastNvlApi = createMockNvlApi();
    const onNodeToggle = vi.fn();
    const { NvlGraphView } = await import('./NvlGraphView');

    render(
      <NvlGraphView
        graph={graph}
        selectedNodeIds={['exhibit:magnet-maze']}
        highlightDepth={1}
        layoutVersion={0}
        nodeColors={nodeColors}
        onNodeToggle={onNodeToggle}
      />
    );
    await new Promise((resolve) => window.setTimeout(resolve, 160));
    lastNvlApi.restart.mockClear();
    lastNvlApi.fit.mockClear();

    lastNvlProps?.mouseEventCallbacks?.onNodeClick?.({ id: 'material:acrylic' });
    lastNvlProps?.mouseEventCallbacks?.onNodeDoubleClick?.({ id: 'supplier:qisi' });
    lastNvlProps?.mouseEventCallbacks?.onCanvasClick?.();

    expect(onNodeToggle).toHaveBeenCalledWith('material:acrylic');
    expect(onNodeToggle).toHaveBeenCalledWith('supplier:qisi');
    expect(onNodeToggle).toHaveBeenCalledWith(null);
    expect(lastNvlApi.restart).not.toHaveBeenCalled();
    expect(lastNvlApi.fit).not.toHaveBeenCalled();
  });

  it('expands the graph viewport enough to read labels in the canvas', () => {
    const styles = readFileSync(resolve(process.cwd(), 'src/styles.css'), 'utf8');

    expect(styles).toContain('--graph-viewport-height: clamp(520px, 68vh, 720px);');
    expect(styles).toContain('height: var(--graph-viewport-height);');
    expect(styles).toContain('max-height: var(--graph-viewport-height);');
    expect(styles).toMatch(/\.nvl-readable-overlay\s*\{[^}]*overflow: hidden;/);
    expect(styles).toContain('overflow: auto;');
  });
});
