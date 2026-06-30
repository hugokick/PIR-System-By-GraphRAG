# Neo4j Demo Graph Integration

## 目标

本支线用于提供一套独立的 Neo4j 演示图谱能力，给前端知识图谱窗口提供真实 Neo4j 查询结果作为项目演示佐证。当前实现保持严格隔离，不修改主线 CRUD，不替换现有图谱逻辑，不接 GraphRAG 路由，也不做 PostgreSQL 与 Neo4j 的实时双写。

## 当前产物

- `backend/app/neo4j_demo/seed.py`
  - `build_demo_seed_statements()`: 生成 Neo4j Cypher 语句列表
  - `build_demo_seed_script()`: 生成可直接粘贴到 Neo4j Browser 的完整脚本
- `backend/app/neo4j_demo/query.py`
  - `build_exhibit_graph_cypher()`: 构建按 `exhibit_id` 查询中心子图的一跳 Cypher
  - `map_neo4j_records_to_graph_response()`: 将 Neo4j 记录映射为与现有 `GraphResponse` 兼容的 `nodes/edges`
- `backend/app/neo4j_demo/service.py`
  - `Neo4jBoltGraphClient`: 薄适配层，封装 `session().run()`
  - `Neo4jDemoGraphService`: 优先调用 Neo4j，失败或无数据时回退到当前 Python 图谱

## 如何启动 Neo4j

推荐使用 Docker 本地快速启动：

```bash
docker run --name neo4j-demo ^
  -p 7474:7474 -p 7687:7687 ^
  -e NEO4J_AUTH=neo4j/demo-graph123 ^
  neo4j:5
```

启动后可通过以下地址访问：

- Neo4j Browser: `http://localhost:7474`
- Bolt: `bolt://localhost:7687`

## 如何导入演示数据

当前不直接附带主线导入任务，也不与 PostgreSQL 做同步。演示数据来源于当前后端的 `seed_exhibits`。

在项目根目录执行下面的 Python 命令，可打印完整的 Neo4j seed script：

```bash
python -c "from app.neo4j_demo.seed import build_demo_seed_script; from app.repository import seed_exhibits; print(build_demo_seed_script(seed_exhibits))"
```

将输出结果复制到 Neo4j Browser 中执行即可完成导入。

导入后的演示图谱覆盖这些实体与关系：

- 实体：`Exhibit`、`Project`、`Owner`、`Supplier`、`Material`、`Theme`、`Interaction`、`Document`
- 关系：`BELONGS_TO_PROJECT`、`OWNED_BY`、`SUPPLIED_BY`、`USES_MATERIAL`、`HAS_THEME`、`HAS_INTERACTION`、`HAS_DOCUMENT`、`SIMILAR_TO`

## 如何接入现有 `/api/exhibits/{id}/graph`

当前分支不直接修改现有路由，但已经准备好了可复用的独立服务层。主线如果后续要接入，可以保留当前 `/api/exhibits/{id}/graph` 的入口不变，只在服务层增加可选切换：

1. 根据配置或环境变量决定是否启用 Neo4j 演示查询
2. 启用时实例化 `Neo4jBoltGraphClient` 与 `Neo4jDemoGraphService`
3. 调用 `Neo4jDemoGraphService.get_exhibit_graph(exhibit_id)`
4. 如果 Neo4j 不可用、查询失败或无结果，自动回退到当前 Python/PostgreSQL 图谱

这样可以做到：

- 前端接口不变
- 主线图谱逻辑不被替换
- 演示环境可优先展示真实 Neo4j 查询结果

## Fallback 设计

当前策略是：

- 优先 Neo4j
- Neo4j 不可用时回退到当前 Python/PostgreSQL 图谱

回退触发条件包括：

- Neo4j client 未配置
- Neo4j 查询抛出异常
- Neo4j 返回空结果
- Neo4j 返回记录但映射后没有节点

回退目标是当前已有的 `build_exhibit_graph()`，因此最终返回仍然是现有前端可消费的 `GraphResponse` 结构。

## 当前为什么不做双写同步

当前 Neo4j 的定位是“演示图谱”，不是主库或生产查询链路，因此不做 PostgreSQL 与 Neo4j 双写，原因有三点：

- 主线数据仍以当前主存储为准，避免引入一致性风险
- 主线 CRUD 仍在演进，过早双写会把主线变更复杂度放大
- 演示目标只需要证明“同一领域模型可以投影到 Neo4j 并被真实查询”

## 后续如何演进为 PostgreSQL 主库 + Neo4j 投影

后续如果主线希望把这套演示图谱演进为正式图谱投影，推荐路线是：

1. PostgreSQL 继续作为主库
2. 在展项新增、编辑、删除之后，产生统一的图谱投影事件
3. 由独立投影任务批量或异步把实体和关系同步到 Neo4j
4. 保持 API 路由不变，仅在服务层增加“Neo4j 投影可用时优先查询”的策略
5. 继续保留 fallback，避免 Neo4j 暂时不可用时影响主线功能

## 当前不做的事情

- 不修改主线 `main.py`
- 不直接接入现有 `/api/exhibits/{id}/graph`
- 不做 PostgreSQL 与 Neo4j 实时双写
- 不接 GraphRAG 路由
- 不接向量索引
- 不替换主线现有图谱逻辑
