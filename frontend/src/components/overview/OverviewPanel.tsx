import { useEffect, useRef, useState } from "react";
import {
  fetchLocations,
  fetchOverview,
  type LocationOverviewDto,
  type LocationSummaryDto,
  type OverviewZoneDto,
} from "../../services/api";

// Every card below is built from ONE response: GET /api/locations/{id}/overview.
// This panel never calls the device, reading or automation endpoints itself.
export default function OverviewPanel() {
  const [locations, setLocations] = useState<LocationSummaryDto[]>([]);
  const [locationId, setLocationId] = useState("");
  const [overview, setOverview] = useState<LocationOverviewDto | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const latestRequest = useRef(0); // ignore answers to an older selection

  async function load(id: string) {
    const request = ++latestRequest.current;
    try {
      setLoading(true);
      setError(null);
      const data = await fetchOverview(id);
      if (request === latestRequest.current) setOverview(data);
    } catch (e) {
      if (request === latestRequest.current) {
        setOverview(null);
        setError(e instanceof Error ? e.message : "Could not load overview.");
      }
    } finally {
      if (request === latestRequest.current) setLoading(false);
    }
  }

  // The dropdown uses the existing locations list; the first location is selected.
  useEffect(() => {
    fetchLocations()
      .then((rows) => {
        setLocations(rows);
        if (rows.length > 0) {
          setLocationId(rows[0].id);
          load(rows[0].id);
        }
      })
      .catch(() => setError("Could not load locations."));
  }, []);

  function handleSelect(id: string) {
    setLocationId(id);
    load(id); // one overview fetch per selection
  }

  if (locations.length === 0 && !error) {
    return <p className="text-slate-400 text-sm">No locations yet. Create one in Configuration.</p>;
  }

  return (
    <div className="space-y-4 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        <select
          value={locationId}
          onChange={(e) => handleSelect(e.target.value)}
          className="border rounded px-2 py-1"
        >
          {locations.map((l) => (
            <option key={l.id} value={l.id}>{l.name}</option>
          ))}
        </select>
        <button
          onClick={() => load(locationId)}
          disabled={loading || !locationId}
          className="px-3 py-1.5 border rounded hover:bg-slate-50 disabled:opacity-50 text-xs"
        >
          {loading ? "Loading…" : "Refresh"}
        </button>
      </div>

      {error && <p className="text-red-500 text-xs">{error}</p>}

      {overview && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="border rounded p-3">
              <div className="text-xs text-slate-500 mb-1">Assigned devices</div>
              <div>
                <span className="text-xl font-semibold">{overview.device_counts.sensor}</span>{" "}
                <span className="text-slate-500">sensors</span>
                {" · "}
                <span className="text-xl font-semibold">{overview.device_counts.actuator}</span>{" "}
                <span className="text-slate-500">actuators</span>
              </div>
            </div>

            <div className="border rounded p-3">
              <div className="text-xs text-slate-500 mb-1">Strategy</div>
              {overview.strategy_key ? (
                <div className="text-xl font-semibold">{overview.strategy_key}</div>
              ) : (
                <div className="text-slate-400">No strategy saved</div>
              )}
            </div>

            <div className="border rounded p-3">
              <div className="text-xs text-slate-500 mb-1">Recommendation</div>
              {overview.last_recommendation ? (
                <>
                  <span
                    className={`px-2 py-0.5 rounded text-xs font-medium ${
                      overview.last_recommendation.action === "irrigate"
                        ? "bg-blue-100 text-blue-800"
                        : "bg-slate-100 text-slate-700"
                    }`}
                  >
                    {overview.last_recommendation.action}
                  </span>
                  <p className="mt-1">{overview.last_recommendation.reason}</p>
                </>
              ) : (
                <div className="text-slate-400">Save a strategy to get a recommendation</div>
              )}
            </div>
          </div>

          {overview.zones.length === 0 ? (
            <p className="text-slate-400">This location has no zones.</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {overview.zones.map((z) => (
                <ZoneCard key={z.id} zone={z} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function ZoneCard({ zone }: { zone: OverviewZoneDto }) {
  const readingFor = new Map(zone.latest_readings.map((r) => [r.device_id, r]));

  return (
    <div className="border rounded p-3 space-y-2">
      <div>
        <div className="font-medium">{zone.name}</div>
        <div className="text-xs text-slate-500">
          Moisture {zone.moisture_threshold_low}–{zone.moisture_threshold_high} vwc
        </div>
      </div>

      {zone.devices.length === 0 ? (
        <p className="text-slate-400 text-xs">No devices assigned</p>
      ) : (
        <ul className="space-y-2">
          {zone.devices.map((d) => {
            const r = readingFor.get(d.id);
            return (
              <li key={d.id} className="border-t pt-2 first:border-t-0 first:pt-0">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium">{d.display_name || d.device_type}</span>
                  <span className="text-xs text-slate-500">{d.role} · {d.device_type}</span>
                </div>
                {r ? (
                  <div className="text-xs">
                    <span className="text-base font-semibold">{r.value}</span>{" "}
                    <span className="text-slate-500">{r.unit}</span>
                    <span className="text-slate-400">
                      {" · "}tracking {r.tracking_enabled ? "on" : "off"}
                      {" · "}every {r.sampling_interval_seconds}s
                      {" · "}{new Date(r.recorded_at).toLocaleTimeString()}
                    </span>
                  </div>
                ) : (
                  <div className="text-xs text-slate-400">No reading</div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}