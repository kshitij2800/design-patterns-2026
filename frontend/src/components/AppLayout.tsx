import { NavLink, Outlet } from "react-router-dom";
import HealthStatus from "./HealthStatus";

export default function AppLayout() {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between">
        <span className="text-lg font-semibold text-emerald-700">
          🌱 Smart Greenhouse
        </span>
        <nav className="flex items-center gap-6">
          <NavLink to="/" className={({ isActive }) => isActive ? "text-emerald-600 font-medium" : "text-slate-500 hover:text-slate-800"}>
            Home
          </NavLink>
          <NavLink to="/dashboard" className={({ isActive }) => isActive ? "text-emerald-600 font-medium" : "text-slate-500 hover:text-slate-800"}>
            Dashboard
          </NavLink>
          <HealthStatus />
        </nav>
      </header>
      <main className="p-6">
        <Outlet />
      </main>
    </div>
  );
}