# PIR-System-By-GraphRAG

面向科技馆、博物馆等展陈场景的“展项图鉴查询 MVP 系统”。系统用于对展项进行数字化建档、分类检索、可视化展示和动态管理，帮助科展人员快速查找公司负责过的展项展品，并向业主提供造价、材质、造型、互动形式、项目案例和资料依据等参考信息。

当前版本是可演示、可试用的全栈 MVP，使用 React/Vite + FastAPI + PostgreSQL/pgvector + Neo4j 演示图谱 + 可配置文件存储。

## 公网测试

当前云端测试入口：

```text
http://106.52.200.183/pir-system/
```

演示账号：

| 角色 | 用户名 | 密码 | 主要权限 |
| --- | --- | --- | --- |
| 管理员 | `admin` | `admin123` | 审核、删除、操作日志、导出日志、全部维护操作 |
| 编辑 | `editor` | `editor123` | 新增/编辑、上传资料、导入表格、维护相似展项 |
| 访客 | `viewer` | `viewer123` | 只读浏览、检索、查看图谱与资料 |

手动验收步骤见：[docs/manual-test-checklist.md](docs/manual-test-checklist.md)。

## 已实现能力

- 展项档案列表、详情、新增、编辑、软删除和审核状态管理
- 场馆类型、类别、主题、项目、业主、供应商、标签、材料、交互方式、状态、预算区间等结构化筛选
- PostgreSQL 持久化仓储、实体关系投影、操作日志、审计日志 CSV 导出和 pgvector 检索向量
- 当前展项子图与全库 Neo4j 演示图谱展示，支持缩放、拖拽、重布局、节点选择和一跳高亮
- 相似展项关系人工维护，以及只读 KG 推荐候选的人工采纳
- 图片、视频、PDF、Office、Excel/CSV、文本资料上传、缩略图预览、PDF/图片/视频弹窗预览和原文件下载
- 文本、PDF、DOCX、XLSX、PPTX 等资料的文本抽取、文档切片独立持久化表、chunk embedding 和 GraphRAG 引用来源链路
- 上传资料字段抽取建议，可将建议字段套用到编辑表单，由人工确认后保存
- CSV / XLSX 导入预览、中文/历史表头映射、GB18030 编码兼容、错误行提示、提交写入和同批相似展项引用校验
- 混合检索：结构化过滤 + 关键词 + pgvector 语义分数 + 规则查询理解
- GraphRAG 问答：基于展项档案和上传资料回答，返回编号引用、来源卡片、置信度和 warning
- 管理员、编辑、访客角色权限；公网测试环境要求登录，Bearer token 带过期时间，后端关闭演示角色请求头认证
- 管理员系统状态接口，可检查仓储类型、文件存储后端、认证模式、Neo4j 演示配置和关键数据计数
- 删除保护：已审核或已落地档案及其资料不能被直接删除

## 核心字段

展项档案当前核心字段：

- `id`：展项编号，建议使用英文、数字和短横线
- `name`：展项名称
- `category`：类别或学科领域
- `theme`：主题
- `venue_type`：适用场馆
- `budget_min` / `budget_max`：造价区间，单位元
- `materials`：材料列表
- `dimensions`：尺寸说明
- `interactions`：交互方式列表
- `supplier`：供应商
- `project`：项目编号与项目名称
- `owner`：业主
- `project_year`：项目年份
- `status`：展项状态
- `review_status`：审核状态
- `description`：展项说明
- `tags`：标签
- `media_assets` / `documents`：媒体和资料档案
- `related_exhibit_ids`：人工维护的相似展项编号

导入模板支持中文表头和常见历史表头别名，例如“档案编号、展品名称、所属项目、建设单位、项目 ID、预算 下限”等。

## 本地运行

前端：

```bash
npm install
npm run dev -- --port 5173
```

访问：

```text
http://127.0.0.1:5173/
```

后端：

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

访问：

```text
http://127.0.0.1:8000/docs
```

## Docker Compose 测试环境

云端或本地容器化测试：

```bash
docker compose -f docker-compose.cloud.yml up -d --build
```

默认容器端口：

```text
http://<服务器公网 IP>:18080/
```

当前公网环境通过宿主机 Nginx 挂载到：

```text
http://<服务器公网 IP>/pir-system/
```

管理员登录后可用系统状态接口快速核对测试环境：

```http
GET /api/admin/system-status
```

`docker-compose.cloud.yml` 内部包含：

- `postgres`：PostgreSQL + pgvector，未暴露到公网
- `neo4j`：Neo4j 5 演示图谱，未暴露到公网
- `backend`：FastAPI API 服务
- `frontend`：Nginx 托管前端静态文件
- `file_storage`：上传资料本地对象存储卷

云端测试环境可用脚本备份 PostgreSQL、上传资料卷和 Neo4j 演示图谱卷：

```bash
./deploy/backup-cloud.sh
```

恢复需要显式确认，避免误覆盖测试库：

```bash
CONFIRM_RESTORE=YES ./deploy/restore-cloud.sh ./backups/pir-system-YYYYMMDDTHHMMSSZ
```

## 验证

```bash
pytest backend/tests
npm run test -- --run
npm run build
```

生产构建目前会提示 NVL 图谱组件 chunk 较大，这是已知提醒，不影响构建结果。

## 重要文档

- 开发计划：[docs/展项图鉴查询MVP系统开发计划.md](docs/展项图鉴查询MVP系统开发计划.md)
- 领域模型：[docs/domain-model.md](docs/domain-model.md)
- GraphRAG 设计：[docs/graphrag-design.md](docs/graphrag-design.md)
- KG / GraphRAG 契约：[docs/kg-graphrag-contract.md](docs/kg-graphrag-contract.md)
- Neo4j 演示图谱接入：[docs/neo4j-demo-graph-integration.md](docs/neo4j-demo-graph-integration.md)
- 部署建议：[docs/部署与测试环境建议.md](docs/部署与测试环境建议.md)

## 后续建议

- 继续接入生产级 embedding / LLM 服务与检索评测；当前已预留 OpenAI-compatible embedding 和 LLM provider，保留现有 GraphRAG API 契约
- 为生产环境配置 MinIO / 云对象存储和更完善的备份生命周期策略；当前云端 Compose 已提供基础备份/恢复脚本
- 完善生产级认证、备份、监控和审计策略

## 认证配置

公网测试环境使用演示账号和签名 Bearer token。token 默认有效期为 8 小时，可通过后端环境变量调整：

```text
AUTH_TOKEN_TTL_SECONDS=28800
AUTH_TOKEN_SECRET=replace-with-a-long-random-secret
ALLOW_ROLE_HEADER_AUTH=false
```

`AUTH_TOKEN_SECRET` 在正式环境必须替换为随机密钥；`ALLOW_ROLE_HEADER_AUTH=false` 用于关闭本地开发阶段的 `X-User-Role` 演示头认证。

## 可选对象存储

默认使用本地文件存储，可通过 `FILE_STORAGE_ROOT` 指定路径。需要切换到 MinIO 或 S3-compatible 对象存储时，在后端环境中配置：

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

上传、预览、下载、删除的 API URL 保持 `/api/files/{file_id}` 不变；文档解析会通过本地缓存读取对象存储文件。

## 可选 Embedding Provider

默认不配置外部 embedding 服务，系统会继续使用可测试、可复现的本地 `stable_embedding` fallback。需要接入兼容 OpenAI embeddings 的服务时，可在后端环境中配置：

```text
EMBEDDING_PROVIDER=openai-compatible
EMBEDDING_BASE_URL=https://your-embedding-endpoint/v1
EMBEDDING_API_KEY=your-api-key
EMBEDDING_MODEL=your-embedding-model
EMBEDDING_DIMENSIONS=1536
EMBEDDING_TIMEOUT_SECONDS=20
```

配置缺失、provider 调用失败或返回向量维度不匹配时，会自动回退到本地 `stable_embedding`；数据库 `pgvector` 字段和现有检索 / GraphRAG API 结构不变。

## 可选 LLM Provider

默认不配置外部 LLM，GraphRAG 回答使用可测试的本地 deterministic fallback。需要接入兼容 chat-completions 的 LLM 服务时，可在后端环境中配置：

```text
RAG_LLM_PROVIDER=openai-compatible
RAG_LLM_BASE_URL=https://your-llm-endpoint/v1
RAG_LLM_API_KEY=your-api-key
RAG_LLM_MODEL=your-chat-model
RAG_LLM_TIMEOUT_SECONDS=20
```

provider 返回空结果、异常或配置缺失时会自动回退到本地答案组织器，不改变 `/api/graphrag/answer` 请求 / 响应结构。
