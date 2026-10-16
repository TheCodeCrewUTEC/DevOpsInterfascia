import hashlib
import json
import os

import redis
from dotenv import load_dotenv

load_dotenv()

# Caché de lecturas en el mismo Redis que usa la cola de arq.
# Si Redis no está (tests, desarrollo local) se consulta la base como siempre.
TTL_SEGUNDOS = int(os.getenv("CACHE_TTL_SEGUNDOS", "300"))
PREFIJO = "cache:"

_cliente: redis.Redis | None = None


def _redis() -> redis.Redis | None:
    global _cliente

    host = os.getenv("REDIS_HOST")
    if not host or TTL_SEGUNDOS <= 0:
        return None

    if _cliente is None:
        _cliente = redis.Redis(
            host=host,
            port=int(os.getenv("REDIS_PORT", "6379")),
            db=int(os.getenv("REDIS_DB", "0")),
            decode_responses=True,
            socket_connect_timeout=0.5,
            socket_timeout=0.5,
        )

    return _cliente


def clave(recurso: str, parametros: dict) -> str:
    texto = json.dumps(parametros, sort_keys=True, default=str)
    return f"{PREFIJO}{recurso}:{hashlib.sha256(texto.encode()).hexdigest()}"


def leer(clave_cache: str):
    cliente = _redis()
    if cliente is None:
        return None

    try:
        guardado = cliente.get(clave_cache)
    except redis.RedisError as error:
        print(f"[CACHE] No se pudo leer de Redis: {error}")
        return None

    return json.loads(guardado) if guardado else None


def guardar(clave_cache: str, valor) -> None:
    cliente = _redis()
    if cliente is None:
        return

    try:
        # Las fechas quedan como texto ISO; los response_model de FastAPI las vuelven a parsear
        cliente.set(clave_cache, json.dumps(valor, default=str), ex=TTL_SEGUNDOS)
    except redis.RedisError as error:
        print(f"[CACHE] No se pudo guardar en Redis: {error}")
