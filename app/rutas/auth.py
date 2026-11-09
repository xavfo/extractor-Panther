"""Rutas de entrada: inicio y cierre de sesión."""
from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from .. import auth, db
from ..web import contexto, plantillas

router = APIRouter()


def _destino_seguro(request: Request) -> str:
    destino = request.query_params.get("next", "/")
    return destino if destino.startswith("/") and not destino.startswith("//") else "/"


@router.get("/login")
def formulario(request: Request):
    if auth.usuario_sesion(request):
        return RedirectResponse("/", status_code=303)
    return plantillas.TemplateResponse(
        request, "login.html", contexto(request, error=None, usuario_form="")
    )


@router.post("/login")
def ingresar(
    request: Request,
    usuario: str = Form(""),
    password: str = Form(""),
):
    ip = request.client.host if request.client else "desconocida"
    clave = f"{ip}|{usuario.strip().lower()}"

    if not auth.permitir_intento(clave):
        return plantillas.TemplateResponse(
            request,
            "login.html",
            contexto(
                request,
                error="Demasiados intentos fallidos. Espera cinco minutos.",
                usuario_form=usuario,
            ),
            status_code=429,
        )

    try:
        datos = auth.autenticar(usuario, password)
    except Exception:  # noqa: BLE001 - la base puede estar apagada
        return plantillas.TemplateResponse(
            request,
            "login.html",
            contexto(
                request,
                error="No hay conexión con MySQL. Revisa que el servidor esté encendido.",
                usuario_form=usuario,
            ),
            status_code=503,
        )

    if not datos:
        auth.registrar_fallo(clave)
        return plantillas.TemplateResponse(
            request,
            "login.html",
            contexto(
                request,
                error="Usuario o contraseña incorrectos.",
                usuario_form=usuario,
            ),
            status_code=401,
        )

    auth.limpiar_intentos(clave)
    request.session["usuario"] = datos
    return RedirectResponse(_destino_seguro(request), status_code=303)


@router.get("/logout")
def salir(request: Request):
    auth.cerrar_sesion(request)
    return RedirectResponse("/login", status_code=303)


@router.get("/salud")
def salud():
    return {"aplicacion": "vetvisor", "base_datos": db.disponible()}
