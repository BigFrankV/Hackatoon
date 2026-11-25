import { ShellLayout } from "@/components/layout/ShellLayout";
import { adminNavItems, platformNavItems, userNavItems } from "@/components/layout/nav";
import { useAuth } from "@/lib/auth/AuthProvider";

export function AppLayout() {
  const { user } = useAuth();

  if (!user) return null;

  if (user.role === "super_admin") {
    return <ShellLayout brand="Consola de la plataforma" items={platformNavItems} />;
  }

  const items = user.role === "admin" ? adminNavItems : userNavItems;
  const brand = user.role === "admin" ? "Consola de administración" : "Espacio de trabajo";

  return <ShellLayout brand={brand} items={items} />;
}
