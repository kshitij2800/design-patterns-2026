import { useEffect, useState } from "react";
import ActuatorStateBadge from "../../features/devices/ActuatorStateBadge";
import {
  COMMAND_TYPES,
  fetchCommands,
  fetchDevices,
  sendCommand,
  type CommandLogDto,
  type CommandType,
  type DeviceDto,
} from "../../services/api";

// Buttons only send POST /api/commands. Enabling a button is decided by the
// backend's allowed_commands — React has no "if state == ..." rules.
export default function CommandPanel() {
  const [actuators, setActuators] = useState<DeviceDto[]>([]);
  const [history, setHistory] = useState<CommandLogDto[]>([]);
  const [levels, setLevels] = useState<Record<string, string>>({});
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function reload() {
    try {
      const [devices, rows] = await Promise.all([fetchDevices({ role: "actuator" }), fetchCommands(50)]);
      setActuators(devices);
      setHistory(rows);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load commands.");
    }
  }

  useEffect(() => { reload(); }, []);

  async function run(device: DeviceDto, commandType: CommandType) {
    const payload =
      commandType === "set_light_level" ? { level: Number(levels[device.id] ?? "1") } : {};
    try {
      setBusyId(device.id);
      setError(null);
      await sendCommand(commandType, device.id, payload); // result shows up in the history table
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not send command.");
    } finally {
      setBusyId(null);
      await reload();   // refreshed allowed_commands + history
    }
  }

  return (
    <div className="space-y-4 text-sm">
      {error && <p className="text-red-500 text-xs">{error}</p>}

      {actuators.length === 0 ? (
        <p className="text-slate-400">No actuators yet. Provision a device family first.</p>
      ) : (
        <ul className="space-y-2">
          {actuators.map((a) => (
            <li key={a.id} className="border rounded p-3 flex flex-wrap items-center gap-2">
              <span className="font-medium mr-1">{a.display_name}</span>
              {a.state && <ActuatorStateBadge state={a.state} allowedCommands={a.allowed_commands} />}
              <span className="flex-1" />
              {COMMAND_TYPES.map((c) => (
                <span key={c} className="flex items-center gap-1">
                  {c === "set_light_level" && (
                    <input
                      type="number"
                      min={0}
                      value={levels[a.id] ?? "1"}
                      onChange={(e) => setLevels({ ...levels, [a.id]: e.target.value })}
                      className="w-14 border rounded px-1 py-0.5 text-xs"
                      aria-label="Light level"
                    />
                  )}
                  <button
                    onClick={() => run(a, c)}
                    disabled={busyId === a.id || !a.allowed_commands.includes(c)}
                    className="px-2 py-1 border rounded text-xs hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    {c}
                  </button>
                </span>
              ))}
            </li>
          ))}
        </ul>
      )}

      <div>
        <h3 className="text-xs font-medium text-slate-500 mb-1">Command history</h3>
        {history.length === 0 ? (
          <p className="text-slate-400">No commands yet.</p>
        ) : (
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr className="text-left text-slate-500 border-b">
                <th className="py-1 pr-2">Time</th>
                <th className="py-1 pr-2">Device</th>
                <th className="py-1 pr-2">Command</th>
                <th className="py-1 pr-2">Payload</th>
                <th className="py-1 pr-2">Status</th>
                <th className="py-1 pr-2">Error</th>
              </tr>
            </thead>
            <tbody>
              {history.map((r) => (
                <tr key={r.id} className="border-b last:border-0">
                  <td className="py-1 pr-2">{new Date(r.created_at).toLocaleTimeString()}</td>
                  <td className="py-1 pr-2 font-mono">{r.device_id.slice(0, 8)}</td>
                  <td className="py-1 pr-2 font-mono">{r.command_type}</td>
                  <td className="py-1 pr-2 font-mono">{JSON.stringify(r.payload)}</td>
                  <td className="py-1 pr-2">{r.status}</td>
                  <td className="py-1 pr-2 text-slate-500">{r.error_message ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}