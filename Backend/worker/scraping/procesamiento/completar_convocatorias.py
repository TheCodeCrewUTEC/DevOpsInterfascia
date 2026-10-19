"""Completa solo los campos vacíos de las convocatorias ya guardadas.

No carga el modelo de embeddings y no reescribe un campo que ya tiene valor.
Las fechas y la institución se leen del texto del documento. Qwen se consulta
únicamente cuando ese campo sigue vacío.
"""

import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extraer_convocatorias import (  # noqa: E402
    CAMPOS,
    actualizar_convocatoria,
    construir_contexto,
    construir_prompt,
    consultar_qwen,
    financiamiento_en_bd,
    institucion_en_bd,
    normalizar_resultado,
    obtener_conexion,
    periodo_en_bd,
)

CAMPOS_A_COMPLETAR = (
    "institucion",
    "fecha_apertura",
    "fecha_cierre",
    "descripcion",
    "beneficiarios",
    "requisitos",
    "financiamiento",
)


def vacio(campo, valor):
    if valor is None:
        return True
    if isinstance(valor, str) and not valor.strip():
        return True
    if campo == "institucion" and str(valor).strip().upper() == "ANDE":
        return True
    return False


def convocatorias_incompletas(cur):
    cur.execute(
        """
        SELECT
            id,
            titulo,
            institucion,
            fecha_apertura,
            fecha_cierre,
            descripcion,
            beneficiarios,
            requisitos,
            financiamiento
        FROM convocatoria
        WHERE institucion IS NULL
           OR btrim(institucion) = ''
           OR upper(btrim(institucion)) = 'ANDE'
           OR fecha_apertura IS NULL
           OR fecha_cierre IS NULL
           OR descripcion IS NULL
           OR btrim(descripcion) = ''
           OR beneficiarios IS NULL
           OR btrim(beneficiarios) = ''
           OR requisitos IS NULL
           OR btrim(requisitos) = ''
           OR financiamiento IS NULL
        ORDER BY id
        """
    )
    columnas = (
        "id",
        "titulo",
        "institucion",
        "fecha_apertura",
        "fecha_cierre",
        "descripcion",
        "beneficiarios",
        "requisitos",
        "financiamiento",
    )
    return [
        dict(zip(columnas, fila))
        for fila in cur.fetchall()
    ]


def chunks_del_campo(cur, convocatoria_id, keywords):
    encontrados = {}

    for keyword in keywords:
        cur.execute(
            """
            SELECT ch.id, ch.contenido
            FROM chunk ch
            INNER JOIN documento d
                ON d.id = ch.documento_id
            WHERE d.convocatoria_id = %s
              AND ch.contenido ILIKE %s
            ORDER BY ch.id
            LIMIT 2
            """,
            (convocatoria_id, f"%{keyword}%"),
        )
        for chunk_id, contenido in cur.fetchall():
            encontrados.setdefault(
                chunk_id,
                {
                    "chunk_id": chunk_id,
                    "contenido": contenido,
                    "origen": "keyword",
                },
            )
        if len(encontrados) >= 8:
            break

    if encontrados:
        return list(encontrados.values())

    cur.execute(
        """
        SELECT ch.id, ch.contenido
        FROM chunk ch
        INNER JOIN documento d
            ON d.id = ch.documento_id
        WHERE d.convocatoria_id = %s
        ORDER BY ch.id
        LIMIT 4
        """,
        (convocatoria_id,),
    )
    return [
        {
            "chunk_id": chunk_id,
            "contenido": contenido,
            "origen": "inicio",
        }
        for chunk_id, contenido in cur.fetchall()
    ]


def completar_desde_documento(cur, convocatoria):
    pendientes = {
        campo
        for campo in CAMPOS_A_COMPLETAR
        if vacio(campo, convocatoria[campo])
    }
    guardados = []

    if "fecha_apertura" in pendientes or "fecha_cierre" in pendientes:
        apertura, cierre = periodo_en_bd(cur, convocatoria["id"])
        if "fecha_apertura" in pendientes and apertura is not None:
            convocatoria["fecha_apertura"] = apertura
            guardados.append(("fecha_apertura", apertura))
        if "fecha_cierre" in pendientes and cierre is not None:
            convocatoria["fecha_cierre"] = cierre
            guardados.append(("fecha_cierre", cierre))

    if "institucion" in pendientes:
        institucion = institucion_en_bd(cur, convocatoria["id"])
        if institucion is None and str(convocatoria["institucion"] or "").strip().upper() == "ANDE":
            institucion = "Agencia Nacional de Desarrollo (ANDE)"
        if institucion is not None:
            convocatoria["institucion"] = institucion
            guardados.append(("institucion", institucion))

    if "financiamiento" in pendientes:
        monto = financiamiento_en_bd(cur, convocatoria["id"])
        if monto is not None:
            convocatoria["financiamiento"] = monto
            guardados.append(("financiamiento", monto))

    for campo, valor in guardados:
        actualizar_convocatoria(cur, convocatoria["id"], campo, valor)
        print(f"      ✓ {campo} leído del documento")

    return len(guardados)


def completar_con_qwen(cur, convocatoria):
    consultas = 0
    guardados = 0

    for campo in CAMPOS_A_COMPLETAR:
        if not vacio(campo, convocatoria[campo]):
            continue

        chunks = chunks_del_campo(
            cur,
            convocatoria["id"],
            CAMPOS[campo]["keywords"],
        )
        contexto = construir_contexto(chunks)
        if not contexto.strip():
            print(f"      · {campo}: no hay texto para consultar")
            continue

        print(f"      → Qwen: {campo}")
        consultas += 1
        resultado = consultar_qwen(
            construir_prompt(
                campo,
                CAMPOS[campo]["pregunta"],
                contexto,
            )
        )
        valor = normalizar_resultado(
            campo,
            resultado.get("respuesta"),
        )
        if actualizar_convocatoria(cur, convocatoria["id"], campo, valor):
            convocatoria[campo] = valor
            guardados += 1
            print(f"      ✓ {campo} guardado")

    return consultas, guardados


def main():
    inicio = time.time()
    print("Completando campos vacíos de convocatorias")
    conn = obtener_conexion()
    revisadas = 0
    actualizados = 0
    consultas = 0
    errores = 0

    try:
        with conn.cursor() as cur:
            convocatorias = convocatorias_incompletas(cur)
            print(f"Convocatorias con algún campo vacío: {len(convocatorias)}")

            for posicion, convocatoria in enumerate(convocatorias, start=1):
                faltantes = [
                    campo
                    for campo in CAMPOS_A_COMPLETAR
                    if vacio(campo, convocatoria[campo])
                ]
                print(
                    f"\n[{posicion}/{len(convocatorias)}] "
                    f"{convocatoria['id']} {convocatoria['titulo']}"
                )
                print(f"      Faltan: {', '.join(faltantes)}")

                try:
                    desde_documento = completar_desde_documento(cur, convocatoria)
                    consultas_qwen, desde_qwen = completar_con_qwen(cur, convocatoria)
                    conn.commit()
                    revisadas += 1
                    actualizados += desde_documento + desde_qwen
                    consultas += consultas_qwen
                except Exception as error:
                    conn.rollback()
                    errores += 1
                    print(f"      ✗ {type(error).__name__}: {error}")
                    traceback.print_exc()
    finally:
        conn.close()

    segundos = time.time() - inicio
    print("\nListo")
    print(f"Revisadas:           {revisadas}")
    print(f"Campos completados:  {actualizados}")
    print(f"Consultas a Qwen:    {consultas}")
    print(f"Errores:             {errores}")
    print(f"Tiempo:              {int(segundos // 60)} min {segundos % 60:.0f} seg")


if __name__ == "__main__":
    main()
