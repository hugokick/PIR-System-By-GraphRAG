# 领域模型与轻量知识图谱设计

> 阶段：阶段 1  
> 目标：把展项档案和知识图谱关系建模清楚，为后端、PostgreSQL、图谱查询 API 和后续 RAG 检索提供稳定契约。

## 1. 设计原则

MVP 阶段不直接引入 Neo4j。系统先使用 PostgreSQL 的实体表、关系表和查询 API 表达轻量知识图谱。

这样可以同时满足三件事：

- 业务人员能稳定录入和维护展项档案
- 后端能根据关系表生成图谱 nodes 和 edges
- 后续可在同一数据模型上接入 pgvector、RAG 和更复杂的图数据库

## 2. 核心实体

| 实体 | 类型 | 数据表 | 说明 |
| --- | --- | --- | --- |
| 展项 | `exhibit` | `exhibits` | 展陈案例或展品的核心档案节点 |
| 项目 | `project` | `projects` | 展项所属建设项目或案例项目 |
| 业主 | `owner` | `owners` | 项目业主、场馆或委托单位 |
| 供应商 | `supplier` | `suppliers` | 展项设计、制作、设备或内容供应单位 |
| 材料 | `material` | `materials` | 金属、木作、亚克力、钢结构等材料实体 |
| 主题 | `theme` | `themes` | 力学、天文、水资源等展项主题 |
| 交互方式 | `interaction` | `interactions` | 机械互动、沉浸影像、按钮互动等体验形式 |
| 媒体资产 | `media_asset` | `media_assets` | 图片、视频、设计图等可预览资产 |
| 文档资料 | `document` | `documents` | 报价单、说明文档、Excel 资料等文件节点 |

## 3. 核心关系

| 关系 | 类型 | 起点 | 终点 | 持久化位置 |
| --- | --- | --- | --- | --- |
| 所属项目 | `belongs_to_project` | 展项 | 项目 | `exhibits.project_id` |
| 业主 | `owned_by` | 展项 | 业主 | `projects.owner_id` |
| 供应商 | `supplied_by` | 展项 | 供应商 | `exhibits.supplier_id` |
| 使用材料 | `uses_material` | 展项 | 材料 | `exhibit_materials` |
| 主题 | `has_theme` | 展项 | 主题 | `exhibits.theme_id` |
| 交互方式 | `has_interaction` | 展项 | 交互方式 | `exhibit_interactions` |
| 媒体资产 | `has_media` | 展项 | 媒体资产 | `media_assets.exhibit_id` |
| 文档资料 | `has_document` | 展项 | 文档资料 | `exhibit_documents` |
| 相似展项 | `similar_to` | 展项 | 展项 | `exhibit_relations` |

## 4. 建议数据库表

### `exhibits`

保存展项核心档案字段，并连接项目、供应商和主题。

关键字段：

- `id`
- `name`
- `category`
- `theme_id`
- `project_id`
- `supplier_id`
- `budget_min`
- `budget_max`
- `dimensions`
- `status`
- `description`
- `tags`
- `created_at`
- `updated_at`

### `projects`

保存项目、业主、年份和场馆类型信息。

关键字段：

- `id`
- `name`
- `owner_id`
- `venue_type`
- `project_year`
- `location`
- `created_at`
- `updated_at`

### 字典和主体表

- `owners`
- `suppliers`
- `materials`
- `themes`
- `interactions`

这些表优先保留 `id`、`name`、`description`、`created_at`、`updated_at`，后续按业务需要扩展。

### 文件与媒体表

- `media_assets`：图片、视频、设计图等可预览资产
- `documents`：报价、说明文档、Excel、PDF 等资料文件
- `exhibit_documents`：展项和文档的多对多关系

### 多对多关系表

- `exhibit_materials`
- `exhibit_interactions`
- `exhibit_relations`

`exhibit_relations` 预留关系类型和权重：

- `relation_type`
- `weight`
- `note`

MVP 阶段主要使用 `similar_to`。

## 5. 图谱 API 草案

### 展项列表

```http
GET /api/exhibits
```

支持过滤条件：

- `keyword`
- `venue_type`
- `category`
- `theme`
- `budget_min`
- `budget_max`
- `material`
- `interaction`
- `status`

### 新增展项

```http
POST /api/exhibits
```

新增展项时，后端负责同步生成或关联：

- 项目
- 业主
- 供应商
- 主题
- 材料
- 交互方式
- 文档资料
- 相似展项关系

### 展项详情

```http
GET /api/exhibits/{id}
```

返回展项核心字段、媒体资产、文档资料和关系摘要。

### 更新展项

```http
PUT /api/exhibits/{id}
```

更新展项时，后端负责同步更新关系表。材料、交互方式和文档关系建议采用“替换当前集合”的方式，减少关系漂移。

### 删除展项

```http
DELETE /api/exhibits/{id}
```

MVP 阶段建议优先做软删除或归档，避免误删历史项目资料。

### 展项图谱

```http
GET /api/exhibits/{id}/graph
```

返回结构：

```json
{
  "nodes": [
    { "id": "exhibit:1", "label": "杠杆乐园", "type": "exhibit" },
    { "id": "material:metal", "label": "金属", "type": "material" }
  ],
  "edges": [
    { "source": "exhibit:1", "target": "material:metal", "label": "使用材料", "type": "uses_material" }
  ]
}
```

## 6. 阶段 1 验收

阶段 1 完成后，应满足：

- 能明确列出 MVP 图谱实体
- 能明确列出展项中心关系
- 能明确映射实体和关系到 PostgreSQL 表
- 能明确后端图谱 API 的输入和输出
- 代码中有可测试的图谱契约，防止后续实现偏离计划

代码契约位置：

```text
src/domain/graphSchema.ts
src/domain/graphSchema.test.ts
```
