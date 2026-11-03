const STATE_STYLES: Record<string, string> = {
  idle: "bg-slate-100 text-slate-700",
  running: "bg-emerald-100 text-emerald-800",
  error: "bg-red-100 text-red-800",
  maintenance: "bg-amber-100 text-amber-800",
  off: "bg-slate-100 text-slate-500",
};

export default function ActuatorStateBadge({
  state,
  allowedCommands,
}: {
  state: string;
  allowedCommands: string[];
}) {
  const style = STATE_STYLES[state] ?? "bg-slate-100 text-slate-700";
  const title =
    allowedCommands.length > 0
      ? `Available: ${allowedCommands.join(", ")}`
      : "No actions available";

  return (
    <span
      title={title}
      className={`text-xs px-2 py-0.5 rounded-full font-medium ${style}`}
    >
      {state}
    </span>
  );
}