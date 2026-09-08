# Stack Tecnológico - Interfascia

## 📋 Resumen del Proyecto
Interfascia es una aplicación full-stack containerizada que utiliza microservicios con un backend en Python y un frontend en HTML/CSS.

---

## 🔙 Backend

### Lenguaje de Programación
- **Python** - Lenguaje principal para la lógica del servidor

### Framework Web
- **FastAPI** - Framework moderno y rápido para construcción de APIs REST
  - Características: Validación automática de datos, documentación interactiva Swagger
  - Versión: Última disponible en requirements.txt

### Servidor de Aplicación
- **Uvicorn** - Servidor ASGI asincrónico de alto rendimiento
  - Ejecuta la aplicación FastAPI
  - Soporta características asincrónicas de Python

### Puerto
- **Puerto 8000** - Donde se expone el backend (mapea a puerto 80 del contenedor)

---

## 🎨 Frontend

### Lenguaje de Marcado
- **HTML5** - Estructura del sitio web

### Lenguaje de Estilos
- **CSS3** - Estilos y diseño visual

### Características
- Interfaz minimalista
- Soporte multiidioma: Español (lang="es")
- Responsive design (viewport meta tag)

### Puerto
- **Puerto 3000** - Donde se expone el frontend

---

## 🐳 DevOps & Containerización

### Orquestación
- **Docker Compose** - Gestión de múltiples contenedores
  - Archivo: `docker-compose.yml`
  - Versión: Configurada en formato estándar
  - Nombre del proyecto: "interfascia"

### Containerización
- **Docker** - Encapsulación de aplicaciones
  - Dockerfile en Backend/ para la imagen del backend
  - Dockerfile en Frontend/ para la imagen del frontend

### Servidor Web
- **Nginx** - Servidor web/reverse proxy
  - Archivo: `nginx.conf` (en Backend/)
  - Usado para enrutar y servir contenido estático

### Configuración
- **Variables de Entorno** - Gestión mediante archivo `.env`
  - Utilizado por el servicio backend
  - Permite configuración dinámica sin recompilar imágenes

---

## 📊 Arquitectura de Servicios

### Servicios Definidos

#### 1. Frontend (interfascia-frontend)
- **Puerto expuesto**: 3000:3000
- **Contexto de build**: ./Frontend
- **Restart policy**: unless-stopped
- **Dependencias**: Ninguna explícita
- **Container name**: interfascia-frontend

#### 2. Backend (interfascia-backend)
- **Puerto expuesto**: 8000:80
- **Contexto de build**: ./Backend
- **Restart policy**: unless-stopped
- **Dependencias**: Ninguna explícita (pero frontend depende de él)
- **Container name**: interfascia-backend
- **Configuración**: Usa archivo .env

---

## 🔌 Endpoints del Backend

### GET /
**Descripción**: Endpoint raíz de prueba
```json
{
  "mensaje": "✅ Backend de Interfascia funcionando correctamente"
}
```

### GET /health
**Descripción**: Verificar estado del backend
```json
{
  "status": "healthy"
}
```

---

## 📦 Dependencias del Proyecto

### Backend (requirements.txt)
- fastapi
- uvicorn

---

## 🔧 Requisitos del Sistema

### Para desarrollo local:
- Python 3.7+ (recomendado 3.10+)
- Docker
- Docker Compose

### Para producción:
- Docker
- Docker Compose
- Mínimo 512MB de RAM disponible
- Puertos 3000 y 8000 disponibles

---

## 🚀 Flujo de Operación

1. **Docker Compose** inicia dos servicios simultáneamente
2. **Backend** (FastAPI + Uvicorn) se ejecuta en el puerto 8000
3. **Frontend** (HTML/CSS servido por Nginx) se ejecuta en el puerto 3000
4. Los contenedores se reinician automáticamente si fallan (`unless-stopped`)
5. Las solicitudes del frontend pueden comunicarse con el backend a través de la red Docker

---

## 📝 Notas Adicionales

- La aplicación utiliza una arquitectura de **microservicios containerizada**
- Separación clara entre presentación (Frontend) y lógica de negocio (Backend)
- Configuración simplificada con Docker Compose para desarrollo y producción
- Base sólida para escalabilidad futura

---

**Última actualización**: 2026-08-30
