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
    EntityRef,
    ExhibitResponse,
    GraphEdge,
    GraphNode,
    GraphResponse,
    MediaAsset,
)
from .services.embeddings import (
    embedding_text_for_document_chunk,
    embedding_text_for_exhibit,
    stable_embedding,
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


class ExhibitRepository:
    def __init__(self, exhibits: list[ExhibitResponse] | None = None):
        self._exhibits = list(exhibits or seed_exhibits)
        self._deleted_ids: set[str] = set()
        self._audit_logs: list[AuditLogEntry] = []

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
        exhibit_embedding = vector_literal(stable_embedding(embedding_text_for_exhibit(exhibit)))
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
        self._sync_search_embeddings(cursor, exhibit, exhibit_embedding)
        self._sync_kg_projection(cursor)

    def _sync_search_embeddings(
        self,
        cursor: Any,
        exhibit: ExhibitResponse,
        exhibit_embedding: str | None = None,
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
            embedding=exhibit_embedding or vector_literal(stable_embedding(exhibit_text)),
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
                    embedding=vector_literal(stable_embedding(chunk_text)),
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
        for row in cursor.fetchall():
            self._sync_search_embeddings(cursor, self.exhibit_from_row(row))
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
        for table_name in [
            "exhibit_relations",
            "document_chunks",
            "exhibit_documents",
            "exhibit_interactions",
            "exhibit_materials",
            "media_assets",
            "exhibits",
            "documents",
        ]:
            cursor.execute(f"DELETE FROM {table_name}")

        for exhibit in exhibits:
            cursor.execute(
                """
                INSERT INTO owners (id, name, updated_at)
                VALUES (%s, %s, now())
                ON CONFLICT (id) DO UPDATE
                SET name = EXCLUDED.name,
                    updated_at = now()
                """,
                (exhibit.owner.id, exhibit.owner.name),
            )
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
                    exhibit.owner.id,
                    exhibit.venue_type,
                    exhibit.project_year,
                ),
            )
            cursor.execute(
                """
                INSERT INTO suppliers (id, name, updated_at)
                VALUES (%s, %s, now())
                ON CONFLICT (id) DO UPDATE
                SET name = EXCLUDED.name,
                    updated_at = now()
                """,
                (exhibit.supplier.id, exhibit.supplier.name),
            )
            cursor.execute(
                """
                INSERT INTO themes (id, name, category, updated_at)
                VALUES (%s, %s, %s, now())
                ON CONFLICT (id) DO UPDATE
                SET name = EXCLUDED.name,
                    category = EXCLUDED.category,
                    updated_at = now()
                """,
                (exhibit.theme.id, exhibit.theme.name, exhibit.category),
            )
            for material in exhibit.materials:
                cursor.execute(
                    """
                    INSERT INTO materials (id, name, updated_at)
                    VALUES (%s, %s, now())
                    ON CONFLICT (id) DO UPDATE
                    SET name = EXCLUDED.name,
                        updated_at = now()
                    """,
                    (material.id, material.name),
                )
            for interaction in exhibit.interactions:
                cursor.execute(
                    """
                    INSERT INTO interactions (id, name, updated_at)
                    VALUES (%s, %s, now())
                    ON CONFLICT (id) DO UPDATE
                    SET name = EXCLUDED.name,
                        updated_at = now()
                    """,
                    (interaction.id, interaction.name),
                )

        for exhibit in exhibits:
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
                    exhibit.theme.id,
                    exhibit.project.id,
                    exhibit.supplier.id,
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
                cursor.execute(
                    """
                    INSERT INTO exhibit_materials (exhibit_id, material_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (exhibit.id, material.id),
                )
            for interaction in exhibit.interactions:
                cursor.execute(
                    """
                    INSERT INTO exhibit_interactions (exhibit_id, interaction_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (exhibit.id, interaction.id),
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
                        vector_literal(stable_embedding(document_text)),
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
                            vector_literal(stable_embedding(chunk_text)),
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
        exhibit_embedding = vector_literal(stable_embedding(embedding_text_for_exhibit(updated)))
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
                self._sync_search_embeddings(cursor, updated, exhibit_embedding)
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
        query_embedding = vector_literal(stable_embedding(query))
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
