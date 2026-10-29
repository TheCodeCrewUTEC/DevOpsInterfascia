from fastapi import APIRouter, HTTPException, Query
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


@router.get("/{investigador_id}", response_model=InvestigadorResponse)
def obtener_investigador(investigador_id: int):
    investigador = investigador_service.obtener_investigador(investigador_id)
    if investigador is None:
        raise HTTPException(status_code=404, detail="Investigador no encontrado")
    return investigador
