export type GraphNodeType =
  | 'exhibit'
  | 'project'
  | 'owner'
  | 'supplier'
  | 'material'
  | 'theme'
  | 'interaction'
  | 'media_asset'
  | 'document';

export type GraphEdgeType =
  | 'belongs_to_project'
  | 'owned_by'
  | 'supplied_by'
  | 'uses_material'
  | 'has_theme'
  | 'has_interaction'
  | 'has_media'
  | 'has_document'
  | 'similar_to';

export type GraphNodeDefinition = {
  type: GraphNodeType;
  label: string;
  table: string;
  description: string;
};

export type GraphEdgeDefinition = {
  type: GraphEdgeType;
  label: string;
  source: GraphNodeType;
  target: GraphNodeType;
  table: string;
};

export type TableDefinition = {
  name: string;
  purpose: string;
  primaryKey: string;
  keyColumns: string[];
};

export type ApiDraftEndpoint = {
  method: 'GET' | 'POST' | 'PUT' | 'DELETE';
  path: string;
  purpose: string;
};

export const graphNodeTypes: GraphNodeDefinition[] = [
  {
    type: 'exhibit',
    label: '展项',
    table: 'exhibits',
    description: '展陈案例或展品的核心档案节点'
  },
  {
    type: 'project',
    label: '项目',
    table: 'projects',
    description: '展项所属建设项目或案例项目'
  },
  {
    type: 'owner',
    label: '业主',
    table: 'owners',
    description: '项目业主、场馆或委托单位'
  },
  {
    type: 'supplier',
    label: '供应商',
    table: 'suppliers',
    description: '展项设计、制作、设备或内容供应单位'
  },
  {
    type: 'material',
    label: '材料',
    table: 'materials',
    description: '金属、木作、亚克力、钢结构等材料实体'
  },
  {
    type: 'theme',
    label: '主题',
    table: 'themes',
    description: '力学、天文、水资源等展项主题'
  },
  {
    type: 'interaction',
    label: '交互方式',
    table: 'interactions',
    description: '机械互动、沉浸影像、按钮互动等体验形式'
  },
  {
    type: 'media_asset',
    label: '媒体资产',
    table: 'media_assets',
    description: '图片、视频、设计图等可预览资产'
  },
  {
    type: 'document',
    label: '文档资料',
    table: 'documents',
    description: '报价单、说明文档、Excel 资料等文件节点'
  }
];

export const graphEdgeTypes: GraphEdgeDefinition[] = [
  {
    type: 'belongs_to_project',
    label: '所属项目',
    source: 'exhibit',
    target: 'project',
    table: 'exhibits'
  },
  {
    type: 'owned_by',
    label: '业主',
    source: 'exhibit',
    target: 'owner',
    table: 'projects'
  },
  {
    type: 'supplied_by',
    label: '供应商',
    source: 'exhibit',
    target: 'supplier',
    table: 'exhibits'
  },
  {
    type: 'uses_material',
    label: '使用材料',
    source: 'exhibit',
    target: 'material',
    table: 'exhibit_materials'
  },
  {
    type: 'has_theme',
    label: '主题',
    source: 'exhibit',
    target: 'theme',
    table: 'exhibits'
  },
  {
    type: 'has_interaction',
    label: '交互方式',
    source: 'exhibit',
    target: 'interaction',
    table: 'exhibit_interactions'
  },
  {
    type: 'has_media',
    label: '媒体资产',
    source: 'exhibit',
    target: 'media_asset',
    table: 'media_assets'
  },
  {
    type: 'has_document',
    label: '文档资料',
    source: 'exhibit',
    target: 'document',
    table: 'exhibit_documents'
  },
  {
    type: 'similar_to',
    label: '相似展项',
    source: 'exhibit',
    target: 'exhibit',
    table: 'exhibit_relations'
  }
];

export const tableDefinitions: TableDefinition[] = [
  {
    name: 'exhibits',
    purpose: '保存展项核心档案字段，并连接项目、供应商和主题',
    primaryKey: 'id',
    keyColumns: ['id', 'name', 'project_id', 'supplier_id', 'theme_id', 'budget_min', 'budget_max', 'status']
  },
  {
    name: 'projects',
    purpose: '保存项目、业主、年份和场馆类型信息',
    primaryKey: 'id',
    keyColumns: ['id', 'name', 'owner_id', 'venue_type', 'project_year']
  },
  {
    name: 'owners',
    purpose: '保存业主或场馆单位',
    primaryKey: 'id',
    keyColumns: ['id', 'name']
  },
  {
    name: 'suppliers',
    purpose: '保存供应商单位',
    primaryKey: 'id',
    keyColumns: ['id', 'name', 'contact_note']
  },
  {
    name: 'materials',
    purpose: '保存材料字典',
    primaryKey: 'id',
    keyColumns: ['id', 'name']
  },
  {
    name: 'themes',
    purpose: '保存主题和学科领域字典',
    primaryKey: 'id',
    keyColumns: ['id', 'name', 'category']
  },
  {
    name: 'interactions',
    purpose: '保存交互方式字典',
    primaryKey: 'id',
    keyColumns: ['id', 'name']
  },
  {
    name: 'media_assets',
    purpose: '保存图片、视频、设计图等媒体资产元数据',
    primaryKey: 'id',
    keyColumns: ['id', 'exhibit_id', 'type', 'name', 'object_key']
  },
  {
    name: 'documents',
    purpose: '保存报价文件、说明文档、Excel 等资料元数据',
    primaryKey: 'id',
    keyColumns: ['id', 'name', 'file_type', 'object_key', 'source_note']
  },
  {
    name: 'exhibit_materials',
    purpose: '保存展项和材料的多对多关系',
    primaryKey: 'exhibit_id, material_id',
    keyColumns: ['exhibit_id', 'material_id']
  },
  {
    name: 'exhibit_interactions',
    purpose: '保存展项和交互方式的多对多关系',
    primaryKey: 'exhibit_id, interaction_id',
    keyColumns: ['exhibit_id', 'interaction_id']
  },
  {
    name: 'exhibit_relations',
    purpose: '保存相似展项和后续扩展的展项间关系',
    primaryKey: 'id',
    keyColumns: ['id', 'source_exhibit_id', 'target_exhibit_id', 'relation_type', 'weight']
  },
  {
    name: 'exhibit_documents',
    purpose: '保存展项和文档资料的多对多关系',
    primaryKey: 'exhibit_id, document_id',
    keyColumns: ['exhibit_id', 'document_id']
  }
];

export const apiDraft: ApiDraftEndpoint[] = [
  {
    method: 'GET',
    path: '/api/exhibits',
    purpose: '分页查询展项，支持关键词、场馆、主题、预算、材料、交互方式和状态过滤'
  },
  {
    method: 'POST',
    path: '/api/exhibits',
    purpose: '新增展项，并同步创建材料、交互方式、文档等图谱关系'
  },
  {
    method: 'GET',
    path: '/api/exhibits/{id}',
    purpose: '获取展项详情、媒体资产和文档资料'
  },
  {
    method: 'PUT',
    path: '/api/exhibits/{id}',
    purpose: '更新展项档案，并同步更新相关图谱关系'
  },
  {
    method: 'DELETE',
    path: '/api/exhibits/{id}',
    purpose: '删除或归档展项，MVP 阶段优先做软删除'
  },
  {
    method: 'GET',
    path: '/api/exhibits/{id}/graph',
    purpose: '返回以展项为中心的 nodes 和 edges，用于前端图谱展示'
  }
];

export function validateGraphContract() {
  const requiredNodeTypes = new Set<GraphNodeType>([
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
  const requiredEdgeTypes = new Set<GraphEdgeType>([
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

  const nodeTypes = new Set(graphNodeTypes.map((node) => node.type));
  const edgeTypes = new Set(graphEdgeTypes.map((edge) => edge.type));
  const tableNames = new Set(tableDefinitions.map((table) => table.name));
  const endpointKeys = new Set(apiDraft.map((endpoint) => `${endpoint.method} ${endpoint.path}`));

  const valid =
    [...requiredNodeTypes].every((type) => nodeTypes.has(type)) &&
    [...requiredEdgeTypes].every((type) => edgeTypes.has(type)) &&
    graphEdgeTypes.every((edge) => tableNames.has(edge.table)) &&
    endpointKeys.has('GET /api/exhibits/{id}/graph');

  return {
    nodeTypes: graphNodeTypes.length,
    edgeTypes: graphEdgeTypes.length,
    tables: tableDefinitions.length,
    endpoints: apiDraft.length,
    valid
  };
}
