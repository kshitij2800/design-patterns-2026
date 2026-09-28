import type { DeviceFamily } from "../../services/api";

interface Props {
  selected: DeviceFamily;
  onSelect: (family: DeviceFamily) => void;
}

const FAMILIES: { key: DeviceFamily; label: string }[] = [
  { key: "simulation", label: "Simulation" },
  { key: "edge", label: "Edge" },
];

export default function DeviceFamilySwitcher({ selected, onSelect }: Props) {
  return (
    <div className="flex gap-2">
      {FAMILIES.map((f) => (
        <button
          key={f.key}
          onClick={() => onSelect(f.key)}
          className={`px-3 py-1 rounded text-sm font-medium border transition-colors ${
            selected === f.key
              ? "bg-emerald-600 text-white border-emerald-600"
              : "bg-white text-slate-600 border-slate-300 hover:border-emerald-400"
          }`}
        >
          {f.label}
        </button>
      ))}
    </div>
  );
}