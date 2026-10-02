from fastapi import APIRouter, Query
from app.schemas.investigador import InvestigadorResponse
from app.services import investigador_service

router = APIRouter(
    prefix="/api/investigadores",
    tags=["Investigadores"]
)


@router.get("/", response_model=list[InvestigadorResponse])
def obtener_investigadores(
    buscar: str | None = None,
    limit: int = Query(50, ge=1, le=100),
):
    return investigador_service.obtener_investigadores(
        buscar=buscar,
        limit=limit,
    )
