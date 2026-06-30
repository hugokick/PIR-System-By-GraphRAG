from app.repository import seed_exhibits
from app.schemas import DocumentAsset, EntityRef, ExhibitResponse, MediaAsset


space_dome_exhibit = ExhibitResponse(
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
    project=EntityRef(id="jiangbei-2023", name="江北科技馆宇宙探索剧场项目"),
    owner=EntityRef(id="jiangbei-owner", name="江北科技馆"),
    project_year=2023,
    status="已落地",
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
    related_exhibit_ids=[],
)


neo4j_demo_exhibits = [*seed_exhibits, space_dome_exhibit]
