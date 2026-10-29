from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from prometheus_fastapi_instrumentator import Instrumentator

from app.database.connection import ensure_schema
from app.services.uso_service import registrar_si_corresponde


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_schema()
    yield

from app.routers import formularios
from app.routers import convocatorias
from app.routers import documentos
from app.routers import chunks
from app.routers import auth
from app.routers import investigadores
from app.routers import proyectos
from app.routers import usuarios
from app.routers import perfil
from app.routers import alertas
from app.routers import analisis
from app.routers import uso


app = FastAPI(
    title="Interfascia API",
    version="1.0.0",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Métricas de uso (RF006-08): si la request es una funcionalidad contada, agrega el
# registro como tarea en segundo plano de la respuesta (corre después de enviarla, así
# no suma latencia). registrar_si_corresponde nunca lanza; el try es por las dudas, para
# que registrar jamás cambie la respuesta. Las excepciones de la ruta se propagan igual.
@app.middleware("http")
async def registrar_uso(request: Request, call_next):
    response = await call_next(request)
    try:
        registrar_si_corresponde(request, response)
    except Exception as error:
        print(f"[USO] Error al registrar el uso: {error}")
    return response


app.include_router(convocatorias.router)
app.include_router(documentos.router)
app.include_router(chunks.router)
app.include_router(auth.router)
app.include_router(formularios.router)
app.include_router(investigadores.router)
app.include_router(proyectos.router)
app.include_router(usuarios.router)
app.include_router(perfil.router)
app.include_router(alertas.router)
app.include_router(alertas.router_admin)
app.include_router(analisis.router)
app.include_router(uso.router_admin)

# Métricas para Prometheus/Grafana (requests, latencia, errores por ruta).
# /metrics no se publica: el proxy de Next lo bloquea y Prometheus entra por la red de Docker.
Instrumentator(excluded_handlers=["/metrics"]).instrument(app).expose(app, include_in_schema=False)
app.include_router(relacionar.router)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    schema = openapi_schema["components"]["schemas"][
        "Body_crear_formulario_job_formularios_jobs_post"
    ]

    schema["properties"]["documentos"]["items"] = {
        "type": "string",
        "format": "binary"
    }

    app.openapi_schema = openapi_schema

    return app.openapi_schema

app.openapi = custom_openapi


@app.get("/")
def root():
    return {
        "mensaje": "Interfascia API funcionando"
    }
