from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class Device:
    id: UUID | None
    device_type: str
    role: str          
    device_family: str  
    display_name: str
    default_config: dict
    zone_id: UUID | None = None
    location_id: UUID | None = None
    sampling_interval_seconds: int = 300
    tracking_enabled: bool = True

    @property
    def protocol(self) -> str:
        """Which transport talks to this device: "simulation" or "mqtt".

        Devices saved before Phase 5 without a protocol count as simulation.
        """
        return self.default_config.get("protocol", "simulation")