"""Rutas del visor: panel, pacientes, informes, exámenes y tablas."""
from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from .. import auth, consultas, importador
from ..web import contexto, plantillas

router = APIRouter()


def _exigir_sesion(request: Request) -> RedirectResponse | None:
    if auth.usuario_sesion(request):
        return None
    destino = request.url.path
    if request.url.query:
        destino += "?" + request.url.query
    return RedirectResponse(f"/login?next={destino}", status_code=303)


def _error(request: Request, exc: Exception):
    return plantillas.TemplateResponse(
        request,
        "error.html",
        contexto(request, error=f"{type(exc).__name__}: {exc}"),
        status_code=500,
    )


@router.get("/")
def panel(request: Request):
    redireccion = _exigir_sesion(request)
    if redireccion:
        return redireccion
    try:
        datos = {
            "resumen": consultas.resumen(),
            "ultima": importador.ultima_importacion(),
            "informes": consultas.informes_recientes(6),
            "citas": consultas.proximas_citas(6),
        }
    except Exception as exc:  # noqa: BLE001
        return _error(request, exc)
    return plantillas.TemplateResponse(request, "panel.html", contexto(request, **datos))


@router.get("/pacientes")
def pacientes(request: Request, q: str = "", pagina: int = 1):
    redireccion = _exigir_sesion(request)
    if redireccion:
        return redireccion
    try:
        datos = consultas.listar_pacientes(q, pagina)
    except Exception as exc:  # noqa: BLE001
        return _error(request, exc)
    return plantillas.TemplateResponse(
        request, "pacientes.html", contexto(request, **datos)
    )


@router.get("/pacientes/{codigo}")
def paciente(request: Request, codigo: str, seccion: str = "resumen"):
    redireccion = _exigir_sesion(request)
    if redireccion:
        return redireccion
    try:
        ficha = consultas.obtener_paciente(codigo)
        if not ficha:
            return plantillas.TemplateResponse(
                request, "no_encontrado.html",
                contexto(request, titulo="Paciente no encontrado",
                         detalle=f"No existe el paciente {codigo}."),
                status_code=404,
            )
        datos = {
            "paciente": ficha,
            "historia": consultas.historia_paciente(codigo),
            "saldo": consultas.saldo_paciente(codigo),
            "seccion": seccion,
        }
    except Exception as exc:  # noqa: BLE001
        return _error(request, exc)
    return plantillas.TemplateResponse(
        request, "paciente.html", contexto(request, **datos)
    )


@router.get("/informes")
def informes(request: Request, q: str = "", pagina: int = 1):
    redireccion = _exigir_sesion(request)
    if redireccion:
        return redireccion
    try:
        datos = consultas.listar_informes(q, pagina)
    except Exception as exc:  # noqa: BLE001
        return _error(request, exc)
    return plantillas.TemplateResponse(
        request, "informes.html", contexto(request, **datos)
    )


@router.get("/informes/{codigo}")
def informe(request: Request, codigo: str):
    redireccion = _exigir_sesion(request)
    if redireccion:
        return redireccion
    try:
        ficha = consultas.obtener_informe(codigo)
        if not ficha:
            return plantillas.TemplateResponse(
                request, "no_encontrado.html",
                contexto(request, titulo="Informe no encontrado",
                         detalle=f"No existe el informe {codigo}."),
                status_code=404,
            )
    except Exception as exc:  # noqa: BLE001
        return _error(request, exc)
    return plantillas.TemplateResponse(
        request, "informe.html", contexto(request, informe=ficha)
    )


@router.get("/examenes")
def examenes(request: Request, q: str = "", pagina: int = 1):
    redireccion = _exigir_sesion(request)
    if redireccion:
        return redireccion
    try:
        datos = consultas.listar_examenes(q, pagina)
    except Exception as exc:  # noqa: BLE001
        return _error(request, exc)
    return plantillas.TemplateResponse(
        request, "examenes.html", contexto(request, **datos)
    )


@router.get("/tablas")
def tablas(request: Request):
    redireccion = _exigir_sesion(request)
    if redireccion:
        return redireccion
    try:
        datos = {
            "tablas": consultas.tablas_con_conteo(),
            "ultima": importador.ultima_importacion(),
        }
    except Exception as exc:  # noqa: BLE001
        return _error(request, exc)
    return plantillas.TemplateResponse(request, "tablas.html", contexto(request, **datos))


@router.get("/tablas/{nombre}")
def tabla(request: Request, nombre: str, pagina: int = 1):
    redireccion = _exigir_sesion(request)
    if redireccion:
        return redireccion
    try:
        datos = consultas.filas_tabla(nombre, pagina)
        if not datos:
            return plantillas.TemplateResponse(
                request, "no_encontrado.html",
                contexto(request, titulo="Tabla desconocida",
                         detalle=f"La tabla {nombre} no está en el catálogo."),
                status_code=404,
            )
    except Exception as exc:  # noqa: BLE001
        return _error(request, exc)
    return plantillas.TemplateResponse(request, "tabla.html", contexto(request, **datos))


@router.post("/importar")
def importar(request: Request):
    redireccion = _exigir_sesion(request)
    if redireccion:
        return redireccion
    usuario = auth.usuario_sesion(request) or {}
    if usuario.get("rol") != "admin":
        return RedirectResponse(
            "/tablas?mensaje=Solo un administrador puede importar&tipo=error",
            status_code=303,
        )
    try:
        resultado = importador.importar()
    except Exception as exc:  # noqa: BLE001
        return RedirectResponse(
            f"/tablas?mensaje=Error al importar: {type(exc).__name__}"
            f"&tipo=error",
            status_code=303,
        )
    mensaje = (
        f"Importación {resultado['estado']}: {resultado['archivos']} archivos, "
        f"{resultado['filas']} filas en {resultado['segundos']} s"
    )
    tipo = "ok" if resultado["estado"] == "ok" else "aviso"
    return RedirectResponse(
        f"/tablas?mensaje={_url(mensaje)}&tipo={tipo}",
        status_code=303,
    )


def _url(texto: str) -> str:
    from urllib.parse import quote_plus

    return quote_plus(texto)


@router.get("/usuarios")
def usuarios(request: Request):
    redireccion = _exigir_sesion(request)
    if redireccion:
        return redireccion
    usuario = auth.usuario_sesion(request) or {}
    if usuario.get("rol") != "admin":
        return RedirectResponse("/?mensaje=Sin permisos&tipo=error", status_code=303)
    return plantillas.TemplateResponse(
        request, "usuarios.html",
        contexto(request, usuarios=auth.listar_usuarios(), error=None),
    )


@router.post("/usuarios")
def crear_usuario(
    request: Request,
    usuario: str = Form(""),
    nombre: str = Form(""),
    correo: str = Form(""),
    password: str = Form(""),
    rol: str = Form("recepcion"),
):
    redireccion = _exigir_sesion(request)
    if redireccion:
        return redireccion
    actual = auth.usuario_sesion(request) or {}
    if actual.get("rol") != "admin":
        return RedirectResponse("/?mensaje=Sin permisos&tipo=error", status_code=303)

    usuario = usuario.strip().lower()
    nombre = nombre.strip()
    error = None
    if not usuario or len(usuario) < 3:
        error = "El usuario debe tener al menos 3 caracteres."
    elif not nombre:
        error = "Falta el nombre completo."
    elif len(password) < 8:
        error = "La contraseña debe tener al menos 8 caracteres."
    elif rol not in {"admin", "veterinario", "recepcion"}:
        error = "Rol inválido."

    if error:
        return plantillas.TemplateResponse(
            request, "usuarios.html",
            contexto(request, usuarios=auth.listar_usuarios(), error=error),
            status_code=400,
        )

    from datetime import datetime

    from .. import db

    try:
        db.ejecutar(
            "INSERT INTO usuarios (usuario, nombre, correo, password_hash, rol, activo, creado_en) "
            "VALUES (:usuario, :nombre, :correo, :hash, :rol, 1, :creado)",
            {
                "usuario": usuario,
                "nombre": nombre,
                "correo": correo.strip() or None,
                "hash": auth.hash_password(password),
                "rol": rol,
                "creado": datetime.now(),
            },
        )
    except Exception:  # noqa: BLE001 - choque de usuario único
        return plantillas.TemplateResponse(
            request, "usuarios.html",
            contexto(request, usuarios=auth.listar_usuarios(),
                     error="Ese nombre de usuario ya existe."),
            status_code=400,
        )
    return RedirectResponse("/usuarios?mensaje=Usuario creado", status_code=303)
