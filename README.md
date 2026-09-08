# Interfascia

Interfascia es un proyecto piloto orientado a facilitar la vinculación entre proyectos, inversores, fondos y capacidades de investigación en Uruguay.

El proyecto utiliza una arquitectura basada en servicios desacoplados y contenedores Docker, con el objetivo de facilitar el desarrollo, las pruebas y el despliegue del sistema.

## Tecnologías

### Frontend
- Next.js
- React
- TypeScript
- Vitest

### Backend
- Python
- FastAPI
- Uvicorn
- pytest
- Nginx

### Base de Datos
- PostgreSQL
- pgvector

### Inteligencia Artificial
- Ollama
- Mistral

### Infraestructura
- Docker
- Docker Compose

### CI/CD
- GitHub Actions

## Arquitectura

La arquitectura prevista para el proyecto está compuesta por un Frontend y un Backend, junto con los servicios de persistencia e inteligencia artificial.

Nginx forma parte del contenedor del Backend y actúa como reverse proxy delante de FastAPI/Uvicorn.

```text
                         Usuario
                            │
                            ▼
                     ┌──────────────┐
                     │   Frontend   │
                     │   Next.js    │
                     │ React/TS     │
                     └──────────────┘
                            │
                            │
                            ▼
                ┌─────────────────────────┐
                │        Backend          │
                │                         │
                │         Nginx           │
                │           │             │
                │           ▼             │
                │   FastAPI + Uvicorn     │
                └───────────┬─────────────┘
                            │
                   ┌────────┴────────┐
                   │                 │
                   ▼                 ▼
          ┌────────────────┐   ┌───────────────┐
          │ PostgreSQL     │   │    Ollama     │
          │ + pgvector     │   │   + Mistral   │
          └────────────────┘   └───────────────┘
```
## Puertos

Durante el desarrollo se utilizan actualmente:

| Servicio | Puerto |
|---|---|
| Frontend | 3000 | 3000 |
| Nginx + Backend | 8000 | 80 |
| FastAPI/Uvicorn | — | 8001 |
| PostgreSQL | 5432 | 5432 |
| Ollama | 11434 | 11434 |

### Frontend:  http://localhost:3000

### Backend: http://localhost:8000
#### Health check del Backend: http://localhost:8000/health
#### Documentación de FastAPI: http://localhost:8000/docs

*Los puertos correspondientes a PostgreSQL, Nginx y Ollama se definirán en la configuración final de la infraestructura.

## Desarrollo local

Para preparar el entorno de desarrollo consultar: SETUP.md

### Frontend

Desde la carpeta Frontend:
```text
npm ci
```
Ejecutar en modo desarrollo:
```text
npm run dev
```
Ejecutar tests:
```text
npm test
```
Construir la aplicación:
```text
npm run build
```
### Backend

Desde la carpeta Backend se recomienda utilizar un entorno virtual de Python.

Instalar las dependencias:
```text
python -m pip install -r requirements.txt
```
Ejecutar el servidor:
```text
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
Ejecutar tests:
```text
python -m pytest
```
### Docker

Para construir y levantar los servicios:
```text
docker compose up -d --build
```
Ver el estado de los contenedores:
```text
docker compose ps
```
Ver los logs:
```text
docker compose logs
```
Detener los servicios:
```text   
docker compose down
```
## Integración Continua
 
El proyecto utiliza GitHub Actions para automatizar las validaciones del código

Actualmente el pipeline realiza:

```
Push / Pull Request
        │
        ▼
GitHub Actions
        │
        ├── Frontend
        │     ├── npm ci
        │     ├── Vitest
        │     └── Next.js build
        │
        ├── Backend
        │     ├── pip install
        │     ├── pytest
        │     └── Verificación FastAPI
        │
        └── Docker
              └── Docker Compose build
```

El pipeline permite detectar errores antes de realizar un despliegue.

## Estado del proyecto

El proyecto se encuentra actualmente en etapa de desarrollo.

La arquitectura y el pipeline se implementarán progresivamente, incorporando:

- PostgreSQL
- pgvector
- Ollama
- Mistral
- Análisis de calidad de código
- Análisis de vulnerabilidades
- Registro de imágenes Docker
- Despliegue automatizado

## Autores
Proyecto Academico UTEC por estudiantes de 8vo semestre de LTI:
- Florencia Balestena
- Nicolas Dossantos
- Antonio Zito