from typing import Any, Protocol


class ChatProvider(Protocol):
    async def structured(self, schema: type, messages: list, tools: list | None = None) -> Any: ...
    async def perceive(self, content: bytes, mime: str) -> str: ...


class EmbeddingProvider(Protocol):
    model: str
    dimension: int

    async def embed(self, texts: list[str], task: str) -> list[list[float]]: ...
