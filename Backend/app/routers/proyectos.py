from fastapi import APIRouter, Query
from app.schemas.proyecto import ProyectoResponse
from app.services import proyecto_service

router = APIRouter(
    prefix="/api/proyectos",
    tags=["Proyectos"]
)


@router.get("/", response_model=list[ProyectoResponse])
def obtener_proyectos(
    buscar: str | None = None,
    limit: int = Query(50, ge=1, le=100),
):
    return proyecto_service.obtener_proyectos(
        buscar=buscar,
        limit=limit,
    )
