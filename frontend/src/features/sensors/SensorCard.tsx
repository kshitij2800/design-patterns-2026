import { useEffect, useState } from "react";
import {
  fetchLatestReading,
  readSensorNow,
  updateSampling,
  type ReadingDto,
  type SensorDto,
} from "../../services/api";

// TEMPORARY: poll the latest stored reading every few seconds so sampler rows show up.
// Phase 12 replaces this poll with a WebSocket.
const POLL_MS = 3000;

export default function SensorCard({ sensor }: { sensor: SensorDto }) {
  const [reading, setReading] = useState<ReadingDto | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [interval, setIntervalSecs] = useState(String(sensor.sampling_interval_seconds));
  const [tracking, setTracking] = useState(sensor.tracking_enabled);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function poll() {
      try {
        const latest = await fetchLatestReading(sensor.id);
        if (!cancelled) setReading(latest);
      } catch {
        if (!cancelled) setError("Could not load latest reading.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    poll();
    const id = window.setInterval(poll, POLL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [sensor.id]);

  async function handleReadNow() {
    try {
      setBusy(true);
      setError(null);
      setReading(await readSensorNow(sensor.id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not read sensor.");
    } finally {
      setBusy(false);
    }
  }

  async function saveSampling(nextInterval: string, nextTracking: boolean) {
    try {
      setBusy(true);
      setError(null);
      const res = await updateSampling(sensor.id, Number(nextInterval), nextTracking);
      setIntervalSecs(String(res.sampling_interval_seconds));
      setTracking(res.tracking_enabled);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not update sampling.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="border rounded p-3 text-sm space-y-2">
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="font-medium">{sensor.display_name}</div>
          <div className="text-gray-500">{sensor.device_type}</div>
        </div>
        {reading && (
          <span className="px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-700">
            {reading.source}
          </span>
        )}
      </div>

      {loading ? (
        <p className="text-gray-400">Loading…</p>
      ) : reading ? (
        <p>
          <span className="text-xl font-semibold">{reading.value}</span>{" "}
          <span className="text-gray-500">{reading.unit}</span>{" "}
          <span className="text-gray-400 text-xs">
            {new Date(reading.recorded_at).toLocaleTimeString()}
          </span>
        </p>
      ) : (
        <p className="text-gray-400">No readings yet</p>
      )}

      <button
        onClick={handleReadNow}
        disabled={busy}
        className="px-3 py-1.5 bg-slate-800 text-white rounded hover:bg-slate-700 disabled:opacity-50 text-xs"
      >
        {busy ? "Working…" : "Read now"}
      </button>

      <div className="flex items-center gap-3 text-xs">
        <label className="flex items-center gap-1">
          Every
          <input
            type="number"
            min={5}
            value={interval}
            onChange={(e) => setIntervalSecs(e.target.value)}
            onBlur={() => saveSampling(interval, tracking)}
            disabled={busy}
            className="w-16 border rounded px-1 py-0.5"
          />
          s
        </label>
        <label className="flex items-center gap-1">
          <input
            type="checkbox"
            checked={tracking}
            onChange={(e) => saveSampling(interval, e.target.checked)}
            disabled={busy}
          />
          Tracking
        </label>
      </div>

      <p className="text-gray-400 text-xs">Value refreshes every few seconds (temporary polling).</p>
      {error && <p className="text-red-500 text-xs">{error}</p>}
    </div>
  );
}