from uuid import UUID

from app.core.errors import RescueNotFound
from app.domain.agents import CommunicationRequest
from app.domain.network import OutboxMessage
from app.services.agent_tools import ClarificationResult
from app.services.event_processing import UnitOfWorkFactory


class CommunicationRequestService:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def queue(
        self,
        rescue_id: UUID,
        target: str,
        question: str,
        reason: str,
        trace_id: str,
    ) -> ClarificationResult:
        request = CommunicationRequest(
            rescue_id=rescue_id,
            target=target,
            question=question,
            reason=reason,
            trace_id=trace_id,
        )
        async with self._uow_factory() as uow:
            if await uow.rescues.get(rescue_id) is None:
                raise RescueNotFound()
            persisted = await uow.communication_requests.append(request)
            await uow.outbox.append(
                OutboxMessage(
                    aggregate_type="rescue",
                    aggregate_id=rescue_id,
                    message_type="clarification_requested",
                    payload={"communication_request_id": str(persisted.id), "target": target},
                    trace_id=trace_id,
                )
            )
            await uow.commit()
        return ClarificationResult(
            request_id=persisted.id,
            status=persisted.status.value,
            delivery_claimed=False,
        )
