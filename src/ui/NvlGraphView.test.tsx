import { describe, expect, it } from 'vitest';
import type { GraphEdge, GraphNode } from '../types';
import { buildNvlGraphData, nvlGraphStyling } from './nvlGraphData';

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
  exhibit: '#0f8b78',
  material: '#6b7a30',
  supplier: '#7a4f9f',
  theme: '#8b4d2f'
};

describe('NvlGraphView graph mapping', () => {
  it('passes Neo4j-style node emphasis and relationship captions to NVL', () => {
    const { nodes, rels } = buildNvlGraphData(graph, 'exhibit:magnet-maze', nodeColors);

    expect(nodes.find((node) => node.id === 'exhibit:magnet-maze')).toMatchObject({
      caption: 'Magnet Maze',
      color: '#0f8b78',
      size: 54,
      selected: true,
      activated: true,
      captionSize: 13,
      disabled: false
    });
    expect(nodes.find((node) => node.id === 'material:acrylic')).toMatchObject({
      disabled: false,
      size: 34
    });
    expect(nodes.find((node) => node.id === 'supplier:qisi')).toMatchObject({
      disabled: true
    });

    const selectedRelationship = rels.find((rel) => rel.type === 'USES_MATERIAL');
    expect(selectedRelationship).toMatchObject({
      caption: 'USES_MATERIAL',
      color: '#243f80',
      width: 4,
      captionSize: 6,
      disabled: false
    });
    expect(rels.find((rel) => rel.type === 'SUPPORTS_THEME')).toMatchObject({
      disabled: true,
      width: 1.5
    });
  });

  it('uses stable Neo4j canvas styling options', () => {
    expect(nvlGraphStyling).toMatchObject({
      selectedBorderColor: '#4f88ff',
      selectedInnerBorderColor: '#ffffff',
      dropShadowColor: '#1f4e79',
      disabledItemColor: '#c8d2cf'
    });
  });
});
