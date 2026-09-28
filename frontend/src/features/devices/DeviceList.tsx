import { useEffect, useState } from "react";
import {
  fetchDevices,
  provisionDeviceFamily,
  type DeviceDto,
  type DeviceFamily,
} from "../../services/api";
import DeviceFamilySwitcher from "./DeviceFamilySwitcher";

export default function DeviceList() {
  const [family, setFamily] = useState<DeviceFamily>("simulation");
  const [devices, setDevices] = useState<DeviceDto[]>([]);
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

  async function provision() {
    try {
      setError(null);
      await provisionDeviceFamily(family);
      await load(family);
    } catch {
      setError(`Could not provision ${family} kit.`);
    }
  }

  function handleFamilySelect(f: DeviceFamily) {
    setFamily(f);
    load(f);
  }

  useEffect(() => { load(family); }, []);

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
        </div>
      ))}
    </div>
  );
}