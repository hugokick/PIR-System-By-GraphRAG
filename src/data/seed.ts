import type { Exhibit } from '../types';

export const seedExhibits: Exhibit[] = [
  {
    id: 'lever-play',
    name: '杠杆乐园',
    category: '基础科学',
    theme: '力学',
    venueType: '儿童科技馆',
    budgetMin: 200000,
    budgetMax: 350000,
    materials: ['金属', '木作', '亚克力'],
    dimensions: '4200x2600x2200mm',
    interactions: ['机械互动', '亲子协作', '动手实验'],
    supplier: '启思互动工坊',
    projectYear: 2024,
    owner: '青禾儿童科技馆',
    status: '已落地',
    description: '通过推拉、配重和跷跷板结构帮助低龄儿童理解杠杆原理，适合亲子共同操作。',
    tags: ['低龄儿童', '力学', '预算适中', '高互动'],
    media: [
      {
        id: 'lever-render',
        type: 'image',
        name: '展项效果图',
        url: 'https://picsum.photos/seed/exhibit-lever/900/600',
        note: '示意图，后续替换为项目实拍'
      }
    ],
    documents: [],
    relatedProjectIds: ['qinghe-2024'],
    relatedExhibitIds: ['pulley-wall']
  },
  {
    id: 'pulley-wall',
    name: '滑轮挑战墙',
    category: '基础科学',
    theme: '力学',
    venueType: '儿童科技馆',
    budgetMin: 150000,
    budgetMax: 280000,
    materials: ['金属', '绳索', '防火板'],
    dimensions: '5200x900x2600mm',
    interactions: ['机械互动', '竞赛互动'],
    supplier: '启思互动工坊',
    projectYear: 2024,
    owner: '青禾儿童科技馆',
    status: '制作中',
    description: '观众通过不同滑轮组提升同一重物，比较省力效果和路径差异。',
    tags: ['低龄儿童', '力学', '低预算', '多人协作'],
    media: [
      {
        id: 'pulley-sketch',
        type: 'drawing',
        name: '结构草图',
        url: 'https://picsum.photos/seed/exhibit-pulley/900/600'
      }
    ],
    documents: [],
    relatedProjectIds: ['qinghe-2024'],
    relatedExhibitIds: ['lever-play']
  },
  {
    id: 'water-cycle',
    name: '城市水循环沙盘',
    category: '生态环境',
    theme: '水资源',
    venueType: '综合科技馆',
    budgetMin: 420000,
    budgetMax: 680000,
    materials: ['亚克力', '水泵', 'LED'],
    dimensions: '6000x3200x1800mm',
    interactions: ['按钮互动', '数字投影', '模型演示'],
    supplier: '澄境模型',
    projectYear: 2022,
    owner: '江北科技馆',
    status: '维护中',
    description: '用实体沙盘、循环水路和投影叠加展示城市降雨、排水、净化和再利用过程。',
    tags: ['生态', '水循环', '模型沙盘'],
    media: [
      {
        id: 'water-model',
        type: 'image',
        name: '沙盘局部',
        url: 'https://picsum.photos/seed/exhibit-water/900/600'
      }
    ],
    documents: [],
    relatedProjectIds: ['jiangbei-2022'],
    relatedExhibitIds: []
  },
  {
    id: 'space-dome',
    name: '星际穹幕影院',
    category: '宇宙探索',
    theme: '天文',
    venueType: '综合科技馆',
    budgetMin: 900000,
    budgetMax: 1600000,
    materials: ['钢结构', '投影幕', '音响系统'],
    dimensions: '直径9000mm',
    interactions: ['沉浸影像', '课程讲解'],
    supplier: '星图数字',
    projectYear: 2023,
    owner: '江北科技馆',
    status: '已落地',
    description: '沉浸式球幕内容播放空间，服务天文课程、科普影片和主题活动。',
    tags: ['沉浸式', '天文', '高预算'],
    media: [
      {
        id: 'dome-view',
        type: 'image',
        name: '穹幕空间',
        url: 'https://picsum.photos/seed/exhibit-space/900/600'
      }
    ],
    documents: [],
    relatedProjectIds: ['jiangbei-2023'],
    relatedExhibitIds: []
  }
];
