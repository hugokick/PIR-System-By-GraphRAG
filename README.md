# 展项图鉴查询 MVP 系统

面向科技馆、博物馆等展陈场景的展项数字档案与智能检索 MVP。当前版本先用 React/Vite、本地种子数据和浏览器 localStorage 打通第一条业务闭环。

## 已实现

- 展项档案列表、详情和新增录入
- 场馆类型、类别、主题、材料、交互方式、状态等结构化筛选
- 面向中文描述的轻量语义检索雏形
- 展项、项目、业主、材料、供应商、主题、相似展项关系图谱
- 图片/文档上传入口与媒体预览链接
- 基础数据看板

## 本地运行

```bash
npm install
npm run dev -- --port 5173
```

访问 http://127.0.0.1:5173/

## 验证

```bash
npm test
npm run build
npm audit --audit-level=high
```

## 部署建议

当前前端 Demo 可以直接部署到 GitHub Pages、Vercel、Netlify 或任意 Nginx 静态站点。详见：

[docs/部署与测试环境建议.md](docs/部署与测试环境建议.md)

## 后续建议

- 用 FastAPI/NestJS + PostgreSQL 持久化展项、项目、媒体、关系数据
- 接入 pgvector 做真正的向量语义检索，并保留结构化过滤条件
- 将上传媒体切到 MinIO 或云对象存储
- 为问答增加 RAG 引用来源与权限控制
