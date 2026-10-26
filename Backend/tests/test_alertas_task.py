import asyncio

from worker.tasks import alertas_task


def test_revisar_alertas_tambien_calcula_cierres(monkeypatch):
    llamadas = []

    def falsa(nombre, resultado):
        def funcion():
            llamadas.append(nombre)
            return resultado
        return funcion

    monkeypatch.setattr(alertas_task, "revisar_convocatorias", falsa("revision", {"aperturas": 1}))
    monkeypatch.setattr(alertas_task, "avisar_cierres", falsa("cierres", {"cierres": 2}))
    monkeypatch.setattr(alertas_task, "enviar_correos_pendientes", falsa("correos", {"enviados": 0}))

    resultado = asyncio.run(alertas_task.revisar_alertas({}))

    # Los correos van al final, para incluir los avisos de cierre recién creados
    assert llamadas == ["revision", "cierres", "correos"]
    assert resultado == {
        "revision": {"aperturas": 1},
        "cierres": {"cierres": 2},
        "correos": {"enviados": 0},
    }
