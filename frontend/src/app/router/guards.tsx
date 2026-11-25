import type { PropsWithChildren } from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";

import { PageLoader } from "@/components/ui/PageLoader";
import { useAuth } from "@/lib/auth/AuthProvider";
import { hasPermission, hasRole } from "@/lib/permissions";
import type { UserRole } from "@/types";

export function RequireAuth() {
  const { status } = useAuth();
  const location = useLocation();

  if (status === "loading") {
    return <PageLoader label="Verificando sesión..." />;
  }

  if (status === "unauthenticated") {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return <Outlet />;
}

export function RequireRoles({ roles }: { roles: UserRole[] }) {
  const { user } = useAuth();
  if (!hasRole(user, roles)) {
    return <Navigate to="/forbidden" replace />;
  }
  return <Outlet />;
}

export function RequirePermission({ permission }: { permission: string }) {
  const { user } = useAuth();
  if (!hasPermission(user, permission)) {
    return <Navigate to="/forbidden" replace />;
  }
  return <Outlet />;
}

export function PublicOnly({ children }: PropsWithChildren) {
  const { status, user } = useAuth();
  if (status === "loading") {
    return <PageLoader label="Verificando sesión..." />;
  }
  if (status === "authenticated" && user) {
    const target = user.role === "super_admin" ? "/platform" : "/app";
    return <Navigate to={target} replace />;
  }
  return <>{children}</>;
}
