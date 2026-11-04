from fastapi import Request

from aquaclean.domain.entities import Actor
from aquaclean.domain.errors import DomainError


def actor(request: Request) -> Actor:
    # No role/client/organization headers or message values can grant capabilities.
    return request.app.state.runtime.actor


async def same_origin(request: Request, call_next):
    origin = request.headers.get("origin")
    if request.method not in {"GET", "HEAD", "OPTIONS"} and origin:
        from urllib.parse import urlsplit

        if urlsplit(origin).netloc != request.headers.get("host"):
            from fastapi.responses import JSONResponse

            return JSONResponse(
                {"detail": "Origen no permitido.", "code": "forbidden"}, status_code=403
            )
    return await call_next(request)


def require_demo(settings):
    if settings.auth_mode != "demo_local":
        raise DomainError("Perfil de autenticación no implementado.", "auth_mode", 503)
