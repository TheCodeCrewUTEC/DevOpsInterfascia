from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import convocatorias
from app.routers import documentos
from app.routers import chunks

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

@app.get("/")
def root():
    return {
        "mensaje": "Interfascia API funcionando"
    }