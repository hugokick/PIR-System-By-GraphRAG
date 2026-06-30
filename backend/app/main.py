from collections.abc import Callable

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from .repository import create_repository
from .neo4j_demo.service import create_neo4j_demo_graph_service
from .schemas import (
    AuditLogListResponse,
    AuthLoginRequest,
    AuthLoginResponse,
    AuthUser,
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
)
from .services.assets import file_extension, file_path, media_type_from_upload, save_upload_file
from .services.auth import authenticate_demo_user, issue_access_token, verify_access_token
from .services.documents import extract_document_chunks
from .services.graphrag import answer_from_graphrag_context, search_graphrag_context
from .services.hybrid_search import search_hybrid_exhibits
from .services.imports import build_import_items, build_import_template_xlsx, parse_import_file

app = FastAPI(
    title="Exhibit Atlas API",
    description="展项图鉴查询 MVP 后端 API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "exhibit-atlas-api"}


@app.get("/api/exhibits", response_model=ExhibitListResponse)
def list_exhibits(
    keyword: str | None = None,
    venue_type: str | None = None,
    category: str | None = None,
    theme: str | None = None,
    material: str | None = None,
    interaction: str | None = None,
    status: str | None = None,
    budget_min: int | None = Query(default=None, ge=0),
    budget_max: int | None = Query(default=None, ge=0),
) -> ExhibitListResponse:
    items = repository.list_exhibits(
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
    return ExhibitListResponse(total=len(items), items=items)


@app.post("/api/exhibits/import", response_model=ExhibitImportResponse)
def import_exhibits(
    commit: bool = Form(default=False),
    file: UploadFile = File(...),
    role: str = Depends(require_roles("admin", "editor")),
) -> ExhibitImportResponse:
    rows = parse_import_file(file)
    items, errors = build_import_items(rows)
    imported: list[ExhibitResponse] = []

    if commit and not errors:
        for item in items:
            existing = repository.get_exhibit(item.id)
            if existing is None:
                imported.append(repository.create_exhibit(item))
                write_audit(role, "import_create_exhibit", item.id, f"Imported exhibit {item.id}")
            else:
                imported.append(repository.update_exhibit(item.id, item) or item)
                write_audit(role, "import_update_exhibit", item.id, f"Updated exhibit {item.id} from import")

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
    try:
        created = repository.create_exhibit(payload.to_response())
        write_audit(role, "create_exhibit", created.id, f"Created exhibit {created.id}")
        return created
    except ValueError:
        raise conflict(payload.id)


@app.put("/api/exhibits/{exhibit_id}", response_model=ExhibitResponse)
def update_exhibit(
    exhibit_id: str,
    payload: ExhibitWriteRequest,
    role: str = Depends(require_roles("admin", "editor")),
) -> ExhibitResponse:
    updated = repository.update_exhibit(exhibit_id, payload.to_response())
    if updated is None:
        raise not_found(exhibit_id)
    write_audit(role, "update_exhibit", exhibit_id, f"Updated exhibit {exhibit_id}")
    return updated


@app.delete("/api/exhibits/{exhibit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exhibit(
    exhibit_id: str,
    role: str = Depends(require_roles("admin")),
) -> Response:
    deleted = repository.delete_exhibit(exhibit_id)
    if not deleted:
        raise not_found(exhibit_id)
    write_audit(role, "delete_exhibit", exhibit_id, f"Deleted exhibit {exhibit_id}")
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
            chunks=extract_document_chunks(document_id, path, extension) if path else [],
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

    saved = repository.update_exhibit(exhibit_id, updated) or updated
    write_audit(role, audit_action, exhibit_id, f"Uploaded {filename} to exhibit {exhibit_id}")
    return saved


@app.get("/api/admin/audit-logs", response_model=AuditLogListResponse)
def list_audit_logs(
    limit: int = Query(default=100, ge=1, le=500),
    role: str = Depends(require_roles("admin")),
) -> AuditLogListResponse:
    logs = repository.list_audit_logs(limit=limit)
    return AuditLogListResponse(total=len(logs), items=logs)


@app.get("/api/files/{file_id}")
def download_file(file_id: str) -> FileResponse:
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
    return FileResponse(path)


@app.get("/api/exhibits/{exhibit_id}/graph", response_model=GraphResponse)
def get_exhibit_graph(exhibit_id: str) -> GraphResponse:
    exhibit = repository.get_exhibit(exhibit_id)
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
    )


@app.post("/api/graphrag/search", response_model=GraphRagSearchResponse)
def graphrag_search(payload: GraphRagSearchRequest) -> GraphRagSearchResponse:
    return search_graphrag_context(
        payload.query,
        repository.list_exhibits(),
        top_k=payload.top_k,
        filters=payload.filters,
    )


@app.post("/api/graphrag/answer", response_model=GraphRagAnswerResponse)
def graphrag_answer(payload: GraphRagAnswerRequest) -> GraphRagAnswerResponse:
    return answer_from_graphrag_context(
        payload.query,
        repository.list_exhibits(),
        top_k=payload.top_k,
        filters=payload.filters,
    )
