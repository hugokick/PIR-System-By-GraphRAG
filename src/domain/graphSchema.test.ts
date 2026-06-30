import { describe, expect, it } from 'vitest';
import {
  apiDraft,
  graphEdgeTypes,
  graphNodeTypes,
  tableDefinitions,
  validateGraphContract
} from './graphSchema';

describe('graph schema contract', () => {
  it('covers the MVP graph entities from the development plan', () => {
    expect(graphNodeTypes.map((node) => node.type)).toEqual([
      'exhibit',
      'project',
      'owner',
      'supplier',
      'material',
      'theme',
      'interaction',
      'media_asset',
      'document'
    ]);
  });

  it('models the required exhibit-centered graph relations', () => {
    expect(graphEdgeTypes.map((edge) => edge.type)).toEqual([
      'belongs_to_project',
      'owned_by',
      'supplied_by',
      'uses_material',
      'has_theme',
      'has_interaction',
      'has_media',
      'has_document',
      'similar_to'
    ]);
  });

  it('defines relational tables needed to persist graph nodes and edges', () => {
    expect(tableDefinitions.map((table) => table.name)).toEqual([
      'exhibits',
      'projects',
      'owners',
      'suppliers',
      'materials',
      'themes',
      'interactions',
      'media_assets',
      'documents',
      'exhibit_materials',
      'exhibit_interactions',
      'exhibit_relations',
      'exhibit_documents'
    ]);
  });

  it('declares the backend API draft for CRUD, filtering, and graph querying', () => {
    expect(apiDraft.map((endpoint) => `${endpoint.method} ${endpoint.path}`)).toEqual([
      'GET /api/exhibits',
      'POST /api/exhibits',
      'GET /api/exhibits/{id}',
      'PUT /api/exhibits/{id}',
      'DELETE /api/exhibits/{id}',
      'GET /api/exhibits/{id}/graph'
    ]);
  });

  it('passes a contract validation check for stage 1 acceptance', () => {
    expect(validateGraphContract()).toEqual({
      nodeTypes: 9,
      edgeTypes: 9,
      tables: 13,
      endpoints: 6,
      valid: true
    });
  });
});
