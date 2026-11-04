from starlette.responses import JSONResponse


class UploadLimitMiddleware:
    """Reject oversized multipart bodies before parsing, including chunked uploads."""

    def __init__(self, app, max_bytes: int):
        self.app, self.max_bytes = app, max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] in {"GET", "HEAD"}:
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers", []))
        try:
            declared = int(headers.get(b"content-length", b"0"))
        except ValueError:
            declared = self.max_bytes + 1
        if declared > self.max_bytes:
            return await JSONResponse(
                {"detail": "El cuerpo excede el límite de subida.", "code": "file_too_large"},
                status_code=413,
            )(scope, receive, send)
        consumed = 0

        async def limited_receive():
            nonlocal consumed
            message = await receive()
            consumed += len(message.get("body", b""))
            if consumed > self.max_bytes:
                from starlette.exceptions import HTTPException

                raise HTTPException(413, "El cuerpo excede el límite de subida.")
            return message

        await self.app(scope, limited_receive, send)
