from fastapi import FastAPI, File, Form, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from .repository import create_repository
from .schemas import (
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
    MediaAsset,
)
from .services.assets import file_extension, file_path, media_type_from_upload, save_upload_file
from .services.graphrag import answer_from_graphrag_context, search_graphrag_context
from .services.graph import build_exhibit_graph
from .services.imports import build_import_items, parse_import_file

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


def not_found(exhibit_id: str) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={
            "error": "NotFound",
            "message": "Exhibit not found",
            "details": {"id": exhibit_id},
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
) -> ExhibitImportResponse:
    rows = parse_import_file(file)
    items, errors = build_import_items(rows)
    imported: list[ExhibitResponse] = []

    if commit and not errors:
        for item in items:
            existing = repository.get_exhibit(item.id)
            if existing is None:
                imported.append(repository.create_exhibit(item))
            else:
                imported.append(repository.update_exhibit(item.id, item) or item)

    return ExhibitImportResponse(
        total_rows=len(rows),
        valid_rows=len(items),
        imported_count=len(imported),
        errors=errors,
        items=imported if commit and not errors else items,
    )


@app.get("/api/exhibits/{exhibit_id}", response_model=ExhibitResponse)
def get_exhibit(exhibit_id: str) -> ExhibitResponse:
    exhibit = repository.get_exhibit(exhibit_id)
    if exhibit is None:
        raise not_found(exhibit_id)
    return exhibit


@app.post("/api/exhibits", response_model=ExhibitResponse, status_code=status.HTTP_201_CREATED)
def create_exhibit(payload: ExhibitWriteRequest) -> ExhibitResponse:
    try:
        return repository.create_exhibit(payload.to_response())
    except ValueError:
        raise conflict(payload.id)


@app.put("/api/exhibits/{exhibit_id}", response_model=ExhibitResponse)
def update_exhibit(exhibit_id: str, payload: ExhibitWriteRequest) -> ExhibitResponse:
    updated = repository.update_exhibit(exhibit_id, payload.to_response())
    if updated is None:
        raise not_found(exhibit_id)
    return updated


@app.delete("/api/exhibits/{exhibit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exhibit(exhibit_id: str) -> Response:
    deleted = repository.delete_exhibit(exhibit_id)
    if not deleted:
        raise not_found(exhibit_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/api/exhibits/{exhibit_id}/assets", response_model=ExhibitResponse, status_code=status.HTTP_201_CREATED)
def upload_exhibit_asset(
    exhibit_id: str,
    asset_kind: str = Form(default="media"),
    note: str | None = Form(default=None),
    file: UploadFile = File(...),
) -> ExhibitResponse:
    exhibit = repository.get_exhibit(exhibit_id)
    if exhibit is None:
        raise not_found(exhibit_id)

    file_id, filename = save_upload_file(file)
    url = f"/api/files/{file_id}"
    if asset_kind == "document":
        document = DocumentAsset(
            id=f"document-{file_id}",
            name=filename,
            file_type=file_extension(filename),
            url=url,
            source_note=note,
        )
        updated = exhibit.model_copy(update={"documents": [*exhibit.documents, document]})
    else:
        asset = MediaAsset(
            id=f"media-{file_id}",
            type=media_type_from_upload(file),
            name=filename,
            url=url,
            note=note,
        )
        updated = exhibit.model_copy(update={"media_assets": [*exhibit.media_assets, asset]})

    return repository.update_exhibit(exhibit_id, updated) or updated


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
    if exhibit is None:
        raise not_found(exhibit_id)
    return build_exhibit_graph(exhibit, repository.list_exhibits())


@app.post("/api/graphrag/search", response_model=GraphRagSearchResponse)
def graphrag_search(payload: GraphRagSearchRequest) -> GraphRagSearchResponse:
    return search_graphrag_context(
        payload.query,
        repository.list_exhibits(),
        top_k=payload.top_k,
    )


@app.post("/api/graphrag/answer", response_model=GraphRagAnswerResponse)
def graphrag_answer(payload: GraphRagAnswerRequest) -> GraphRagAnswerResponse:
    return answer_from_graphrag_context(
        payload.query,
        repository.list_exhibits(),
        top_k=payload.top_k,
    )
