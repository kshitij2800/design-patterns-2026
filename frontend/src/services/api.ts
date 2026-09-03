export interface HealthResponse {
  status: string;
  db: "ok" | "fail";
}

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"}/health`);
  if (!res.ok) throw new Error("Health check failed");
  return res.json();
}