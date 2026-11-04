from datetime import UTC, datetime
from pathlib import Path

from langsmith import traceable

from aquaclean.application.ports import EmbeddingProvider
from aquaclean.domain.entities import ORG, Actor, Clock, digest
from aquaclean.domain.errors import DomainError
from aquaclean.infrastructure.persistence.database import Database


class KnowledgeRepository:
    def __init__(self, db: Database, embeddings: EmbeddingProvider, clock: Clock):
        self.db, self.embeddings, self.clock = db, embeddings, clock
        self.collection = digest({"model": embeddings.model, "dimension": embeddings.dimension})[
            :24
        ]

    async def ingest_demo(self) -> dict:
        # Only checked-in, approved synthetic documents enter this path, never user attachments.
        vectors_written = 0
        for path in sorted(Path("knowledge").glob("*.md")):
            content = path.read_text()
            doc_id = "demo:" + path.stem
            chunks = [c.strip() for c in content.split("\n\n") if c.strip()]
            prior = await self.db.one("SELECT hash FROM app.documents WHERE id=%s", (doc_id,))
            count = await self.db.one(
                "SELECT count(*) n FROM app.chunks WHERE document_id=%s AND collection_id=%s",
                (doc_id, self.collection),
            )
            if prior and prior["hash"] == digest(content) and count["n"] == len(chunks):
                continue
            vectors = await self.embeddings.embed(chunks, "RETRIEVAL_DOCUMENT")
            async with self.db.pool.connection() as conn, conn.transaction():
                await conn.execute(
                    "SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (doc_id,)
                )
                await conn.execute(
                    "INSERT INTO app.collections(id,model,dimension,verified_at) VALUES(%s,%s,%s,now()) ON CONFLICT(id) DO NOTHING",
                    (self.collection, self.embeddings.model, self.embeddings.dimension),
                )
                await conn.execute(
                    "INSERT INTO app.documents(id,organization_id,roles,title,version,hash,approved,valid_from) VALUES(%s,%s,%s,%s,'retail-demo-2',%s,true,%s) ON CONFLICT(id) DO UPDATE SET hash=excluded.hash,title=excluded.title,version=excluded.version",
                    (
                        doc_id,
                        ORG,
                        ["attention", "logistics", "quality", "admin"],
                        chunks[0].lstrip("# "),
                        digest(content),
                        datetime(2026, 1, 1, tzinfo=UTC),
                    ),
                )
                await conn.execute(
                    "DELETE FROM app.chunks WHERE document_id=%s AND collection_id=%s",
                    (doc_id, self.collection),
                )
                for index, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True)):
                    if len(vector) != self.embeddings.dimension:
                        raise DomainError("Dimensión incorrecta; ingesta revertida.")
                    await conn.execute(
                        "INSERT INTO app.chunks(id,document_id,collection_id,section,content,hash,embedding) VALUES(%s,%s,%s,%s,%s,%s,%s::vector)",
                        (
                            f"{doc_id}:{self.collection}:{index}",
                            doc_id,
                            self.collection,
                            str(index + 1),
                            chunk,
                            digest(chunk),
                            str(vector),
                        ),
                    )
                vectors_written += len(vectors)
        return {
            "collection": self.collection,
            "model": self.embeddings.model,
            "dimension": self.embeddings.dimension,
            "written": vectors_written,
        }

    @traceable(
        name="AquaClean.filtered_retrieval",
        run_type="retriever",
        process_inputs=lambda x: {
            "query": x.get("query"),
            "client_scope": bool(x.get("client_id")),
        },
    )
    async def search(self, actor: Actor, query: str, client_id: str | None = None) -> list[dict]:
        actor.scope(actor.organization_id, client_id or actor.client_id)
        collection = await self.db.one(
            "SELECT * FROM app.collections WHERE id=%s AND model=%s AND dimension=%s",
            (self.collection, self.embeddings.model, self.embeddings.dimension),
        )
        if not collection:
            raise DomainError(
                "Conocimiento sin ingerir con el modelo y dimensión configurados. Ejecute ingest-demo.",
                "knowledge_unavailable",
                503,
            )
        vector = (await self.embeddings.embed([query], "RETRIEVAL_QUERY"))[0]
        return await self.db.all(
            """SELECT c.id AS chunk_id,c.document_id,c.section,c.page,c.content,c.hash,d.title,d.version,d.valid_from,
          c.embedding <=> %s::vector AS distance FROM app.chunks c JOIN app.documents d ON d.id=c.document_id
          WHERE c.collection_id=%s AND d.organization_id=%s AND d.approved=true
          AND d.roles && %s::text[] AND (d.client_id IS NULL OR d.client_id=%s)
          AND d.valid_from<=%s AND (d.valid_until IS NULL OR d.valid_until>%s)
          ORDER BY c.embedding <=> %s::vector LIMIT 5""",
            (
                str(vector),
                self.collection,
                actor.organization_id,
                list(actor.roles),
                client_id or actor.client_id,
                self.clock.now(),
                self.clock.now(),
                str(vector),
            ),
        )
