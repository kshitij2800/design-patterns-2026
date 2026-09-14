import SensorList from "../features/sensors/SensorList";

const placeholders = [
  { id: "config", label: "Configuration" },
  { id: "automation", label: "Automation" },
  { id: "overview", label: "Overview" },
  { id: "controls", label: "Controls" },
  { id: "events", label: "Events" },
];

export default function DashboardPage() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div id="sensors" className="bg-white rounded-xl border border-slate-200 p-6">
        <h2 className="text-sm font-medium text-slate-500 mb-4">Sensors</h2>
        <SensorList />
      </div>

      {placeholders.map((p) => (
        <div key={p.id} id={p.id} className="bg-white rounded-xl border border-slate-200 p-6">
          <h2 className="text-sm font-medium text-slate-500 mb-2">{p.label}</h2>
          <p className="text-slate-400 text-sm">Coming in a later phase</p>
        </div>
      ))}
    </div>
  );
}