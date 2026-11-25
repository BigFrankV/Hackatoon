import { Navigate } from "react-router-dom";

import { ShellLayout } from "@/components/layout/ShellLayout";
import { platformNavItems } from "@/components/layout/nav";
import { useAuth } from "@/lib/auth/AuthProvider";

export function PlatformLayout() {
  const { user } = useAuth();
  if (!user) return null;
  if (user.role !== "super_admin") {
    return <Navigate to="/app" replace />;
  }
  return <ShellLayout brand="Consola de la plataforma" items={platformNavItems} />;
}
