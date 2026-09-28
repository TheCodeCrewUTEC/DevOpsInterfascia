# SETUP - Entorno de Desarrollo Interfascia

Este documento explica cómo preparar una computadora para trabajar con el proyecto **Interfascia**.

La VM utilizada para despliegue no necesita tener Node.js, npm ni Python instalados, ya que las aplicaciones se ejecutan dentro de contenedores Docker. Esta guía está dirigida a los **desarrolladores que trabajan directamente sobre el código fuente en sus computadoras**.

---

## 1. Requisitos previos

Cada desarrollador debe tener instaladas las siguientes herramientas:

| Herramienta | Versión recomendada | Uso |
|---|---|---|
| Git | 2.x o superior | Control de versiones |
| Node.js | 20.x | Desarrollo del Frontend |
| npm | Incluido con Node.js | Dependencias y scripts del Frontend |
| Python | 3.12.x | Desarrollo del Backend |
| Docker Desktop | Versión actual | Contenedores |
| Docker Compose | Incluido con Docker Desktop | Orquestación |
| Editor de código | VS Code recomendado | Desarrollo |

> **Importante:** npm se instala automáticamente junto con Node.js. No es necesario instalar npm por separado.

---

# 2. Instalar Git

Instalar Git en la computadora.

Comprobar la instalación:

```bash
git --version
````

Debe mostrar una versión de Git, por ejemplo:

```text
git version 2.x.x
```

---

# 3. Instalar Node.js

Instalar **Node.js 20.x**.

npm viene incluido con Node.js.

Comprobar la instalación:

```bash
node --version
```

```bash
npm --version
```

Ejemplo:

```text
v20.x.x
10.x.x
```

---

# 4. Instalar Python

Instalar **Python 3.12.x**.

Comprobar:

```bash
python --version
```

En algunos sistemas puede ser necesario utilizar:

```bash
python3 --version
```

---

# 5. Instalar Docker

Instalar Docker Desktop.

Comprobar:

```bash
docker --version
```

Y:

```bash
docker compose version
```

Docker Compose se utilizará para levantar los diferentes servicios del proyecto.

---

# 6. Clonar el repositorio

Clonar el repositorio:

```bash
git clone URL_DEL_REPOSITORIO
```

Ingresar al proyecto:

```bash
cd DevOpsInterfascia
```

La estructura inicial será similar a:

```text
DevOpsInterfascia/
├── Frontend/
├── Backend/
├── .github/
├── docker-compose.yml
├── .gitignore
├── .env.example
├── README.md
└── SETUP.md
```

---

# 7. Configuración del Frontend

Ingresar a la carpeta:

```bash
cd Frontend
```

Instalar las dependencias:

```bash
npm ci
```

Este comando utiliza `package-lock.json` para instalar las versiones exactas de las dependencias definidas por el proyecto.

Entre las principales tecnologías utilizadas se encuentran:

* Next.js
* React
* TypeScript
* Vitest

---

#### 7.1 Ejecutar Frontend en desarrollo

```bash
npm run dev
```

La aplicación estará disponible en:

```text
http://localhost:3000
```

---

#### 7.2 Ejecutar tests del Frontend

```bash
npm test
```

Los tests del Frontend utilizan **Vitest**.

---

#### 7.3 Construir el Frontend

```bash
npm run build
```

Este comando realiza el build de producción de Next.js.

---

# 8. Configuración del Backend

Abrir una nueva terminal y entrar a:

```bash
cd DevOpsInterfascia/Backend
```

Se recomienda utilizar un entorno virtual de Python para evitar mezclar las dependencias del proyecto con las del sistema.

---

## 8. Instalar dependencias del Backend

Con el entorno virtual activo:

```bash
python -m pip install -r requirements.txt
```

Las principales tecnologías utilizadas por el Backend son:

* Python
* FastAPI
* Uvicorn
* pytest

---

# 9. Ejecutar Backend

Desde la carpeta `Backend`:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

El Backend estará disponible en:

```text
http://localhost:8000
```

---

#### 9.1 Health Check

Para verificar que el Backend está funcionando:

```text
http://localhost:8000/health
```

---

#### 9.2 Documentación de FastAPI

FastAPI proporciona documentación automática mediante Swagger:

```text
http://localhost:8000/docs
```

---

# 10. Ejecutar tests del Backend

Desde la carpeta `Backend`:

```bash
python -m pytest
```

Actualmente el proyecto cuenta con tests básicos para verificar los endpoints principales.

El resultado esperado es similar a:

```text
collected 2 items

tests/test_main.py ..    [100%]

2 passed
```

---

# 11. Variables de entorno

Las configuraciones sensibles no deben almacenarse directamente en el repositorio.

El proyecto utilizará un archivo:

```text
.env
```

Cada desarrollador deberá crear su propio archivo `.env` a partir de:

```text
.env.example
```

Ejemplo:

```bash
cp .env.example .env
```

En Windows también puede copiarse manualmente el archivo.

> **Importante:** el archivo `.env` no debe subirse a Git.

El archivo `.env.example` sí debe mantenerse en el repositorio como referencia para los desarrolladores.

---

# 11.1 Autenticación con Keycloak

El login y el registro los maneja **Keycloak**. Las rutas `/login` y `/registro` de la app redirigen a sus pantallas y, al terminar, vuelven a la app con la sesión iniciada.

1. Generar dos secretos (uno para `AUTH_SECRET` y otro para `KEYCLOAK_FRONTEND_CLIENT_SECRET`):

```bash
node -e "console.log(require('crypto').randomBytes(32).toString('base64url'))"
```

2. Completar en el `.env` de la raíz: `AUTH_SECRET`, `KEYCLOAK_FRONTEND_CLIENT_SECRET`, `KEYCLOAK_ADMIN_PASSWORD`.

3. Levantar solo Keycloak (la primera vez importa el realm `interfascia` desde `keycloak/realm-interfascia.json`):

```bash
docker compose up -d keycloak
```

4. Para correr el frontend con `npm run dev`, copiar `Frontend/.env.example` a `Frontend/.env.local` y poner los mismos secretos.

| Servicio | URL |
|---|---|
| Consola de administración | http://localhost:8080/admin (usuario `admin`) |
| Realm de la app | http://localhost:8080/realms/interfascia |

> El realm solo se importa si todavía no existe. Si se modifica `realm-interfascia.json`, borrar el volumen para reimportarlo: `docker compose down` y `docker volume rm interfascia_keycloak_data`.

**Diseño de las pantallas.** Las pantallas de login, registro y recuperar contraseña usan el tema propio `keycloak/themes/interfascia/`, que replica el wireframe de Figma (navbar y footer de la app incluidos):

| Archivo | Qué es |
|---|---|
| `login/template.ftl` | Estructura común: navbar, tarjeta o página, footer |
| `login/login.ftl` | Formulario de inicio de sesión |
| `login/register.ftl` | Formulario de registro en dos columnas |
| `login/resources/css/interfascia.css` | Estilos (equivalentes a las clases Tailwind de la app) |
| `login/resources/js/addable-select.js` | Botón "+" de los campos con varios valores |
| `login/messages/messages_es.properties` | Textos de las pantallas |

En modo desarrollo Keycloak no cachea el tema: alcanza con guardar y recargar el navegador.

Los campos extra del registro (departamento de residencia, departamentos de actuación, celular, instituciones y roles) están definidos en el perfil de usuario dentro de `realm-interfascia.json` (componente `UserProfileProvider`). Las opciones de cada lista se editan ahí.

En el Backend, las rutas que requieren usuario usan la dependencia `obtener_usuario_actual` (o `requiere_rol("...")`) de `app/auth.py`, que valida el token de Keycloak. Ejemplo: `GET /api/auth/me`.

---

# 12. Docker Compose

El proyecto utiliza Docker Compose para ejecutar los servicios mediante contenedores.

Desde la raíz del proyecto:

```bash
docker compose up -d --build
```

Este comando:

1. Construye las imágenes necesarias.
2. Crea los contenedores.
3. Inicia los servicios en segundo plano.

---

#### 12.1 Ver el estado de los contenedores

```bash
docker compose ps
```

---

#### 12.2 Ver los logs

Para ver los logs de todos los servicios:

```bash
docker compose logs
```

Para ver solamente el Frontend:

```bash
docker compose logs frontend
```

Para ver solamente el Backend:

```bash
docker compose logs backend
```

---

#### 12.3 Detener los contenedores

```bash
docker compose down
```

---

# 13. Verificar el ambiente mediante Docker

Una vez ejecutado:

```bash
docker compose up -d --build
```

verificar el Frontend:

```text
http://localhost:3000
```

Verificar el Backend:

```text
http://localhost:8000
```

Verificar el Health Check:

```text
http://localhost:8000/health
```

Verificar la documentación de FastAPI:

```text
http://localhost:8000/docs
```

---

# 14. Tests antes de realizar un commit

Antes de subir cambios al repositorio se recomienda ejecutar las pruebas localmente.

## Frontend

Desde `Frontend`:

```bash
npm test
```

Luego:

```bash
npm run build
```

## Backend

Desde `Backend`:

```bash
python -m pytest
```

De esta forma se verifica que los cambios no rompan las funcionalidades existentes antes de realizar el `push`.

---

# 15. Flujo de trabajo con Git

Actualizar el repositorio antes de comenzar a trabajar:

```bash
git pull
```

Realizar los cambios necesarios.

Verificar los archivos modificados:

```bash
git status
```

Agregar los cambios:

```bash
git add .
```

Crear el commit:

```bash
git commit -m "Descripción del cambio"
```

Subir los cambios:

```bash
git push
```

---

# 16. GitHub Actions

Después de realizar un `git push`, GitHub Actions ejecutará automáticamente el pipeline de integración continua.

Actualmente el pipeline realiza validaciones sobre:

### Frontend

```text
npm ci
    ↓
Vitest
    ↓
Next.js build
```

### Backend

```text
pip install
    ↓
pytest
    ↓
Verificación FastAPI
```

### Docker

```text
Frontend + Backend
        ↓
Docker Compose build
```

Si alguna de las etapas falla, el pipeline será marcado como fallido.

Esto permite detectar problemas antes de continuar con el proceso de despliegue.

---

# 17. Archivos que NO deben subirse a Git

## Frontend

No subir:

```text
node_modules/
.next/
.env
.env.local
```

## Backend

No subir:

```text
.venv/
__pycache__/
.pytest_cache/
.env
```

Estos archivos y carpetas deben estar incluidos en `.gitignore`.

---

# 18. Estructura esperada

La estructura del proyecto debe ser similar a:

```text
DevOpsInterfascia/
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── Frontend/
│   ├── app/
│   ├── public/
│   ├── tests/
│   ├── Dockerfile
│   ├── package.json
│   ├── package-lock.json
│   └── ...
│
├── Backend/
│   ├── tests/
│   │   └── test_main.py
│   ├── main.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── ...
│
├── docker-compose.yml
├── .gitignore
├── .env.example
├── README.md
└── SETUP.md
```

---

# 19. Resumen rápido

Para preparar el entorno:

```bash
git clone URL_DEL_REPOSITORIO
cd DevOpsInterfascia
```

### Frontend

```bash
cd Frontend
npm ci
npm test
npm run build
```

Para ejecutarlo:

```bash
npm run dev
```

### Backend

```bash
cd Backend
python -m venv .venv
```

Activar el entorno virtual y luego:

```bash
python -m pip install -r requirements.txt
python -m pytest
```

Para ejecutarlo:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Docker

Desde la raíz:

```bash
docker compose up -d --build
```

Verificar:

```bash
docker compose ps
```

Aplicaciones:

```text
Frontend → http://localhost:3000
Backend  → http://localhost:8000
Health   → http://localhost:8000/health
Swagger  → http://localhost:8000/docs
```

Después de realizar un `git push`, GitHub Actions ejecutará automáticamente las pruebas y builds configurados.

```

**Este `SETUP.md` está pensado para el estado actual del proyecto.** Cuando agreguen PostgreSQL + pgvector, Nginx y Ollama al `docker-compose.yml`, ahí sí conviene agregar una sección específica explicando esos servicios, pero sin obligar a cada desarrollador a instalarlos manualmente si van a ejecutarse mediante Docker.
```
