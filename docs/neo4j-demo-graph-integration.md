# Neo4j 演示图谱接入说明

## 目标

本支线用于给现有知识图谱窗口提供一条真实 Neo4j 查询链路，作为项目演示佐证。主线接口仍保持 `/api/exhibits/{exhibit_id}/graph` 不变；启用 Neo4j 演示配置后，后端优先查询 Neo4j，查询失败、无数据或未启用时自动回退到现有 Python/PostgreSQL 图谱构建逻辑。

## 当前主线接入点

- `backend/app/neo4j_demo/query.py`
  - 构建中心展项子图 Cypher。
  - 将 Neo4j records 映射为现有 `GraphResponse` 的 `nodes/edges`。
- `backend/app/neo4j_demo/seed.py`
  - 基于当前展项样例数据生成可逐条执行的 Cypher seed statements。
  - 覆盖实体：`Exhibit`、`Project`、`Owner`、`Supplier`、`Material`、`Theme`、`Interaction`、`Document`。
- `backend/app/neo4j_demo/service.py`
  - `Neo4jDemoGraphService` 负责 Neo4j 优先查询与 fallback。
  - `create_neo4j_demo_graph_service()` 根据环境变量创建可选 Neo4j client。
- `backend/app/main.py`
  - `/api/exhibits/{exhibit_id}/graph` 已接入该服务工厂。

## 环境变量

云端 `docker-compose.cloud.yml` 已启用以下配置：

```env
NEO4J_DEMO_ENABLED=true
NEO4J_DEMO_AUTO_SEED=true
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=demo-graph123
```

未设置 `NEO4J_DEMO_ENABLED=true` 时，接口行为等同于原有图谱逻辑。

## 云端服务

云端测试环境新增内部 Neo4j 容器：

- 容器名：`exhibit-atlas-neo4j`
- 镜像：`neo4j:5`
- 数据卷：`exhibit_atlas_neo4j_data`
- 网络：仅在 `exhibit-atlas-mvp` compose 网络内访问，不向公网暴露 `7474/7687`。

后端容器启动后，在第一次图谱查询时自动 seed 当前展项样例数据；seed 成功后，同一后端进程内不会重复清库导入。

## Fallback 策略

以下情况会回退到现有 `build_exhibit_graph()`：

- 未启用 Neo4j 演示配置。
- 缺少 Neo4j 连接参数。
- Python Neo4j driver 不存在。
- Neo4j 查询异常。
- Neo4j 返回空记录。
- 记录映射后没有有效节点。

因此，Neo4j 演示链路不会阻断现有前端图谱窗口。

## 后续演进

当前 Neo4j 是演示投影，不是主库，也不承担生产级双写一致性。后续如果要演进为正式图谱投影，建议按以下顺序推进：

1. PostgreSQL 继续作为主数据源。
2. 展项新增、编辑、删除后产生统一图谱投影事件。
3. 独立同步任务批量或异步写入 Neo4j。
4. 保持 `/api/exhibits/{id}/graph` API 不变，只增强服务层策略。
5. GraphRAG 再逐步消费 Neo4j 子图与文档引用，不直接耦合 CRUD。
