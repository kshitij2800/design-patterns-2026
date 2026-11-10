import { useEffect, useState } from "react";
import { fetchExecutions, type ExecutionDto } from "../../services/api";

export default function ExecutionLog() {
  const [rows, setRows] = useState<ExecutionDto[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      setLoading(true);
      setError(null);
      setRows(await fetchExecutions(20));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load execution log.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  return (
    <div className="space-y-2 text-sm">
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs text-slate-400">
          Any command succeeds until the actuator has been running for 30 minutes. A success
          row has an empty message and policy <code>logging</code>; a blocked row shows
          "Max run time exceeded" with policies <code>maxRunTime, logging</code>.
        </p>
        <button onClick={load} disabled={loading} className="px-3 py-1.5 border rounded hover:bg-slate-50 disabled:opacity-50 text-xs">
          {loading ? "Loading…" : "Refresh"}
        </button>
      </div>
      {error && <p className="text-red-500 text-xs">{error}</p>}
      {rows.length === 0 && !loading ? (
        <p className="text-slate-400">No executions yet.</p>
      ) : (
        <table className="w-full text-xs border-collapse">
          <thead>
            <tr className="text-left text-slate-500 border-b">
              <th className="py-1 pr-2">Time</th>
              <th className="py-1 pr-2">Device</th>
              <th className="py-1 pr-2">Result</th>
              <th className="py-1 pr-2">Policies</th>
              <th className="py-1 pr-2">Message</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className="border-b last:border-0">
                <td className="py-1 pr-2">{new Date(r.created_at).toLocaleTimeString()}</td>
                <td className="py-1 pr-2 font-mono">{r.device_id.slice(0, 8)}</td>
                <td className="py-1 pr-2">
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${r.success ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"}`}>
                    {r.success ? "success" : "blocked"}
                  </span>
                </td>
                <td className="py-1 pr-2">{r.policy_applied.join(", ")}</td>
                <td className="py-1 pr-2 text-slate-500">{r.message ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}