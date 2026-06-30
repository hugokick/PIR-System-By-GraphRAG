# PIR-System-By-GraphRAG

面向科技馆、博物馆等展陈场景，对展项进行数字化建档、分类检索、可视化展示、动态管理。核心是用结构化数据与多媒体形式沉淀展项全生命周期信息，供科展人员工作时快速查找公司负责过的展项展品，给业主提供造价、材质、造型、互动形式等参考数据。

当前版本是“展项图鉴查询 MVP 系统”的前端演示版，使用 React/Vite、本地种子数据和浏览器 localStorage 打通第一条业务闭环。

## 已实现

- 展项档案列表、详情和新增录入
- 场馆类型、类别、主题、材料、交互方式、状态等结构化筛选
- 面向中文描述的轻量语义检索雏形
- 展项、项目、业主、材料、供应商、主题、相似展项关系图谱
- 图片/文档上传入口与媒体预览链接
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

当前前端 Demo 可以直接部署到 GitHub Pages、Vercel、Netlify 或任意 Nginx 静态站点。详见：

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

- 用 FastAPI/NestJS + PostgreSQL 持久化展项、项目、媒体、关系数据
- 接入 pgvector 做真正的向量语义检索，并保留结构化过滤条件
- 将上传媒体切到 MinIO 或云对象存储
- 为问答增加 RAG 引用来源与权限控制

## Demo accounts

- admin / admin123
- editor / editor123
- viewer / viewer123
