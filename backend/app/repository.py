import json
import os
import uuid
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from .kg.builder import build_exhibit_kg_snapshot
from .schemas import AuditLogEntry, DocumentAsset, EntityRef, ExhibitResponse, MediaAsset
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

    def list_audit_logs(self, limit: int = 100) -> list[AuditLogEntry]:
        return list(reversed(self._audit_logs[-limit:]))

    def list_exhibits(
        self,
        keyword: str | None = None,
        venue_type: str | None = None,
        category: str | None = None,
        theme: str | None = None,
        project_id: str | None = None,
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
        snapshot = build_exhibit_kg_snapshot(self._list_active_exhibits_with_cursor(cursor))

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

    def list_audit_logs(self, limit: int = 100) -> list[AuditLogEntry]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, actor_role, action, resource_type, resource_id, summary, created_at
                    FROM audit_log_entries
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (limit,),
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
