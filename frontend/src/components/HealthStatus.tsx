import { useEffect, useState } from "react";
import { fetchHealth } from "../services/api";
import type { HealthResponse } from "../services/api";


export default function HealthStatus() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetchHealth()
      .then(setHealth)
      .catch(() => setError(true));
  }, []);

  if (error)
    return (
      <span className="px-3 py-1 rounded-full text-sm bg-red-100 text-red-700 ring-1 ring-red-300">
        API: unreachable
      </span>
    );

  if (!health)
    return (
      <span className="px-3 py-1 rounded-full text-sm bg-gray-100 text-gray-500">
        Checking…
      </span>
    );

  const ok = health.status === "ok";
  return (
    <span className={`px-3 py-1 rounded-full text-sm font-medium ring-1 ${ok ? "bg-emerald-100 text-emerald-700 ring-emerald-300" : "bg-amber-100 text-amber-700 ring-amber-300"}`}>
      API: {health.status} · DB: {health.db}
    </span>
  );
}