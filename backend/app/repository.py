from .schemas import DocumentAsset, EntityRef, ExhibitResponse, MediaAsset


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


class ExhibitRepository:
    def __init__(self, exhibits: list[ExhibitResponse] | None = None):
        self._exhibits = list(exhibits or seed_exhibits)
        self._deleted_ids: set[str] = set()

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

    def list_exhibits(
        self,
        keyword: str | None = None,
        venue_type: str | None = None,
        category: str | None = None,
        theme: str | None = None,
        material: str | None = None,
        interaction: str | None = None,
        status: str | None = None,
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
                material=material,
                interaction=interaction,
                status=status,
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
        material: str | None,
        interaction: str | None,
        status: str | None,
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
        if material and material not in [entity.name for entity in item.materials]:
            return False
        if interaction and interaction not in [entity.name for entity in item.interactions]:
            return False
        if status and item.status != status:
            return False
        if budget_min is not None and item.budget_max < budget_min:
            return False
        if budget_max is not None and item.budget_min > budget_max:
            return False
        return True
