import { useEffect, useState } from "react";
import { fetchSensors, createSensor, type SensorDto } from "../../services/api";
import SensorCard from "./SensorCard";

export default function SensorList() {
  const [sensors, setSensors] = useState<SensorDto[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      setLoading(true);
      setError(null);
      setSensors(await fetchSensors());
    } catch {
      setError("Could not load sensors.");
    } finally {
      setLoading(false);
    }
  }

  async function add(type: string) {
    try {
      setError(null);
      await createSensor(type);
      await load();
    } catch {
      setError(`Could not create ${type} sensor.`);
    }
  }

  useEffect(() => { load(); }, []);

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <button
          onClick={() => add("moisture")}
          className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 text-sm"
        >
          + Moisture Sensor
        </button>
        <button
          onClick={() => add("light")}
          className="px-4 py-2 bg-yellow-500 text-white rounded hover:bg-yellow-600 text-sm"
        >
          + Light Sensor
        </button>
      </div>

      {loading && <p className="text-gray-500 text-sm">Loading sensors…</p>}
      {error && <p className="text-red-500 text-sm">{error}</p>}
      {!loading && !error && sensors.length === 0 && (
        <p className="text-gray-400 text-sm">No sensors yet. Add one above.</p>
      )}

      {sensors.map((s) => (
        <SensorCard key={s.id} sensor={s} />
      ))}
    </div>
  );
}