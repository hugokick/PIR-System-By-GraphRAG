import { render } from '@testing-library/react';
import React from 'react';
import { describe, expect, it, vi } from 'vitest';
import type { GraphEdge, GraphNode } from '../types';
import { buildNvlGraphData, nvlGraphStyling } from './nvlGraphData';

let lastNvlProps: { layout?: string; positions?: { id: string; x?: number; y?: number }[] } | null = null;

vi.mock('@neo4j-nvl/react', () => ({
  InteractiveNvlWrapper: React.forwardRef(
    (props: { layout?: string; positions?: { id: string; x?: number; y?: number }[] }, _ref) => {
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
      size: 58,
      selected: true,
      activated: true,
      captionSize: 14,
      disabled: false
    });
    expect(nodes.find((node) => node.id === 'material:acrylic')).toMatchObject({
      disabled: false,
      size: 34
    });
    expect(nodes.find((node) => node.id === 'supplier:qisi')).toMatchObject({
      disabled: true
    });
    expect(new Set(nodes.map((node) => `${Math.round(node.x ?? 0)},${Math.round(node.y ?? 0)}`)).size).toBe(nodes.length);

    const selectedRelationship = rels.find((rel) => rel.type === 'USES_MATERIAL');
    expect(selectedRelationship).toMatchObject({
      caption: 'USES_MATERIAL',
      color: '#f79767',
      width: 4.5,
      captionSize: 5.5,
      disabled: false
    });
    expect(rels.find((rel) => rel.type === 'SUPPORTS_THEME')).toMatchObject({
      disabled: true,
      color: '#6f7d8f',
      width: 1.2
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
    expect(lastNvlProps?.positions).toHaveLength(graph.nodes.length);
    expect(new Set(lastNvlProps?.positions?.map((node) => `${node.x},${node.y}`)).size).toBe(graph.nodes.length);
  });
});
