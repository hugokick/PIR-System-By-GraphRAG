# 展项图鉴查询 MVP 后端

阶段 2 后端骨架，使用 FastAPI 提供展项查询、详情和图谱查询 API。

当前状态：

- FastAPI 应用已初始化
- 展项列表、详情、图谱查询 API 已具备测试
- PostgreSQL + pgvector 初始化 SQL 已准备
- Docker Compose 已提供 PostgreSQL 本地容器
- API 暂时使用内存种子仓储，下一步切换为 PostgreSQL 持久化读写

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
GET /api/exhibits
GET /api/exhibits/{id}
GET /api/exhibits/{id}/graph
```

## 下一步

- 增加 PostgreSQL 数据访问层
- 增加 `POST /api/exhibits`
- 增加 `PUT /api/exhibits/{id}`
- 增加软删除 `DELETE /api/exhibits/{id}`
- 前端从 localStorage 切换为调用后端 API
