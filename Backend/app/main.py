from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app.routers import formularios
from app.routers import convocatorias
from app.routers import documentos
from app.routers import chunks
from app.routers import auth
from app.routers import investigadores
from app.routers import proyectos


app = FastAPI(
    title="Interfascia API",
    version="1.0.0"
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


app.include_router(convocatorias.router)
app.include_router(documentos.router)
app.include_router(chunks.router)
app.include_router(auth.router)
app.include_router(formularios.router)
app.include_router(investigadores.router)
app.include_router(proyectos.router)

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
