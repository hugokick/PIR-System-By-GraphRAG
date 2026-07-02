# 展项图鉴查询 MVP 后端

FastAPI 后端为展项数字档案、结构化检索、轻量图谱、Neo4j 演示图谱和 GraphRAG 问答提供 API。

当前状态：

- 展项列表、详情、新增、编辑、删除、审核状态和相似展项关系 API 已具备测试
- 未配置 `DATABASE_URL` 时使用内存种子仓储，配置后使用 PostgreSQL 持久化读写
- PostgreSQL 仓储已支持 JSONB 主档案、标准实体/关系表投影、软删除、操作日志、pgvector 检索向量、`document_chunks` 独立持久化表、文档 chunk embedding，以及 `kg_nodes` / `kg_edges` 运行时图谱投影表
- 文件上传支持图片、视频、PDF、Office、Excel/CSV、文本资料，默认本地文件存储，也可配置 S3/MinIO-compatible 对象存储
- CSV / XLSX 导入支持预览、错误行提示、提交写入和相似展项引用校验
- 当前展项图谱 API 优先读取 PostgreSQL 标准实体/关系表；关系表未命中时回退到 `kg_nodes` / `kg_edges` 投影表，Neo4j 演示图谱继续支持回退查询和全库演示图谱
- GraphRAG 检索 / 问答接口已复用 PostgreSQL KG 投影快照，并返回编号引用来源；上传文本和 PDF 资料可进入引用链路
- 管理员、编辑、访客角色权限和带过期时间的 Bearer token 演示登录已接入

## 建议使用虚拟环境

不要直接把后端依赖安装进全局 Python 环境。

```bash
cd C:\Users\yqzhe\Documents\展项图鉴查询MVP系统
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
```

## 运行测试

```bash
python -m pytest backend/tests -q
```

## 启动 API

```bash
uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

访问：

```text
http://127.0.0.1:8000/docs
```

## 启动 PostgreSQL

```bash
docker compose up -d postgres
```

默认连接信息：

```text
POSTGRES_DB=exhibit_atlas
POSTGRES_USER=exhibit_atlas
POSTGRES_PASSWORD=exhibit_atlas_dev
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
```

初始化脚本：

```text
backend/sql/001_init.sql
```

## 已实现 API

```http
GET /health
POST /api/auth/login
GET /api/auth/me
GET /api/exhibits
POST /api/exhibits
GET /api/exhibits/{id}
PUT /api/exhibits/{id}
DELETE /api/exhibits/{id}
PATCH /api/exhibits/{id}/review-status
PATCH /api/exhibits/{id}/related-exhibits
POST /api/exhibits/{id}/assets
DELETE /api/exhibits/{id}/assets/{asset_id}
GET /api/files/{file_id}
GET /api/dashboard/summary
POST /api/exhibits/import
GET /api/exhibits/import-template
GET /api/exhibits/{id}/graph
GET /api/neo4j-demo/graph
POST /api/search/hybrid
POST /api/graphrag/search
POST /api/graphrag/answer
GET /api/admin/audit-logs
```

## 下一步

- 继续让标准实体/关系表从当前重建投影逐步演进为增量同步，并评估列表/筛选查询读取实体表的时机
- 继续接入生产级 embedding / LLM 服务与检索评测；当前已支持可选 OpenAI-compatible embedding 和 LLM provider，同时保持现有 GraphRAG API 契约
- 为生产环境配置 MinIO / 云对象存储、备份和生命周期策略

## 认证环境变量

演示登录会签发带 `exp` 的 Bearer token。默认有效期为 8 小时，可通过环境变量调整：

```text
AUTH_TOKEN_TTL_SECONDS=28800
AUTH_TOKEN_SECRET=replace-with-a-long-random-secret
ALLOW_ROLE_HEADER_AUTH=false
```

`AUTH_TOKEN_SECRET` 用于 HMAC 签名，正式环境必须替换；`ALLOW_ROLE_HEADER_AUTH=false` 用于公网测试或生产化环境，避免继续接受 `X-User-Role` 演示请求头。

## 可选对象存储

默认使用本地文件存储，可通过 `FILE_STORAGE_ROOT` 指定路径。若需要接入 MinIO 或 S3-compatible 对象存储，可配置：

```text
FILE_STORAGE_BACKEND=s3
S3_BUCKET=your-bucket
S3_ENDPOINT_URL=http://minio:9000
S3_ACCESS_KEY_ID=your-access-key
S3_SECRET_ACCESS_KEY=your-secret-key
S3_REGION=us-east-1
S3_PREFIX=pir-system
S3_CACHE_ROOT=/app/backend/storage-cache
```

上传后仍返回 `/api/files/{file_id}`，下载 / 预览 / 删除接口不变。文档解析和预览会在后端本地缓存对象文件，缓存目录由 `S3_CACHE_ROOT` 控制。

## 可选 Embedding Provider

默认不配置外部 embedding 服务，后端会继续使用 deterministic `stable_embedding` fallback。若需要接入兼容 OpenAI embeddings 的服务，可配置：

```text
EMBEDDING_PROVIDER=openai-compatible
EMBEDDING_BASE_URL=https://your-embedding-endpoint/v1
EMBEDDING_API_KEY=your-api-key
EMBEDDING_MODEL=your-embedding-model
EMBEDDING_DIMENSIONS=1536
EMBEDDING_TIMEOUT_SECONDS=20
```

配置缺失、provider 调用失败或返回维度不匹配时，仓储写入、文档 chunk embedding、混合检索查询向量都会自动回退到本地 `stable_embedding`；请求 / 响应结构和 `pgvector` 存储维度不变。

## 可选 GraphRAG LLM Provider

默认不配置外部 LLM，`/api/graphrag/answer` 会使用 deterministic fallback。若需要接入兼容 chat-completions 的 LLM 服务，可配置：

```text
RAG_LLM_PROVIDER=openai-compatible
RAG_LLM_BASE_URL=https://your-llm-endpoint/v1
RAG_LLM_API_KEY=your-api-key
RAG_LLM_MODEL=your-chat-model
RAG_LLM_TIMEOUT_SECONDS=20
```

配置缺失、provider 返回空结果或调用失败时，接口自动回退到本地答案组织器；请求和响应结构不变。
