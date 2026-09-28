from sqlalchemy import String, DateTime, Index, Numeric, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from infrastructure.db import Base


class LocationRow(Base):
    __tablename__ = "locations"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    zones: Mapped[list["ZoneRow"]] = relationship(
        back_populates="location",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ZoneRow.name",
    )


class ZoneRow(Base):
    __tablename__ = "zones"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    location_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("locations.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    moisture_threshold_low: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    moisture_threshold_high: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    schedule: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'"))

    location: Mapped["LocationRow"] = relationship(back_populates="zones")

    __table_args__ = (
        Index("ix_zones_location_id", "location_id"),
    )


class DeviceRow(Base):
    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    device_type: Mapped[str] = mapped_column(String(64), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="sensor")
    display_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    default_config: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'"))
    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    device_family: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'simulation'"),
    )
    zone_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("zones.id", ondelete="SET NULL"),
        nullable=True,
    )
    location_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("locations.id", ondelete="SET NULL"),
        nullable=True,
    )

    __table_args__ = (
        Index("ix_devices_role", "role"),
        Index("ix_devices_family", "device_family"),
        Index("ix_devices_zone_id", "zone_id"),
    )