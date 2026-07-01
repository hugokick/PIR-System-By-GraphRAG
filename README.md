# PIR-System-By-GraphRAG

面向科技馆、博物馆等展陈场景，对展项进行数字化建档、分类检索、可视化展示、动态管理。核心是用结构化数据与多媒体形式沉淀展项全生命周期信息，供科展人员工作时快速查找公司负责过的展项展品，给业主提供造价、材质、造型、互动形式等参考数据。

当前版本是“展项图鉴查询 MVP 系统”的全栈 MVP，使用 React/Vite + FastAPI，并可通过 PostgreSQL / pgvector、Neo4j 演示图谱和本地文件存储支撑可试用的业务验证环境。

## 已实现

- 展项档案列表、详情和新增录入
- 场馆类型、类别、主题、材料、交互方式、状态等结构化筛选
- PostgreSQL 持久化仓储、软删除、操作日志和 pgvector 检索向量
- 混合检索与 GraphRAG 问答雏形，回答返回编号引用来源
- 当前展项子图和全库 Neo4j 演示图谱展示
- 图片、视频、PDF、Office、Excel/CSV、文本资料上传、预览或下载
- CSV / XLSX 导入预览、错误行提示、提交写入和相似展项关系校验
- 管理员、编辑、访客角色权限和演示登录
- 基础数据看板

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

## 验证

```bash
npm test
python -m pytest backend/tests -q
npm run build
npm audit --audit-level=high
```

## 部署建议

当前全栈 MVP 建议部署到云服务器 Docker Compose 测试环境。早期纯前端 Demo 的静态部署说明仍保留在：

[docs/部署与测试环境建议.md](docs/部署与测试环境建议.md)

云服务器测试环境：

```bash
docker compose -f docker-compose.cloud.yml up -d --build
```

默认入口：

```text
http://<服务器公网 IP>:18080/
```

若服务器仅开放 80 端口，可通过宿主机 Nginx 反代到：

```text
http://<服务器公网 IP>/pir-system/
```

## 后续建议

- 将当前 PostgreSQL JSONB 档案逐步拆分为更标准的实体表 / 关系表
- 接入真实 embedding 模型和 LLM 答案生成，保留现有 GraphRAG API 契约
- 将上传媒体切到 MinIO 或云对象存储
- 完善生产级认证、权限和审计策略

## Demo accounts

- admin / admin123
- editor / editor123
- viewer / viewer123
