const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

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