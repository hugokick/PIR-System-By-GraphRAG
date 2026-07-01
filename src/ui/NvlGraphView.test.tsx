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
} | null = null;

vi.mock('@neo4j-nvl/react', () => ({
  InteractiveNvlWrapper: React.forwardRef(
    (
      props: {
        layout?: string;
        layoutOptions?: Record<string, unknown>;
        nvlOptions?: Record<string, unknown>;
        positions?: { id: string; x?: number; y?: number }[];
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
      size: 40,
      selected: true,
      activated: true,
      pinned: true,
      captionSize: 13,
      captionAlign: 'bottom',
      disabled: false
    });
    expect(nodes.find((node) => node.id === 'material:acrylic')).toMatchObject({
      disabled: false,
      size: 24,
      captionSize: 12
    });
    expect(nodes.find((node) => node.id === 'material:acrylic')?.captions?.map((caption) => caption.value)).toEqual([
      'Acrylic',
      'material'
    ]);
    expect(nodes.find((node) => node.id === 'supplier:qisi')).toMatchObject({
      disabled: true
    });
    expect(Math.max(...nodes.map((node) => Math.hypot(node.x ?? 0, node.y ?? 0)))).toBeGreaterThanOrEqual(150);
    expect(new Set(nodes.map((node) => `${Math.round(node.x ?? 0)},${Math.round(node.y ?? 0)}`)).size).toBe(nodes.length);

    const selectedRelationship = rels.find((rel) => rel.type === 'USES_MATERIAL');
    expect(selectedRelationship).toMatchObject({
      caption: 'USES_MATERIAL',
      color: '#f79767',
      width: 3.4,
      captionSize: 8.5,
      captionAlign: 'center',
      disabled: false
    });
    expect(rels.find((rel) => rel.type === 'SUPPORTS_THEME')).toMatchObject({
      disabled: true,
      color: '#6f7d8f',
      width: 1,
      captionSize: 7
    });
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
      relationshipThreshold: 1000,
      renderer: 'canvas'
    });
    expect(lastNvlProps?.positions).toHaveLength(graph.nodes.length);
    expect(new Set(lastNvlProps?.positions?.map((node) => `${node.x},${node.y}`)).size).toBe(graph.nodes.length);
  });

  it('renders readable node and relationship labels above the canvas', async () => {
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

    expect([...container.querySelectorAll('.nvl-node-caption')].map((node) => node.textContent)).toContain('Magnet Maze');
    expect([...container.querySelectorAll('.nvl-node-caption')].map((node) => node.textContent)).toContain('Acrylic');
    expect([...container.querySelectorAll('.nvl-edge-caption')].map((edge) => edge.textContent)).toContain('USES_MATERIAL');
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
        selectedNodeId="exhibit:center"
        layoutVersion={0}
        nodeColors={nodeColors}
        onNodeSelect={() => undefined}
      />
    );

    const edgeLabels = [...container.querySelectorAll('.nvl-edge-caption')].map((edge) => edge.textContent);
    expect(edgeLabels).toContain('SELECTED_EDGE_0');
    expect(edgeLabels).not.toContain('UNRELATED_EDGE');
  });

  it('keeps the graph viewport compact instead of reserving a tall empty area', () => {
    const styles = readFileSync(resolve(process.cwd(), 'src/styles.css'), 'utf8');

    expect(styles).toContain('--graph-viewport-height: clamp(320px, 42vh, 420px);');
    expect(styles).toContain('height: var(--graph-viewport-height);');
    expect(styles).not.toContain('min-height: 480px;');
  });
});
