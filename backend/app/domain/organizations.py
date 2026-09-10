from uuid import UUID

from pydantic import Field

from app.domain.base import TimestampedEntity
from app.domain.enums import ActorRole, OrganizationType


class Organization(TimestampedEntity):
    name: str = Field(min_length=1, max_length=255)
    organization_type: OrganizationType


class User(TimestampedEntity):
    organization_id: UUID
    email: str = Field(min_length=3, max_length=320, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    display_name: str = Field(min_length=1, max_length=255)
    role: ActorRole
    active: bool = True


class Donor(TimestampedEntity):
    organization_id: UUID
    contact_user_id: UUID


class Recipient(TimestampedEntity):
    organization_id: UUID
    contact_user_id: UUID
    capacity_notes: str | None = Field(default=None, max_length=1000)


class Driver(TimestampedEntity):
    organization_id: UUID | None = None
    user_id: UUID
    available: bool = True
