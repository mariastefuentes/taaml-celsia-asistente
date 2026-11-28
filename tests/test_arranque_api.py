from types import SimpleNamespace

from taaml import arranque_api


def _api_saludable(monkeypatch, activa):
    monkeypatch.setattr(arranque_api, "api_activa", lambda timeout=2.0: activa)


def _puerto(monkeypatch, ocupado):
    monkeypatch.setattr(arranque_api, "puerto_ocupado", lambda host=arranque_api.HOST, port=arranque_api.PORT: ocupado)


def test_api_activa_no_inicia_otra_instancia(monkeypatch, capsys):
    _api_saludable(monkeypatch, True)
    llamadas = []
    monkeypatch.setattr(arranque_api, "iniciar_uvicorn", lambda: llamadas.append("uvicorn"))

    assert arranque_api.main([]) == 0
    assert llamadas == []
    assert "ya está ejecutándose" in capsys.readouterr().out


def test_puerto_ocupado_por_otro_programa_no_mata_y_no_inicia(monkeypatch, capsys):
    _api_saludable(monkeypatch, False)
    _puerto(monkeypatch, True)
    llamadas = []
    monkeypatch.setattr(arranque_api, "iniciar_uvicorn", lambda: llamadas.append("uvicorn"))

    assert arranque_api.main([]) == 1
    assert llamadas == []
    err = capsys.readouterr().err
    assert "ocupado" in err and "No se mata ningún proceso" in err


def test_puerto_libre_inicia_uvicorn_normalmente(monkeypatch):
    _api_saludable(monkeypatch, False)
    _puerto(monkeypatch, False)
    llamadas = []
    monkeypatch.setattr(arranque_api, "iniciar_uvicorn", lambda: llamadas.append("uvicorn"))

    assert arranque_api.main([]) == 0
    assert llamadas == ["uvicorn"]


def test_api_activa_verifica_api_salud(monkeypatch):
    def responder(url, timeout):
        assert url == arranque_api.SALUD_URL
        return SimpleNamespace(status_code=200, json=lambda: {"estado": "ok"})

    monkeypatch.setattr(arranque_api.requests, "get", responder)
    assert arranque_api.api_activa() is True


def test_api_activa_rechaza_otro_programa(monkeypatch):
    monkeypatch.setattr(arranque_api.requests, "get", lambda url, timeout: SimpleNamespace(status_code=200, json=lambda: {"otro": "servicio"}))
    assert arranque_api.api_activa() is False


def test_puerto_ocupado_no_es_fallo_por_proceso_ocupado(monkeypatch):
    class Socket:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def bind(self, address):
            raise OSError(10048, "address in use")

    monkeypatch.setattr(arranque_api.socket, "socket", lambda *args, **kwargs: Socket())
    assert arranque_api.puerto_ocupado() is True
