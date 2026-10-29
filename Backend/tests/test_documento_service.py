from app.services import documento_service


class CursorFalso:
    def __init__(self, existe_tabla):
        self.existe_tabla = existe_tabla
        self.consultas = []

    def execute(self, sql, params=None):
        self.consultas.append(sql)

    def fetchone(self):
        return ("documento" if self.existe_tabla else None,)

    def fetchall(self):
        return [(1, 7, "Bases.pdf", "https://ejemplo.uy/bases.pdf", None)]

    def close(self):
        pass


class ConexionFalsa:
    def __init__(self, cursor):
        self._cursor = cursor
        self.cerrada = False

    def cursor(self):
        return self._cursor

    def close(self):
        self.cerrada = True


def test_documentos_sin_tabla_devuelve_lista_vacia(monkeypatch):
    cursor = CursorFalso(existe_tabla=False)
    conexion = ConexionFalsa(cursor)
    monkeypatch.setattr(documento_service, "get_connection", lambda: conexion)

    assert documento_service.obtener_documento_por_convocatoria(7) == []
    assert len(cursor.consultas) == 1
    assert conexion.cerrada


def test_documentos_con_tabla_devuelve_filas(monkeypatch):
    cursor = CursorFalso(existe_tabla=True)
    conexion = ConexionFalsa(cursor)
    monkeypatch.setattr(documento_service, "get_connection", lambda: conexion)

    documentos = documento_service.obtener_documento_por_convocatoria(7)

    assert documentos[0]["nombre"] == "Bases.pdf"
    assert documentos[0]["convocatoria_id"] == 7
    assert conexion.cerrada
