import { BrowserRouter, Routes, Route } from "react-router-dom";
import AppLayout from "./components/AppLayout";
import DashboardPage from "./pages/DashboardPage";

function HomePage() {
  return (
    <div className="text-center py-20">
      <h1 className="text-3xl font-bold text-emerald-600 mb-4">Smart Greenhouse</h1>
      <p className="text-slate-500">Monitor and control your greenhouse environment.</p>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AppLayout />}>
          <Route index element={<HomePage />} />
          <Route path="dashboard" element={<DashboardPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}