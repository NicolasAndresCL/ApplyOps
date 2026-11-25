"""Contract test de Get on Board contra una respuesta real capturada el 2026-11-25.

Si Get on Board cambia la forma de su API, estos tests fallan al actualizar el
fixture (`tests/fixtures/getonboard_search.json`), antes de que la
recolección empiece a guardar datos vacíos en producción.

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest

from applyops.adapters.outbound.getonboard import FuenteGetOnBoard, mapear_oferta, texto_plano
from applyops.adapters.outbound.http_resiliente import ClienteHttpResiliente
from applyops.domain.errores import FuenteNoDisponibleError
from applyops.domain.oferta import Modalidad, Seniority

FIXTURE = Path(__file__).parents[1] / "fixtures" / "getonboard_search.json"


@pytest.fixture
def respuesta_real() -> dict[str, Any]:
    datos: dict[str, Any] = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return datos


def _fuente(
    paginas: list[dict[str, Any]], max_paginas: int = 4
) -> tuple[FuenteGetOnBoard, list[httpx.Request]]:
    pedidos: list[httpx.Request] = []

    def manejar(request: httpx.Request) -> httpx.Response:
        pedidos.append(request)
        return httpx.Response(200, json=paginas[len(pedidos) - 1])

    http = ClienteHttpResiliente(
        httpx.Client(transport=httpx.MockTransport(manejar)), "getonboard", dormir=lambda _: None
    )
    return FuenteGetOnBoard(http, max_paginas=max_paginas), pedidos


def test_el_fixture_tiene_la_forma_esperada(respuesta_real: dict[str, Any]) -> None:
    assert set(respuesta_real) == {"data", "meta"}
    assert {"page", "per_page", "total_pages"} <= set(respuesta_real["meta"])
    atributos = respuesta_real["data"][0]["attributes"]
    for campo in (
        "title",
        "remote_modality",
        "countries",
        "min_salary",
        "max_salary",
        "seniority",
        "lang",
        "published_at",
        "company",
        "description",
    ):
        assert campo in atributos, f"Get on Board ya no envía {campo!r}"


def test_mapea_una_oferta_real(respuesta_real: dict[str, Any]) -> None:
    oferta = mapear_oferta(respuesta_real["data"][0])

    assert oferta.fuente == "getonboard"
    assert oferta.id_externo == "data-engineer-gcp-tcit-santiago"
    assert oferta.clave == "getonboard:data-engineer-gcp-tcit-santiago"
    assert oferta.titulo == "Data Engineer GCP / Senior"
    assert oferta.empresa == "TCIT"
    assert oferta.url == "https://www.getonbrd.com/jobs/data-engineer-gcp-tcit-santiago"
    assert oferta.modalidad is Modalidad.HIBRIDO
    assert oferta.paises == ("Chile",)
    assert (oferta.sueldo_min_usd, oferta.sueldo_max_usd) == (1900, 2800)
    assert oferta.seniority is Seniority.SENIOR
    assert oferta.idioma is None  # lang_not_specified
    assert oferta.publicada_en == datetime.fromtimestamp(1795095444, tz=UTC)
    assert "BigQuery" in oferta.descripcion
    assert "<li>" not in oferta.descripcion


def test_mapea_idioma_y_sueldo_ausente(respuesta_real: dict[str, Any]) -> None:
    sin_sueldo = mapear_oferta(respuesta_real["data"][1])
    en_ingles = mapear_oferta(respuesta_real["data"][2])
    assert (sin_sueldo.sueldo_min_usd, sin_sueldo.sueldo_max_usd) == (None, None)
    assert sin_sueldo.seniority is Seniority.SEMI_SENIOR
    assert en_ingles.idioma == "en"


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        ("fully_remote", Modalidad.REMOTO),
        ("remote_local", Modalidad.REMOTO_LOCAL),
        ("no_remote", Modalidad.PRESENCIAL),
        ("algo_nuevo", Modalidad.DESCONOCIDA),
        (None, Modalidad.DESCONOCIDA),
    ],
)
def test_modalidades(
    respuesta_real: dict[str, Any], valor: str | None, esperado: Modalidad
) -> None:
    item = respuesta_real["data"][0]
    item["attributes"]["remote_modality"] = valor
    assert mapear_oferta(item).modalidad is esperado


def test_texto_plano_quita_html_y_entidades() -> None:
    assert texto_plano("<p>Hola&nbsp;<b>mundo</b></p>\n<ul><li>uno</li></ul>") == "Hola mundo uno"


def test_buscar_pagina_hasta_total_pages(respuesta_real: dict[str, Any]) -> None:
    pagina = {**respuesta_real, "meta": {"page": 1, "per_page": 3, "total_pages": 2}}
    fuente, pedidos = _fuente([pagina, pagina])
    resultado = fuente.buscar("python")
    ofertas = resultado.ofertas

    assert len(ofertas) == 6
    assert len(pedidos) == 2
    params = pedidos[0].url.params
    assert params["query"] == "python"
    assert params["page"] == "1"
    assert params["expand"] == '["company", "location_tenants"]'
    assert pedidos[1].url.params["page"] == "2"


def test_buscar_respeta_max_paginas(respuesta_real: dict[str, Any]) -> None:
    pagina = {**respuesta_real, "meta": {"page": 1, "per_page": 3, "total_pages": 43}}
    fuente, pedidos = _fuente([pagina] * 5, max_paginas=2)
    fuente.buscar("python")
    assert len(pedidos) == 2


def test_oferta_rota_se_omite_sin_tumbar_la_pagina(respuesta_real: dict[str, Any]) -> None:
    del respuesta_real["data"][1]["attributes"]["title"]
    respuesta_real["meta"]["total_pages"] = 1
    fuente, _ = _fuente([respuesta_real])
    resultado = fuente.buscar("python")
    ofertas = resultado.ofertas
    assert [o.id_externo for o in ofertas] == [
        "data-engineer-gcp-tcit-santiago",
        "senior-software-engineer-data-acquisition-team-checkr-santiago",
    ]


def test_respuesta_sin_data_es_fuente_no_disponible() -> None:
    fuente, _ = _fuente([{"errors": ["mantención"]}])
    with pytest.raises(FuenteNoDisponibleError, match="contrato"):
        fuente.buscar("python")


def test_remote_no_es_un_pais_y_remote_local_usa_location_tenants() -> None:
    """Regresión 2026-11-25: «Remote» leído como país descartó 62 de 239 ofertas reales."""
    remotas = json.loads((FIXTURE.parent / "getonboard_remotas.json").read_text(encoding="utf-8"))
    local, global_ = (mapear_oferta(item) for item in remotas["data"])

    assert local.modalidad is Modalidad.REMOTO_LOCAL
    assert local.paises == ("Chile",)
    assert global_.modalidad is Modalidad.REMOTO
    assert global_.paises == ()


def test_remote_local_en_chile_no_se_descarta_con_el_perfil_de_ejemplo() -> None:
    from applyops.adapters.outbound.perfil_yaml import cargar_perfil
    from applyops.domain.scoring import puntuar

    remotas = json.loads((FIXTURE.parent / "getonboard_remotas.json").read_text(encoding="utf-8"))
    perfil = cargar_perfil(FIXTURE.parents[2] / "perfil" / "busqueda.example.yaml")
    for item in remotas["data"]:
        assert not puntuar(mapear_oferta(item), perfil).descartada


def test_meta_que_no_es_objeto_degrada_la_consulta(respuesta_real: dict[str, Any]) -> None:
    """Regresión (Sourcery, 2026-11-25): antes reventaba con AttributeError y abortaba todo."""
    fuente, _ = _fuente([{**respuesta_real, "meta": ["raro"]}])
    with pytest.raises(FuenteNoDisponibleError, match="meta"):
        fuente.buscar("python")


def test_titulo_nulo_se_omite_sin_tumbar_la_pagina(respuesta_real: dict[str, Any]) -> None:
    """Regresión (Sourcery, 2026-11-25): `None.strip()` escapaba como AttributeError."""
    respuesta_real["data"][0]["attributes"]["title"] = None
    respuesta_real["meta"]["total_pages"] = 1
    fuente, _ = _fuente([respuesta_real])
    resultado = fuente.buscar("python")
    claves = [o.id_externo for o in resultado.ofertas]
    assert "data-engineer-gcp-tcit-santiago" not in claves
    assert len(claves) == 2, "las demás ofertas de la página se conservan"


@pytest.mark.parametrize(
    ("company", "esperado"),
    [
        ("texto", "desconocida"),
        ({"data": "x"}, "desconocida"),
        ({"data": {"id": "acme", "attributes": "x"}}, "acme"),
        (None, "desconocida"),
    ],
)
def test_empresa_tolera_formas_raras(
    respuesta_real: dict[str, Any], company: Any, esperado: str
) -> None:
    item = respuesta_real["data"][0]
    item["attributes"]["company"] = company
    assert mapear_oferta(item).empresa == esperado


def test_completa_solo_si_llega_a_la_ultima_pagina(respuesta_real: dict[str, Any]) -> None:
    """Regresión (Sourcery, PR #5): un corte por tope se trataba como respuesta completa."""
    hasta_el_final = {**respuesta_real, "meta": {"page": 1, "per_page": 3, "total_pages": 2}}
    fuente, _ = _fuente([hasta_el_final, hasta_el_final])
    assert fuente.buscar("python").completa is True

    cortada = {**respuesta_real, "meta": {"page": 1, "per_page": 3, "total_pages": 43}}
    fuente, pedidos = _fuente([cortada] * 5, max_paginas=2)
    resultado = fuente.buscar("python")
    assert resultado.completa is False
    assert len(pedidos) == 2


def test_sin_total_pages_es_incompleta(respuesta_real: dict[str, Any]) -> None:
    fuente, _ = _fuente([{**respuesta_real, "meta": {}}])
    resultado = fuente.buscar("python")
    assert resultado.completa is False
    assert len(resultado.ofertas) == 3
