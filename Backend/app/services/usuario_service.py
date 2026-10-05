from app.database.connection import get_connection
from app.services import keycloak_admin_service as keycloak

ESTADOS = ("pendiente", "aprobado", "rechazado")

COLUMNAS = (
    "keycloak_id",
    "email",
    "nombre",
    "apellido",
    "celular",
    "departamento_residencia",
    "departamentos_actuacion",
    "instituciones",
    "perfil",
    "perfil_otro",
    "rol",
    "estado",
)

COLUMNAS_LECTURA = COLUMNAS + ("revisado_por", "revisado_en", "creado", "actualizado")


def _fila_a_dict(fila) -> dict:
    return dict(zip(COLUMNAS_LECTURA, fila))


def guardar_usuario(datos: dict, actualizar_estado: bool = False) -> dict:
    """Inserta o actualiza un usuario por keycloak_id.

    Sin actualizar_estado, un usuario existente conserva su estado (un reintento del
    aviso de registro no debe volver a dejar pendiente a alguien ya aprobado).
    """

    valores = {
        "departamentos_actuacion": [],
        "instituciones": [],
        "estado": "pendiente",
        **{k: v for k, v in datos.items() if k in COLUMNAS},
    }
    columnas = [c for c in COLUMNAS if c in valores]
    actualizables = [
        c for c in columnas
        if c != "keycloak_id" and (actualizar_estado or c != "estado")
    ]

    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                INSERT INTO usuarios ({", ".join(columnas)})
                VALUES ({", ".join(["%s"] * len(columnas))})
                ON CONFLICT (keycloak_id) DO UPDATE SET
                    {", ".join(f"{c} = EXCLUDED.{c}" for c in actualizables)},
                    actualizado = NOW()
                RETURNING {", ".join(COLUMNAS_LECTURA)}
                """,
                [valores[c] for c in columnas],
            )
            usuario = _fila_a_dict(cur.fetchone())

        conn.commit()
        return usuario

    finally:
        conn.close()


def listar_usuarios(estado: str | None = None) -> list[dict]:
    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT {", ".join(COLUMNAS_LECTURA)}
                FROM usuarios
                WHERE %s::text IS NULL OR estado = %s
                ORDER BY creado DESC
                """,
                (estado, estado),
            )
            return [_fila_a_dict(fila) for fila in cur.fetchall()]

    finally:
        conn.close()


def marcar_estado(keycloak_id: str, estado: str, revisado_por: str | None) -> dict | None:
    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                UPDATE usuarios
                SET estado = %s,
                    revisado_por = %s,
                    revisado_en = NOW(),
                    actualizado = NOW()
                WHERE keycloak_id = %s
                RETURNING {", ".join(COLUMNAS_LECTURA)}
                """,
                (estado, revisado_por, keycloak_id),
            )
            fila = cur.fetchone()

        conn.commit()
        return _fila_a_dict(fila) if fila else None

    finally:
        conn.close()


def _primero(atributos: dict, nombre: str) -> str | None:
    valores = atributos.get(nombre) or []
    return valores[0] if valores else None


def datos_desde_keycloak(usuario: dict, rol: str | None) -> dict:
    atributos = usuario.get("attributes") or {}
    estado = _primero(atributos, "estadoAprobacion")

    if estado not in ESTADOS:
        # Cuentas anteriores al flujo de aprobación: habilitada equivale a aprobada
        estado = "aprobado" if usuario.get("enabled") else "pendiente"

    return {
        "keycloak_id": usuario["id"],
        "email": usuario.get("email"),
        "nombre": usuario.get("firstName"),
        "apellido": usuario.get("lastName"),
        "celular": _primero(atributos, "celular"),
        "departamento_residencia": _primero(atributos, "departamentoResidencia"),
        "departamentos_actuacion": atributos.get("departamentosActuacion") or [],
        "instituciones": atributos.get("instituciones") or [],
        "perfil": _primero(atributos, "perfil"),
        "perfil_otro": _primero(atributos, "perfilOtro"),
        "rol": rol,
        "estado": estado,
    }


def sincronizar_desde_keycloak() -> int:
    """Copia todos los usuarios de Keycloak a la tabla (Keycloak manda sobre el estado)."""

    usuarios = keycloak.listar_usuarios()

    for usuario in usuarios:
        rol = keycloak.rol_de_usuario(usuario["id"])
        guardar_usuario(datos_desde_keycloak(usuario, rol), actualizar_estado=True)

    return len(usuarios)
