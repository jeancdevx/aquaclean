class DomainError(Exception):
    def __init__(self, message: str, code: str = "invalid", status: int = 422):
        super().__init__(message)
        self.code = code
        self.status = status


class ProviderUnavailable(DomainError):
    def __init__(self, message: str = "IA no disponible. Configure Gemini y compruebe el modelo."):
        super().__init__(message, "provider_unavailable", 503)
