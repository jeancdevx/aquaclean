from aquaclean.domain.entities import Actor
from aquaclean.infrastructure.persistence.commands import CommandRepository


class CommandExecutor:
    def __init__(self, repository: CommandRepository):
        self.repository = repository

    async def execute(
        self, actor: Actor, case_id: str, command_id: str, approval_id: str, selection: dict
    ) -> dict:
        # The transaction revalidates permissions, evidence, policy, versions, capacity and consent.
        return await self.repository.execute(actor, case_id, command_id, approval_id, selection)
