import type { DemoPersonnel } from "@/lib/types";

export type DemoRole = "personnel" | "welfare-officer";

export const ROLE_LABELS: Record<DemoRole, string> = {
  personnel: "Personnel",
  "welfare-officer": "Welfare Officer",
};

export function getDemoRole(): DemoRole | null {
  const role = sessionStorage.getItem("manobal-demo-role");
  return role === "personnel" || role === "welfare-officer" ? role : null;
}

export function setDemoRole(role: DemoRole) {
  sessionStorage.setItem("manobal-demo-role", role);
}

export function clearDemoRole() {
  sessionStorage.removeItem("manobal-demo-role");
}

export function latestDemoHistory(profile: DemoPersonnel) {
  return profile.history[profile.history.length - 1];
}

export function riskTone(band: string) {
  return band.toLowerCase() === "high" ? "danger" : band.toLowerCase() === "moderate" ? "watch" : "safe";
}

export function formatPercent(value: number) {
  return `${Math.round(value * 100)}%`;
}

export function displayFeature(feature: string) {
  return feature.replaceAll("__", " · ").replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}