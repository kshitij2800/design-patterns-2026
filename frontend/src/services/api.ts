const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function readError(res: Response, fallback: string): Promise<Error> {
  try {
    const body = await res.json();
    if (typeof body.detail === "string") return new Error(body.detail);
    if (Array.isArray(body.detail)) {
      return new Error(
        body.detail.map((d: { msg?: string }) => d.msg ?? "Invalid input").join("; ")
      );
    }
  } catch {
  }
  return new Error(fallback);
}

export interface HealthResponse {
  status: string;
  db: "ok" | "fail";
}

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error("Health check failed");
  return res.json();
}

export interface SensorDto {
  id: string;
  device_type: string;
  display_name: string;
  default_config: Record<string, unknown>;
}

export async function fetchSensors(): Promise<SensorDto[]> {
  const res = await fetch(`${API_BASE}/api/sensors`);
  if (!res.ok) throw new Error("Failed to fetch sensors");
  return res.json();
}

export async function createSensor(
  type: string,
  displayName?: string
): Promise<SensorDto> {
  const res = await fetch(`${API_BASE}/api/sensors`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ type, display_name: displayName ?? null }),
  });
  if (!res.ok) throw new Error("Failed to create sensor");
  return res.json();
}

export type DeviceFamily = "simulation" | "edge";

export interface DeviceDto {
  id: string;
  device_type: string;
  role: "sensor" | "actuator";
  device_family: string;
  display_name: string;
  default_config: Record<string, unknown>;
  zone_id: string | null;
  location_id: string | null;
}

export async function fetchDevices(params?: {
  family?: DeviceFamily;
  role?: string;
}): Promise<DeviceDto[]> {
  const query = new URLSearchParams();
  if (params?.family) query.set("family", params.family);
  if (params?.role) query.set("role", params.role);
  const res = await fetch(`${API_BASE}/api/devices?${query}`);
  if (!res.ok) throw new Error("Failed to fetch devices");
  return res.json();
}

export async function provisionDeviceFamily(
  family: DeviceFamily
): Promise<DeviceDto[]> {
  const res = await fetch(`${API_BASE}/api/devices/provision?family=${family}`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Provision failed");
  return res.json();
}


export interface ZoneInput {
  name: string;
  moisture_threshold_low: number;
  moisture_threshold_high: number;
  schedule?: Record<string, unknown>;
}

export interface ZoneDto {
  id: string;
  location_id: string;
  name: string;
  moisture_threshold_low: number;
  moisture_threshold_high: number;
  schedule: Record<string, unknown>;
}

export interface LocationSummaryDto {
  id: string;
  name: string;
}

export interface LocationConfigDto {
  location: LocationSummaryDto;
  zones: ZoneDto[];
}

const JSON_HEADERS = { "Content-Type": "application/json" };

export async function fetchLocations(): Promise<LocationSummaryDto[]> {
  const res = await fetch(`${API_BASE}/api/locations`);
  if (!res.ok) throw await readError(res, "Could not load locations.");
  return res.json();
}

export async function createLocationConfig(
  locationName: string,
  zones: ZoneInput[]
): Promise<LocationConfigDto> {
  const res = await fetch(`${API_BASE}/api/locations/config`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify({ location_name: locationName, zones }),
  });
  if (!res.ok) throw await readError(res, "Could not create location.");
  return res.json();
}

export async function fetchLocationConfig(locationId: string): Promise<LocationConfigDto> {
  const res = await fetch(`${API_BASE}/api/locations/${locationId}/config`);
  if (!res.ok) throw await readError(res, "Could not load location.");
  return res.json();
}

export async function deleteLocation(locationId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/locations/${locationId}`, { method: "DELETE" });
  if (!res.ok) throw await readError(res, "Could not delete location.");
}

export async function addZone(locationId: string, zone: ZoneInput): Promise<ZoneDto> {
  const res = await fetch(`${API_BASE}/api/locations/${locationId}/zones`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(zone),
  });
  if (!res.ok) throw await readError(res, "Could not add zone.");
  return res.json();
}

export async function updateZone(
  locationId: string,
  zoneId: string,
  zone: ZoneInput
): Promise<ZoneDto> {
  const res = await fetch(`${API_BASE}/api/locations/${locationId}/zones/${zoneId}`, {
    method: "PATCH",
    headers: JSON_HEADERS,
    body: JSON.stringify(zone),
  });
  if (!res.ok) throw await readError(res, "Could not update zone.");
  return res.json();
}

export async function deleteZone(locationId: string, zoneId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/locations/${locationId}/zones/${zoneId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw await readError(res, "Could not delete zone.");
}

export async function fetchZoneDevices(locationId: string, zoneId: string): Promise<DeviceDto[]> {
  const res = await fetch(`${API_BASE}/api/locations/${locationId}/zones/${zoneId}/devices`);
  if (!res.ok) throw await readError(res, "Could not load zone devices.");
  return res.json();
}

export async function assignDeviceZone(deviceId: string, zoneId: string | null): Promise<void> {
  const res = await fetch(`${API_BASE}/api/devices/${deviceId}/zone`, {
    method: "PATCH",
    headers: JSON_HEADERS,
    body: JSON.stringify({ zone_id: zoneId }),
  });
  if (!res.ok) throw await readError(res, "Could not assign zone.");
}