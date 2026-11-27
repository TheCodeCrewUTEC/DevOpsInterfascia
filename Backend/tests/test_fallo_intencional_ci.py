"""Fallo aislado para comprobar que el job de tests de CI corta la corrida.

No cubre producción. Cuando el workflow quede verificado, este archivo se borra.
"""


def test_fallo_intencional_de_ci():
    raise AssertionError(
        "FALLO INTENCIONAL DE CI: este test existe solo para hacer fallar "
        "el paso 'Ejecutar tests' del job backend. No indica un defecto de producción."
    )
