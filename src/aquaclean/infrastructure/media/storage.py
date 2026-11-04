import asyncio
import hashlib
from pathlib import Path
from uuid import uuid4

from aquaclean.config import Settings
from aquaclean.domain.entities import Actor
from aquaclean.domain.errors import DomainError
from aquaclean.infrastructure.media.validation import validate
from aquaclean.infrastructure.persistence.repositories import Repository


class MediaStorage:
    def __init__(self, repo: Repository, settings: Settings):
        self.repo, self.settings = repo, settings

    async def save(self, actor: Actor, case_id: str, filename: str, data: bytes) -> dict:
        await self.repo.case(actor, case_id)
        info = await asyncio.to_thread(validate, data, filename, self.settings)
        aid = str(uuid4())
        # Storage keys are server-generated; original names never become filesystem paths.
        await asyncio.to_thread(self.settings.media_root.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread((self.settings.media_root / aid).write_bytes, data)
        clean_name = Path(filename.replace("\\", "/")).name[:180]
        await self.repo.db.execute(
            "INSERT INTO app.attachments(id,case_id,organization_id,filename,mime,size,hash,storage_key,pages,duration) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                aid,
                case_id,
                actor.organization_id,
                clean_name,
                info["mime"],
                len(data),
                hashlib.sha256(data).hexdigest(),
                aid,
                info["pages"],
                info["duration"],
            ),
        )
        return await self.get(actor, case_id, aid)

    async def get(self, actor: Actor, case_id: str, attachment_id: str) -> dict:
        await self.repo.case(actor, case_id)
        row = await self.repo.db.one(
            "SELECT * FROM app.attachments WHERE id=%s AND case_id=%s AND organization_id=%s",
            (attachment_id, case_id, actor.organization_id),
        )
        if not row:
            raise DomainError("Adjunto no disponible.", "not_found", 404)
        return row

    def path(self, attachment: dict) -> Path:
        return self.settings.media_root / str(attachment["id"])
