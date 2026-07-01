# 展项图鉴查询 MVP 后端

FastAPI 后端为展项数字档案、结构化检索、轻量图谱、Neo4j 演示图谱和 GraphRAG 问答提供 API。

当前状态：

- 展项列表、详情、新增、编辑、删除、审核状态和相似展项关系 API 已具备测试
- 未配置 `DATABASE_URL` 时使用内存种子仓储，配置后使用 PostgreSQL 持久化读写
- PostgreSQL 仓储已支持 JSONB 档案、软删除、操作日志、pgvector 检索向量和文档 chunk embedding
- 文件上传支持图片、视频、PDF、Office、Excel/CSV、文本资料，本地对象存储路径可通过 `FILE_STORAGE_ROOT` 配置
- CSV / XLSX 导入支持预览、错误行提示、提交写入和相似展项引用校验
- Neo4j 演示图谱支持当前展项子图和全库演示图谱查询
- GraphRAG 检索 / 问答接口已返回编号引用来源，上传文本和 PDF 资料可进入引用链路
- 管理员、编辑、访客角色权限和 Bearer token 演示登录已接入

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

- 将 PostgreSQL JSONB 档案逐步拆分为更标准的实体表 / 关系表，降低后续知识图谱同步成本
- 接入真实 embedding 模型和 LLM 答案生成，同时保持现有 GraphRAG API 契约
- 将本地文件存储替换或扩展为 MinIO / 云对象存储
