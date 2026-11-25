import { useMemo, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/Button";
import type { NavItem } from "@/components/layout/nav";
import { useAuth } from "@/lib/auth/AuthProvider";
import { hasPermission, hasRole, ROLE_LABELS } from "@/lib/permissions";

interface ShellLayoutProps {
  brand: string;
  items: NavItem[];
}

function navLinkClass(isActive: boolean): string {
  return `block rounded-md px-3 py-2 text-sm font-medium transition ${
    isActive
      ? "bg-slate-900 text-white"
      : "text-slate-700 hover:bg-slate-100 hover:text-slate-900"
  }`;
}

export function ShellLayout({ brand, items }: ShellLayoutProps) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);

  const visibleItems = useMemo(() => {
    return items.filter((item) => {
      if (item.roles && !hasRole(user, item.roles)) return false;
      if (item.permission && !hasPermission(user, item.permission)) return false;
      return true;
    });
  }, [items, user]);

  const sections = useMemo(() => {
    const map = new Map<string, NavItem[]>();
    for (const item of visibleItems) {
      const section = item.section || "Menú";
      const existing = map.get(section) || [];
      existing.push(item);
      map.set(section, existing);
    }
    return Array.from(map.entries());
  }, [visibleItems]);

  const handleLogout = async () => {
    setLoggingOut(true);
    try {
      await logout();
      navigate("/login", { replace: true });
    } finally {
      setLoggingOut(false);
    }
  };

  const navContent = (
    <div className="flex h-full flex-col">
      <div className="border-b border-slate-200 px-4 py-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {brand}
        </p>
        <p className="mt-1 text-sm font-semibold text-slate-900">Licitaciones AI</p>
      </div>
      <nav className="flex-1 space-y-5 overflow-y-auto px-3 py-4">
        {sections.map(([section, sectionItems]) => (
          <div key={section}>
            <p className="px-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
              {section}
            </p>
            <div className="mt-2 space-y-1">
              {sectionItems.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === "/app" || item.to === "/platform"}
                  className={({ isActive }) => navLinkClass(isActive)}
                  onClick={() => setMobileOpen(false)}
                >
                  {item.label}
                </NavLink>
              ))}
            </div>
          </div>
        ))}
      </nav>
      <div className="border-t border-slate-200 p-4">
        <div className="mb-3 rounded-md bg-slate-50 p-3">
          <p className="truncate text-sm font-medium text-slate-900">
            {user ? `${user.first_name} ${user.last_name}` : "Usuario desconocido"}
          </p>
          <p className="truncate text-xs text-slate-500">{user?.email}</p>
          <p className="mt-1 text-xs text-slate-500">
            {user ? ROLE_LABELS[user.role] : ""}
            {user?.company?.display_name ? ` · ${user.company.display_name}` : ""}
          </p>
        </div>
        <Button
          variant="secondary"
          className="w-full"
          onClick={handleLogout}
          loading={loggingOut}
        >
          Cerrar sesión
        </Button>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-slate-50 lg:flex">
      <aside className="hidden w-64 shrink-0 border-r border-slate-200 bg-white lg:block">
        {navContent}
      </aside>

      {mobileOpen ? (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div
            className="absolute inset-0 bg-slate-900/40"
            onClick={() => setMobileOpen(false)}
          />
          <aside className="absolute inset-y-0 left-0 w-72 max-w-[85vw] bg-white shadow-xl">
            {navContent}
          </aside>
        </div>
      ) : null}

      <div className="min-w-0 flex-1">
        <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur">
          <div className="flex items-center justify-between px-4 py-3 sm:px-6">
            <div className="flex items-center gap-3">
              <button
                type="button"
                className="rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-700 lg:hidden"
                onClick={() => setMobileOpen(true)}
                aria-label="Abrir menú de navegación"
              >
                Menú
              </button>
              <div>
                <p className="text-sm font-semibold text-slate-900">{brand}</p>
                <p className="text-xs text-slate-500">
                  {user ? ROLE_LABELS[user.role] : ""}
                </p>
              </div>
            </div>
            <div className="hidden text-right sm:block">
              <p className="text-sm font-medium text-slate-900">
                {user ? `${user.first_name} ${user.last_name}` : ""}
              </p>
              <p className="text-xs text-slate-500">{user?.email}</p>
            </div>
          </div>
        </header>
        <main className="px-4 py-6 sm:px-6">
          <div className="mx-auto max-w-7xl">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
