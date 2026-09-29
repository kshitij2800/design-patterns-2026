import { useState } from "react";
import SensorList from "../features/sensors/SensorList";
import DeviceList from "../features/devices/DeviceList";
import LocationConfigWizard from "../components/config/LocationConfigWizard";

const placeholders = [
  { id: "automation", label: "Automation" },
  { id: "overview", label: "Overview" },
  { id: "controls", label: "Controls" },
  { id: "events", label: "Events" },
];

export default function DashboardPage() {
  const [refreshKey, setRefreshKey] = useState(0);
  const bump = () => setRefreshKey((k) => k + 1);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div id="sensors" className="bg-white rounded-xl border border-slate-200 p-6">
        <h2 className="text-sm font-medium text-slate-500 mb-4">Sensors</h2>
        <SensorList />
      </div>

      <div id="devices" className="bg-white rounded-xl border border-slate-200 p-6">
        <h2 className="text-sm font-medium text-slate-500 mb-4">Devices</h2>
        <DeviceList refreshKey={refreshKey} onChanged={bump} />
      </div>

      <div id="configuration" className="bg-white rounded-xl border border-slate-200 p-6 md:col-span-2">
        <h2 className="text-sm font-medium text-slate-500 mb-4">Configuration</h2>
        <LocationConfigWizard refreshKey={refreshKey} onChanged={bump} />
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