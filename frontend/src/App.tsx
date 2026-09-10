import { Routes, Route } from "react-router-dom";
import Landing from "@/pages/Landing";
import Login from "@/pages/Login";
import OfficerDashboard from "@/pages/OfficerDashboard";
import PersonnelDashboard from "@/pages/PersonnelDashboard";
import PersonnelProfile from "@/pages/PersonnelProfile";
import Analysis from "@/pages/Analysis";
import Interventions from "@/pages/Interventions";
import Insights from "@/pages/Insights";
import Ethics from "@/pages/Ethics";
import AppShell from "@/components/AppShell";

// One <Route> per page in src/pages; BrowserRouter already wraps this in main.tsx.
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route element={<AppShell />}>
        <Route path="/officer" element={<OfficerDashboard />} />
        <Route path="/personnel" element={<PersonnelDashboard />} />
        <Route path="/personnel/:personnelId" element={<PersonnelProfile />} />
        <Route path="/analysis" element={<Analysis />} />
        <Route path="/interventions" element={<Interventions />} />
        <Route path="/insights" element={<Insights />} />
        <Route path="/ethics" element={<Ethics />} />
      </Route>
    </Routes>
  );
}
