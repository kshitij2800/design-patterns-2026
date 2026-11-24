import { useEffect, useState } from "react";
import {
  fetchAlerts,
  fetchLocations,
  fetchOverview,
  type AlertDto,
  type LocationSummaryDto,
  type OverviewZoneDto,
} from "../../services/api";

// Polls the DB-backed alerts list. Phase 12 replaces this poll with services/realtime.ts.
const POLL_MS = 5000;

const SEVERITY_STYLES: Record<AlertDto["severity"], string> = {
  info: "bg-sky-100 text-sky-800",
  warning: "bg-amber-100 text-amber-800",
  critical: "bg-red-100 text-red-800",
};

export default function EventFeed() {
  const [alerts, setAlerts] = useState<AlertDto[]>([]);
  const [locations, setLocations] = useState<LocationSummaryDto[]>([]);
  const [zones, setZones] = useState<OverviewZoneDto[]>([]);
  const [locationId, setLocationId] = useState("");
  const [zoneId, setZoneId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchLocations().then(setLocations).catch(() => setError("Could not load locations."));
  }, []);

  // Zone choices for the chosen location (from the Phase 7 overview response).
  useEffect(() => {
    setZoneId("");
    setZones([]);
    if (!locationId) return;
    let cancelled = false;
    fetchOverview(locationId)
      .then((o) => { if (!cancelled) setZones(o.zones); })
      .catch(() => { if (!cancelled) setError("Could not load zones."); });
    return () => { cancelled = true; };
  }, [locationId]);

  // Poll GET /api/alerts every 5 s with the current filters (default status=active).
  useEffect(() => {
    let cancelled = false;
    async function poll() {
      try {
        const rows = await fetchAlerts({
          locationId: locationId || undefined,
          zoneId: zoneId || undefined,
        });
        if (!cancelled) {
          setAlerts(rows);
          setError(null);
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Could not load alerts.");
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
  }, [locationId, zoneId]);

  function placeOf(a: AlertDto): string {
    if (!a.location_id) return "Unassigned device";
    const loc = locations.find((l) => l.id === a.location_id)?.name ?? "Location";
    const zone = zones.find((z) => z.id === a.zone_id)?.name;
    return zone ? `${loc} · ${zone}` : loc;
  }

  return (
    <div className="space-y-3 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        <select
          value={locationId}
          onChange={(e) => setLocationId(e.target.value)}
          className="border rounded px-2 py-1"
          aria-label="Filter by location"
        >
          <option value="">All locations</option>
          {locations.map((l) => (
            <option key={l.id} value={l.id}>{l.name}</option>
          ))}
        </select>
        <select
          value={zoneId}
          onChange={(e) => setZoneId(e.target.value)}
          disabled={!locationId}
          className="border rounded px-2 py-1 disabled:opacity-50"
          aria-label="Filter by zone"
        >
          <option value="">All zones</option>
          {zones.map((z) => (
            <option key={z.id} value={z.id}>{z.name}</option>
          ))}
        </select>
        <span className="text-xs text-slate-400">Refreshes every 5 s</span>
      </div>

      {error && <p className="text-red-500 text-xs">{error}</p>}

      {loading ? (
        <p className="text-slate-400">Loading…</p>
      ) : alerts.length === 0 ? (
        <p className="text-slate-400">No active alerts.</p>
      ) : (
        <ul className="divide-y border rounded">
          {alerts.map((a) => (
            <li key={a.id} className="p-2 flex flex-wrap items-center gap-2">
              <span className={`px-2 py-0.5 rounded text-xs font-medium ${SEVERITY_STYLES[a.severity]}`}>
                {a.severity}
              </span>
              <span className="font-medium">{a.message}</span>
              <span className="font-mono text-xs text-slate-500">{a.event_type}</span>
              <span className="flex-1" />
              <span className="text-xs text-slate-500">{placeOf(a)}</span>
              <span className="text-xs text-slate-400">{new Date(a.created_at).toLocaleTimeString()}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}