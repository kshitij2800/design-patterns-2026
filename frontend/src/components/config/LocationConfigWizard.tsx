import { useEffect, useState } from "react";
import {
  addZone,
  createLocationConfig,
  deleteLocation,
  deleteZone,
  fetchLocationConfig,
  fetchLocations,
  fetchZoneDevices,
  updateZone,
  type DeviceDto,
  type LocationConfigDto,
  type LocationSummaryDto,
  type ZoneDto,
  type ZoneInput,
} from "../../services/api";

type ZoneForm = { name: string; low: string; high: string; watering: string };

interface Props {
  refreshKey: number;
  onChanged: () => void;
}

const emptyZone = (): ZoneForm => ({ name: "", low: "0.2", high: "0.45", watering: "" });

const inputCls = "border border-slate-300 rounded px-2 py-1 text-sm w-full";
const btn = "px-3 py-1.5 rounded text-sm";

function toInput(f: ZoneForm): ZoneInput {
  return {
    name: f.name.trim(),
    moisture_threshold_low: Number(f.low),
    moisture_threshold_high: Number(f.high),
    schedule: f.watering ? { watering: f.watering } : {},
  };
}

function validateZone(f: ZoneForm): string | null {
  if (!f.name.trim()) return "Zone name is required.";
  const low = Number(f.low);
  const high = Number(f.high);
  if (f.low === "" || f.high === "" || Number.isNaN(low) || Number.isNaN(high)) {
    return "Thresholds must be numbers.";
  }
  if (low < 0 || low > 1 || high < 0 || high > 1) return "Thresholds must be between 0 and 1.";
  if (low >= high) return "Low threshold must be less than high threshold.";
  return null;
}

function ZoneFields({ value, onChange }: { value: ZoneForm; onChange: (v: ZoneForm) => void }) {
  const problem = validateZone(value);
  return (
    <div className="space-y-1">
      <div className="grid grid-cols-2 gap-2">
        <input
          className={inputCls}
          placeholder="Zone name"
          value={value.name}
          onChange={(e) => onChange({ ...value, name: e.target.value })}
        />
        <input
          className={inputCls}
          type="time"
          title="Watering time (optional)"
          value={value.watering}
          onChange={(e) => onChange({ ...value, watering: e.target.value })}
        />
        <input
          className={inputCls}
          type="number"
          step="0.01"
          min="0"
          max="1"
          placeholder="Low VWC (0–1)"
          value={value.low}
          onChange={(e) => onChange({ ...value, low: e.target.value })}
        />
        <input
          className={inputCls}
          type="number"
          step="0.01"
          min="0"
          max="1"
          placeholder="High VWC (0–1)"
          value={value.high}
          onChange={(e) => onChange({ ...value, high: e.target.value })}
        />
      </div>
      {problem && <p className="text-xs text-amber-600">{problem}</p>}
    </div>
  );
}

export default function LocationConfigWizard({ refreshKey, onChanged }: Props) {
  const [locations, setLocations] = useState<LocationSummaryDto[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [config, setConfig] = useState<LocationConfigDto | null>(null);
  const [zoneDevices, setZoneDevices] = useState<Record<string, DeviceDto[]>>({});
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [newName, setNewName] = useState("");
  const [newZones, setNewZones] = useState<ZoneForm[]>([emptyZone()]);
  const [addForm, setAddForm] = useState<ZoneForm>(emptyZone());
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<ZoneForm>(emptyZone());

  function showError(e: unknown) {
    setError(e instanceof Error ? e.message : "Request failed.");
  }

  async function run(action: () => Promise<void>, message: string) {
    setError(null);
    setSuccess(null);
    try {
      await action();
      setSuccess(message);
    } catch (e) {
      showError(e);
    }
  }

  useEffect(() => {
    fetchLocations().then(setLocations).catch(showError);
  }, [refreshKey]);

  useEffect(() => {
    if (!selectedId) {
      setConfig(null);
      setZoneDevices({});
      return;
    }
    const id = selectedId;
    (async () => {
      const cfg = await fetchLocationConfig(id);
      setConfig(cfg);
      const entries = await Promise.all(
        cfg.zones.map(async (z) => [z.id, await fetchZoneDevices(id, z.id)] as const)
      );
      setZoneDevices(Object.fromEntries(entries));
    })().catch(showError);
  }, [selectedId, refreshKey]);

  async function handleCreate() {
    if (!newName.trim()) {
      setError("Location name is required.");
      return;
    }
    const problem = newZones.map(validateZone).find((p) => p !== null);
    if (problem) {
      setError(problem);
      return;
    }
    await run(async () => {
      const cfg = await createLocationConfig(newName.trim(), newZones.map(toInput));
      setNewName("");
      setNewZones([emptyZone()]);
      setSelectedId(cfg.location.id);
      onChanged();
    }, "Location created.");
  }

  async function handleDeleteLocation(loc: LocationSummaryDto) {
    if (!window.confirm(`Delete location "${loc.name}" and all its zones?`)) return;
    await run(async () => {
      await deleteLocation(loc.id);
      if (selectedId === loc.id) setSelectedId(null);
      onChanged();
    }, "Location deleted.");
  }

  async function handleAddZone() {
    if (!selectedId) return;
    const problem = validateZone(addForm);
    if (problem) {
      setError(problem);
      return;
    }
    const id = selectedId;
    await run(async () => {
      await addZone(id, toInput(addForm));
      setAddForm(emptyZone());
      onChanged();
    }, "Zone added.");
  }

  function startEdit(z: ZoneDto) {
    setEditingId(z.id);
    setEditForm({
      name: z.name,
      low: String(z.moisture_threshold_low),
      high: String(z.moisture_threshold_high),
      watering: typeof z.schedule.watering === "string" ? z.schedule.watering : "",
    });
  }

  async function handleSaveEdit() {
    if (!selectedId || !editingId) return;
    const problem = validateZone(editForm);
    if (problem) {
      setError(problem);
      return;
    }
    const locId = selectedId;
    const zoneId = editingId;
    await run(async () => {
      await updateZone(locId, zoneId, toInput(editForm));
      setEditingId(null);
      onChanged();
    }, "Zone updated.");
  }

  async function handleDeleteZone(z: ZoneDto) {
    if (!selectedId) return;
    if (!window.confirm(`Delete zone "${z.name}"? Its devices become unassigned.`)) return;
    const id = selectedId;
    await run(async () => {
      await deleteZone(id, z.id);
      onChanged();
    }, "Zone deleted.");
  }

  return (
    <div className="space-y-6 text-sm">
      {error && (
        <div className="rounded border border-red-200 bg-red-50 text-red-700 px-3 py-2">{error}</div>
      )}
      {success && (
        <div className="rounded border border-emerald-200 bg-emerald-50 text-emerald-700 px-3 py-2">
          {success}
        </div>
      )}

      <section className="space-y-2">
        <h3 className="font-medium text-slate-700">Saved locations (newest first)</h3>
        {locations.length === 0 && (
          <p className="text-slate-400">No locations yet. Create one below.</p>
        )}
        <ul className="space-y-1">
          {locations.map((loc) => (
            <li
              key={loc.id}
              className={`flex items-center justify-between rounded border px-3 py-2 ${
                loc.id === selectedId ? "border-emerald-500 bg-emerald-50" : "border-slate-200"
              }`}
            >
              <button className="text-left font-medium" onClick={() => setSelectedId(loc.id)}>
                {loc.name}
              </button>
              <button
                className="text-red-600 hover:underline text-xs"
                onClick={() => handleDeleteLocation(loc)}
              >
                Delete
              </button>
            </li>
          ))}
        </ul>
      </section>

      {config && (
        <section className="space-y-3 rounded border border-slate-200 p-3">
          <div>
            <h3 className="font-medium text-slate-700">{config.location.name}</h3>
            <p className="text-xs text-slate-400 font-mono">Location id: {config.location.id}</p>
          </div>

          {config.zones.map((z) => (
            <div key={z.id} className="rounded border border-slate-200 p-2 space-y-1">
              {editingId === z.id ? (
                <>
                  <ZoneFields value={editForm} onChange={setEditForm} />
                  <div className="flex gap-2">
                    <button
                      className={`${btn} bg-emerald-600 text-white hover:bg-emerald-700`}
                      onClick={handleSaveEdit}
                    >
                      Save
                    </button>
                    <button
                      className={`${btn} bg-slate-100 hover:bg-slate-200`}
                      onClick={() => setEditingId(null)}
                    >
                      Cancel
                    </button>
                  </div>
                </>
              ) : (
                <>
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{z.name}</span>
                    <div className="flex gap-3 text-xs">
                      <button className="text-slate-600 hover:underline" onClick={() => startEdit(z)}>
                        Edit
                      </button>
                      <button className="text-red-600 hover:underline" onClick={() => handleDeleteZone(z)}>
                        Delete
                      </button>
                    </div>
                  </div>
                  <div className="text-slate-500">
                    VWC {z.moisture_threshold_low} – {z.moisture_threshold_high}
                    {typeof z.schedule.watering === "string" ? ` · watering ${z.schedule.watering}` : ""}
                  </div>
                  <div className="text-xs text-slate-400">
                    Devices:{" "}
                    {(zoneDevices[z.id] ?? []).map((d) => d.display_name).join(", ") || "none"}
                  </div>
                </>
              )}
            </div>
          ))}

          <div className="space-y-2 border-t border-slate-100 pt-3">
            <h4 className="font-medium text-slate-600">Add zone</h4>
            <ZoneFields value={addForm} onChange={setAddForm} />
            <button
              className={`${btn} bg-emerald-600 text-white hover:bg-emerald-700`}
              onClick={handleAddZone}
            >
              + Add zone
            </button>
          </div>
        </section>
      )}

      <section className="space-y-2 rounded border border-dashed border-slate-300 p-3">
        <h3 className="font-medium text-slate-700">New location</h3>
        <input
          className={inputCls}
          placeholder="Location name"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
        />
        {newZones.map((z, i) => (
          <div key={i} className="rounded border border-slate-200 p-2 space-y-1">
            <ZoneFields
              value={z}
              onChange={(v) => setNewZones(newZones.map((old, j) => (j === i ? v : old)))}
            />
            {newZones.length > 1 && (
              <button
                className="text-xs text-red-600 hover:underline"
                onClick={() => setNewZones(newZones.filter((_, j) => j !== i))}
              >
                Remove zone
              </button>
            )}
          </div>
        ))}
        <div className="flex gap-2">
          <button
            className={`${btn} bg-slate-100 hover:bg-slate-200`}
            onClick={() => setNewZones([...newZones, emptyZone()])}
          >
            + Another zone
          </button>
          <button
            className={`${btn} bg-emerald-600 text-white hover:bg-emerald-700`}
            onClick={handleCreate}
          >
            Create location
          </button>
        </div>
      </section>
    </div>
  );
}