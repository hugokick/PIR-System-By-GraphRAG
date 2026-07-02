import os
import csv
from io import StringIO
from collections.abc import Callable

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from .ai.document_extraction import (
    DocumentExtractionInput,
    DocumentExtractionResult,
    DocumentTextInput,
    extract_document_suggestions,
)
from .kg.recommendations import (
    DocumentChunkRef,
    RecommendationInputs,
    RecommendationResult,
    recommend_relations,
)
from .repository import create_repository
from .neo4j_demo.service import create_neo4j_demo_graph_service
from .schemas import (
    AuditLogListResponse,
    AuthLoginRequest,
    AuthLoginResponse,
    AuthUser,
    DashboardSummaryResponse,
    DocumentAsset,
    ExhibitImportResponse,
    ExhibitListResponse,
    ExhibitResponse,
    ExhibitWriteRequest,
    GraphResponse,
    GraphRagAnswerRequest,
    GraphRagAnswerResponse,
    GraphRagSearchRequest,
    GraphRagSearchResponse,
    HybridSearchRequest,
    HybridSearchResponse,
    MediaAsset,
    RelatedExhibitsUpdateRequest,
    ReviewStatusUpdateRequest,
)
from .services.assets import (
    delete_stored_file,
    file_extension,
    file_id_from_url,
    file_path,
    media_type_from_upload,
    save_upload_file,
)
from .services.auth import authenticate_demo_user, issue_access_token, verify_access_token
from .services.dashboard import summarize_dashboard
from .services.documents import extract_document_chunks
from .services.graphrag import answer_from_graphrag_context, search_graphrag_context
from .services.hybrid_search import search_hybrid_exhibits
from .services.imports import (
    ImportFileParseError,
    build_import_items,
    build_import_template_xlsx,
    parse_import_file,
)

app = FastAPI(
    title="Exhibit Atlas API",
    description="展项图鉴查询 MVP 后端 API",
    version="0.1.0",
)

def cors_allowed_origins() -> list[str]:
    configured = os.environ.get("CORS_ALLOW_ORIGINS")
    if configured:
        return [origin.strip() for origin in configured.split(",") if origin.strip()]
    return [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5174",
        "http://localhost:5174",
    ]


app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

AUDIT_ACTION_LABELS = {
    "create_exhibit": "新增档案",
    "update_exhibit": "编辑档案",
    "delete_exhibit": "删除档案",
    "update_review_status": "更新审核",
    "upload_document": "上传资料",
    "upload_media": "上传媒体",
    "delete_document": "删除资料",
    "delete_media": "删除媒体",
    "update_exhibit_relations": "更新相似关系",
    "import_create_exhibit": "导入新增",
    "import_update_exhibit": "导入更新",
    "import_exhibits": "批量导入",
    "import_batch": "批量导入",
}

repository = create_repository()

VALID_ROLES = ("admin", "editor", "viewer")


def not_found(exhibit_id: str) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={
            "error": "NotFound",
            "message": "Exhibit not found",
            "details": {"id": exhibit_id},
        },
    )


def forbidden(required_roles: tuple[str, ...], role: str) -> HTTPException:
    return HTTPException(
        status_code=403,
        detail={
            "error": "Forbidden",
            "message": "Current role is not allowed to perform this action",
            "details": {
                "role": role,
                "required_roles": list(required_roles),
            },
        },
    )


def conflict(exhibit_id: str) -> HTTPException:
    return HTTPException(
        status_code=409,
        detail={
            "error": "Conflict",
            "message": "Exhibit id already exists",
            "details": {"id": exhibit_id},
        },
    )


def protected_delete(exhibit: ExhibitResponse) -> HTTPException:
    return HTTPException(
        status_code=409,
        detail={
            "error": "ProtectedExhibit",
            "message": "Approved or landed exhibits cannot be deleted directly",
            "details": {
                "id": exhibit.id,
                "status": exhibit.status,
                "review_status": exhibit.review_status,
            },
        },
    )


def invalid_credentials() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail={
            "error": "InvalidCredentials",
            "message": "Username or password is incorrect",
            "details": {},
        },
    )


def invalid_token() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail={
            "error": "InvalidToken",
            "message": "Authorization token is invalid",
            "details": {},
        },
    )


def role_header_auth_enabled() -> bool:
    value = os.environ.get("ALLOW_ROLE_HEADER_AUTH", "true").strip().lower()
    return value not in {"0", "false", "no", "off"}


def invalid_related_exhibits(exhibit_id: str, invalid_ids: list[str]) -> HTTPException:
    return HTTPException(
        status_code=400,
        detail={
            "error": "InvalidRelatedExhibits",
            "message": "Related exhibit ids must reference existing exhibits and cannot reference the current exhibit",
            "details": {"id": exhibit_id, "invalid_ids": invalid_ids},
        },
    )


def invalid_import_file(filename: str | None) -> HTTPException:
    return HTTPException(
        status_code=400,
        detail={
            "error": "InvalidImportFile",
            "message": "Import file could not be parsed",
            "details": {
                "filename": filename or "uploaded-file",
                "supported_formats": ["csv", "xlsx"],
            },
        },
    )


def invalid_asset_kind(asset_kind: str) -> HTTPException:
    return HTTPException(
        status_code=400,
        detail={
            "error": "InvalidAssetKind",
            "message": "Asset kind must be media or document",
            "details": {
                "asset_kind": asset_kind,
                "valid_asset_kinds": ["media", "document"],
            },
        },
    )


def normalize_related_exhibit_ids(related_exhibit_ids: list[str]) -> list[str]:
    return list(dict.fromkeys([item.strip() for item in related_exhibit_ids if item.strip()]))


def invalid_related_exhibit_ids(exhibit_id: str, related_exhibit_ids: list[str]) -> list[str]:
    return [
        item
        for item in related_exhibit_ids
        if item == exhibit_id or repository.get_exhibit(item) is None
    ]


def normalize_write_review_status(
    exhibit: ExhibitResponse,
    role: str,
    existing: ExhibitResponse | None = None,
) -> ExhibitResponse:
    if role == "admin":
        return exhibit
    if existing is None or existing.review_status in {"已审核", "已退回"}:
        review_status = "待审核"
    else:
        review_status = existing.review_status
    return exhibit.model_copy(update={"review_status": review_status})


def current_role(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_user_role: str | None = Header(default=None, alias="X-User-Role"),
) -> str:
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise invalid_token()
        user = verify_access_token(token)
        if user is None:
            raise invalid_token()
        return user.role

    if not role_header_auth_enabled():
        return "viewer"

    role = (x_user_role or "viewer").strip().lower()
    if role not in VALID_ROLES:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "InvalidRole",
                "message": "Unknown user role",
                "details": {"role": role, "valid_roles": list(VALID_ROLES)},
            },
        )
    return role


def require_roles(*roles: str) -> Callable[[str], str]:
    required_roles = tuple(roles)

    def dependency(role: str = Depends(current_role)) -> str:
        if role not in required_roles:
            raise forbidden(required_roles, role)
        return role

    return dependency


def write_audit(role: str, action: str, resource_id: str, summary: str) -> None:
    repository.add_audit_log(
        actor_role=role,
        action=action,
        resource_type="exhibit",
        resource_id=resource_id,
        summary=summary,
    )


@app.post("/api/auth/login", response_model=AuthLoginResponse)
def login(payload: AuthLoginRequest) -> AuthLoginResponse:
    user = authenticate_demo_user(payload.username, payload.password)
    if user is None:
        raise invalid_credentials()
    return AuthLoginResponse(
        access_token=issue_access_token(user),
        user=AuthUser(username=user.username, role=user.role, display_name=user.display_name),
    )


@app.get("/api/auth/me", response_model=AuthUser)
def current_auth_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> AuthUser:
    if not authorization:
        raise invalid_token()
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise invalid_token()
    user = verify_access_token(token)
    if user is None:
        raise invalid_token()
    return AuthUser(username=user.username, role=user.role, display_name=user.display_name)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "exhibit-atlas-api"}


@app.get("/api/exhibits", response_model=ExhibitListResponse)
def list_exhibits(
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
    budget_min: int | None = Query(default=None, ge=0),
    budget_max: int | None = Query(default=None, ge=0),
) -> ExhibitListResponse:
    items = repository.list_exhibits(
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
    return ExhibitListResponse(total=len(items), items=items)


@app.get("/api/dashboard/summary", response_model=DashboardSummaryResponse)
def dashboard_summary(
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
    budget_min: int | None = Query(default=None, ge=0),
    budget_max: int | None = Query(default=None, ge=0),
) -> DashboardSummaryResponse:
    items = repository.list_exhibits(
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
    return summarize_dashboard(items)


@app.post("/api/exhibits/import", response_model=ExhibitImportResponse)
def import_exhibits(
    commit: bool = Form(default=False),
    file: UploadFile = File(...),
    role: str = Depends(require_roles("admin", "editor")),
) -> ExhibitImportResponse:
    try:
        rows = parse_import_file(file)
    except ImportFileParseError:
        raise invalid_import_file(file.filename)
    existing_exhibit_ids = {item.id for item in repository.list_exhibits()}
    items, errors = build_import_items(rows, known_exhibit_ids=existing_exhibit_ids)
    imported: list[ExhibitResponse] = []

    if commit and not errors:
        for item in items:
            existing = repository.get_exhibit(item.id)
            if existing is None:
                exhibit = normalize_write_review_status(item, role)
                imported.append(repository.create_exhibit(exhibit))
                write_audit(role, "import_create_exhibit", exhibit.id, f"导入新增档案 {exhibit.id}")
            else:
                exhibit = normalize_write_review_status(item, role, existing)
                imported.append(repository.update_exhibit(item.id, exhibit) or exhibit)
                summary = f"导入覆盖档案 {item.id}"
                if role != "admin" and existing.review_status in {"已审核", "已退回"}:
                    summary += "，审核状态已回到待审核"
                write_audit(
                    role,
                    "import_update_exhibit",
                    item.id,
                    summary,
                )
        filename = file.filename or "uploaded-file"
        write_audit(
            role,
            "import_batch",
            filename,
            f"批量导入 {filename}: total_rows={len(rows)}, valid_rows={len(items)}, imported={len(imported)}",
        )

    return ExhibitImportResponse(
        total_rows=len(rows),
        valid_rows=len(items),
        imported_count=len(imported),
        errors=errors,
        items=imported if commit and not errors else items,
    )


@app.get("/api/exhibits/import-template")
def download_import_template() -> Response:
    return Response(
        content=build_import_template_xlsx(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": 'attachment; filename="exhibit-import-template.xlsx"',
        },
    )


@app.get("/api/exhibits/{exhibit_id}", response_model=ExhibitResponse)
def get_exhibit(exhibit_id: str) -> ExhibitResponse:
    exhibit = repository.get_exhibit(exhibit_id)
    if exhibit is None:
        raise not_found(exhibit_id)
    return exhibit


@app.post("/api/exhibits", response_model=ExhibitResponse, status_code=status.HTTP_201_CREATED)
def create_exhibit(
    payload: ExhibitWriteRequest,
    role: str = Depends(require_roles("admin", "editor")),
) -> ExhibitResponse:
    related_ids = normalize_related_exhibit_ids(payload.related_exhibit_ids)
    invalid_ids = invalid_related_exhibit_ids(payload.id, related_ids)
    if invalid_ids:
        raise invalid_related_exhibits(payload.id, invalid_ids)

    try:
        exhibit = normalize_write_review_status(
            payload.to_response().model_copy(update={"related_exhibit_ids": related_ids}),
            role,
        )
        created = repository.create_exhibit(exhibit)
        write_audit(role, "create_exhibit", created.id, f"新增档案 {created.id}")
        return created
    except ValueError:
        raise conflict(payload.id)


@app.put("/api/exhibits/{exhibit_id}", response_model=ExhibitResponse)
def update_exhibit(
    exhibit_id: str,
    payload: ExhibitWriteRequest,
    role: str = Depends(require_roles("admin", "editor")),
) -> ExhibitResponse:
    existing = repository.get_exhibit(exhibit_id)
    if existing is None:
        raise not_found(exhibit_id)

    related_ids = normalize_related_exhibit_ids(payload.related_exhibit_ids)
    invalid_ids = invalid_related_exhibit_ids(exhibit_id, related_ids)
    if invalid_ids:
        raise invalid_related_exhibits(exhibit_id, invalid_ids)

    exhibit = normalize_write_review_status(
        payload.to_response().model_copy(update={"related_exhibit_ids": related_ids}),
        role,
        existing,
    )
    updated = repository.update_exhibit(
        exhibit_id,
        exhibit,
    )
    if updated is None:
        raise not_found(exhibit_id)
    summary = f"编辑档案 {exhibit_id}"
    if role != "admin" and existing.review_status in {"已审核", "已退回"}:
        summary += "，审核状态已回到待审核"
    write_audit(role, "update_exhibit", exhibit_id, summary)
    return updated


@app.patch("/api/exhibits/{exhibit_id}/review-status", response_model=ExhibitResponse)
def update_exhibit_review_status(
    exhibit_id: str,
    payload: ReviewStatusUpdateRequest,
    role: str = Depends(require_roles("admin")),
) -> ExhibitResponse:
    exhibit = repository.get_exhibit(exhibit_id)
    if exhibit is None:
        raise not_found(exhibit_id)

    updated = exhibit.model_copy(update={"review_status": payload.review_status})
    saved = repository.update_exhibit(exhibit_id, updated) or updated
    write_audit(
        role,
        "update_review_status",
        exhibit_id,
        f"更新审核状态 {exhibit_id} 为 {payload.review_status}",
    )
    return saved


@app.patch("/api/exhibits/{exhibit_id}/related-exhibits", response_model=ExhibitResponse)
def update_exhibit_related_exhibits(
    exhibit_id: str,
    payload: RelatedExhibitsUpdateRequest,
    role: str = Depends(require_roles("admin", "editor")),
) -> ExhibitResponse:
    exhibit = repository.get_exhibit(exhibit_id)
    if exhibit is None:
        raise not_found(exhibit_id)

    related_ids = normalize_related_exhibit_ids(payload.related_exhibit_ids)
    invalid_ids = invalid_related_exhibit_ids(exhibit_id, related_ids)
    if invalid_ids:
        raise invalid_related_exhibits(exhibit_id, invalid_ids)

    updated = normalize_write_review_status(
        exhibit.model_copy(update={"related_exhibit_ids": related_ids}),
        role,
        exhibit,
    )
    saved = repository.update_exhibit(exhibit_id, updated) or updated
    summary = f"更新相似关系 {exhibit_id}: {', '.join(related_ids) if related_ids else '无'}"
    if role != "admin" and exhibit.review_status in {"已审核", "已退回"}:
        summary += "，审核状态已回到待审核"
    write_audit(
        role,
        "update_exhibit_relations",
        exhibit_id,
        summary,
    )
    return saved


@app.delete("/api/exhibits/{exhibit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exhibit(
    exhibit_id: str,
    role: str = Depends(require_roles("admin")),
) -> Response:
    exhibit = repository.get_exhibit(exhibit_id)
    if exhibit is None:
        raise not_found(exhibit_id)
    if exhibit.review_status == "已审核" or exhibit.status == "已落地":
        raise protected_delete(exhibit)

    deleted = repository.delete_exhibit(exhibit_id)
    if not deleted:
        raise not_found(exhibit_id)
    write_audit(role, "delete_exhibit", exhibit_id, f"删除档案 {exhibit_id}")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/api/exhibits/{exhibit_id}/assets", response_model=ExhibitResponse, status_code=status.HTTP_201_CREATED)
def upload_exhibit_asset(
    exhibit_id: str,
    asset_kind: str = Form(default="media"),
    note: str | None = Form(default=None),
    file: UploadFile = File(...),
    role: str = Depends(require_roles("admin", "editor")),
) -> ExhibitResponse:
    exhibit = repository.get_exhibit(exhibit_id)
    if exhibit is None:
        raise not_found(exhibit_id)
    if asset_kind not in {"media", "document"}:
        raise invalid_asset_kind(asset_kind)

    file_id, filename = save_upload_file(file)
    url = f"/api/files/{file_id}"
    if asset_kind == "document":
        document_id = f"document-{file_id}"
        extension = file_extension(filename)
        path = file_path(file_id)
        document = DocumentAsset(
            id=document_id,
            name=filename,
            file_type=extension,
            url=url,
            source_note=note,
            chunks=extract_document_chunks(
                document_id,
                path,
                extension,
                exhibit_id=exhibit_id,
                file_name=filename,
                source_note=note,
            )
            if path
            else [],
        )
        updated = exhibit.model_copy(update={"documents": [*exhibit.documents, document]})
        audit_action = "upload_document"
    else:
        asset = MediaAsset(
            id=f"media-{file_id}",
            type=media_type_from_upload(file),
            name=filename,
            url=url,
            note=note,
        )
        updated = exhibit.model_copy(update={"media_assets": [*exhibit.media_assets, asset]})
        audit_action = "upload_media"

    updated = normalize_write_review_status(updated, role, exhibit)
    saved = repository.update_exhibit(exhibit_id, updated) or updated
    upload_label = "上传资料" if audit_action == "upload_document" else "上传媒体"
    summary = f"{upload_label} {filename} 到档案 {exhibit_id}"
    if role != "admin" and exhibit.review_status in {"已审核", "已退回"}:
        summary += "，审核状态已回到待审核"
    write_audit(role, audit_action, exhibit_id, summary)
    return saved


@app.get(
    "/api/exhibits/{exhibit_id}/documents/{document_id}/extraction-suggestions",
    response_model=DocumentExtractionResult,
)
def get_document_extraction_suggestions(
    exhibit_id: str,
    document_id: str,
    role: str = Depends(require_roles("admin", "editor")),
) -> DocumentExtractionResult:
    exhibit = repository.get_exhibit(exhibit_id)
    if exhibit is None:
        raise not_found(exhibit_id)
    document = next((item for item in exhibit.documents if item.id == document_id), None)
    if document is None:
        raise not_found(document_id)

    return extract_document_suggestions(
        DocumentExtractionInput(
            document_id=document.id,
            file_name=document.name,
            file_type=document.file_type,
            source_note=document.source_note,
            chunks=[
                DocumentTextInput(
                    chunk_id=chunk.id,
                    text=chunk.text,
                    sequence=chunk.sequence,
                    source_locator=None,
                )
                for chunk in document.chunks
            ],
        )
    )


@app.get(
    "/api/exhibits/{exhibit_id}/relation-recommendations",
    response_model=RecommendationResult,
)
def get_exhibit_relation_recommendations(
    exhibit_id: str,
    role: str = Depends(require_roles("admin", "editor")),
) -> RecommendationResult:
    exhibit = repository.get_exhibit(exhibit_id)
    if exhibit is None:
        raise not_found(exhibit_id)

    exhibits = repository.list_exhibits()
    return recommend_relations(
        RecommendationInputs(
            target_exhibit=exhibit,
            all_exhibits=exhibits,
            snapshot=kg_snapshot_for_query(),
            document_chunks=document_chunk_refs_for_recommendations(exhibits),
        )
    )


@app.delete("/api/exhibits/{exhibit_id}/assets/{asset_id}", response_model=ExhibitResponse)
def delete_exhibit_asset(
    exhibit_id: str,
    asset_id: str,
    role: str = Depends(require_roles("admin")),
) -> ExhibitResponse:
    exhibit = repository.get_exhibit(exhibit_id)
    if exhibit is None:
        raise not_found(exhibit_id)
    if exhibit.review_status == "已审核" or exhibit.status == "已落地":
        raise protected_delete(exhibit)

    deleted_media = next((asset for asset in exhibit.media_assets if asset.id == asset_id), None)
    deleted_document = next((document for document in exhibit.documents if document.id == asset_id), None)
    next_media_assets = [asset for asset in exhibit.media_assets if asset.id != asset_id]
    next_documents = [document for document in exhibit.documents if document.id != asset_id]
    if len(next_media_assets) == len(exhibit.media_assets) and len(next_documents) == len(exhibit.documents):
        raise not_found(asset_id)

    updated = exhibit.model_copy(
        update={"media_assets": next_media_assets, "documents": next_documents}
    )
    saved = repository.update_exhibit(exhibit_id, updated) or updated
    action = "delete_document" if len(next_documents) < len(exhibit.documents) else "delete_media"
    deleted_url = deleted_document.url if deleted_document else deleted_media.url if deleted_media else ""
    file_id = file_id_from_url(deleted_url)
    if file_id:
        delete_stored_file(file_id)
    delete_label = "删除资料" if action == "delete_document" else "删除媒体"
    write_audit(role, action, exhibit_id, f"{delete_label} {asset_id} 从档案 {exhibit_id}")
    return saved


@app.get("/api/admin/audit-logs", response_model=AuditLogListResponse)
def list_audit_logs(
    limit: int = Query(default=100, ge=1, le=500),
    action: str | None = None,
    resource_id: str | None = None,
    role: str = Depends(require_roles("admin")),
) -> AuditLogListResponse:
    logs = repository.list_audit_logs(limit=limit, action=action, resource_id=resource_id)
    return AuditLogListResponse(total=len(logs), items=logs)


@app.get("/api/admin/audit-logs/export")
def export_audit_logs(
    limit: int = Query(default=500, ge=1, le=5000),
    action: str | None = None,
    resource_id: str | None = None,
    role: str = Depends(require_roles("admin")),
) -> Response:
    logs = repository.list_audit_logs(limit=limit, action=action, resource_id=resource_id)
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["日志编号", "操作者角色", "动作", "资源类型", "资源编号", "摘要", "时间"])
    for entry in logs:
        writer.writerow(
            [
                entry.id,
                entry.actor_role,
                AUDIT_ACTION_LABELS.get(entry.action, entry.action),
                entry.resource_type,
                entry.resource_id,
                entry.summary,
                entry.created_at,
            ]
        )
    content = "\ufeff" + output.getvalue()
    headers = {"Content-Disposition": 'attachment; filename="audit-logs.csv"'}
    return Response(content=content, media_type="text/csv; charset=utf-8", headers=headers)


@app.get("/api/files/{file_id}")
def download_file(file_id: str, download: bool = Query(default=False)) -> FileResponse:
    path = file_path(file_id)
    if path is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "NotFound",
                "message": "File not found",
                "details": {"id": file_id},
            },
        )
    return FileResponse(
        path,
        filename=path.name,
        content_disposition_type="attachment" if download else "inline",
    )


@app.get("/api/exhibits/{exhibit_id}/graph", response_model=GraphResponse)
def get_exhibit_graph(exhibit_id: str) -> GraphResponse:
    exhibit = repository.get_exhibit(exhibit_id)
    repository_graph_reader = getattr(repository, "get_exhibit_graph", None)
    if exhibit is not None and callable(repository_graph_reader):
        graph = repository_graph_reader(exhibit.id)
        if graph.nodes:
            return graph

    service = create_neo4j_demo_graph_service(repository.list_exhibits())
    try:
        graph = service.get_exhibit_graph(exhibit.id if exhibit else exhibit_id)
    finally:
        service.close()
    if exhibit is None and not graph.nodes:
        raise not_found(exhibit_id)
    return graph


@app.get("/api/neo4j-demo/graph", response_model=GraphResponse)
def get_neo4j_demo_graph() -> GraphResponse:
    service = create_neo4j_demo_graph_service(repository.list_exhibits())
    try:
        return service.get_demo_graph()
    finally:
        service.close()


@app.post("/api/search/hybrid", response_model=HybridSearchResponse)
def hybrid_search(payload: HybridSearchRequest) -> HybridSearchResponse:
    return search_hybrid_exhibits(
        payload.query,
        repository.list_exhibits(),
        limit=payload.limit,
        filters=payload.filters,
        semantic_scores=semantic_scores_for_query(payload.query, payload.limit),
    )


def semantic_scores_for_query(query: str, limit: int) -> dict[str, float]:
    scorer = getattr(repository, "semantic_scores", None)
    if not callable(scorer):
        return {}
    try:
        return scorer(query, limit=max(limit * 5, 20))
    except Exception:
        return {}


def kg_snapshot_for_query():
    snapshot_reader = getattr(repository, "get_kg_snapshot", None)
    if not callable(snapshot_reader):
        return None
    try:
        return snapshot_reader()
    except Exception:
        return None


def document_chunk_refs_for_recommendations(exhibits: list[ExhibitResponse]) -> list[DocumentChunkRef]:
    return [
        DocumentChunkRef(
            exhibit_id=exhibit.id,
            document_id=document.id,
            chunk_id=chunk.id,
            text=chunk.text,
        )
        for exhibit in exhibits
        for document in exhibit.documents
        for chunk in document.chunks
        if chunk.id
    ]


@app.post("/api/graphrag/search", response_model=GraphRagSearchResponse)
def graphrag_search(payload: GraphRagSearchRequest) -> GraphRagSearchResponse:
    return search_graphrag_context(
        payload.query,
        repository.list_exhibits(),
        top_k=payload.top_k,
        filters=payload.filters,
        semantic_scores=semantic_scores_for_query(payload.query, payload.top_k),
        snapshot=kg_snapshot_for_query(),
    )


@app.post("/api/graphrag/answer", response_model=GraphRagAnswerResponse)
def graphrag_answer(payload: GraphRagAnswerRequest) -> GraphRagAnswerResponse:
    return answer_from_graphrag_context(
        payload.query,
        repository.list_exhibits(),
        top_k=payload.top_k,
        filters=payload.filters,
        semantic_scores=semantic_scores_for_query(payload.query, payload.top_k),
        snapshot=kg_snapshot_for_query(),
    )
