import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { getAuthData } from "@/lib/auth";
import type { UserRole } from "@/lib/types";

const HOME_PATHS: Record<UserRole, string> = {
  PERSONNEL: "/personnel",
  WELFARE_OFFICER: "/officer",
  COMMANDER: "/command",
};

interface RequireRoleProps {
  roles: UserRole[];
  children: ReactNode;
}

export default function RequireRole({ roles, children }: RequireRoleProps) {
  const location = useLocation();
  const auth = getAuthData();

  if (!auth) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  if (!roles.includes(auth.role as UserRole)) {
    return <Navigate to={HOME_PATHS[auth.role as UserRole] ?? "/"} replace />;
  }

  return <>{children}</>;
}