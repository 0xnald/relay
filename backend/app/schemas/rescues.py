from uuid import UUID

from pydantic import AwareDatetime, BaseModel

from app.domain.enums import RescueStatus
from app.domain.rescue import Rescue


class RescueResponse(BaseModel):
    id: UUID
    donation_id: UUID
    status: RescueStatus
    version: int
    created_at: AwareDatetime
    updated_at: AwareDatetime

    @classmethod
    def from_domain(cls, rescue: Rescue) -> "RescueResponse":
        return cls.model_validate(rescue, from_attributes=True)
