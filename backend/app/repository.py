import json
import os
import uuid
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from .kg.builder import build_exhibit_kg_snapshot
from .kg.models import KGEdge, KGNode, KGSnapshot
from .schemas import (
    AuditLogEntry,
    DocumentAsset,
    DocumentExtractionSuggestionRecord,
    EntityRef,
    ExhibitResponse,
    GraphEdge,
    GraphNode,
    GraphResponse,
    MediaAsset,
)
from .services.embeddings import (
    embedding_provider_from_env,
    embedding_text_for_document_chunk,
    embedding_text_for_exhibit,
    embedding_vector,
    vector_literal,
)


seed_exhibits = [
    ExhibitResponse(
        id="lever-play",
        name="杠杆乐园",
        category="基础科学",
        theme=EntityRef(id="mechanics", name="力学"),
        venue_type="儿童科技馆",
        budget_min=200000,
        budget_max=350000,
        materials=[
            EntityRef(id="metal", name="金属"),
            EntityRef(id="woodwork", name="木作"),
            EntityRef(id="acrylic", name="亚克力"),
        ],
        dimensions="4200x2600x2200mm",
        interactions=[
            EntityRef(id="mechanical", name="机械互动"),
            EntityRef(id="family", name="亲子协作"),
            EntityRef(id="hands-on", name="动手实验"),
        ],
        supplier=EntityRef(id="qisi", name="启思互动工坊"),
        project=EntityRef(id="qinghe-2024", name="青禾儿童科技馆更新项目"),
        owner=EntityRef(id="qinghe-owner", name="青禾儿童科技馆"),
        project_year=2024,
        status="已落地",
        review_status="已审核",
        description="通过推拉、配重和跷跷板结构帮助低龄儿童理解杠杆原理，适合亲子共同操作。",
        tags=["低龄儿童", "力学", "预算适中", "高互动"],
        media_assets=[
            MediaAsset(
                id="lever-render",
                type="image",
                name="展项效果图",
                url="https://picsum.photos/seed/exhibit-lever/900/600",
                note="示意图，后续替换为项目实拍",
            )
        ],
        documents=[
            DocumentAsset(
                id="lever-brief",
                name="杠杆乐园展项说明",
                file_type="pdf",
                url="/files/lever-brief.pdf",
                source_note="样例文档，用于验证 RAG 来源链路",
            )
        ],
        related_exhibit_ids=["pulley-wall"],
    ),
    ExhibitResponse(
        id="pulley-wall",
        name="滑轮挑战墙",
        category="基础科学",
        theme=EntityRef(id="mechanics", name="力学"),
        venue_type="儿童科技馆",
        budget_min=150000,
        budget_max=280000,
        materials=[
            EntityRef(id="metal", name="金属"),
            EntityRef(id="rope", name="绳索"),
            EntityRef(id="fireproof-board", name="防火板"),
        ],
        dimensions="5200x900x2600mm",
        interactions=[
            EntityRef(id="mechanical", name="机械互动"),
            EntityRef(id="competition", name="竞赛互动"),
        ],
        supplier=EntityRef(id="qisi", name="启思互动工坊"),
        project=EntityRef(id="qinghe-2024", name="青禾儿童科技馆更新项目"),
        owner=EntityRef(id="qinghe-owner", name="青禾儿童科技馆"),
        project_year=2024,
        status="制作中",
        review_status="待审核",
        description="观众通过不同滑轮组提升同一重物，比较省力效果和路径差异。",
        tags=["低龄儿童", "力学", "低预算", "多人协作"],
        media_assets=[
            MediaAsset(
                id="pulley-sketch",
                type="drawing",
                name="结构草图",
                url="https://picsum.photos/seed/exhibit-pulley/900/600",
            )
        ],
        documents=[],
        related_exhibit_ids=["lever-play"],
    ),
    ExhibitResponse(
        id="water-cycle",
        name="城市水循环沙盘",
        category="生态环境",
        theme=EntityRef(id="water-resource", name="水资源"),
        venue_type="综合科技馆",
        budget_min=420000,
        budget_max=680000,
        materials=[
            EntityRef(id="acrylic", name="亚克力"),
            EntityRef(id="water-pump", name="水泵"),
            EntityRef(id="led", name="LED"),
        ],
        dimensions="6000x3200x1800mm",
        interactions=[
            EntityRef(id="button", name="按钮互动"),
            EntityRef(id="projection", name="数字投影"),
            EntityRef(id="model-demo", name="模型演示"),
        ],
        supplier=EntityRef(id="chengjing", name="澄境模型"),
        project=EntityRef(id="jiangbei-2022", name="江北科技馆生态展区"),
        owner=EntityRef(id="jiangbei-owner", name="江北科技馆"),
        project_year=2022,
        status="维护中",
        review_status="已退回",
        description="用实体沙盘、循环水路和投影叠加展示城市降雨、排水、净化和再利用过程。",
        tags=["生态", "水循环", "模型沙盘"],
        media_assets=[
            MediaAsset(
                id="water-model",
                type="image",
                name="沙盘局部",
                url="https://picsum.photos/seed/exhibit-water/900/600",
            )
        ],
        documents=[],
        related_exhibit_ids=[],
    ),
]

seed_exhibits.extend(
    [
        ExhibitResponse(
            id="space-dome",
            name="星际穹幕影院",
            category="宇宙探索",
            theme=EntityRef(id="astronomy", name="天文"),
            venue_type="综合科技馆",
            budget_min=900000,
            budget_max=1600000,
            materials=[
                EntityRef(id="steel-structure", name="钢结构"),
                EntityRef(id="projection-screen", name="投影幕"),
                EntityRef(id="audio-system", name="音响系统"),
            ],
            dimensions="直径9000mm",
            interactions=[
                EntityRef(id="immersive-image", name="沉浸影像"),
                EntityRef(id="course-explanation", name="课程讲解"),
            ],
            supplier=EntityRef(id="xingtu", name="星图数字"),
            project=EntityRef(id="jiangbei-2023", name="江北科技馆宇宙探索展区"),
            owner=EntityRef(id="jiangbei-owner", name="江北科技馆"),
            project_year=2023,
            status="已落地",
            review_status="已审核",
            description="沉浸式球幕内容播放空间，服务天文课程、科普影片和主题活动。",
            tags=["沉浸式", "天文", "高预算"],
            media_assets=[
                MediaAsset(
                    id="dome-view",
                    type="image",
                    name="穹幕空间",
                    url="https://picsum.photos/seed/exhibit-space/900/600",
                )
            ],
            documents=[
                DocumentAsset(
                    id="space-dome-brief",
                    name="星际穹幕影院项目说明",
                    file_type="pdf",
                    url="/files/space-dome-brief.pdf",
                    source_note="演示用穹幕影院资料。",
                )
            ],
            related_exhibit_ids=["ai-portrait"],
        ),
        ExhibitResponse(
            id="magnet-maze",
            name="磁力迷宫",
            category="基础科学",
            theme=EntityRef(id="electromagnetism", name="电磁学"),
            venue_type="儿童科技馆",
            budget_min=180000,
            budget_max=320000,
            materials=[
                EntityRef(id="acrylic", name="亚克力"),
                EntityRef(id="magnet", name="磁铁"),
                EntityRef(id="metal", name="金属"),
            ],
            dimensions="3600x1800x1800mm",
            interactions=[
                EntityRef(id="hands-on", name="动手实验"),
                EntityRef(id="mechanical", name="机械互动"),
            ],
            supplier=EntityRef(id="qisi", name="启思互动工坊"),
            project=EntityRef(id="qinghe-2024", name="青禾儿童科技馆更新项目"),
            owner=EntityRef(id="qinghe-owner", name="青禾儿童科技馆"),
            project_year=2024,
            status="概念方案",
            review_status="待审核",
            description="观众通过磁棒控制小球穿越透明迷宫，观察磁力吸引、排斥和隔空作用。",
            tags=["低龄儿童", "电磁学", "低预算", "动手实验"],
            media_assets=[
                MediaAsset(
                    id="magnet-maze-render",
                    type="image",
                    name="磁力迷宫效果图",
                    url="https://picsum.photos/seed/exhibit-magnet/900/600",
                )
            ],
            documents=[],
            related_exhibit_ids=["lever-play"],
        ),
        ExhibitResponse(
            id="sound-wave-lab",
            name="声波可视化实验台",
            category="基础科学",
            theme=EntityRef(id="acoustics", name="声学"),
            venue_type="儿童科技馆",
            budget_min=220000,
            budget_max=380000,
            materials=[
                EntityRef(id="acrylic", name="亚克力"),
                EntityRef(id="speaker", name="扬声器"),
                EntityRef(id="led", name="LED"),
            ],
            dimensions="3200x1600x1700mm",
            interactions=[
                EntityRef(id="knob-control", name="旋钮调节"),
                EntityRef(id="hands-on", name="动手实验"),
            ],
            supplier=EntityRef(id="qisi", name="启思互动工坊"),
            project=EntityRef(id="qinghe-2024", name="青禾儿童科技馆更新项目"),
            owner=EntityRef(id="qinghe-owner", name="青禾儿童科技馆"),
            project_year=2024,
            status="制作中",
            review_status="待审核",
            description="通过频率旋钮、振动膜和灯带反馈，把声音的频率、振幅和共振现象转化为可见变化。",
            tags=["低龄儿童", "声学", "高互动", "低预算"],
            media_assets=[
                MediaAsset(
                    id="sound-wave-render",
                    type="image",
                    name="声波实验台效果图",
                    url="https://picsum.photos/seed/exhibit-sound/900/600",
                )
            ],
            documents=[],
            related_exhibit_ids=["magnet-maze"],
        ),
        ExhibitResponse(
            id="thermal-storm",
            name="热力风暴互动台",
            category="基础科学",
            theme=EntityRef(id="thermodynamics", name="热学"),
            venue_type="综合科技馆",
            budget_min=350000,
            budget_max=550000,
            materials=[
                EntityRef(id="stainless-steel", name="不锈钢"),
                EntityRef(id="sensor", name="传感器"),
                EntityRef(id="led", name="LED"),
            ],
            dimensions="4800x2200x2100mm",
            interactions=[
                EntityRef(id="infrared", name="红外感应"),
                EntityRef(id="model-demo", name="模型演示"),
            ],
            supplier=EntityRef(id="yuanchuang", name="源创科教"),
            project=EntityRef(id="jiangbei-2022", name="江北科技馆生态展区"),
            owner=EntityRef(id="jiangbei-owner", name="江北科技馆"),
            project_year=2022,
            status="已落地",
            review_status="已审核",
            description="用热成像、风机和灯光模拟冷热空气对流，解释城市热岛和天气变化。",
            tags=["热学", "传感互动", "中预算", "资料引用"],
            media_assets=[
                MediaAsset(
                    id="thermal-table",
                    type="image",
                    name="热力互动台",
                    url="https://picsum.photos/seed/exhibit-thermal/900/600",
                )
            ],
            documents=[
                DocumentAsset(
                    id="thermal-plan",
                    name="thermal-plan.pdf",
                    file_type="pdf",
                    url="/files/thermal-plan.pdf",
                    source_note="热学互动台设计依据样例。",
                )
            ],
            related_exhibit_ids=["water-cycle"],
        ),
        ExhibitResponse(
            id="wind-tunnel",
            name="风洞飞行实验舱",
            category="基础科学",
            theme=EntityRef(id="aerodynamics", name="空气动力学"),
            venue_type="综合科技馆",
            budget_min=500000,
            budget_max=850000,
            materials=[
                EntityRef(id="steel-structure", name="钢结构"),
                EntityRef(id="acrylic", name="亚克力"),
                EntityRef(id="fan", name="风机"),
            ],
            dimensions="6200x2400x2600mm",
            interactions=[
                EntityRef(id="button", name="按钮互动"),
                EntityRef(id="digital-screen", name="数字屏幕"),
            ],
            supplier=EntityRef(id="yuanchuang", name="源创科教"),
            project=EntityRef(id="linhai-2025", name="临海航空航天科普中心"),
            owner=EntityRef(id="linhai-owner", name="临海科普中心"),
            project_year=2025,
            status="概念方案",
            review_status="草稿",
            description="观众调整机翼角度并观察升力变化，配合风速显示和烟线展示气流路径。",
            tags=["空气动力", "中高预算", "航空", "可调参数"],
            media_assets=[
                MediaAsset(
                    id="wind-tunnel-render",
                    type="image",
                    name="风洞舱效果图",
                    url="https://picsum.photos/seed/exhibit-wind/900/600",
                )
            ],
            documents=[],
            related_exhibit_ids=["space-dome"],
        ),
        ExhibitResponse(
            id="robot-arm",
            name="协作机器人装配线",
            category="智能制造",
            theme=EntityRef(id="robotics", name="机器人"),
            venue_type="产业科技馆",
            budget_min=650000,
            budget_max=950000,
            materials=[
                EntityRef(id="aluminum-profile", name="铝型材"),
                EntityRef(id="servo-motor", name="伺服电机"),
                EntityRef(id="touch-screen", name="触摸屏"),
            ],
            dimensions="7000x2600x2300mm",
            interactions=[
                EntityRef(id="programming", name="编程互动"),
                EntityRef(id="touch-screen", name="触摸互动"),
            ],
            supplier=EntityRef(id="futurebot", name="未来机器人"),
            project=EntityRef(id="yungu-2025", name="云谷未来产业馆"),
            owner=EntityRef(id="yungu-owner", name="云谷产业园"),
            project_year=2025,
            status="制作中",
            review_status="待审核",
            description="用安全协作机械臂完成分拣、搬运和装配任务，展示工业自动化流程。",
            tags=["机器人", "智能制造", "高互动", "中高预算"],
            media_assets=[
                MediaAsset(
                    id="robot-arm-render",
                    type="image",
                    name="机器人装配线",
                    url="https://picsum.photos/seed/exhibit-robot/900/600",
                )
            ],
            documents=[],
            related_exhibit_ids=["ai-portrait"],
        ),
        ExhibitResponse(
            id="ai-portrait",
            name="AI 画像识别站",
            category="人工智能",
            theme=EntityRef(id="ai", name="人工智能"),
            venue_type="综合科技馆",
            budget_min=400000,
            budget_max=700000,
            materials=[
                EntityRef(id="camera", name="摄像头"),
                EntityRef(id="display", name="显示屏"),
                EntityRef(id="sheet-metal", name="钣金"),
            ],
            dimensions="3000x1800x2200mm",
            interactions=[
                EntityRef(id="ai-interaction", name="AI互动"),
                EntityRef(id="touch-screen", name="触摸互动"),
            ],
            supplier=EntityRef(id="xingtu", name="星图数字"),
            project=EntityRef(id="yungu-2025", name="云谷未来产业馆"),
            owner=EntityRef(id="yungu-owner", name="云谷产业园"),
            project_year=2025,
            status="概念方案",
            review_status="草稿",
            description="通过摄像头采集姿态和表情，实时生成职业画像、科学家角色和互动问答。",
            tags=["人工智能", "AI互动", "人脸识别", "中预算"],
            media_assets=[
                MediaAsset(
                    id="ai-portrait-render",
                    type="image",
                    name="AI 画像识别站",
                    url="https://picsum.photos/seed/exhibit-ai/900/600",
                )
            ],
            documents=[],
            related_exhibit_ids=["robot-arm"],
        ),
        ExhibitResponse(
            id="earthquake-table",
            name="地震安全模拟平台",
            category="地球科学",
            theme=EntityRef(id="earth-science", name="地球科学"),
            venue_type="防灾科普馆",
            budget_min=320000,
            budget_max=580000,
            materials=[
                EntityRef(id="steel-structure", name="钢结构"),
                EntityRef(id="motor", name="电机"),
                EntityRef(id="acrylic", name="亚克力"),
            ],
            dimensions="4500x2400x1800mm",
            interactions=[
                EntityRef(id="button", name="按钮互动"),
                EntityRef(id="model-demo", name="模型演示"),
            ],
            supplier=EntityRef(id="chengjing", name="澄境模型"),
            project=EntityRef(id="nanling-2023", name="南岭防灾科普馆"),
            owner=EntityRef(id="nanling-owner", name="南岭应急管理中心"),
            project_year=2023,
            status="已落地",
            review_status="已审核",
            description="用可控震动平台比较不同建筑结构的抗震表现，并引导观众学习避险路线。",
            tags=["防灾", "地震", "模型演示", "中预算"],
            media_assets=[
                MediaAsset(
                    id="earthquake-table-render",
                    type="image",
                    name="地震平台",
                    url="https://picsum.photos/seed/exhibit-earthquake/900/600",
                )
            ],
            documents=[],
            related_exhibit_ids=["water-cycle"],
        ),
        ExhibitResponse(
            id="recycling-line",
            name="垃圾分类分拣线",
            category="生态环境",
            theme=EntityRef(id="recycling", name="循环经济"),
            venue_type="生态文明馆",
            budget_min=280000,
            budget_max=460000,
            materials=[
                EntityRef(id="conveyor", name="输送带"),
                EntityRef(id="sensor", name="传感器"),
                EntityRef(id="woodwork", name="木作"),
            ],
            dimensions="5600x1800x1900mm",
            interactions=[
                EntityRef(id="sorting-game", name="分拣游戏"),
                EntityRef(id="competition", name="竞赛互动"),
            ],
            supplier=EntityRef(id="chengjing", name="澄境模型"),
            project=EntityRef(id="jiangbei-2022", name="江北科技馆生态展区"),
            owner=EntityRef(id="jiangbei-owner", name="江北科技馆"),
            project_year=2022,
            status="维护中",
            review_status="已退回",
            description="观众把不同垃圾投入分拣线，系统识别类别并展示资源回收路径。",
            tags=["生态", "垃圾分类", "多人协作", "中预算"],
            media_assets=[
                MediaAsset(
                    id="recycling-line-render",
                    type="image",
                    name="分拣线局部",
                    url="https://picsum.photos/seed/exhibit-recycling/900/600",
                )
            ],
            documents=[],
            related_exhibit_ids=["water-cycle"],
        ),
        ExhibitResponse(
            id="human-body",
            name="人体探秘互动墙",
            category="生命科学",
            theme=EntityRef(id="life-science", name="生命科学"),
            venue_type="自然博物馆",
            budget_min=450000,
            budget_max=750000,
            materials=[
                EntityRef(id="model", name="模型"),
                EntityRef(id="touch-screen", name="触摸屏"),
                EntityRef(id="led", name="LED"),
            ],
            dimensions="6800x800x2400mm",
            interactions=[
                EntityRef(id="touch-screen", name="触摸互动"),
                EntityRef(id="quiz", name="问答互动"),
            ],
            supplier=EntityRef(id="shengjing", name="生境科普"),
            project=EntityRef(id="hewan-2024", name="河湾自然博物馆生命展厅"),
            owner=EntityRef(id="hewan-owner", name="河湾自然博物馆"),
            project_year=2024,
            status="已落地",
            review_status="已审核",
            description="以分层人体模型和触摸问答展示循环、呼吸、消化系统之间的协同关系。",
            tags=["生命科学", "触摸互动", "家庭观众", "中预算"],
            media_assets=[
                MediaAsset(
                    id="human-body-render",
                    type="image",
                    name="人体互动墙",
                    url="https://picsum.photos/seed/exhibit-body/900/600",
                )
            ],
            documents=[],
            related_exhibit_ids=["brainwave-focus"],
        ),
        ExhibitResponse(
            id="solar-grid",
            name="太阳能微电网沙盘",
            category="能源科技",
            theme=EntityRef(id="new-energy", name="新能源"),
            venue_type="产业科技馆",
            budget_min=550000,
            budget_max=900000,
            materials=[
                EntityRef(id="solar-panel", name="太阳能板"),
                EntityRef(id="led", name="LED"),
                EntityRef(id="model", name="模型"),
            ],
            dimensions="5200x3200x1600mm",
            interactions=[
                EntityRef(id="slider", name="滑杆调节"),
                EntityRef(id="digital-screen", name="数字屏幕"),
            ],
            supplier=EntityRef(id="yuanchuang", name="源创科教"),
            project=EntityRef(id="yungu-2025", name="云谷未来产业馆"),
            owner=EntityRef(id="yungu-owner", name="云谷产业园"),
            project_year=2025,
            status="概念方案",
            review_status="草稿",
            description="观众调节日照、储能和负载参数，观察微电网在不同场景下的供能策略。",
            tags=["新能源", "沙盘", "参数调节", "中高预算"],
            media_assets=[
                MediaAsset(
                    id="solar-grid-render",
                    type="image",
                    name="微电网沙盘",
                    url="https://picsum.photos/seed/exhibit-solar/900/600",
                )
            ],
            documents=[],
            related_exhibit_ids=["recycling-line"],
        ),
        ExhibitResponse(
            id="high-speed-rail",
            name="高铁调度指挥舱",
            category="交通科技",
            theme=EntityRef(id="transportation", name="交通科技"),
            venue_type="交通主题馆",
            budget_min=700000,
            budget_max=1200000,
            materials=[
                EntityRef(id="train-model", name="列车模型"),
                EntityRef(id="control-console", name="控制台"),
                EntityRef(id="led", name="LED"),
            ],
            dimensions="7600x2800x2400mm",
            interactions=[
                EntityRef(id="dispatch-game", name="调度游戏"),
                EntityRef(id="digital-screen", name="数字屏幕"),
            ],
            supplier=EntityRef(id="tracklab", name="轨迹实验室"),
            project=EntityRef(id="linhai-2025", name="临海航空航天科普中心"),
            owner=EntityRef(id="linhai-owner", name="临海科普中心"),
            project_year=2025,
            status="制作中",
            review_status="待审核",
            description="通过列车模型、信号灯和调度屏模拟高铁线路运行，让观众完成发车、避让和准点挑战。",
            tags=["交通科技", "调度互动", "高预算", "多人协作"],
            media_assets=[
                MediaAsset(
                    id="rail-dispatch-render",
                    type="image",
                    name="高铁调度舱",
                    url="https://picsum.photos/seed/exhibit-rail/900/600",
                )
            ],
            documents=[],
            related_exhibit_ids=["wind-tunnel"],
        ),
        ExhibitResponse(
            id="brainwave-focus",
            name="脑电专注力挑战",
            category="生命科学",
            theme=EntityRef(id="brain-science", name="脑科学"),
            venue_type="自然博物馆",
            budget_min=380000,
            budget_max=680000,
            materials=[
                EntityRef(id="eeg-headset", name="脑电头环"),
                EntityRef(id="display", name="显示屏"),
                EntityRef(id="acrylic", name="亚克力"),
            ],
            dimensions="3600x2200x2100mm",
            interactions=[
                EntityRef(id="biofeedback", name="生物反馈"),
                EntityRef(id="competition", name="竞赛互动"),
            ],
            supplier=EntityRef(id="shengjing", name="生境科普"),
            project=EntityRef(id="hewan-2024", name="河湾自然博物馆生命展厅"),
            owner=EntityRef(id="hewan-owner", name="河湾自然博物馆"),
            project_year=2024,
            status="概念方案",
            review_status="草稿",
            description="利用脑电头环采集专注度信号，驱动小球竞速和屏幕反馈，解释注意力与神经活动。",
            tags=["脑科学", "生物反馈", "竞赛互动", "中预算"],
            media_assets=[
                MediaAsset(
                    id="brainwave-render",
                    type="image",
                    name="专注力挑战台",
                    url="https://picsum.photos/seed/exhibit-brain/900/600",
                )
            ],
            documents=[],
            related_exhibit_ids=["human-body"],
        ),
    ]
)


class ExhibitRepository:
    def __init__(self, exhibits: list[ExhibitResponse] | None = None):
        self._exhibits = list(exhibits or seed_exhibits)
        self._deleted_ids: set[str] = set()
        self._audit_logs: list[AuditLogEntry] = []
        self._document_extraction_suggestions: dict[str, DocumentExtractionSuggestionRecord] = {}

    def get_exhibit(self, exhibit_id: str) -> ExhibitResponse | None:
        if exhibit_id in self._deleted_ids:
            return None
        return next((item for item in self._exhibits if item.id == exhibit_id), None)

    def create_exhibit(self, exhibit: ExhibitResponse) -> ExhibitResponse:
        if self.get_exhibit(exhibit.id) is not None:
            raise ValueError("duplicate_exhibit_id")
        self._deleted_ids.discard(exhibit.id)
        self._exhibits.append(exhibit)
        return exhibit

    def update_exhibit(self, exhibit_id: str, exhibit: ExhibitResponse) -> ExhibitResponse | None:
        if exhibit_id in self._deleted_ids:
            return None
        for index, current in enumerate(self._exhibits):
            if current.id == exhibit_id:
                updated = exhibit.model_copy(update={"id": exhibit_id})
                self._exhibits[index] = updated
                return updated
        return None

    def delete_exhibit(self, exhibit_id: str) -> bool:
        if self.get_exhibit(exhibit_id) is None:
            return False
        self._deleted_ids.add(exhibit_id)
        return True

    def add_audit_log(
        self,
        *,
        actor_role: str,
        action: str,
        resource_type: str,
        resource_id: str,
        summary: str,
    ) -> AuditLogEntry:
        entry = AuditLogEntry(
            id=f"audit-{len(self._audit_logs) + 1}",
            actor_role=actor_role,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            summary=summary,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._audit_logs.append(entry)
        return entry

    def list_audit_logs(
        self,
        limit: int = 100,
        action: str | None = None,
        resource_id: str | None = None,
    ) -> list[AuditLogEntry]:
        logs = self._audit_logs
        if action:
            logs = [entry for entry in logs if entry.action == action]
        if resource_id:
            logs = [entry for entry in logs if entry.resource_id == resource_id]
        return list(reversed(logs[-limit:]))

    def upsert_document_extraction_suggestion(
        self,
        *,
        exhibit: ExhibitResponse,
        document: DocumentAsset,
        suggestion: Any,
    ) -> DocumentExtractionSuggestionRecord:
        now = datetime.now(timezone.utc).isoformat()
        existing = self._document_extraction_suggestions.get(document.id)
        record = DocumentExtractionSuggestionRecord(
            id=existing.id if existing else f"doc-suggestion-{document.id}",
            exhibit_id=exhibit.id,
            exhibit_name=exhibit.name,
            document_id=document.id,
            file_name=document.name,
            status="pending",
            suggestion=suggestion,
            created_at=existing.created_at if existing else now,
            updated_at=now,
        )
        self._document_extraction_suggestions[document.id] = record
        return record

    def list_document_extraction_suggestions(
        self,
        *,
        status: str | None = None,
        exhibit_id: str | None = None,
        limit: int = 100,
    ) -> list[DocumentExtractionSuggestionRecord]:
        records = list(self._document_extraction_suggestions.values())
        if status:
            records = [item for item in records if item.status == status]
        if exhibit_id:
            records = [item for item in records if item.exhibit_id == exhibit_id]
        records.sort(key=lambda item: item.updated_at, reverse=True)
        return records[:limit]

    def list_exhibits(
        self,
        keyword: str | None = None,
        venue_type: str | None = None,
        category: str | None = None,
        theme: str | None = None,
        project_id: str | None = None,
        owner: str | None = None,
        supplier: str | None = None,
        tag: str | None = None,
        material: str | None = None,
        interaction: str | None = None,
        status: str | None = None,
        review_status: str | None = None,
        budget_min: int | None = None,
        budget_max: int | None = None,
    ) -> list[ExhibitResponse]:
        return [
            item
            for item in self._exhibits
            if item.id not in self._deleted_ids
            if self._matches(
                item,
                keyword=keyword,
                venue_type=venue_type,
                category=category,
                theme=theme,
                project_id=project_id,
                owner=owner,
                supplier=supplier,
                tag=tag,
                material=material,
                interaction=interaction,
                status=status,
                review_status=review_status,
                budget_min=budget_min,
                budget_max=budget_max,
            )
        ]

    def _matches(
        self,
        item: ExhibitResponse,
        keyword: str | None,
        venue_type: str | None,
        category: str | None,
        theme: str | None,
        project_id: str | None,
        owner: str | None,
        supplier: str | None,
        tag: str | None,
        material: str | None,
        interaction: str | None,
        status: str | None,
        review_status: str | None,
        budget_min: int | None,
        budget_max: int | None,
    ) -> bool:
        if keyword:
            text = " ".join(
                [
                    item.name,
                    item.category,
                    item.theme.name,
                    item.venue_type,
                    item.owner.name,
                    item.supplier.name,
                    item.description,
                    *[material.name for material in item.materials],
                    *[interaction.name for interaction in item.interactions],
                    *item.tags,
                ]
            ).lower()
            if keyword.lower() not in text:
                return False
        if venue_type and item.venue_type != venue_type:
            return False
        if category and item.category != category:
            return False
        if theme and item.theme.name != theme:
            return False
        if project_id and item.project.id != project_id:
            return False
        if owner and owner not in (item.owner.id, item.owner.name):
            return False
        if supplier and supplier not in (item.supplier.id, item.supplier.name):
            return False
        if tag and tag not in item.tags:
            return False
        if material and material not in [entity.name for entity in item.materials]:
            return False
        if interaction and interaction not in [entity.name for entity in item.interactions]:
            return False
        if status and item.status != status:
            return False
        if review_status and item.review_status != review_status:
            return False
        if budget_min is not None and item.budget_max < budget_min:
            return False
        if budget_max is not None and item.budget_min > budget_max:
            return False
        return True


class PostgresExhibitRepository:
    def __init__(self, database_url: str, initialize: bool = True):
        self.database_url = database_url
        if initialize:
            self.initialize()

    @staticmethod
    def schema_sql() -> str:
        return """
        CREATE EXTENSION IF NOT EXISTS vector;

        CREATE TABLE IF NOT EXISTS exhibit_records (
          id TEXT PRIMARY KEY,
          payload JSONB NOT NULL,
          deleted_at TIMESTAMPTZ,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_exhibit_records_payload
          ON exhibit_records USING GIN (payload);

        ALTER TABLE exhibit_records
          ADD COLUMN IF NOT EXISTS embedding vector(1536);

        CREATE TABLE IF NOT EXISTS owners (
          id TEXT PRIMARY KEY,
          name TEXT NOT NULL UNIQUE,
          description TEXT,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE IF NOT EXISTS projects (
          id TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          owner_id TEXT NOT NULL REFERENCES owners(id),
          venue_type TEXT NOT NULL,
          project_year INTEGER NOT NULL,
          location TEXT,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE IF NOT EXISTS suppliers (
          id TEXT PRIMARY KEY,
          name TEXT NOT NULL UNIQUE,
          contact_note TEXT,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE IF NOT EXISTS themes (
          id TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          category TEXT NOT NULL,
          description TEXT,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          UNIQUE (name, category)
        );

        CREATE TABLE IF NOT EXISTS materials (
          id TEXT PRIMARY KEY,
          name TEXT NOT NULL UNIQUE,
          description TEXT,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE IF NOT EXISTS interactions (
          id TEXT PRIMARY KEY,
          name TEXT NOT NULL UNIQUE,
          description TEXT,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE IF NOT EXISTS exhibits (
          id TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          category TEXT NOT NULL,
          theme_id TEXT NOT NULL REFERENCES themes(id),
          project_id TEXT NOT NULL REFERENCES projects(id),
          supplier_id TEXT NOT NULL REFERENCES suppliers(id),
          budget_min INTEGER NOT NULL CHECK (budget_min >= 0),
          budget_max INTEGER NOT NULL CHECK (budget_max >= budget_min),
          dimensions TEXT NOT NULL,
          status TEXT NOT NULL,
          review_status TEXT NOT NULL DEFAULT '待审核',
          description TEXT NOT NULL,
          tags TEXT[] NOT NULL DEFAULT '{}',
          embedding vector(1536),
          deleted_at TIMESTAMPTZ,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        ALTER TABLE exhibits
          ADD COLUMN IF NOT EXISTS review_status TEXT NOT NULL DEFAULT '待审核';

        CREATE TABLE IF NOT EXISTS exhibit_materials (
          exhibit_id TEXT NOT NULL REFERENCES exhibits(id) ON DELETE CASCADE,
          material_id TEXT NOT NULL REFERENCES materials(id),
          PRIMARY KEY (exhibit_id, material_id)
        );

        CREATE TABLE IF NOT EXISTS exhibit_interactions (
          exhibit_id TEXT NOT NULL REFERENCES exhibits(id) ON DELETE CASCADE,
          interaction_id TEXT NOT NULL REFERENCES interactions(id),
          PRIMARY KEY (exhibit_id, interaction_id)
        );

        CREATE TABLE IF NOT EXISTS media_assets (
          id TEXT PRIMARY KEY,
          exhibit_id TEXT NOT NULL REFERENCES exhibits(id) ON DELETE CASCADE,
          type TEXT NOT NULL,
          name TEXT NOT NULL,
          object_key TEXT NOT NULL,
          public_url TEXT,
          note TEXT,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE IF NOT EXISTS documents (
          id TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          file_type TEXT NOT NULL,
          object_key TEXT NOT NULL,
          source_note TEXT,
          embedding vector(1536),
          created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE IF NOT EXISTS exhibit_documents (
          exhibit_id TEXT NOT NULL REFERENCES exhibits(id) ON DELETE CASCADE,
          document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
          PRIMARY KEY (exhibit_id, document_id)
        );

        CREATE TABLE IF NOT EXISTS document_chunks (
          id TEXT PRIMARY KEY,
          exhibit_id TEXT NOT NULL REFERENCES exhibits(id) ON DELETE CASCADE,
          document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
          sequence INTEGER NOT NULL,
          text TEXT NOT NULL,
          embedding vector(1536) NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE IF NOT EXISTS exhibit_relations (
          id TEXT PRIMARY KEY,
          source_exhibit_id TEXT NOT NULL REFERENCES exhibits(id) ON DELETE CASCADE,
          target_exhibit_id TEXT NOT NULL REFERENCES exhibits(id) ON DELETE CASCADE,
          relation_type TEXT NOT NULL,
          weight NUMERIC(5, 4) NOT NULL DEFAULT 1.0,
          note TEXT,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          CHECK (source_exhibit_id <> target_exhibit_id)
        );

        CREATE INDEX IF NOT EXISTS idx_exhibits_project_id ON exhibits(project_id);
        CREATE INDEX IF NOT EXISTS idx_exhibits_theme_id ON exhibits(theme_id);
        CREATE INDEX IF NOT EXISTS idx_exhibits_supplier_id ON exhibits(supplier_id);
        CREATE INDEX IF NOT EXISTS idx_exhibit_relations_source ON exhibit_relations(source_exhibit_id);
        CREATE INDEX IF NOT EXISTS idx_exhibit_relations_target ON exhibit_relations(target_exhibit_id);
        CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id ON document_chunks(document_id);
        CREATE INDEX IF NOT EXISTS idx_document_chunks_exhibit_id ON document_chunks(exhibit_id);

        CREATE TABLE IF NOT EXISTS document_extraction_suggestions (
          id TEXT PRIMARY KEY,
          exhibit_id TEXT NOT NULL,
          exhibit_name TEXT NOT NULL,
          document_id TEXT NOT NULL UNIQUE,
          file_name TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'pending',
          suggestion JSONB NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_document_extraction_suggestions_status
          ON document_extraction_suggestions (status, updated_at DESC);

        CREATE INDEX IF NOT EXISTS idx_document_extraction_suggestions_exhibit
          ON document_extraction_suggestions (exhibit_id, updated_at DESC);

        CREATE TABLE IF NOT EXISTS search_embeddings (
          id TEXT PRIMARY KEY,
          owner_type TEXT NOT NULL,
          owner_id TEXT NOT NULL,
          chunk_id TEXT,
          text TEXT NOT NULL,
          embedding vector(1536) NOT NULL,
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_search_embeddings_owner
          ON search_embeddings (owner_type, owner_id);

        CREATE INDEX IF NOT EXISTS idx_search_embeddings_embedding
          ON search_embeddings USING ivfflat (embedding vector_cosine_ops)
          WITH (lists = 100);

        CREATE TABLE IF NOT EXISTS kg_nodes (
          id TEXT PRIMARY KEY,
          type TEXT NOT NULL,
          label TEXT NOT NULL,
          attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
          source_refs TEXT[] NOT NULL DEFAULT '{}',
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE IF NOT EXISTS kg_edges (
          id TEXT PRIMARY KEY,
          source TEXT NOT NULL,
          target TEXT NOT NULL,
          type TEXT NOT NULL,
          label TEXT NOT NULL,
          weight NUMERIC(8, 4) NOT NULL DEFAULT 1.0,
          source_refs TEXT[] NOT NULL DEFAULT '{}',
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_kg_nodes_type
          ON kg_nodes (type);

        CREATE INDEX IF NOT EXISTS idx_kg_edges_source
          ON kg_edges (source);

        CREATE INDEX IF NOT EXISTS idx_kg_edges_target
          ON kg_edges (target);

        CREATE TABLE IF NOT EXISTS audit_log_entries (
          id TEXT PRIMARY KEY,
          actor_role TEXT NOT NULL,
          action TEXT NOT NULL,
          resource_type TEXT NOT NULL,
          resource_id TEXT NOT NULL,
          summary TEXT NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_audit_log_entries_created_at
          ON audit_log_entries (created_at DESC);
        """

    def initialize(self) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(self.schema_sql())
                cursor.execute("SELECT COUNT(*) AS count FROM exhibit_records")
                row = cursor.fetchone()
                count = row["count"] if isinstance(row, Mapping) else row[0]
                if count == 0:
                    for exhibit in seed_exhibits:
                        self._insert_or_restore(cursor, exhibit)
                else:
                    self._backfill_search_embeddings(cursor)

    def _connect(self):
        import psycopg
        from psycopg.rows import dict_row

        return psycopg.connect(self.database_url, row_factory=dict_row)

    def _insert_or_restore(self, cursor: Any, exhibit: ExhibitResponse) -> None:
        provider = embedding_provider_from_env()
        exhibit_embedding = vector_literal(
            embedding_vector(embedding_text_for_exhibit(exhibit), provider=provider)
        )
        cursor.execute(
            """
            INSERT INTO exhibit_records (id, payload, embedding, deleted_at, updated_at)
            VALUES (%s, %s::jsonb, %s::vector, NULL, now())
            ON CONFLICT (id) DO UPDATE
            SET payload = EXCLUDED.payload,
                embedding = EXCLUDED.embedding,
                deleted_at = NULL,
                updated_at = now()
            """,
            (exhibit.id, exhibit.model_dump_json(), exhibit_embedding),
        )
        self._sync_search_embeddings(cursor, exhibit, exhibit_embedding, provider=provider)
        self._sync_kg_projection(cursor)

    def _sync_search_embeddings(
        self,
        cursor: Any,
        exhibit: ExhibitResponse,
        exhibit_embedding: str | None = None,
        provider: Any = None,
    ) -> None:
        cursor.execute(
            """
            DELETE FROM search_embeddings
            WHERE owner_type = %s AND owner_id = %s
            """,
            ("exhibit", exhibit.id),
        )

        exhibit_text = embedding_text_for_exhibit(exhibit)
        self._insert_search_embedding(
            cursor,
            embedding_id=f"exhibit:{exhibit.id}",
            owner_type="exhibit",
            owner_id=exhibit.id,
            chunk_id=None,
            text=exhibit_text,
            embedding=exhibit_embedding or vector_literal(embedding_vector(exhibit_text, provider=provider)),
        )

        for document in exhibit.documents:
            for chunk in document.chunks:
                chunk_text = embedding_text_for_document_chunk(exhibit, document, chunk)
                self._insert_search_embedding(
                    cursor,
                    embedding_id=f"exhibit:{exhibit.id}:chunk:{chunk.id}",
                    owner_type="exhibit",
                    owner_id=exhibit.id,
                    chunk_id=chunk.id,
                    text=chunk_text,
                    embedding=vector_literal(embedding_vector(chunk_text, provider=provider)),
                )

    def _insert_search_embedding(
        self,
        cursor: Any,
        *,
        embedding_id: str,
        owner_type: str,
        owner_id: str,
        chunk_id: str | None,
        text: str,
        embedding: str,
    ) -> None:
        cursor.execute(
            """
            INSERT INTO search_embeddings
              (id, owner_type, owner_id, chunk_id, text, embedding, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s::vector, now())
            ON CONFLICT (id) DO UPDATE
            SET text = EXCLUDED.text,
                embedding = EXCLUDED.embedding,
                updated_at = now()
            """,
            (embedding_id, owner_type, owner_id, chunk_id, text, embedding),
        )

    def _backfill_search_embeddings(self, cursor: Any) -> None:
        cursor.execute(
            """
            SELECT payload
            FROM exhibit_records
            WHERE deleted_at IS NULL
            ORDER BY created_at ASC
            """
        )
        provider = embedding_provider_from_env()
        for row in cursor.fetchall():
            self._sync_search_embeddings(cursor, self.exhibit_from_row(row), provider=provider)
        self._sync_kg_projection(cursor)

    def _list_active_exhibits_with_cursor(self, cursor: Any) -> list[ExhibitResponse]:
        cursor.execute(
            """
            SELECT payload
            FROM exhibit_records
            WHERE deleted_at IS NULL
            ORDER BY created_at ASC
            """
        )
        return [self.exhibit_from_row(row) for row in cursor.fetchall()]

    def _sync_kg_projection(self, cursor: Any) -> None:
        active_exhibits = self._list_active_exhibits_with_cursor(cursor)
        self._sync_domain_projection(cursor, active_exhibits)
        snapshot = build_exhibit_kg_snapshot(active_exhibits)

        cursor.execute("DELETE FROM kg_edges")
        cursor.execute("DELETE FROM kg_nodes")

        for node in snapshot.nodes:
            cursor.execute(
                """
                INSERT INTO kg_nodes
                  (id, type, label, attributes, source_refs, updated_at)
                VALUES (%s, %s, %s, %s::jsonb, %s, now())
                ON CONFLICT (id) DO UPDATE
                SET type = EXCLUDED.type,
                    label = EXCLUDED.label,
                    attributes = EXCLUDED.attributes,
                    source_refs = EXCLUDED.source_refs,
                    updated_at = now()
                """,
                (
                    node.id,
                    node.type,
                    node.label,
                    json.dumps(node.attributes, ensure_ascii=False),
                    node.source_refs,
                ),
            )

        for edge in snapshot.edges:
            edge_id = f"{edge.source}|{edge.type}|{edge.target}"
            cursor.execute(
                """
                INSERT INTO kg_edges
                  (id, source, target, type, label, weight, source_refs, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, now())
                ON CONFLICT (id) DO UPDATE
                SET source = EXCLUDED.source,
                    target = EXCLUDED.target,
                    type = EXCLUDED.type,
                    label = EXCLUDED.label,
                    weight = EXCLUDED.weight,
                    source_refs = EXCLUDED.source_refs,
                    updated_at = now()
                """,
                (
                    edge_id,
                    edge.source,
                    edge.target,
                    edge.type,
                    edge.label,
                    edge.weight,
                    edge.source_refs,
                ),
            )

    def _sync_domain_projection(self, cursor: Any, exhibits: list[ExhibitResponse]) -> None:
        owner_ids_by_name: dict[str, str] = {}
        supplier_ids_by_name: dict[str, str] = {}
        theme_ids_by_key: dict[tuple[str, str], str] = {}
        material_ids_by_name: dict[str, str] = {}
        interaction_ids_by_name: dict[str, str] = {}
        for exhibit in exhibits:
            owner_ids_by_name.setdefault(exhibit.owner.name, exhibit.owner.id)
            supplier_ids_by_name.setdefault(exhibit.supplier.name, exhibit.supplier.id)
            theme_ids_by_key.setdefault((exhibit.theme.name, exhibit.category), exhibit.theme.id)
            for material in exhibit.materials:
                material_ids_by_name.setdefault(material.name, material.id)
            for interaction in exhibit.interactions:
                interaction_ids_by_name.setdefault(interaction.name, interaction.id)

        for table_name in [
            "exhibit_relations",
            "document_chunks",
            "exhibit_documents",
            "exhibit_interactions",
            "exhibit_materials",
            "media_assets",
            "exhibits",
            "documents",
            "projects",
            "owners",
            "suppliers",
            "themes",
            "materials",
            "interactions",
        ]:
            cursor.execute(f"DELETE FROM {table_name}")

        inserted_owners: set[str] = set()
        inserted_suppliers: set[str] = set()
        inserted_themes: set[str] = set()
        inserted_materials: set[str] = set()
        inserted_interactions: set[str] = set()

        for exhibit in exhibits:
            owner_id = owner_ids_by_name[exhibit.owner.name]
            if owner_id in inserted_owners:
                continue
            cursor.execute(
                """
                INSERT INTO owners (id, name, updated_at)
                VALUES (%s, %s, now())
                ON CONFLICT (id) DO UPDATE
                SET name = EXCLUDED.name,
                    updated_at = now()
                """,
                (owner_id, exhibit.owner.name),
            )
            inserted_owners.add(owner_id)

        for exhibit in exhibits:
            owner_id = owner_ids_by_name[exhibit.owner.name]
            cursor.execute(
                """
                INSERT INTO projects (id, name, owner_id, venue_type, project_year, updated_at)
                VALUES (%s, %s, %s, %s, %s, now())
                ON CONFLICT (id) DO UPDATE
                SET name = EXCLUDED.name,
                    owner_id = EXCLUDED.owner_id,
                    venue_type = EXCLUDED.venue_type,
                    project_year = EXCLUDED.project_year,
                    updated_at = now()
                """,
                (
                    exhibit.project.id,
                    exhibit.project.name,
                    owner_id,
                    exhibit.venue_type,
                    exhibit.project_year,
                ),
            )

        for exhibit in exhibits:
            supplier_id = supplier_ids_by_name[exhibit.supplier.name]
            if supplier_id in inserted_suppliers:
                continue
            cursor.execute(
                """
                INSERT INTO suppliers (id, name, updated_at)
                VALUES (%s, %s, now())
                ON CONFLICT (id) DO UPDATE
                SET name = EXCLUDED.name,
                    updated_at = now()
                """,
                (supplier_id, exhibit.supplier.name),
            )
            inserted_suppliers.add(supplier_id)

        for exhibit in exhibits:
            theme_key = (exhibit.theme.name, exhibit.category)
            theme_id = theme_ids_by_key[theme_key]
            if theme_id in inserted_themes:
                continue
            cursor.execute(
                """
                INSERT INTO themes (id, name, category, updated_at)
                VALUES (%s, %s, %s, now())
                ON CONFLICT (id) DO UPDATE
                SET name = EXCLUDED.name,
                    category = EXCLUDED.category,
                    updated_at = now()
                """,
                (theme_id, exhibit.theme.name, exhibit.category),
            )
            inserted_themes.add(theme_id)

        for exhibit in exhibits:
            for material in exhibit.materials:
                material_id = material_ids_by_name[material.name]
                if material_id in inserted_materials:
                    continue
                cursor.execute(
                    """
                    INSERT INTO materials (id, name, updated_at)
                    VALUES (%s, %s, now())
                    ON CONFLICT (id) DO UPDATE
                    SET name = EXCLUDED.name,
                        updated_at = now()
                    """,
                    (material_id, material.name),
                )
                inserted_materials.add(material_id)
            for interaction in exhibit.interactions:
                interaction_id = interaction_ids_by_name[interaction.name]
                if interaction_id in inserted_interactions:
                    continue
                cursor.execute(
                    """
                    INSERT INTO interactions (id, name, updated_at)
                    VALUES (%s, %s, now())
                    ON CONFLICT (id) DO UPDATE
                    SET name = EXCLUDED.name,
                        updated_at = now()
                    """,
                    (interaction_id, interaction.name),
                )
                inserted_interactions.add(interaction_id)

        for exhibit in exhibits:
            theme_id = theme_ids_by_key[(exhibit.theme.name, exhibit.category)]
            supplier_id = supplier_ids_by_name[exhibit.supplier.name]
            cursor.execute(
                """
                INSERT INTO exhibits
                  (id, name, category, theme_id, project_id, supplier_id,
                   budget_min, budget_max, dimensions, status, review_status,
                   description, tags, embedding, deleted_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NULL, NULL, now())
                ON CONFLICT (id) DO UPDATE
                SET name = EXCLUDED.name,
                    category = EXCLUDED.category,
                    theme_id = EXCLUDED.theme_id,
                    project_id = EXCLUDED.project_id,
                    supplier_id = EXCLUDED.supplier_id,
                    budget_min = EXCLUDED.budget_min,
                    budget_max = EXCLUDED.budget_max,
                    dimensions = EXCLUDED.dimensions,
                    status = EXCLUDED.status,
                    review_status = EXCLUDED.review_status,
                    description = EXCLUDED.description,
                    tags = EXCLUDED.tags,
                    deleted_at = NULL,
                    updated_at = now()
                """,
                (
                    exhibit.id,
                    exhibit.name,
                    exhibit.category,
                    theme_id,
                    exhibit.project.id,
                    supplier_id,
                    exhibit.budget_min,
                    exhibit.budget_max,
                    exhibit.dimensions,
                    exhibit.status,
                    exhibit.review_status,
                    exhibit.description,
                    exhibit.tags,
                ),
            )
            for material in exhibit.materials:
                material_id = material_ids_by_name[material.name]
                cursor.execute(
                    """
                    INSERT INTO exhibit_materials (exhibit_id, material_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (exhibit.id, material_id),
                )
            for interaction in exhibit.interactions:
                interaction_id = interaction_ids_by_name[interaction.name]
                cursor.execute(
                    """
                    INSERT INTO exhibit_interactions (exhibit_id, interaction_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (exhibit.id, interaction_id),
                )
            for asset in exhibit.media_assets:
                cursor.execute(
                    """
                    INSERT INTO media_assets (id, exhibit_id, type, name, object_key, public_url, note)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE
                    SET exhibit_id = EXCLUDED.exhibit_id,
                        type = EXCLUDED.type,
                        name = EXCLUDED.name,
                        object_key = EXCLUDED.object_key,
                        public_url = EXCLUDED.public_url,
                        note = EXCLUDED.note
                    """,
                    (asset.id, exhibit.id, asset.type, asset.name, asset.url, asset.url, asset.note),
                )
            provider = embedding_provider_from_env()
            for document in exhibit.documents:
                document_text = embedding_text_for_document_chunk(
                    exhibit,
                    document,
                    document.chunks[0],
                ) if document.chunks else embedding_text_for_exhibit(exhibit)
                cursor.execute(
                    """
                    INSERT INTO documents (id, name, file_type, object_key, source_note, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s::vector)
                    ON CONFLICT (id) DO UPDATE
                    SET name = EXCLUDED.name,
                        file_type = EXCLUDED.file_type,
                        object_key = EXCLUDED.object_key,
                        source_note = EXCLUDED.source_note,
                        embedding = EXCLUDED.embedding
                    """,
                    (
                        document.id,
                        document.name,
                        document.file_type,
                        document.url,
                        document.source_note,
                        vector_literal(embedding_vector(document_text, provider=provider)),
                    ),
                )
                cursor.execute(
                    """
                    INSERT INTO exhibit_documents (exhibit_id, document_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (exhibit.id, document.id),
                )
                for chunk in document.chunks:
                    chunk_text = embedding_text_for_document_chunk(exhibit, document, chunk)
                    cursor.execute(
                        """
                        INSERT INTO document_chunks
                          (id, exhibit_id, document_id, sequence, text, embedding, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s::vector, now())
                        ON CONFLICT (id) DO UPDATE
                        SET exhibit_id = EXCLUDED.exhibit_id,
                            document_id = EXCLUDED.document_id,
                            sequence = EXCLUDED.sequence,
                            text = EXCLUDED.text,
                            embedding = EXCLUDED.embedding,
                            updated_at = now()
                        """,
                        (
                            chunk.id,
                            exhibit.id,
                            document.id,
                            chunk.sequence,
                            chunk.text,
                            vector_literal(embedding_vector(chunk_text, provider=provider)),
                        ),
                    )

        active_ids = {exhibit.id for exhibit in exhibits}
        for exhibit in exhibits:
            for target_id in exhibit.related_exhibit_ids:
                if target_id not in active_ids:
                    continue
                cursor.execute(
                    """
                    INSERT INTO exhibit_relations
                      (id, source_exhibit_id, target_exhibit_id, relation_type)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE
                    SET source_exhibit_id = EXCLUDED.source_exhibit_id,
                        target_exhibit_id = EXCLUDED.target_exhibit_id,
                        relation_type = EXCLUDED.relation_type
                    """,
                    (f"{exhibit.id}|similar_to|{target_id}", exhibit.id, target_id, "similar_to"),
                )

    def exhibit_from_row(self, row: Mapping[str, Any] | tuple[Any, ...]) -> ExhibitResponse:
        payload = row["payload"] if isinstance(row, Mapping) else row[0]
        if isinstance(payload, str):
            payload = json.loads(payload)
        return ExhibitResponse.model_validate(payload)

    def get_exhibit(self, exhibit_id: str) -> ExhibitResponse | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT payload
                    FROM exhibit_records
                    WHERE id = %s AND deleted_at IS NULL
                    """,
                    (exhibit_id,),
                )
                row = cursor.fetchone()
        return self.exhibit_from_row(row) if row else None

    def create_exhibit(self, exhibit: ExhibitResponse) -> ExhibitResponse:
        if self.get_exhibit(exhibit.id) is not None:
            raise ValueError("duplicate_exhibit_id")
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._insert_or_restore(cursor, exhibit)
        return exhibit

    def update_exhibit(self, exhibit_id: str, exhibit: ExhibitResponse) -> ExhibitResponse | None:
        if self.get_exhibit(exhibit_id) is None:
            return None
        updated = exhibit.model_copy(update={"id": exhibit_id})
        provider = embedding_provider_from_env()
        exhibit_embedding = vector_literal(
            embedding_vector(embedding_text_for_exhibit(updated), provider=provider)
        )
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE exhibit_records
                    SET payload = %s::jsonb,
                        embedding = %s::vector,
                        updated_at = now()
                    WHERE id = %s AND deleted_at IS NULL
                    """,
                    (updated.model_dump_json(), exhibit_embedding, exhibit_id),
                )
                self._sync_search_embeddings(cursor, updated, exhibit_embedding, provider=provider)
                self._sync_kg_projection(cursor)
        return updated

    def delete_exhibit(self, exhibit_id: str) -> bool:
        if self.get_exhibit(exhibit_id) is None:
            return False
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE exhibit_records
                    SET deleted_at = now(),
                        updated_at = now()
                    WHERE id = %s AND deleted_at IS NULL
                    """,
                    (exhibit_id,),
                )
                cursor.execute(
                    """
                    DELETE FROM search_embeddings
                    WHERE owner_type = %s AND owner_id = %s
                    """,
                    ("exhibit", exhibit_id),
                )
                self._sync_kg_projection(cursor)
        return True

    def list_exhibits(
        self,
        keyword: str | None = None,
        venue_type: str | None = None,
        category: str | None = None,
        theme: str | None = None,
        project_id: str | None = None,
        owner: str | None = None,
        supplier: str | None = None,
        tag: str | None = None,
        material: str | None = None,
        interaction: str | None = None,
        status: str | None = None,
        review_status: str | None = None,
        budget_min: int | None = None,
        budget_max: int | None = None,
    ) -> list[ExhibitResponse]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT payload
                    FROM exhibit_records
                    WHERE deleted_at IS NULL
                    ORDER BY created_at ASC
                    """
                )
                rows = cursor.fetchall()

        items = [self.exhibit_from_row(row) for row in rows]
        matcher = ExhibitRepository([])
        return [
            item
            for item in items
            if matcher._matches(
                item,
                keyword=keyword,
                venue_type=venue_type,
                category=category,
                theme=theme,
                project_id=project_id,
                owner=owner,
                supplier=supplier,
                tag=tag,
                material=material,
                interaction=interaction,
                status=status,
                review_status=review_status,
                budget_min=budget_min,
                budget_max=budget_max,
            )
        ]

    def semantic_scores(self, query: str, limit: int = 20) -> dict[str, float]:
        query_embedding = vector_literal(embedding_vector(query, provider=embedding_provider_from_env()))
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT owner_id, MAX(1 - (embedding <=> %s::vector)) AS score
                    FROM search_embeddings
                    WHERE owner_type = 'exhibit'
                    GROUP BY owner_id
                    ORDER BY score DESC
                    LIMIT %s
                    """,
                    (query_embedding, limit),
                )
                rows = cursor.fetchall()
        scores: dict[str, float] = {}
        for row in rows:
            owner_id = row["owner_id"] if isinstance(row, Mapping) else row[0]
            score = row["score"] if isinstance(row, Mapping) else row[1]
            if score is not None and float(score) > 0:
                scores[owner_id] = float(score)
        return scores

    def get_exhibit_graph(self, exhibit_id: str) -> GraphResponse:
        graph = self._get_exhibit_graph_from_domain_tables(exhibit_id)
        if graph.nodes:
            return graph
        return self._get_exhibit_graph_from_kg_projection(exhibit_id)

    def _get_exhibit_graph_from_domain_tables(self, exhibit_id: str) -> GraphResponse:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                      e.id,
                      e.name,
                      e.theme_id,
                      t.name AS theme_name,
                      e.project_id,
                      p.name AS project_name,
                      o.id AS owner_id,
                      o.name AS owner_name,
                      e.supplier_id,
                      s.name AS supplier_name
                    FROM exhibits e
                    JOIN themes t ON t.id = e.theme_id
                    JOIN projects p ON p.id = e.project_id
                    JOIN owners o ON o.id = p.owner_id
                    JOIN suppliers s ON s.id = e.supplier_id
                    WHERE e.id = %s AND e.deleted_at IS NULL
                    """,
                    (exhibit_id,),
                )
                if not hasattr(cursor, "fetchone"):
                    return GraphResponse(nodes=[], edges=[])
                center = cursor.fetchone()
                if not center:
                    return GraphResponse(nodes=[], edges=[])

                cursor.execute(
                    """
                    SELECT m.id, m.name
                    FROM exhibit_materials em
                    JOIN materials m ON m.id = em.material_id
                    WHERE em.exhibit_id = %s
                    ORDER BY m.name ASC
                    """,
                    (exhibit_id,),
                )
                material_rows = cursor.fetchall()

                cursor.execute(
                    """
                    SELECT i.id, i.name
                    FROM exhibit_interactions ei
                    JOIN interactions i ON i.id = ei.interaction_id
                    WHERE ei.exhibit_id = %s
                    ORDER BY i.name ASC
                    """,
                    (exhibit_id,),
                )
                interaction_rows = cursor.fetchall()

                cursor.execute(
                    """
                    SELECT id, name
                    FROM media_assets
                    WHERE exhibit_id = %s
                    ORDER BY name ASC
                    """,
                    (exhibit_id,),
                )
                media_rows = cursor.fetchall()

                cursor.execute(
                    """
                    SELECT d.id, d.name
                    FROM exhibit_documents ed
                    JOIN documents d ON d.id = ed.document_id
                    WHERE ed.exhibit_id = %s
                    ORDER BY d.name ASC
                    """,
                    (exhibit_id,),
                )
                document_rows = cursor.fetchall()

                cursor.execute(
                    """
                    SELECT target.id, target.name
                    FROM exhibit_relations r
                    JOIN exhibits target ON target.id = r.target_exhibit_id
                    WHERE r.source_exhibit_id = %s
                      AND r.relation_type = 'similar_to'
                      AND target.deleted_at IS NULL
                    ORDER BY target.name ASC
                    """,
                    (exhibit_id,),
                )
                outgoing_relation_rows = cursor.fetchall()

                cursor.execute(
                    """
                    SELECT source.id, source.name
                    FROM exhibit_relations r
                    JOIN exhibits source ON source.id = r.source_exhibit_id
                    WHERE r.target_exhibit_id = %s
                      AND r.relation_type = 'similar_to'
                      AND source.deleted_at IS NULL
                    ORDER BY source.name ASC
                    """,
                    (exhibit_id,),
                )
                incoming_relation_rows = cursor.fetchall()

        nodes: dict[str, GraphNode] = {}
        edges: list[GraphEdge] = []

        def add_node(node_id: str, label: str, node_type: str) -> None:
            if node_id not in nodes:
                nodes[node_id] = GraphNode(id=node_id, label=label, type=node_type)

        def add_edge(source: str, target: str, edge_type: str, label: str) -> None:
            edges.append(GraphEdge(source=source, target=target, type=edge_type, label=label))

        center_id = f"exhibit:{self._row_value(center, 'id', 0)}"
        add_node(center_id, self._row_value(center, "name", 1), "exhibit")

        single_relations = [
            (
                f"project:{self._row_value(center, 'project_id', 4)}",
                self._row_value(center, "project_name", 5),
                "project",
                "belongs_to_project",
                "所属项目",
            ),
            (
                f"owner:{self._row_value(center, 'owner_id', 6)}",
                self._row_value(center, "owner_name", 7),
                "owner",
                "owned_by",
                "业主",
            ),
            (
                f"supplier:{self._row_value(center, 'supplier_id', 8)}",
                self._row_value(center, "supplier_name", 9),
                "supplier",
                "supplied_by",
                "供应商",
            ),
            (
                f"theme:{self._row_value(center, 'theme_id', 2)}",
                self._row_value(center, "theme_name", 3),
                "theme",
                "has_theme",
                "主题",
            ),
        ]
        for target_id, label, node_type, edge_type, edge_label in single_relations:
            add_node(target_id, label, node_type)
            add_edge(center_id, target_id, edge_type, edge_label)

        for row in material_rows:
            target_id = f"material:{self._row_value(row, 'id', 0)}"
            add_node(target_id, self._row_value(row, "name", 1), "material")
            add_edge(center_id, target_id, "uses_material", "使用材料")

        for row in interaction_rows:
            target_id = f"interaction:{self._row_value(row, 'id', 0)}"
            add_node(target_id, self._row_value(row, "name", 1), "interaction")
            add_edge(center_id, target_id, "has_interaction", "交互方式")

        for row in media_rows:
            target_id = f"media_asset:{self._row_value(row, 'id', 0)}"
            add_node(target_id, self._row_value(row, "name", 1), "media_asset")
            add_edge(center_id, target_id, "has_media", "媒体资产")

        for row in document_rows:
            target_id = f"document:{self._row_value(row, 'id', 0)}"
            add_node(target_id, self._row_value(row, "name", 1), "document")
            add_edge(center_id, target_id, "has_document", "文档资料")

        for row in outgoing_relation_rows:
            target_id = f"exhibit:{self._row_value(row, 'id', 0)}"
            add_node(target_id, self._row_value(row, "name", 1), "exhibit")
            add_edge(center_id, target_id, "similar_to", "相似展项")

        for row in incoming_relation_rows:
            source_id = f"exhibit:{self._row_value(row, 'id', 0)}"
            add_node(source_id, self._row_value(row, "name", 1), "exhibit")
            add_edge(source_id, center_id, "similar_to", "相似展项")

        return GraphResponse(nodes=list(nodes.values()), edges=edges)

    def _get_exhibit_graph_from_kg_projection(self, exhibit_id: str) -> GraphResponse:
        center_id = f"exhibit:{exhibit_id}"
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT source, target, label, type
                    FROM kg_edges
                    WHERE source = %s OR target = %s
                    ORDER BY
                      CASE WHEN source = %s THEN 0 ELSE 1 END,
                      type ASC,
                      target ASC,
                      source ASC
                    """,
                    (center_id, center_id, center_id),
                )
                edge_rows = cursor.fetchall()

                node_ids = {center_id}
                ordered_node_ids = [center_id]
                for row in edge_rows:
                    source = row["source"] if isinstance(row, Mapping) else row[0]
                    target = row["target"] if isinstance(row, Mapping) else row[1]
                    for node_id in (source, target):
                        if node_id not in node_ids:
                            node_ids.add(node_id)
                            ordered_node_ids.append(node_id)

                cursor.execute(
                    """
                    SELECT id, label, type
                    FROM kg_nodes
                    WHERE id = ANY(%s)
                    ORDER BY id ASC
                    """,
                    (list(node_ids),),
                )
                node_rows = cursor.fetchall()

        nodes_by_id = {
            self._kg_node_id(row): GraphNode(
                id=self._kg_node_id(row),
                label=self._kg_node_label(row),
                type=self._kg_node_type(row),
            )
            for row in node_rows
        }
        return GraphResponse(
            nodes=[nodes_by_id[node_id] for node_id in ordered_node_ids if node_id in nodes_by_id],
            edges=[
                GraphEdge(
                    source=row["source"] if isinstance(row, Mapping) else row[0],
                    target=row["target"] if isinstance(row, Mapping) else row[1],
                    label=row["label"] if isinstance(row, Mapping) else row[2],
                    type=row["type"] if isinstance(row, Mapping) else row[3],
                )
                for row in edge_rows
            ],
        )

    def get_kg_snapshot(self) -> KGSnapshot:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, type, label, attributes, source_refs
                    FROM kg_nodes
                    ORDER BY id ASC
                    """
                )
                node_rows = cursor.fetchall()

                cursor.execute(
                    """
                    SELECT source, target, type, label, weight, source_refs
                    FROM kg_edges
                    ORDER BY source ASC, type ASC, target ASC
                    """
                )
                edge_rows = cursor.fetchall()

        nodes = [
            KGNode(
                id=self._row_value(row, "id", 0),
                type=self._row_value(row, "type", 1),
                label=self._row_value(row, "label", 2),
                attributes=self._kg_attributes(self._row_value(row, "attributes", 3)),
                source_refs=self._kg_source_refs(self._row_value(row, "source_refs", 4)),
            )
            for row in node_rows
        ]
        edges = [
            KGEdge(
                source=self._row_value(row, "source", 0),
                target=self._row_value(row, "target", 1),
                type=self._row_value(row, "type", 2),
                label=self._row_value(row, "label", 3),
                weight=float(self._row_value(row, "weight", 4) or 1.0),
                source_refs=self._kg_source_refs(self._row_value(row, "source_refs", 5)),
            )
            for row in edge_rows
        ]
        adjacency: dict[str, list[str]] = {}
        for edge in edges:
            adjacency.setdefault(edge.source, []).append(edge.target)

        evidence_snapshot = build_exhibit_kg_snapshot(self.list_exhibits())
        return KGSnapshot(
            nodes=nodes,
            edges=edges,
            evidences=evidence_snapshot.evidences,
            adjacency=adjacency,
            warnings=evidence_snapshot.warnings,
        )

    @staticmethod
    def _kg_node_id(row: Mapping[str, Any] | tuple[Any, ...]) -> str:
        return row["id"] if isinstance(row, Mapping) else row[0]

    @staticmethod
    def _kg_node_label(row: Mapping[str, Any] | tuple[Any, ...]) -> str:
        return row["label"] if isinstance(row, Mapping) else row[1]

    @staticmethod
    def _kg_node_type(row: Mapping[str, Any] | tuple[Any, ...]) -> str:
        return row["type"] if isinstance(row, Mapping) else row[2]

    @staticmethod
    def _row_value(row: Mapping[str, Any] | tuple[Any, ...], key: str, index: int) -> Any:
        return row[key] if isinstance(row, Mapping) else row[index]

    @staticmethod
    def _kg_attributes(value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, str):
            return json.loads(value)
        return dict(value)

    @staticmethod
    def _kg_source_refs(value: Any) -> list[str]:
        if value is None:
            return []
        return list(value)

    def upsert_document_extraction_suggestion(
        self,
        *,
        exhibit: ExhibitResponse,
        document: DocumentAsset,
        suggestion: Any,
    ) -> DocumentExtractionSuggestionRecord:
        record_id = f"doc-suggestion-{document.id}"
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO document_extraction_suggestions
                      (id, exhibit_id, exhibit_name, document_id, file_name, status, suggestion)
                    VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
                    ON CONFLICT (document_id) DO UPDATE
                    SET exhibit_id = EXCLUDED.exhibit_id,
                        exhibit_name = EXCLUDED.exhibit_name,
                        file_name = EXCLUDED.file_name,
                        status = 'pending',
                        suggestion = EXCLUDED.suggestion,
                        updated_at = now()
                    RETURNING
                      id,
                      exhibit_id,
                      exhibit_name,
                      document_id,
                      file_name,
                      status,
                      suggestion,
                      created_at,
                      updated_at
                    """,
                    (
                        record_id,
                        exhibit.id,
                        exhibit.name,
                        document.id,
                        document.name,
                        "pending",
                        suggestion.model_dump_json(),
                    ),
                )
                row = cursor.fetchone()
        return self.document_extraction_suggestion_from_row(row)

    def list_document_extraction_suggestions(
        self,
        *,
        status: str | None = None,
        exhibit_id: str | None = None,
        limit: int = 100,
    ) -> list[DocumentExtractionSuggestionRecord]:
        conditions: list[str] = []
        params: list[Any] = []
        if status:
            conditions.append("status = %s")
            params.append(status)
        if exhibit_id:
            conditions.append("exhibit_id = %s")
            params.append(exhibit_id)
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT
                      id,
                      exhibit_id,
                      exhibit_name,
                      document_id,
                      file_name,
                      status,
                      suggestion,
                      created_at,
                      updated_at
                    FROM document_extraction_suggestions
                    {where_clause}
                    ORDER BY updated_at DESC
                    LIMIT %s
                    """,
                    (*params, limit),
                )
                rows = cursor.fetchall()
        return [self.document_extraction_suggestion_from_row(row) for row in rows]

    @staticmethod
    def document_extraction_suggestion_from_row(
        row: Mapping[str, Any] | tuple[Any, ...],
    ) -> DocumentExtractionSuggestionRecord:
        if isinstance(row, Mapping):
            suggestion = row["suggestion"]
            if isinstance(suggestion, str):
                suggestion = json.loads(suggestion)
            created_at = row["created_at"]
            updated_at = row["updated_at"]
            return DocumentExtractionSuggestionRecord(
                id=row["id"],
                exhibit_id=row["exhibit_id"],
                exhibit_name=row["exhibit_name"],
                document_id=row["document_id"],
                file_name=row["file_name"],
                status=row["status"],
                suggestion=suggestion,
                created_at=created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at),
                updated_at=updated_at.isoformat() if hasattr(updated_at, "isoformat") else str(updated_at),
            )

        suggestion = row[6]
        if isinstance(suggestion, str):
            suggestion = json.loads(suggestion)
        created_at = row[7]
        updated_at = row[8]
        return DocumentExtractionSuggestionRecord(
            id=row[0],
            exhibit_id=row[1],
            exhibit_name=row[2],
            document_id=row[3],
            file_name=row[4],
            status=row[5],
            suggestion=suggestion,
            created_at=created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at),
            updated_at=updated_at.isoformat() if hasattr(updated_at, "isoformat") else str(updated_at),
        )

    def add_audit_log(
        self,
        *,
        actor_role: str,
        action: str,
        resource_type: str,
        resource_id: str,
        summary: str,
    ) -> AuditLogEntry:
        entry_id = f"audit-{uuid.uuid4().hex}"
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO audit_log_entries
                      (id, actor_role, action, resource_type, resource_id, summary)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id, actor_role, action, resource_type, resource_id, summary, created_at
                    """,
                    (entry_id, actor_role, action, resource_type, resource_id, summary),
                )
                row = cursor.fetchone()
        return self.audit_log_from_row(row)

    def list_audit_logs(
        self,
        limit: int = 100,
        action: str | None = None,
        resource_id: str | None = None,
    ) -> list[AuditLogEntry]:
        conditions: list[str] = []
        params: list[Any] = []
        if action:
            conditions.append("action = %s")
            params.append(action)
        if resource_id:
            conditions.append("resource_id = %s")
            params.append(resource_id)
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, actor_role, action, resource_type, resource_id, summary, created_at
                    FROM audit_log_entries
                    {where_clause}
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (*params, limit),
                )
                rows = cursor.fetchall()
        return [self.audit_log_from_row(row) for row in rows]

    @staticmethod
    def audit_log_from_row(row: Mapping[str, Any] | tuple[Any, ...]) -> AuditLogEntry:
        if isinstance(row, Mapping):
            created_at = row["created_at"]
            return AuditLogEntry(
                id=row["id"],
                actor_role=row["actor_role"],
                action=row["action"],
                resource_type=row["resource_type"],
                resource_id=row["resource_id"],
                summary=row["summary"],
                created_at=created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at),
            )

        created_at = row[6]
        return AuditLogEntry(
            id=row[0],
            actor_role=row[1],
            action=row[2],
            resource_type=row[3],
            resource_id=row[4],
            summary=row[5],
            created_at=created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at),
        )


def create_repository_from_env(
    env: Mapping[str, str] | None = None,
    postgres_repository_cls: type[PostgresExhibitRepository] = PostgresExhibitRepository,
):
    source = env if env is not None else os.environ
    database_url = source.get("DATABASE_URL")
    if database_url:
        return postgres_repository_cls(database_url)
    return ExhibitRepository()


def create_repository():
    return create_repository_from_env()
