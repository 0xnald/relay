from pydantic import Field

from app.domain.enums import RecoveryStrategy
from app.schemas.intake import IntakeModel


class RecoveryProposal(IntakeModel):
    strategy: RecoveryStrategy
    reason: str = Field(min_length=1, max_length=1000)
