from fastapi import FastAPI, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware

from .repository import create_repository
from .schemas import ExhibitListResponse, ExhibitResponse, ExhibitWriteRequest, GraphResponse
from .services.graph import build_exhibit_graph

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


@app.get("/api/exhibits/{exhibit_id}/graph", response_model=GraphResponse)
def get_exhibit_graph(exhibit_id: str) -> GraphResponse:
    exhibit = repository.get_exhibit(exhibit_id)
    if exhibit is None:
        raise not_found(exhibit_id)
    return build_exhibit_graph(exhibit, repository.list_exhibits())
