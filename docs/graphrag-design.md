# GraphRAG MVP 设计说明

## 当前目标

本阶段先建立 GraphRAG 的后端 API 契约和最小可运行链路。当前 GraphRAG 问答仍不直接接入 LLM；检索侧已经具备结构化字段、轻量图谱邻域、文档 chunk、确定性本地 embedding 与 pgvector 召回的 MVP 基座，后续可在不改前端/调用方契约的前提下替换为真实 embedding 模型和 LLM 答案生成策略。

## 已提供接口

```http
POST /api/graphrag/search
POST /api/graphrag/answer
```

### `/api/graphrag/search`

请求：

```json
{
  "query": "lever-play",
  "top_k": 5
}
```

返回：

- `items[].exhibit`：命中的展项完整档案
- `items[].score`：规则版相关性分数
- `items[].reasons`：命中原因
- `items[].citations`：展项或文档来源
- `items[].graph`：围绕该展项生成的图谱节点和边

### `/api/graphrag/answer`

请求：

```json
{
  "query": "lever-play",
  "top_k": 3
}
```

返回：

- `answer`：基于当前命中展项生成的规则版答案
- `citations`：去重后的引用来源
- `items`：答案所依据的 GraphRAG 检索结果

当前答案为无 LLM 的中文模板，会根据命中展项、匹配原因和去重后的 citation 生成带 `[1]`、`[2]` 等编号的来源说明。如果库内没有证据，接口会返回空 `items` 和 `citations`，并在 `answer` 中明确说明未找到依据。

## 当前实现边界

当前实现位于：

- `backend/app/services/graphrag.py`
- `backend/app/main.py`
- `backend/app/schemas.py`

当前版本只负责：

- 按展项 ID、名称、类别、主题、材料、交互方式、项目/业主/供应商、说明、文档来源做规则匹配
- 返回匹配原因和引用
- 调用现有图谱服务返回展项邻域
- 使用展项档案、上传文本资料和可抽取文本的 PDF chunk 作为检索与引用来源
- 给问答接口提供无 LLM 的中文、带编号引用的答案模板

暂不负责：

- 外部 embedding 模型接入和 embedding 生命周期调度
- LLM 答案生成
- Neo4j/Cypher
- 自动知识图谱抽取

已具备：

- `backend/app/services/embeddings.py` 提供确定性本地 embedding，维度与 pgvector schema 保持 `1536`
- `PostgresExhibitRepository` 初始化 `vector` 扩展、`search_embeddings` 表和 ivfflat 索引
- 展项新增/更新时同步展项正文和文档 chunk embedding
- `/api/search/hybrid` 可读取 repository 的 pgvector 相似度分数，并合并到混合排序和匹配原因中
- `/api/graphrag/search` 与 `/api/graphrag/answer` 已将 repository 的 pgvector 相似度分数作为 GraphRAG 候选召回信号，命中结果仍返回图谱邻域、reasoning signal 和 citation

## 后续替换点

后续开发 GraphRAG 时优先替换以下内部函数，而不是改 API 契约：

- `search_graphrag_context`
  - 将当前确定性本地 embedding 召回替换为真实 embedding 模型、重排器和更完整的图谱邻域扩展策略
- `answer_from_graphrag_context`
  - 接入 LLM，根据 `items` 和 `citations` 生成带来源答案
- `backend/app/services/documents.py`
  - 将当前内嵌 `DocumentAsset.chunks` 升级为独立持久化 chunk 与引用定位

## 并行开发约束

GraphRAG 深化开发建议放在独立分支或 worktree 中进行。初期尽量只新增以下路径：

- `backend/app/kg/`
- `backend/app/graphrag/`
- `backend/tests/test_kg_*.py`
- `backend/tests/test_graphrag_*.py`
- `docs/kg-construction-plan.md`
- `docs/graphrag-design.md`

如需修改以下文件，应先与主线开发确认：

- `backend/app/main.py`
- `backend/app/repository.py`
- `backend/sql/001_init.sql`
- `docker-compose.cloud.yml`
- `deploy/nginx.conf`
- `src/ui/App.tsx`
- `src/lib/api.ts`

云端测试环境仍使用 `/pir-system/` 子路径，不修改 BIM 系统根路径和宿主机 `/api/` 代理。
