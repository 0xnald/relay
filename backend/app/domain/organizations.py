from uuid import UUID

from pydantic import Field, model_validator

from app.domain.base import DomainModel, TimestampedEntity
from app.domain.enums import ActorRole, DriverStatus, OrganizationType


class GeoPoint(DomainModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class ContactMetadata(DomainModel):
    name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=320)


class DailyAvailability(DomainModel):
    opens_minute: int = Field(ge=0, lt=1440)
    closes_minute: int = Field(gt=0, le=1440)

    @model_validator(mode="after")
    def valid_window(self) -> "DailyAvailability":
        if self.closes_minute <= self.opens_minute:
            raise ValueError("availability close must follow open")
        return self


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
    contact_user_id: UUID | None = None
    name: str = Field(default="Unnamed donor", min_length=1, max_length=255)
    address: str = Field(default="Unknown", min_length=1, max_length=1000)
    location: GeoPoint = GeoPoint(latitude=0, longitude=0)
    contact: ContactMetadata = ContactMetadata()
    synthetic: bool = False


class Recipient(TimestampedEntity):
    organization_id: UUID
    contact_user_id: UUID | None = None
    name: str = Field(default="Unnamed recipient", min_length=1, max_length=255)
    active: bool = True
    address: str = Field(default="Unknown", min_length=1, max_length=1000)
    location: GeoPoint = GeoPoint(latitude=0, longitude=0)
    service_radius_km: float = Field(default=25, gt=0)
    accepted_food_categories: frozenset[str] = frozenset()
    dietary_capabilities: frozenset[str] = frozenset()
    cold_storage_available: bool = False
    freezer_available: bool = False
    total_capacity: float = Field(default=0, ge=0)
    available_capacity: float = Field(default=0, ge=0)
    availability: DailyAvailability = DailyAvailability(opens_minute=0, closes_minute=1440)
    priority: float = Field(default=0.5, ge=0, le=1)
    reliability: float = Field(default=0.5, ge=0, le=1)
    current_load: float = Field(default=0, ge=0)
    contact: ContactMetadata = ContactMetadata()
    synthetic: bool = False
    capacity_notes: str | None = Field(default=None, max_length=1000)


class Driver(TimestampedEntity):
    organization_id: UUID | None = None
    user_id: UUID | None = None
    name: str = Field(default="Unnamed driver", min_length=1, max_length=255)
    active: bool = True
    available: bool = True
    current_location: GeoPoint = GeoPoint(latitude=0, longitude=0)
    vehicle_type: str = Field(default="car", min_length=1, max_length=100)
    vehicle_capacity: float = Field(default=0, ge=0)
    refrigerated_vehicle: bool = False
    availability: DailyAvailability = DailyAvailability(opens_minute=0, closes_minute=1440)
    reliability: float = Field(default=0.5, ge=0, le=1)
    status: DriverStatus = DriverStatus.AVAILABLE
    contact: ContactMetadata = ContactMetadata()
    synthetic: bool = False
