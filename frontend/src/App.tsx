import { Routes, Route, Navigate } from "react-router-dom";
import Landing from "@/pages/Landing";
import WorkspaceSelect from "@/pages/WorkspaceSelect";
import RoleLogin from "@/pages/RoleLogin";
import OfficerDashboard from "@/pages/OfficerDashboard";
import PersonnelDashboard from "@/pages/PersonnelDashboard";
import CommanderWorkspace from "@/pages/CommanderWorkspace";
import Analysis from "@/pages/Analysis";
import Interventions from "@/pages/Interventions";
import Ethics from "@/pages/Ethics";
import AppShell from "@/components/AppShell";
import RequireRole from "@/components/RequireRole";

// One <Route> per page in src/pages; BrowserRouter already wraps this in main.tsx.
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<WorkspaceSelect />} />
      <Route path="/login/:workspace" element={<RoleLogin />} />
      <Route element={<AppShell />}>
        <Route path="/officer" element={<RequireRole roles={["WELFARE_OFFICER"]}><OfficerDashboard /></RequireRole>} />
        <Route path="/personnel" element={<RequireRole roles={["PERSONNEL", "WELFARE_OFFICER"]}><PersonnelDashboard /></RequireRole>} />
        <Route path="/personnel/:personnelId" element={<RequireRole roles={["PERSONNEL", "WELFARE_OFFICER"]}><PersonnelDashboard /></RequireRole>} />
        <Route path="/command" element={<RequireRole roles={["COMMANDER"]}><CommanderWorkspace /></RequireRole>} />
        <Route path="/analysis" element={<RequireRole roles={["PERSONNEL", "WELFARE_OFFICER", "COMMANDER"]}><Analysis /></RequireRole>} />
        <Route path="/interventions" element={<RequireRole roles={["PERSONNEL", "WELFARE_OFFICER"]}><Interventions /></RequireRole>} />
        <Route path="/ethics" element={<RequireRole roles={["PERSONNEL", "WELFARE_OFFICER", "COMMANDER"]}><Ethics /></RequireRole>} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}