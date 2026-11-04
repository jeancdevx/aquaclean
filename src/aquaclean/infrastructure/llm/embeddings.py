import asyncio
import math

from google.genai import types
from langsmith import traceable

from aquaclean.domain.errors import ProviderUnavailable
from aquaclean.infrastructure.llm.provider import GeminiProvider


class GeminiEmbeddings:
    def __init__(self, provider: GeminiProvider):
        self.provider = provider
        self.model = provider.settings.gemini_embedding_model
        self.dimension = provider.settings.embedding_dimension

    @traceable(
        name="Gemini.embeddings",
        run_type="embedding",
        process_inputs=lambda x: {"task": x.get("task"), "count": len(x.get("texts", []))},
        process_outputs=lambda _: {"vectors": "persisted or queried; omitted"},
    )
    async def embed(self, texts: list[str], task: str) -> list[list[float]]:
        self.provider.require()
        try:
            async with asyncio.timeout(self.provider.settings.llm_timeout_seconds):
                response = await self.provider.client.aio.models.embed_content(
                    model=self.model,
                    contents=texts,
                    config=types.EmbedContentConfig(
                        output_dimensionality=self.dimension, task_type=task
                    ),
                )
            vectors = []
            for item in response.embeddings or []:
                values = item.values or []
                norm = math.sqrt(sum(v * v for v in values))
                if (
                    len(values) != self.dimension
                    or not norm
                    or not all(math.isfinite(v) for v in values)
                ):
                    raise ValueError("embedding dimension/norm invalid")
                vectors.append([v / norm for v in values])
            if len(vectors) != len(texts):
                raise ValueError("embedding count invalid")
            return vectors
        except Exception as exc:
            raise ProviderUnavailable(
                "Embeddings no disponibles o dimensión no compatible. No se escribieron vectores simulados."
            ) from exc
