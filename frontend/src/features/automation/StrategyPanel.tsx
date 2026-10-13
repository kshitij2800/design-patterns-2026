import { useEffect, useState } from "react";
import {
  STRATEGY_KEYS,
  evaluateAutomation,
  fetchLocations,
  saveStrategy,
  type RecommendationDto,
} from "../../services/api";

export default function StrategyPanel() {
  const [locations, setLocations] = useState<{ id: string; name: string }[]>([]);
  const [locationId, setLocationId] = useState("");
  const [strategyKey, setStrategyKey] = useState<string>(STRATEGY_KEYS[0]);
  const [result, setResult] = useState<RecommendationDto | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    fetchLocations()
      .then((rows) => {
        setLocations(rows);
        if (rows.length > 0) setLocationId(rows[0].id);
      })
      .catch(() => setError("Could not load locations."));
  }, []);

  async function handleSave() {
    try {
      setBusy(true);
      setError(null);
      setMessage(null);
      await saveStrategy(locationId, strategyKey);
      setMessage(`Saved "${strategyKey}".`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save strategy.");
    } finally {
      setBusy(false);
    }
  }

  async function handleEvaluate() {
    try {
      setBusy(true);
      setError(null);
      setMessage(null);
      setResult(await evaluateAutomation(locationId));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not evaluate.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="border rounded p-3 text-sm space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <select
          value={locationId}
          onChange={(e) => setLocationId(e.target.value)}
          className="border rounded px-2 py-1"
        >
          {locations.map((l) => (
            <option key={l.id} value={l.id}>{l.name}</option>
          ))}
        </select>
        <select
          value={strategyKey}
          onChange={(e) => setStrategyKey(e.target.value)}
          className="border rounded px-2 py-1"
        >
          {STRATEGY_KEYS.map((k) => (
            <option key={k} value={k}>{k}</option>
          ))}
        </select>
        <button
          onClick={handleSave}
          disabled={busy || !locationId}
          className="px-3 py-1.5 bg-slate-800 text-white rounded hover:bg-slate-700 disabled:opacity-50 text-xs"
        >
          Save
        </button>
        <button
          onClick={handleEvaluate}
          disabled={busy || !locationId}
          className="px-3 py-1.5 border rounded hover:bg-slate-50 disabled:opacity-50 text-xs"
        >
          Evaluate
        </button>
      </div>

      <p className="text-gray-400 text-xs">Evaluate uses the saved strategy, so press Save first.</p>
      {message && <p className="text-green-600 text-xs">{message}</p>}
      {error && <p className="text-red-500 text-xs">{error}</p>}

      {result && (
        <div className="border rounded p-2 space-y-2">
          <div>
            <span
              className={`px-2 py-0.5 rounded text-xs font-medium ${
                result.action === "irrigate" ? "bg-blue-100 text-blue-800" : "bg-slate-100 text-slate-700"
              }`}
            >
              {result.action}
            </span>{" "}
            <span className="text-gray-500 text-xs">({result.strategy_key})</span>
            <p>{result.reason}</p>
          </div>
          <ul className="space-y-1 text-xs">
            {result.zones.map((z) => (
              <li key={z.zone_id}>
                <span className="font-medium">{z.zone_name}</span>: {z.action} — {z.reason}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}