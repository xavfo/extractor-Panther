"""Punto de entrada del visor veterinario.

Se sirve con::

    uvicorn app.main:app --host 0.0.0.0 --port 8000

`--host 0.0.0.0` es lo que permite abrirlo desde cualquier equipo de la LAN del
local; la dirección a compartir es la IP del servidor (por ejemplo
``http://192.168.1.50:8000``).
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from . import auth, esquema, importador
from .config import AJUSTES, RAIZ
from .rutas import auth as rutas_auth
from .rutas import visor
from .web import contexto, plantillas

registro = logging.getLogger("vetvisor")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    """Prepara la base al arrancar, sin impedir que la app levante.

    Si MySQL está apagado se registra el error y la pantalla de entrada lo
    explica; así el operador ve el motivo en lugar de una página en blanco.
    """
    app.state.base_lista = False
    try:
        AJUSTES.ruta_almacen.mkdir(parents=True, exist_ok=True)
        importador.crear_base_si_falta()
        esquema.asegurar_tablas_propias()
        creado = auth.crear_admin_si_falta()
        app.state.base_lista = True
        if creado:
            registro.warning(
                "Creado el usuario administrador '%s'. Cambia su contraseña.",
                AJUSTES.admin_usuario,
            )
    except Exception as exc:  # noqa: BLE001 - se informa, no se cae
        registro.error("No se pudo preparar MySQL al arrancar: %s", exc)
    yield


app = FastAPI(title="VetVisor · consulta de datos Panther", lifespan=ciclo_de_vida)

app.add_middleware(
    SessionMiddleware,
    secret_key=AJUSTES.secreto_sesion,
    session_cookie="vetvisor_sesion",
    max_age=8 * 3600,
    same_site="lax",
    https_only=False,
)

app.mount(
    "/static",
    StaticFiles(directory=str(RAIZ / "app" / "static")),
    name="static",
)

app.include_router(rutas_auth.router)
app.include_router(visor.router)


@app.exception_handler(404)
def no_encontrado(request: Request, exc: Exception):
    return plantillas.TemplateResponse(
        request,
        "no_encontrado.html",
        contexto(request, titulo="Página no encontrada",
                 detalle="La dirección no existe en el visor."),
        status_code=404,
    )


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return RedirectResponse("/static/img/logo.svg")
