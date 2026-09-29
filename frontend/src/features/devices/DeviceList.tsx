import { useEffect, useState } from "react";
import {
  assignDeviceZone,
  fetchDevices,
  fetchLocationConfig,
  fetchLocations,
  provisionDeviceFamily,
  type DeviceDto,
  type DeviceFamily,
} from "../../services/api";
import DeviceFamilySwitcher from "./DeviceFamilySwitcher";

type ZoneGroup = {
  locationId: string;
  locationName: string;
  zones: { id: string; label: string }[];
};

interface Props {
  refreshKey: number;
  onChanged: () => void;
}

export default function DeviceList({ refreshKey, onChanged }: Props) {
  const [family, setFamily] = useState<DeviceFamily>("simulation");
  const [devices, setDevices] = useState<DeviceDto[]>([]);
  const [zoneGroups, setZoneGroups] = useState<ZoneGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load(f: DeviceFamily) {
    try {
      setLoading(true);
      setError(null);
      setDevices(await fetchDevices({ family: f }));
    } catch {
      setError("Could not load devices.");
    } finally {
      setLoading(false);
    }
  }

  async function loadZoneGroups() {
    try {
      const locations = await fetchLocations();
      const configs = await Promise.all(locations.map((l) => fetchLocationConfig(l.id)));
      setZoneGroups(
        configs.map((c) => ({
          locationId: c.location.id,
          locationName: c.location.name,
          zones: c.zones.map((z) => ({ id: z.id, label: `${c.location.name} — ${z.name}` })),
        }))
      );
    } catch {
      setError("Could not load zones.");
    }
  }

  async function provision() {
    try {
      setError(null);
      await provisionDeviceFamily(family);
      await load(family);
    } catch {
      setError(`Could not provision ${family} kit.`);
    }
  }

  async function handleAssign(deviceId: string, zoneId: string) {
    try {
      setError(null);
      await assignDeviceZone(deviceId, zoneId || null);
      onChanged();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not assign zone.");
    }
  }

  function handleFamilySelect(f: DeviceFamily) {
    setFamily(f);
    load(f);
  }

  useEffect(() => {
    load(family);
    loadZoneGroups();
  }, [refreshKey]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <DeviceFamilySwitcher selected={family} onSelect={handleFamilySelect} />
        <button
          onClick={provision}
          className="px-4 py-2 bg-emerald-600 text-white rounded hover:bg-emerald-700 text-sm"
        >
          + Provision {family} kit
        </button>
      </div>

      {loading && <p className="text-gray-500 text-sm">Loading devices…</p>}
      {error && <p className="text-red-500 text-sm">{error}</p>}
      {!loading && !error && devices.length === 0 && (
        <p className="text-gray-400 text-sm">
          No {family} devices yet. Provision a kit above.
        </p>
      )}

      {devices.map((d) => (
        <div key={d.id} className="border rounded p-3 text-sm space-y-1">
          <div className="font-medium">{d.display_name}</div>
          <div className="flex gap-2">
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
              d.role === "sensor"
                ? "bg-blue-100 text-blue-700"
                : "bg-green-100 text-green-700"
            }`}>
              {d.role}
            </span>
            <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-slate-100 text-slate-600">
              {d.device_family}
            </span>
          </div>
          <div className="text-gray-500">{d.device_type}</div>
          <div className="text-gray-400 text-xs font-mono">
            {JSON.stringify(d.default_config)}
          </div>
          <label className="flex items-center gap-2 pt-1">
            <span className="text-xs text-gray-500">Zone</span>
            <select
              className="border border-slate-300 rounded px-2 py-1 text-xs flex-1"
              value={d.zone_id ?? ""}
              onChange={(e) => handleAssign(d.id, e.target.value)}
            >
              <option value="">Unassigned</option>
              {zoneGroups.map((g) => (
                <optgroup key={g.locationId} label={g.locationName}>
                  {g.zones.map((z) => (
                    <option key={z.id} value={z.id}>
                      {z.label}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
          </label>
        </div>
      ))}
    </div>
  );
}